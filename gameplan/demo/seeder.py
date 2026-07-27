# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt

"""Deterministic replay engine for the Gameplan demo fixture.

The fixture is an append-only event log (``events.jsonl``): one JSON object per
line, in chronological order. :class:`Seeder` replays each event *as its actor*
through the ORM so every controller side effect (unread records, notifications,
last-post bookkeeping, counters) is produced exactly as it would be in real use.

Timestamps in the fixture are relative to the day the seed runs (the "anchor"),
so the demo always looks like it happened over the last few weeks. After each
insert we rewrite ``creation``/``modified`` to the event's virtual time.

No LLM, no network: everything the demo needs (text, images) ships in the
fixture directory.
"""

import json
import os
import re
from datetime import datetime, timedelta

import frappe
from frappe.utils import add_days, getdate, now_datetime

MAYA_EMAIL = "maya@moonhollow.studio"
DEMO_EMAIL_DOMAIN = "@moonhollow.studio"
DEMO_FILE_FOLDER = "Home/Gameplan Demo"

# "-26d 10:12" -> 26 days before the anchor at 10:12 local time
_TIME_RE = re.compile(r"^\s*([+-]?\d+)d(?:\s+(\d{1,2}):(\d{2}))?\s*$")
_PLACEHOLDER_RE = re.compile(r"\{\{(file|emoji|user):([^}]+)\}\}")

# Event fields that name a symbolic `id` declared by an earlier event, and the event
# types that id is allowed to have been declared by. Drives the static reference pass
# in Seeder.validate_events; keep it in step with the _event_* handlers.
_ID_REFERENCE_KINDS: dict[str, dict[str, set[str]]] = {
	"space": {"community": {"community"}},
	"discussion": {"space": {"space"}},
	"comment": {"on": {"discussion", "task"}},
	"react": {"on": {"discussion", "comment", "task", "page", "poll"}},
	"task": {"space": {"space"}},
	"task_update": {"on": {"task"}},
	"page": {"space": {"space"}},
	"poll": {"on": {"discussion"}},
	"vote": {"on": {"poll"}},
	"bookmark": {"on": {"discussion"}},
	"pin": {"on": {"space"}},
	"visit": {"on": {"discussion"}},
	"draft": {"space": {"space"}},
}

# Event fields holding a single user slug (declared by an earlier `user` event).
_USER_SLUG_FIELDS = ("actor", "assigned_to")

# Event fields holding the name of a file that must exist in the fixture's files/ dir.
_FILE_NAME_FIELDS = ("avatar", "cover", "logo", "image")


class Seeder:
	def __init__(self, fixture_dir: str):
		self.fixture_dir = fixture_dir
		self.files_dir = os.path.join(fixture_dir, "files")
		# The anchor is "day 0" in site time; every relative timestamp hangs off it.
		# The fixture's timeline runs until 09:00 on day 0, so anchoring to today
		# before ~10:00 (e.g. the nightly reseed) would put the freshest posts in
		# the future ("in an hour"), slide back a day in that case.
		self.anchor = getdate() if now_datetime().hour >= 10 else add_days(getdate(), -1)
		# Symbolic id -> (doctype, name) for cross-referencing events.
		self.refs: dict[str, tuple[str, str]] = {}
		self.users: dict[str, str] = {}  # slug -> email
		self.files: dict[str, str] = {}  # file name -> file_url
		self.emojis: dict[str, str] = {}  # emoji slug -> image file_url
		self.maya_last_visit: datetime | None = None
		self.counts: dict[str, int] = {}
		self._deferred_closes: dict[str, str] = {}  # discussion name -> closer email

	# ---- public entry point -------------------------------------------------

	@classmethod
	def validate_events(cls, events_path: str) -> list[str]:
		"""Report problems that would make :meth:`run` fail part-way through the log.

		:func:`gameplan.demo.demo.generate` commits a full ``clear()`` before the
		replay starts, so an event the seeder cannot handle empties the site and
		*then* raises — the delete is committed, the half-applied replay is not, and
		the site is left with no demo data at all. Everything checkable without a
		database round trip is checked here so ``generate`` can refuse before
		anything is deleted.

		That includes cross-references, which are the likeliest way to break a
		hand-edited fixture: dropping one ``space`` line leaves every discussion in it
		pointing at nothing. Every ``on`` / ``space`` / ``community`` id, every actor,
		member and assignee slug, every ``{{...}}`` placeholder and every named file
		must already be declared by an *earlier* line — the replay is chronological, so
		a reference that only resolves later fails there too.
		"""
		problems: list[str] = []
		events: list[tuple[int, dict]] = []
		with open(events_path, encoding="utf-8") as f:
			for number, line in enumerate(f, start=1):
				if not line.strip():
					continue
				try:
					events.append((number, json.loads(line)))
				except json.JSONDecodeError as error:
					problems.append(f"line {number}: invalid JSON ({error})")

		files_dir = os.path.join(os.path.dirname(events_path), "files")
		ids: dict[str, str] = {}  # symbolic id -> the event type that declared it
		user_slugs: set[str] = set()
		emoji_slugs: set[str] = set()

		for number, event in events:
			event_type = event.get("type")
			if not event_type:
				problems.append(f"line {number}: missing 'type'")
				event_type = None
			elif not hasattr(cls, f"_event_{event_type}"):
				problems.append(f"line {number}: no handler for event type {event_type!r}")
				# Nothing is known about an unhandled event's shape, so its references
				# are not worth guessing at — the missing handler is the real problem.
				event_type = None

			timestamp = event.get("t")
			if timestamp is not None and not _TIME_RE.match(timestamp):
				problems.append(f"line {number}: invalid relative time {timestamp!r}")

			if not event_type:
				continue

			problems.extend(
				cls._reference_problems(number, event, event_type, ids, user_slugs, emoji_slugs, files_dir)
			)
			# Declarations are recorded only after this event's own references have been
			# checked, so nothing can satisfy a reference to itself.
			cls._record_declarations(event, event_type, ids, user_slugs, emoji_slugs)

		return problems

	@classmethod
	def _reference_problems(
		cls,
		number: int,
		event: dict,
		event_type: str,
		ids: dict[str, str],
		user_slugs: set[str],
		emoji_slugs: set[str],
		files_dir: str,
	) -> list[str]:
		"""Every reference on one event that does not resolve against the lines above it."""
		problems = []

		for field, kinds in _ID_REFERENCE_KINDS.get(event_type, {}).items():
			target = event.get(field)
			if target is None:
				continue
			if target not in ids:
				problems.append(f"line {number}: {event_type} {field!r} references unknown id {target!r}")
			elif ids[target] not in kinds:
				problems.append(
					f"line {number}: {event_type} {field!r} references {target!r}, declared by a "
					f"{ids[target]!r} event; expected one of {sorted(kinds)}"
				)

		for slug in cls._user_slug_references(event):
			if slug not in user_slugs:
				problems.append(f"line {number}: references unknown user slug {slug!r}")

		file_names = {event.get(field) for field in _FILE_NAME_FIELDS if event.get(field)}
		for kind, key in cls._placeholders(event):
			if kind == "file":
				file_names.add(key)
			elif kind == "user" and key not in user_slugs:
				problems.append(f"line {number}: placeholder {{{{user:{key}}}}} names no user declared above")
			elif kind == "emoji" and key not in emoji_slugs:
				problems.append(
					f"line {number}: placeholder {{{{emoji:{key}}}}} names no custom emoji declared above"
				)

		for name in sorted(file_names):
			if not os.path.exists(os.path.join(files_dir, name)):
				problems.append(f"line {number}: file {name!r} is missing from {files_dir}")

		return problems

	@staticmethod
	def _record_declarations(
		event: dict,
		event_type: str,
		ids: dict[str, str],
		user_slugs: set[str],
		emoji_slugs: set[str],
	):
		symbolic_id = event.get("id")
		if symbolic_id:
			ids[symbolic_id] = event_type
		slug = event.get("slug")
		if slug and event_type == "user":
			user_slugs.add(slug)
		elif slug and event_type == "custom_emoji":
			emoji_slugs.add(slug)

	@staticmethod
	def _user_slug_references(event: dict) -> list[str]:
		"""Every user slug the event names, from whichever field carries it."""
		slugs = [event.get(field) for field in _USER_SLUG_FIELDS]
		slugs += event.get("members") or []
		changes = event.get("changes")
		if isinstance(changes, dict):
			slugs.append(changes.get("assigned_to"))
		return [slug for slug in slugs if slug]

	@staticmethod
	def _placeholders(event: dict) -> list[tuple[str, str]]:
		"""Every ``{{kind:key}}`` placeholder found in the event's string values."""
		found: list[tuple[str, str]] = []
		pending = [event]
		while pending:
			value = pending.pop()
			if isinstance(value, dict):
				pending.extend(value.values())
			elif isinstance(value, list):
				pending.extend(value)
			elif isinstance(value, str):
				found.extend(_PLACEHOLDER_RE.findall(value))
		return found

	def run(self, events_path: str):
		with open(events_path, encoding="utf-8") as f:
			events = [json.loads(line) for line in f if line.strip()]

		for event in events:
			self._replay(event)

		self._apply_deferred_closes()
		self._finalize_maya_read_state()

	# ---- dispatch -----------------------------------------------------------

	def _replay(self, event: dict):
		event_type = event["type"]
		handler = getattr(self, f"_event_{event_type}", None)
		if handler is None:
			raise ValueError(f"Unknown demo event type: {event_type!r}")

		actor = self._actor_email(event)
		ts = self._time(event.get("t"))
		# Track notifications produced by this event so we can backdate them to the
		# event's virtual time (side-effect notifications are stamped at wall clock).
		max_notification_before = self._max_notification_id()

		frappe.set_user(actor)
		try:
			handler(event, actor, ts)
		finally:
			frappe.set_user("Administrator")

		if ts is not None:
			self._backdate_new_notifications(max_notification_before, ts)
		self.counts[event_type] = self.counts.get(event_type, 0) + 1

	# ---- event handlers -----------------------------------------------------

	def _event_user(self, event, actor, ts):
		email = event["email"]
		full_name = event["full_name"]
		first, _, last = full_name.partition(" ")
		avatar = self._file_url(event["avatar"]) if event.get("avatar") else None

		frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": first,
				"last_name": last or None,
				"full_name": full_name,
				"user_type": "System User",
				"user_image": avatar,
				"enabled": 1,
				"send_welcome_email": 0,
				"roles": [{"role": event["role"]}],
			}
		).insert(ignore_permissions=True)
		self.users[event["slug"]] = email
		self.refs[event["id"]] = ("User", email)

		# The User after_insert hook auto-creates the profile; enrich it.
		profile = frappe.get_doc("GP User Profile", {"user": email})
		profile.bio = event.get("bio")
		profile.image = avatar
		if event.get("cover"):
			profile.cover_image = self._file_url(event["cover"])
		profile.save(ignore_permissions=True)
		self._backdate("User", email, ts)

	def _event_community(self, event, actor, ts):
		members = [{"user": self.users[s], "status": "Accepted"} for s in event.get("members", [])]
		team = frappe.get_doc(
			{
				"doctype": "GP Team",
				"name": event["slug"],
				"title": event["title"],
				"icon": event.get("icon"),
				"is_private": 1 if event.get("is_private") else 0,
				"image": self._file_url(event["logo"]) if event.get("logo") else None,
				"members": members,
			}
		)
		# Explicit spaces follow; skip the auto-created "General" landing space.
		team.flags.skip_general_space = True
		team.insert(ignore_permissions=True)
		self.refs[event["id"]] = ("GP Team", team.name)
		self._backdate("GP Team", team.name, ts)

	def _event_space(self, event, actor, ts):
		team = self._ref_name(event["community"])
		space = frappe.get_doc(
			{
				"doctype": "GP Project",
				"title": event["title"],
				"team": team,
				"icon": event.get("icon"),
				"description": event.get("description"),
				"is_private": 1 if event.get("is_private") else 0,
			}
		).insert(ignore_permissions=True)
		self.refs[event["id"]] = ("GP Project", space.name)
		self._backdate("GP Project", space.name, ts)

	def _event_custom_emoji(self, event, actor, ts):
		url = self._file_url(event["image"])
		emoji = frappe.get_doc(
			{
				"doctype": "GP Custom Emoji",
				"title": event["title"],
				"keywords": event.get("keywords"),
				"image": url,
			}
		).insert(ignore_permissions=True)
		self.emojis[event["slug"]] = url
		self.refs[event["id"]] = ("GP Custom Emoji", emoji.name)
		self._backdate("GP Custom Emoji", emoji.name, ts)

	def _event_discussion(self, event, actor, ts):
		space = self._ref_name(event["space"])
		doc = frappe.get_doc(
			{
				"doctype": "GP Discussion",
				"title": event["title"],
				"content": self._resolve(event["content"]),
				"project": space,
				"team": frappe.db.get_value("GP Project", space, "team"),
			}
		)
		if event.get("pinned"):
			doc.pinned_at = ts
			doc.pinned_by = actor
			doc.pin_scope = "Category"
		doc.insert(ignore_permissions=True)
		if event.get("closed"):
			# closing at insert would block the thread's own comments; close after replay
			self._deferred_closes[doc.name] = actor
		self.refs[event["id"]] = ("GP Discussion", doc.name)
		# last_post_at defaults to now() in before_insert; align it with the event.
		frappe.db.set_value(
			"GP Discussion",
			doc.name,
			{"creation": ts, "modified": ts, "last_post_at": ts},
			update_modified=False,
		)

	def _event_comment(self, event, actor, ts):
		ref_dt, ref_name = self._ref(event["on"])
		doc = frappe.get_doc(
			{
				"doctype": "GP Comment",
				"content": self._resolve(event["content"]),
				"reference_doctype": ref_dt,
				"reference_name": ref_name,
			}
		).insert(ignore_permissions=True)
		self.refs[event["id"]] = ("GP Comment", doc.name)
		self._backdate("GP Comment", doc.name, ts)
		# The comment's after_insert bumped the discussion's last_post_at/modified to
		# wall-clock via the parent save; realign both with the event time.
		if ref_dt == "GP Discussion":
			frappe.db.set_value(
				"GP Discussion",
				ref_name,
				{"last_post_at": ts, "modified": ts},
				update_modified=False,
			)

	def _event_react(self, event, actor, ts):
		parent_dt, parent_name = self._ref(event["on"])
		emoji = self._resolve(event["emoji"])
		doc = frappe.get_doc(parent_dt, parent_name)
		if not any(r.user == actor and r.emoji == emoji for r in doc.get("reactions") or []):
			doc.append("reactions", {"emoji": emoji, "user": actor})
		# Saving fires on_update -> notify_reactions, giving the author a notification.
		doc.save(ignore_permissions=True)
		# A reaction updates an existing post: move `modified` only, never `creation`.
		self._touch(parent_dt, parent_name, ts)

	def _event_task(self, event, actor, ts):
		space = self._ref_name(event["space"])
		doc = frappe.get_doc(
			{
				"doctype": "GP Task",
				"title": event["title"],
				"description": self._resolve(event.get("description", "")),
				"project": space,
				"team": frappe.db.get_value("GP Project", space, "team"),
				"status": event.get("status") or "Backlog",
				"priority": event.get("priority"),
				"assigned_to": self.users.get(event["assigned_to"]) if event.get("assigned_to") else None,
				"due_date": self._date(event.get("due")),
			}
		).insert(ignore_permissions=True)
		self.refs[event["id"]] = ("GP Task", doc.name)
		self._backdate("GP Task", doc.name, ts)

	def _event_task_update(self, event, actor, ts):
		task = frappe.get_doc(*self._ref(event["on"]))
		changes = dict(event.get("changes", {}))
		if "assigned_to" in changes and changes["assigned_to"]:
			changes["assigned_to"] = self.users.get(changes["assigned_to"], changes["assigned_to"])
		if "due" in changes:
			changes["due_date"] = self._date(changes.pop("due"))
		task.update(changes)
		if changes.get("status") == "Done":
			task.is_completed = 1
			task.completed_at = ts
			task.completed_by = actor
		task.save(ignore_permissions=True)
		self._touch("GP Task", task.name, ts)

	def _event_page(self, event, actor, ts):
		space = self._ref_name(event["space"])
		doc = frappe.get_doc(
			{
				"doctype": "GP Page",
				"title": event["title"],
				"content": self._resolve(event["content"]),
				"project": space,
				"team": frappe.db.get_value("GP Project", space, "team"),
				"user": actor,
			}
		).insert(ignore_permissions=True)
		self.refs[event["id"]] = ("GP Page", doc.name)
		self._backdate("GP Page", doc.name, ts)

	def _event_poll(self, event, actor, ts):
		discussion = self._ref_name(event["on"])
		doc = frappe.get_doc(
			{
				"doctype": "GP Poll",
				"title": event["title"],
				"discussion": discussion,
				"multiple_answers": 1 if event.get("multiple_answers") else 0,
				"options": [{"title": o} for o in event["options"]],
			}
		).insert(ignore_permissions=True)
		self.refs[event["id"]] = ("GP Poll", doc.name)
		self._backdate("GP Poll", doc.name, ts)
		# Poll insert cascades discussion meta like a comment does.
		frappe.db.set_value(
			"GP Discussion",
			discussion,
			{"last_post_at": ts, "modified": ts},
			update_modified=False,
		)

	def _event_vote(self, event, actor, ts):
		poll = frappe.get_doc(*self._ref(event["on"]))
		poll.submit_vote(event["option"])
		self._touch("GP Poll", poll.name, ts)

	def _event_bookmark(self, event, actor, ts):
		doc = frappe.get_doc(
			{"doctype": "GP Bookmark", "user": actor, "discussion": self._ref_name(event["on"])}
		).insert(ignore_permissions=True)
		self._backdate("GP Bookmark", doc.name, ts)

	def _event_quick_reactions(self, event, actor, ts):
		# Personalized reaction row (Settings > Preferences). Custom-emoji slots
		# are {{emoji:...}} placeholders resolved to their uploaded file URLs.
		emojis = [self._resolve(e) for e in event["emojis"]]
		profile = frappe.db.get_value("GP User Profile", {"user": actor})
		frappe.db.set_value(
			"GP User Profile",
			profile,
			"quick_reaction_emojis",
			json.dumps(emojis),
			update_modified=False,
		)

	def _event_pin(self, event, actor, ts):
		space = self._ref_name(event["on"])
		doc = frappe.get_doc(
			{
				"doctype": "GP Pinned Project",
				"user": actor,
				"project": space,
				"team": frappe.db.get_value("GP Project", space, "team"),
			}
		).insert(ignore_permissions=True)
		self._backdate("GP Pinned Project", doc.name, ts)

	def _event_visit(self, event, actor, ts):
		discussion = self._ref_name(event["on"])
		doc = frappe.get_doc("GP Discussion", discussion)
		# track_visit upserts the visit row, marks unread records read, clears
		# notifications, all as the actor at wall clock; then we backdate the row.
		doc.track_visit()
		visit = frappe.db.get_value("GP Discussion Visit", {"discussion": discussion, "user": actor}, "name")
		if visit:
			frappe.db.set_value(
				"GP Discussion Visit",
				visit,
				{"last_visit": ts, "creation": ts, "modified": ts},
				update_modified=False,
			)
		if actor == MAYA_EMAIL:
			if self.maya_last_visit is None or ts > self.maya_last_visit:
				self.maya_last_visit = ts

	def _event_draft(self, event, actor, ts):
		space = self._ref_name(event["space"]) if event.get("space") else None
		doc = frappe.get_doc(
			{
				"doctype": "GP Draft",
				"title": event["title"],
				"content": self._resolve(event["content"]),
				"type": event.get("draft_type", "Discussion"),
				"project": space,
				"team": frappe.db.get_value("GP Project", space, "team") if space else None,
			}
		).insert(ignore_permissions=True)
		self._backdate("GP Draft", doc.name, ts)

	# ---- finalizers ---------------------------------------------------------

	def _apply_deferred_closes(self):
		for name, closer in self._deferred_closes.items():
			last_post_at = frappe.db.get_value("GP Discussion", name, "last_post_at")
			closed_at = last_post_at + timedelta(minutes=30)
			frappe.db.set_value(
				"GP Discussion",
				name,
				{"closed_at": closed_at, "closed_by": closer, "modified": closed_at},
				update_modified=False,
			)

	def _finalize_maya_read_state(self):
		"""Mark Maya's older notifications read so logging in as her feels lived-in.

		Everything before her last visit is something she has already seen, except
		the newest few, which stay unread so her notification inbox isn't empty
		(being online doesn't mean you've opened the bell).
		"""
		if not self.maya_last_visit:
			return
		Notification = frappe.qb.DocType("GP Notification")
		(
			frappe.qb.update(Notification)
			.set(Notification.read, 1)
			.where((Notification.to_user == MAYA_EMAIL) & (Notification.creation < str(self.maya_last_visit)))
		).run()
		# Flip the newest few back to unread AFTER the read-marking and the visit
		# replay (track_visit clears notifications per discussion as a side effect).
		newest = frappe.get_all(
			"GP Notification",
			filters={"to_user": MAYA_EMAIL},
			order_by="creation desc",
			limit=4,
			pluck="name",
		)
		if newest:
			(
				frappe.qb.update(Notification).set(Notification.read, 0).where(Notification.name.isin(newest))
			).run()

	# ---- helpers ------------------------------------------------------------

	def _actor_email(self, event: dict) -> str:
		slug = event.get("actor")
		return self.users[slug] if slug else "Administrator"

	def _time(self, t: str | None) -> datetime | None:
		if not t:
			return None
		match = _TIME_RE.match(t)
		if not match:
			raise ValueError(f"Invalid relative time: {t!r}")
		days, hour, minute = match.group(1), match.group(2), match.group(3)
		day = self.anchor + timedelta(days=int(days))
		return datetime(day.year, day.month, day.day, int(hour or 0), int(minute or 0))

	def _date(self, s: str | None):
		if not s:
			return None
		match = _TIME_RE.match(s)
		if not match:
			raise ValueError(f"Invalid relative date: {s!r}")
		return self.anchor + timedelta(days=int(match.group(1)))

	def _ref(self, symbolic_id: str) -> tuple[str, str]:
		if symbolic_id not in self.refs:
			raise KeyError(f"Unknown symbolic id: {symbolic_id!r}")
		return self.refs[symbolic_id]

	def _ref_name(self, symbolic_id: str) -> str:
		return self._ref(symbolic_id)[1]

	def _resolve(self, text: str | None) -> str | None:
		"""Expand {{file:...}}, {{emoji:...}}, {{user:...}} placeholders."""
		if not text:
			return text

		def repl(match):
			kind, key = match.group(1), match.group(2)
			if kind == "file":
				return self._file_url(key)
			if kind == "emoji":
				return self.emojis[key]
			if kind == "user":
				return self.users[key]
			return match.group(0)

		return _PLACEHOLDER_RE.sub(repl, text)

	def _file_url(self, name: str) -> str:
		if name in self.files:
			return self.files[name]

		from frappe.utils.file_manager import save_file

		self._ensure_demo_folder()
		path = os.path.join(self.files_dir, name)
		with open(path, "rb") as f:
			content = f.read()
		file_doc = save_file(name, content, None, None, folder=DEMO_FILE_FOLDER, is_private=0)
		self.files[name] = file_doc.file_url
		return file_doc.file_url

	@staticmethod
	def _ensure_demo_folder():
		if frappe.db.exists("File", DEMO_FILE_FOLDER):
			return
		frappe.get_doc(
			{"doctype": "File", "file_name": "Gameplan Demo", "is_folder": 1, "folder": "Home"}
		).insert(ignore_permissions=True)

	@staticmethod
	def _backdate(doctype: str, name: str, ts: datetime | None):
		"""Backdate a freshly-inserted doc's creation and modified to the event time."""
		if ts is None:
			return
		frappe.db.set_value(doctype, name, {"creation": ts, "modified": ts}, update_modified=False)

	@staticmethod
	def _touch(doctype: str, name: str, ts: datetime | None):
		"""Backdate only `modified`, for events that update a pre-existing doc."""
		if ts is None:
			return
		frappe.db.set_value(doctype, name, {"modified": ts}, update_modified=False)

	@staticmethod
	def _max_notification_id() -> int:
		result = frappe.db.sql("SELECT MAX(CAST(name AS UNSIGNED)) FROM `tabGP Notification`")
		return (result and result[0][0]) or 0

	@staticmethod
	def _backdate_new_notifications(previous_max_id: int, ts: datetime):
		# Notifications are created as side effects at wall-clock time; realign the
		# ones this event just produced so Maya's read-state heuristic is meaningful.
		frappe.db.sql(
			"""
			UPDATE `tabGP Notification`
			SET creation = %(ts)s, modified = %(ts)s
			WHERE CAST(name AS UNSIGNED) > %(prev)s
			""",
			{"ts": ts, "prev": previous_max_id},
		)
