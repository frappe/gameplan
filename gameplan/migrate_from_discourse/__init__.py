# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt
"""Import public content from a restored discuss.frappe.io Discourse database.

Entry point: :func:`execute`. Run it with ``bench execute``.

The importer is phased and resumable. Every object it creates is recorded in
``Discourse ID Map``, so a second run skips what the first one already made.

Fidelity decisions live in ``.scratch/discuss-migration/issues/05-fidelity-cut.md``.
Expected counts live in ``research/06-expected-counts.md``.
"""

import os
import re

import frappe
import psycopg2
from frappe.utils import cint, cstr
from psycopg2.extras import DictCursor

from gameplan.migrate_from_discourse.html_transforms import (
	accepted_answer_badge,
	rewrite_internal_links,
	strip_poll_markup,
	synthesized_quote,
	transform_cooked,
)
from gameplan.utils.sanitizer import sanitize_content
from gameplan.utils.utils import url_safe_slug

PHASES = ("categories", "users", "posts", "backfill", "links")

#: Emoji every imported like turns into (ticket 05 §5).
LIKE_EMOJI = "👍"

#: Owner used when a Discourse author has no imported Frappe user.
FALLBACK_USER = "Administrator"

#: Discourse's short-url alphabet (``Base62.encode(sha1.hex)``). Lowercase comes
#: before uppercase, which is not the usual base62 order. Verified against real
#: ``data-base62-sha1`` attributes in the dump.
BASE62_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"

SHA1_RE = re.compile(r"([0-9a-f]{40})")
UPLOAD_SHORT_URL_RE = re.compile(r"upload://([0-9A-Za-z]+)")

# --- Discourse filters, composed exactly as ticket 05 defines them ----------

TOPIC_FILTER = "t.deleted_at is null and t.visible and t.archetype = 'regular'"
POST_FILTER = "p.deleted_at is null and not p.hidden and p.post_type = 1"


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


def get_connection_string():
	dsn = frappe.conf.get("discourse_connection_string") or os.environ.get("DISCOURSE_CONNECTION_STRING")
	if not dsn:
		frappe.throw("Set `discourse_connection_string` in site_config.json")
	return dsn


def get_uploads_root():
	root = frappe.conf.get("discourse_uploads_root") or os.environ.get("DISCOURSE_UPLOADS_ROOT")
	if not root:
		frappe.throw("Set `discourse_uploads_root` in site_config.json")
	return root


# ---------------------------------------------------------------------------
# Postgres access
# ---------------------------------------------------------------------------

_conn = None


def pg():
	"""Return the shared read-only connection to the Discourse restore."""
	global _conn

	if _conn is None or _conn.closed:
		_conn = psycopg2.connect(get_connection_string())
		_conn.set_session(readonly=True)
	return _conn


def close_pg():
	global _conn

	if _conn is not None and not _conn.closed:
		_conn.rollback()
		_conn.close()
	_conn = None


def run_query(query, values=None):
	"""Small result sets only. Everything large goes through `stream_query`."""
	with pg().cursor(cursor_factory=DictCursor) as cursor:
		cursor.execute(query, values)
		return [frappe._dict(row) for row in cursor.fetchall()]


def stream_query(query, values=None, itersize=2000):
	"""Iterate a large result through a server-side (named) cursor.

	Rows arrive `itersize` at a time, so the corpus never lands in memory.
	"""
	name = f"discourse_{frappe.generate_hash(length=10)}"
	with pg().cursor(name=name, cursor_factory=DictCursor) as cursor:
		cursor.itersize = itersize
		cursor.execute(query, values)
		for row in cursor:
			yield frappe._dict(row)


# ---------------------------------------------------------------------------
# Discourse ID Map ledger
# ---------------------------------------------------------------------------
#
# One row per source record. The unique index on (discourse_table, discourse_id)
# means a source row maps to exactly one Gameplan record, so a top-level category
# needs two logical tables:
#
#   categories       -> the GP Project topics of that category land in
#                       (the team's auto-created "General" space for a top-level
#                       category, the space itself for a subcategory)
#   categories_team  -> the GP Team a top-level category became
#
# Other tables used: users, topics, tags, polls, uploads_sha1.


def log_map(reference_doctype, reference_name, table, discourse_id):
	frappe.db.sql(
		"""insert into `tabDiscourse ID Map`
			(name, creation, modified, owner, modified_by, reference_doctype,
			reference_name, discourse_table, discourse_id)
		values (%s, now(), now(), %s, %s, %s, %s, %s, %s)
		on duplicate key update reference_name = values(reference_name)""",
		(
			frappe.generate_hash(length=10),
			frappe.session.user,
			frappe.session.user,
			reference_doctype,
			cstr(reference_name),
			table,
			cstr(discourse_id),
		),
	)


def load_map(table):
	"""Return {discourse_id: reference_name} for one logical source table."""
	rows = frappe.db.sql(
		"""select discourse_id, reference_name from `tabDiscourse ID Map`
		where discourse_table = %s""",
		(table,),
	)
	return {row[0]: row[1] for row in rows}


def mapped_name(table, discourse_id):
	return frappe.db.get_value(
		"Discourse ID Map",
		{"discourse_table": table, "discourse_id": cstr(discourse_id)},
		"reference_name",
	)


# ---------------------------------------------------------------------------
# Transform context: what html_transforms calls back into
# ---------------------------------------------------------------------------


def base62_to_sha1(value):
	"""Decode a Discourse short-url token to a 40-char hex sha1.

	Discourse encodes with a lowercase-before-uppercase alphabet, which is not the
	usual base62 order. Verified against real `data-base62-sha1` attributes.
	"""
	number = 0
	for char in value:
		index = BASE62_ALPHABET.find(char)
		if index < 0:
			return None
		number = number * 62 + index
	return f"{number:040x}"


class ImportContext:
	"""Callbacks `html_transforms` uses to resolve images and mentions.

	Both lookups are cached for the whole run: the same upload and the same
	username come back thousands of times across the corpus.
	"""

	def __init__(self, users_by_username=None, uploads_root=None, is_private=0):
		self.uploads_root = uploads_root or get_uploads_root()
		self.users_by_username = users_by_username or {}
		self.is_private = is_private
		self._file_cache = {}
		self._upload_cache = {}
		self._mention_cache = {}
		self.images_resolved = 0
		self.images_stripped = 0

	# -- images ------------------------------------------------------------

	def resolve_image(self, src, orig_src=None, base62_sha1=None):
		"""Return a local `/files/...` URL for a Discourse upload.

		Resolution is by sha1 against the restored `uploads` table, always to the
		ORIGINAL rendition: the backup holds no `optimized/` tree at all, while most
		cooked `<img src>` values point at one.

		Returns the src unchanged for images hosted somewhere other than the forum,
		and None when the file cannot be found (the caller strips the image).
		"""
		sha1 = self._sha1_from(src, orig_src, base62_sha1)
		upload = self._upload_row(sha1, src)

		if not upload:
			self.images_stripped += 1
			return src if self._is_external(src) else None

		file_url = self._file_for_upload(upload)
		if file_url:
			self.images_resolved += 1
		else:
			self.images_stripped += 1
		return file_url

	def _sha1_from(self, src, orig_src, base62_sha1):
		if base62_sha1:
			sha1 = base62_to_sha1(base62_sha1.strip())
			if sha1:
				return sha1

		for candidate in (orig_src, src):
			if not candidate:
				continue
			short = UPLOAD_SHORT_URL_RE.search(candidate)
			if short:
				sha1 = base62_to_sha1(short.group(1))
				if sha1:
					return sha1
			# `/uploads/default/original/3X/a/b/<sha1>.png` and the optimized variant
			# `<sha1>_2_690x70.png` both carry the sha1 in the filename.
			found = SHA1_RE.search(candidate)
			if found:
				return found.group(1)
		return None

	def _upload_row(self, sha1, src):
		if sha1:
			key = ("sha1", sha1)
		else:
			path = self._uploads_path(src)
			if not path:
				return None
			key = ("url", path)

		if key not in self._upload_cache:
			if key[0] == "sha1":
				# Some sha1s exist twice (same bytes stored as .png and .jpg). The
				# lowest id is the one the rest of the corpus points at.
				rows = run_query(
					"""select url, extension, original_filename from uploads
					where sha1 = %s and id > 0 order by id limit 1""",
					(sha1,),
				)
			else:
				rows = run_query(
					"""select url, extension, original_filename from uploads
					where url = %s order by id limit 1""",
					(key[1],),
				)
			self._upload_cache[key] = rows[0] if rows else None
		return self._upload_cache[key]

	@staticmethod
	def _uploads_path(src):
		"""Reduce any upload src to the site-relative path stored in `uploads.url`."""
		if not src:
			return None
		path = src.split("?", 1)[0].split("#", 1)[0]
		if "://" in path:
			path = "/" + path.split("://", 1)[1].split("/", 1)[-1]
		elif path.startswith("//"):
			path = "/" + path[2:].split("/", 1)[-1]
		index = path.find("/uploads/")
		return path[index:] if index >= 0 else None

	@staticmethod
	def _is_external(src):
		"""True for images hosted off the forum: leave those alone."""
		if not src or src.startswith("/"):
			return False
		if "://" not in src and not src.startswith("//"):
			return False
		host = src.split("://", 1)[-1].lstrip("/").split("/", 1)[0].lower()
		return "discuss.frappe.io" not in host and "discourse-cdn.com" not in host

	def _file_for_upload(self, upload):
		"""Create (or reuse) a Frappe File doc for one `uploads` row."""
		url = upload.url or ""
		if url in self._file_cache:
			return self._file_cache[url]

		self._file_cache[url] = None
		if not url.startswith("/uploads/default/"):
			return None

		sha1_key = SHA1_RE.search(url)
		map_key = sha1_key.group(1) if sha1_key else url

		existing = mapped_name("uploads_sha1", map_key)
		if existing:
			file_url = frappe.db.get_value("File", existing, "file_url")
			if file_url:
				self._file_cache[url] = file_url
				return file_url

		disk_path = os.path.join(self.uploads_root, url[len("/uploads/default/") :])
		try:
			with open(disk_path, "rb") as handle:
				content = handle.read()
		except OSError:
			return None

		file_doc = frappe.get_doc(
			doctype="File",
			file_name=self._file_name(upload, map_key),
			content=content,
			is_private=self.is_private,
		).insert(ignore_permissions=True)

		log_map("File", file_doc.name, "uploads_sha1", map_key)
		self._file_cache[url] = file_doc.file_url
		return file_doc.file_url

	@staticmethod
	def _file_name(upload, map_key):
		name = (upload.original_filename or "image").strip()
		name = re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip("-.") or "image"
		stem, extension = os.path.splitext(name)
		if not extension:
			extension = f".{upload.extension}" if upload.extension else ""
		return f"{stem[:60]}-{map_key[:10]}{extension}"

	# -- mentions ----------------------------------------------------------

	def resolve_mention(self, username):
		"""Discourse username -> Frappe user id (the email). None if not imported."""
		if not username:
			return None
		key = username.strip().lstrip("@").lower()
		if key not in self._mention_cache:
			self._mention_cache[key] = self.users_by_username.get(key)
		return self._mention_cache[key]


# ---------------------------------------------------------------------------
# Category scope
# ---------------------------------------------------------------------------


def get_categories():
	return run_query(
		"""select id, name, slug, parent_category_id, read_restricted, position
		from categories order by coalesce(position, 9999), id"""
	)


def restricted_category_ids(categories):
	"""Read-restricted categories and every descendant of one (ticket 05 §1)."""
	by_id = {c.id: c for c in categories}
	restricted = set()

	for category in categories:
		node = category
		seen = set()
		while node and node.id not in seen:
			seen.add(node.id)
			if node.read_restricted:
				restricted.add(category.id)
				break
			node = by_id.get(node.parent_category_id)
	return restricted


def category_scope(categories, only=None):
	"""Return (importable ids, ids to create).

	`only` limits the run to a few Discourse category ids for smoke tests. Their
	ancestors are still created, because a subcategory needs its team.
	"""
	by_id = {c.id: c for c in categories}
	restricted = restricted_category_ids(categories)
	allowed = {c.id for c in categories if c.id not in restricted}

	if not only:
		return allowed, allowed

	only = {cint(c) for c in only}
	importable = allowed & only
	to_create = set(importable)
	for category_id in importable:
		node = by_id.get(category_id)
		while node and node.parent_category_id:
			node = by_id.get(node.parent_category_id)
			if node:
				to_create.add(node.id)
	return importable, to_create


# ---------------------------------------------------------------------------
# Phase 1: categories -> teams and spaces
# ---------------------------------------------------------------------------


def migrate_categories(only=None):
	"""Top-level category -> GP Team, subcategory -> GP Project.

	A top-level category also owns the team's auto-created "General" space: that is
	where its own topics land, so it is logged in the ID map under `categories`.
	The team itself is logged under `categories_team`.
	"""
	categories = get_categories()
	_, to_create = category_scope(categories, only)
	by_id = {c.id: c for c in categories}

	teams = load_map("categories_team")
	spaces = load_map("categories")
	created = frappe._dict(teams=0, spaces=0)

	roots = [c for c in categories if c.id in to_create and not c.parent_category_id]
	for category in roots:
		if cstr(category.id) in teams:
			continue
		team = frappe.get_doc(
			doctype="GP Team",
			title=category.name[:140],
			readme=sanitize_content(category.description or ""),
			is_private=0,
		).insert(ignore_permissions=True)
		log_map("GP Team", team.name, "categories_team", category.id)
		teams[cstr(category.id)] = team.name
		created.teams += 1

		# GPTeam.after_insert creates this. Without a map row `clear_data` cannot
		# remove it and topics of the parent category cannot find it.
		general = frappe.db.get_value("GP Project", {"team": team.name, "title": "General"})
		if general and cstr(category.id) not in spaces:
			log_map("GP Project", general, "categories", category.id)
			spaces[cstr(category.id)] = general
			created.spaces += 1

	for category in categories:
		if category.id not in to_create or not category.parent_category_id:
			continue
		if cstr(category.id) in spaces:
			continue
		root = by_id.get(category.parent_category_id)
		while root and root.parent_category_id:
			root = by_id.get(root.parent_category_id)
		team = teams.get(cstr(root.id)) if root else None
		if not team:
			print(f"skip category {category.id} ({category.name}): no team")
			continue
		space = frappe.get_doc(
			doctype="GP Project",
			title=category.name[:140],
			team=team,
			description=sanitize_content(category.description or ""),
			is_private=0,
		).insert(ignore_permissions=True)
		log_map("GP Project", space.name, "categories", category.id)
		spaces[cstr(category.id)] = space.name
		created.spaces += 1

	frappe.db.commit()
	print(f"categories: {created.teams} teams, {created.spaces} spaces created")
	return created


# ---------------------------------------------------------------------------
# Phase 2: users
# ---------------------------------------------------------------------------

CONTENT_USERS_SQL = f"""
with kept_topics as (
	select t.id from topics t
	where {TOPIC_FILTER} and t.category_id = any(%(cats)s)
		and exists (
			select 1 from posts p
			where p.topic_id = t.id and p.post_number = 1 and {POST_FILTER}
		)
),
kept_posts as (
	select p.id, p.user_id from posts p
	join kept_topics k on k.id = p.topic_id
	where {POST_FILTER}
),
content_users as (
	select user_id from kept_posts where user_id > 0
	union
	select pa.user_id from post_actions pa
	join kept_posts kp on kp.id = pa.post_id
	where pa.post_action_type_id = 2 and pa.user_id > 0 and pa.deleted_at is null
)
select u.id, u.username, u.name as full_name, u.admin, u.moderator, u.staged,
	ue.email, av.url as avatar_url
from users u
join content_users cu on cu.user_id = u.id
left join user_emails ue on ue.user_id = u.id and ue."primary"
left join user_avatars ua on ua.user_id = u.id
left join uploads av on av.id = ua.custom_upload_id
where not u.staged
order by u.id
"""


def migrate_users(only=None, commit_every=200):
	"""Create a Frappe User for everyone who posted or liked in the kept corpus.

	Login stays impossible: no password is ever set and no welcome mail goes out.
	`enabled` stays 1 so names and avatars render.

	This phase runs alone because `create_user_profile` (a User.after_insert hook)
	calls `frappe.db.commit()` per user. Anything half-written in the same
	transaction would be committed with it.
	"""
	categories = get_categories()
	importable, _ = category_scope(categories, only)
	if not importable:
		print("users: no categories in scope")
		return 0

	existing = load_map("users")
	context = ImportContext()
	created = 0
	seen = 0

	for row in stream_query(CONTENT_USERS_SQL, {"cats": sorted(importable)}):
		seen += 1
		if cstr(row.id) in existing:
			continue
		if created % 100 == 0:
			drain_queue()
		try:
			user = create_user(row, context)
		except Exception:
			frappe.db.rollback()
			print(f"user {row.id} ({row.username}) failed:\n{frappe.get_traceback()}")
			continue
		if not user:
			continue
		log_map("User", user, "users", row.id)
		created += 1
		if created % commit_every == 0:
			frappe.db.commit()
			print(f"users: {created} created ({seen} scanned)")

	frappe.db.commit()
	print(f"users: {created} created, {seen} scanned")
	return created


def create_user(row, context):
	email = (row.email or "").strip().lower()
	if not email or "@" not in email:
		# Keeps authorship intact for the few rows with no primary email.
		email = f"discourse-{row.id}@import.invalid"

	if frappe.db.exists("User", email):
		return email

	full_name = (row.full_name or row.username or "").strip() or f"user-{row.id}"
	parts = full_name.split(" ", 1)
	roles = [{"role": "Gameplan Member"}]
	if row.admin or row.moderator:
		# Inert: login is blocked, so nothing can sign into these accounts.
		roles.append({"role": "Gameplan Admin"})

	user = frappe.get_doc(
		doctype="User",
		user_type="Website User",
		email=email,
		first_name=parts[0][:140],
		last_name=(parts[1][:140] if len(parts) > 1 else None),
		username=row.username,
		enabled=1,
		send_welcome_email=0,
		roles=roles,
	)
	try:
		user.insert(ignore_permissions=True)
	except frappe.NameError:
		return email
	except Exception:
		# `create_user_profile` commits inside User.after_insert, so a throw from a
		# later hook leaves a usable account behind. Re-inserting it would only
		# raise DuplicateEntryError.
		if frappe.db.exists("User", email):
			frappe.clear_last_message()
		else:
			# A username Frappe rejects must not cost us the account.
			user.username = None
			user.insert(ignore_permissions=True)

	set_avatar(frappe._dict(name=email), row, context)
	return email


def drain_queue():
	"""Drop this site's queued jobs so `User.on_update` never hits the ceiling.

	`User.on_update` enqueues `create_contact` per user. A bench with no worker
	fills the queue until `_check_queue_size` throws QueueOverloaded and every
	later User insert fails. Gameplan never reads Contacts, so the jobs are dead
	weight.

	Only jobs belonging to the current site are removed. Redis is shared with
	other benches on this machine and their jobs must survive.
	"""
	try:
		from frappe.utils.background_jobs import get_queue

		site = frappe.local.site
		removed = 0
		for queue_name in ("default", "short", "long"):
			for job in get_queue(queue_name).get_jobs():
				if (job.kwargs or {}).get("site") == site:
					job.delete()
					removed += 1
		return removed
	except Exception:
		print(f"could not drain the job queue: {frappe.get_traceback(with_context=False)}")
		return 0


def set_avatar(user, row, context):
	"""Avatars go on GP User Profile.image; the UI reads that, not `user_image`."""
	if not row.avatar_url:
		return
	file_url = context.resolve_image(row.avatar_url)
	if not file_url or not file_url.startswith("/files/"):
		return

	profile = frappe.db.get_value("GP User Profile", {"user": user.name})
	if profile:
		frappe.db.set_value("GP User Profile", profile, "image", file_url, update_modified=False)
	frappe.db.set_value("User", user.name, "user_image", file_url, update_modified=False)


# ---------------------------------------------------------------------------
# Phase 3: topics -> discussions, posts -> comments
# ---------------------------------------------------------------------------

TOPIC_BATCH_SQL = f"""
select t.id, t.title, t.user_id, t.category_id, t.created_at, t.updated_at,
	t.last_posted_at, t.closed, t.pinned_at,
	p.id as post_id, p.cooked, p.created_at as post_created, p.updated_at as post_updated,
	p.user_id as post_user_id
from topics t
join posts p on p.topic_id = t.id and p.post_number = 1
where {TOPIC_FILTER} and {POST_FILTER}
	and t.category_id = any(%(cats)s) and t.id > %(after)s
order by t.id
limit %(limit)s
"""

REPLY_SQL = f"""
select p.id, p.topic_id, p.post_number, p.reply_to_post_number, p.user_id,
	p.cooked, p.created_at, p.updated_at
from posts p
where p.topic_id = any(%(topics)s) and p.post_number > 1 and {POST_FILTER}
order by p.topic_id, p.post_number
"""


class Maps:
	"""In-memory lookups. One dict beats millions of unindexed probes."""

	def __init__(self, importable):
		self.project_by_category = {
			cint(k): v for k, v in load_map("categories").items() if cint(k) in importable
		}
		# GP Project names are integers in the database and strings in the ID map.
		self.team_by_project = {
			cstr(p.name): p.team for p in frappe.get_all("GP Project", ["name", "team"], limit_page_length=0)
		}
		self.user_by_discourse_id = load_map("users")
		self.imported_topics = set(load_map("topics"))
		self.tag_by_discourse_id = load_map("tags")

		self.full_name_by_user = {}
		self.user_by_username = {}
		for row in frappe.get_all("User", ["name", "username", "full_name"], limit_page_length=0):
			self.full_name_by_user[row.name] = row.full_name
			if row.username:
				self.user_by_username[row.username.lower()] = row.name

	def user(self, discourse_user_id):
		return self.user_by_discourse_id.get(cstr(discourse_user_id)) or FALLBACK_USER

	def full_name(self, frappe_user):
		return self.full_name_by_user.get(frappe_user) or frappe_user


def migrate_posts(only=None, limit=None, start_after=0, batch_size=200, commit_every=25):
	categories = get_categories()
	importable, _ = category_scope(categories, only)
	if not importable:
		print("posts: no categories in scope")
		return 0

	maps = Maps(importable)
	ensure_tags(importable, maps)
	context = ImportContext(users_by_username=maps.user_by_username)

	cats = sorted(importable)
	last_id = cint(start_after)
	imported = 0
	skipped = 0
	failed = 0

	while True:
		topics = run_query(TOPIC_BATCH_SQL, {"cats": cats, "after": last_id, "limit": batch_size})
		if not topics:
			break
		last_id = topics[-1].id

		pending = [t for t in topics if cstr(t.id) not in maps.imported_topics]
		skipped += len(topics) - len(pending)
		if not pending:
			continue

		batch = TopicBatch(pending)
		for topic in pending:
			savepoint = f"topic_{topic.id}"
			frappe.db.savepoint(savepoint)
			try:
				if import_topic(topic, batch, maps, context):
					imported += 1
				else:
					skipped += 1
			except Exception:
				frappe.db.rollback(save_point=savepoint)
				failed += 1
				print(f"topic {topic.id} failed:\n{frappe.get_traceback()}")
			else:
				frappe.db.release_savepoint(savepoint)

			if imported and imported % commit_every == 0:
				frappe.db.commit()
				print(f"posts: {imported} discussions imported")

			if limit and imported >= cint(limit):
				frappe.db.commit()
				print(f"posts: {imported} imported, {skipped} skipped, {failed} failed (limit hit)")
				return imported

	frappe.db.commit()
	print(
		f"posts: {imported} discussions imported, {skipped} skipped, {failed} failed. "
		f"images {context.images_resolved} resolved / {context.images_stripped} unresolved"
	)
	return imported


def ensure_tags(importable, maps):
	"""Create every GP Tag used by the kept corpus up front (ticket 05 §6)."""
	rows = run_query(
		f"""select distinct tg.id, tg.name from tags tg
		join topic_tags tt on tt.tag_id = tg.id
		join topics t on t.id = tt.topic_id
		where {TOPIC_FILTER} and t.category_id = any(%(cats)s)""",
		{"cats": sorted(importable)},
	)
	by_label = {
		row.label: row.name for row in frappe.get_all("GP Tag", ["name", "label"], limit_page_length=0)
	}
	created = 0
	for row in rows:
		if cstr(row.id) in maps.tag_by_discourse_id:
			continue
		label = (row.name or "").strip()[:140]
		if not label:
			continue
		name = by_label.get(label)
		if not name:
			name = frappe.get_doc(doctype="GP Tag", label=label).insert(ignore_permissions=True).name
			by_label[label] = name
			created += 1
		log_map("GP Tag", name, "tags", row.id)
		maps.tag_by_discourse_id[cstr(row.id)] = name
	frappe.db.commit()
	if created:
		print(f"tags: {created} created")


class TopicBatch:
	"""Everything the topics in one keyset batch need, fetched in six queries."""

	def __init__(self, topics):
		topic_ids = [t.id for t in topics]
		first_post_ids = [t.post_id for t in topics]

		self.replies = {}
		for row in run_query(REPLY_SQL, {"topics": topic_ids}):
			self.replies.setdefault(row.topic_id, []).append(row)

		post_ids = list(first_post_ids)
		for rows in self.replies.values():
			post_ids.extend(r.id for r in rows)

		self.likes = {}
		for row in run_query(
			"""select post_id, user_id from post_actions
			where post_id = any(%(posts)s) and post_action_type_id = 2
				and user_id > 0 and deleted_at is null""",
			{"posts": post_ids},
		):
			self.likes.setdefault(row.post_id, []).append(row.user_id)

		self.tags = {}
		for row in run_query(
			"select topic_id, tag_id from topic_tags where topic_id = any(%(topics)s)",
			{"topics": topic_ids},
		):
			self.tags.setdefault(row.topic_id, []).append(row.tag_id)

		self.answers = {}
		for row in run_query(
			"""select topic_id, answer_post_id from discourse_solved_solved_topics
			where topic_id = any(%(topics)s)""",
			{"topics": topic_ids},
		):
			self.answers[row.topic_id] = row.answer_post_id

		self.polls = {}
		for row in run_query(
			"""select id, post_id, name, title, type, status, close_at, updated_at
			from polls where post_id = any(%(posts)s) order by id""",
			{"posts": first_post_ids},
		):
			self.polls.setdefault(row.post_id, []).append(row)

		self.poll_options = {}
		if self.polls:
			poll_ids = [p.id for rows in self.polls.values() for p in rows]
			for row in run_query(
				"select poll_id, html from poll_options where poll_id = any(%(polls)s) order by id",
				{"polls": poll_ids},
			):
				self.poll_options.setdefault(row.poll_id, []).append(row.html)


def import_topic(topic, batch, maps, context):
	project = maps.project_by_category.get(topic.category_id)
	if not project:
		print(f"skip topic {topic.id}: category {topic.category_id} has no space")
		return False

	owner = maps.user(topic.user_id)
	polls = batch.polls.get(topic.post_id) or []
	answer_post_id = batch.answers.get(topic.id)

	content = transform_cooked(topic.cooked or "", context)
	if polls:
		# Ticket 04 rewrites poll markup to a static list, so leaving it would render
		# the poll twice: once dead in the body, once live as a GP Poll record.
		content = strip_poll_markup(content)
	if answer_post_id == topic.post_id:
		content = accepted_answer_badge(content)
	content = sanitize_content(content) or ""
	if not frappe.utils.strip_html(content).strip():
		content = "<p></p>"

	title = (topic.title or "").strip()[:140] or f"Topic {topic.id}"
	discussion = frappe.get_doc(
		doctype="GP Discussion",
		title=title,
		slug=url_safe_slug(title),
		content=content,
		project=project,
		team=maps.team_by_project.get(cstr(project)),
		last_post_at=topic.last_posted_at or topic.created_at,
		creation=topic.created_at,
		modified=topic.updated_at or topic.created_at,
		owner=owner,
		modified_by=owner,
		reactions=build_reactions(batch.likes.get(topic.post_id), maps),
		tags=build_tag_links(batch.tags.get(topic.id), maps),
	)
	if topic.closed:
		# Discourse keeps no "closed at" timestamp, only the flag.
		discussion.closed_at = topic.updated_at or topic.last_posted_at
		discussion.closed_by = owner
	if topic.pinned_at:
		discussion.pinned_at = topic.pinned_at
		discussion.pinned_by = owner
		discussion.pin_scope = "Space"

	insert_with_children(discussion)

	post_authors = {1: owner}
	post_bodies = {1: topic.cooked or ""}
	for reply in batch.replies.get(topic.id) or []:
		post_authors[reply.post_number] = maps.user(reply.user_id)
		post_bodies[reply.post_number] = reply.cooked or ""

	for reply in batch.replies.get(topic.id) or []:
		import_comment(reply, discussion, batch, maps, context, post_authors, post_bodies)

	for poll in polls:
		import_poll(poll, topic, discussion, batch, maps)

	log_map("GP Discussion", discussion.name, "topics", topic.id)
	maps.imported_topics.add(cstr(topic.id))
	return True


def import_comment(reply, discussion, batch, maps, context, post_authors, post_bodies):
	owner = maps.user(reply.user_id)
	raw = reply.cooked or ""
	content = transform_cooked(raw, context)

	parent_number = reply.reply_to_post_number
	if (
		parent_number
		and parent_number != reply.post_number - 1
		and parent_number in post_bodies
		and 'class="quote' not in raw
	):
		# Ticket 05 §4: only synthesize where the arrow carried information.
		parent_author = maps.full_name(post_authors.get(parent_number, FALLBACK_USER))
		excerpt = frappe.utils.strip_html(post_bodies[parent_number]).strip()
		excerpt = re.sub(r"\s+", " ", excerpt)[:200]
		content = synthesized_quote(content, parent_author, excerpt)

	if batch.answers.get(reply.topic_id) == reply.id:
		content = accepted_answer_badge(content)

	content = sanitize_content(content) or ""
	if not content.strip():
		content = "<p></p>"

	comment = frappe.get_doc(
		doctype="GP Comment",
		reference_doctype="GP Discussion",
		reference_name=discussion.name,
		content=content,
		creation=reply.created_at,
		modified=reply.updated_at or reply.created_at,
		owner=owner,
		modified_by=owner,
		reactions=build_reactions(batch.likes.get(reply.id), maps),
	)
	insert_with_children(comment)


def import_poll(poll, topic, discussion, batch, maps):
	options = [
		frappe.utils.strip_html(html or "").strip() for html in (batch.poll_options.get(poll.id) or [])
	]
	options = [o[:140] for o in dict.fromkeys(o for o in options if o)]
	if not options:
		return

	owner = maps.user(topic.post_user_id)
	doc = frappe.get_doc(
		doctype="GP Poll",
		title=(poll.title or poll.name or "Poll")[:140],
		discussion=discussion.name,
		multiple_answers=1 if poll.type == 1 else 0,
		stopped_at=(poll.close_at or poll.updated_at) if poll.status == 1 else None,
		creation=topic.post_created,
		modified=topic.post_updated or topic.post_created,
		owner=owner,
		modified_by=owner,
		options=[{"title": option} for option in options],
	)
	insert_with_children(doc)
	log_map("GP Poll", doc.name, "polls", poll.id)


def build_reactions(user_ids, maps):
	"""Ticket 05 §5: likes only, as 👍, and only from users we imported."""
	reactions = []
	seen = set()
	for user_id in user_ids or []:
		user = maps.user_by_discourse_id.get(cstr(user_id))
		if not user or user in seen:
			continue
		seen.add(user)
		reactions.append({"user": user, "emoji": LIKE_EMOJI})
	return reactions


def build_tag_links(tag_ids, maps):
	links = []
	seen = set()
	for tag_id in tag_ids or []:
		tag = maps.tag_by_discourse_id.get(cstr(tag_id))
		if not tag or tag in seen:
			continue
		seen.add(tag)
		links.append({"tag": tag, "label": frappe.db.get_value("GP Tag", tag, "label")})
	return links


def insert_with_children(doc):
	"""`db_insert` keeps owner/creation/modified and skips validate, hooks and the
	sanitizer. Child rows have to be written by hand, parent name included."""
	doc.db_insert()
	for child in doc.get_all_children():
		child.parent = doc.name
		child.db_insert()


# No GP Unread Record backfill, and no GP Discussion Visit import.
#
# Unread records would be members x discussions rows (tens of millions) and would
# mark years of history unread. With none, imported content counts as read and
# `mark_discussion_as_unread_for_user` creates a record on demand.
#
# GP Discussion Visit is read-state, not a view counter: nothing renders a count
# from it (ticket 05 §8). `topic_users` would add millions of rows for no display.


# ---------------------------------------------------------------------------
# Phase 4: backfill the fields db_insert bypassed
# ---------------------------------------------------------------------------


def backfill_denormalized_fields():
	"""Recompute what `before_save` / `after_insert` would normally maintain.

	`slug` is already written at insert; this fixes any row that missed it.
	Everything else is set in bulk SQL, mirroring `GPDiscussion.update_post_count`,
	`update_participants_count` and `update_last_post`.
	"""
	backfill_slugs()

	# `team` is a fetch_from field, so db_insert never fills it.
	frappe.db.sql(
		"""update `tabGP Discussion` d
		join `tabGP Project` p on p.name = d.project
		set d.team = p.team
		where d.team is null or d.team = '' or d.team != p.team"""
	)

	# Frappe blocks DDL through db.sql because it implicitly commits; sql_ddl is
	# the sanctioned door and commits first.
	frappe.db.sql_ddl("drop temporary table if exists `_gp_stream`")
	frappe.db.sql_ddl(
		"""create temporary table `_gp_stream` (
			discussion bigint not null,
			post_name varchar(140) not null,
			post_type varchar(20) not null,
			creation datetime(6) not null,
			owner varchar(140),
			index (discussion, creation)
		) engine=InnoDB"""
	)
	frappe.db.sql(
		"""insert into `_gp_stream` (discussion, post_name, post_type, creation, owner)
		select cast(reference_name as unsigned), name, 'GP Comment', creation, owner
		from `tabGP Comment`
		where reference_doctype = 'GP Discussion' and reference_name is not null"""
	)
	frappe.db.sql(
		"""insert into `_gp_stream` (discussion, post_name, post_type, creation, owner)
		select cast(discussion as unsigned), name, 'GP Poll', creation, owner
		from `tabGP Poll` where discussion is not null"""
	)

	frappe.db.sql(
		"""update `tabGP Discussion` d
		left join (
			select discussion, count(*) as posts from `_gp_stream` group by discussion
		) s on s.discussion = d.name
		set d.comments_count = coalesce(s.posts, 0)"""
	)

	# Participants = distinct authors in the thread, the discussion owner included.
	frappe.db.sql(
		"""update `tabGP Discussion` d
		left join (
			select discussion, count(distinct owner) as people from (
				select discussion, owner from `_gp_stream`
				union
				select name as discussion, owner from `tabGP Discussion`
			) x group by discussion
		) p on p.discussion = d.name
		set d.participants_count = coalesce(p.people, 1)"""
	)

	frappe.db.sql(
		"""update `tabGP Discussion` d
		join (
			select discussion, post_name, post_type, creation, owner from (
				select s.*, row_number() over (
					partition by discussion order by creation desc, post_name desc
				) as rn from `_gp_stream` s
			) ranked where rn = 1
		) l on l.discussion = d.name
		set d.last_post_type = l.post_type, d.last_post = l.post_name,
			d.last_post_at = l.creation, d.last_post_by = l.owner"""
	)

	# Threads with nothing after the opening post are their own last post.
	frappe.db.sql(
		"""update `tabGP Discussion` d
		left join (select distinct discussion from `_gp_stream`) s on s.discussion = d.name
		set d.last_post_type = null, d.last_post = null,
			d.last_post_at = d.creation, d.last_post_by = d.owner
		where s.discussion is null"""
	)
	frappe.db.sql_ddl("drop temporary table if exists `_gp_stream`")

	frappe.db.sql(
		"""update `tabGP Project` p
		left join (
			select project, count(*) as total from `tabGP Discussion`
			where project is not null group by project
		) d on d.project = p.name
		set p.discussions_count = coalesce(d.total, 0)"""
	)
	frappe.db.commit()

	counts = frappe.db.sql(
		"""select count(*), sum(comments_count), sum(participants_count)
		from `tabGP Discussion`"""
	)[0]
	print(
		f"backfill: {counts[0]} discussions, {cint(counts[1])} thread posts, "
		f"{cint(counts[2])} participant rows"
	)


def backfill_slugs(batch_size=2000):
	updated = 0
	while True:
		rows = frappe.db.sql(
			"""select name, title from `tabGP Discussion`
			where (slug is null or slug = '') and title is not null limit %s""",
			(batch_size,),
			as_dict=True,
		)
		if not rows:
			break
		for row in rows:
			frappe.db.set_value(
				"GP Discussion", row.name, "slug", url_safe_slug(row.title), update_modified=False
			)
		updated += len(rows)
		frappe.db.commit()
	if updated:
		print(f"backfill: {updated} slugs written")


# ---------------------------------------------------------------------------
# Phase 5: second pass over internal links
# ---------------------------------------------------------------------------


def make_link_resolver():
	"""`resolve(kind, key) -> gameplan path or None`, backed by the ID map.

	Runs last, once every topic exists. A target outside the corpus resolves to
	None and the link is left absolute.
	"""
	topics = load_map("topics")
	spaces = {cint(k): v for k, v in load_map("categories").items()}
	project_by_discussion = dict(
		frappe.db.sql("select name, project from `tabGP Discussion` where project is not null")
	)
	users_by_username = {
		row.username.lower(): row.name
		for row in frappe.get_all("User", ["name", "username"], limit_page_length=0)
		if row.username
	}
	slug_to_category = {}
	for category in get_categories():
		if category.slug:
			slug_to_category[category.slug.lower()] = category.id

	def resolve(kind, key):
		kind = (kind or "").strip().lower()
		key = cstr(key).strip().strip("/")
		if not key:
			return None

		if kind in ("t", "topic", "topics", "discussion"):
			discussion = topics.get(key)
			if not discussion:
				return None
			project = project_by_discussion.get(cint(discussion)) or project_by_discussion.get(discussion)
			return f"/g/space/{project}/discussion/{discussion}" if project else None

		if kind in ("u", "user", "users", "person"):
			user = users_by_username.get(key.lstrip("@").lower())
			return f"/g/people/{user}" if user else None

		if kind in ("c", "category", "categories", "space"):
			category_id = cint(key) if key.isdigit() else slug_to_category.get(key.lower())
			project = spaces.get(cint(category_id)) if category_id else None
			return f"/g/space/{project}/discussions" if project else None

		return None

	return resolve


def rewrite_links(batch_size=500):
	resolve = make_link_resolver()
	total_rows = 0
	total_links = 0

	for doctype in ("GP Discussion", "GP Comment"):
		last = 0
		while True:
			rows = frappe.db.sql(
				f"""select name, content from `tab{doctype}`
				where name > %s and (
					content like '%%discuss.frappe.io%%'
					or content like '%%href="/t/%%'
					or content like '%%href="/u/%%'
					or content like '%%href="/c/%%'
				) order by name limit %s""",
				(last, batch_size),
				as_dict=True,
			)
			if not rows:
				break
			last = rows[-1].name
			for row in rows:
				html, rewritten = rewrite_internal_links(row.content or "", resolve)
				if rewritten:
					frappe.db.set_value(doctype, row.name, "content", html, update_modified=False)
					total_rows += 1
					total_links += rewritten
			frappe.db.commit()

	print(f"links: {total_links} rewritten across {total_rows} documents")
	return total_links


# ---------------------------------------------------------------------------
# Reset
# ---------------------------------------------------------------------------

#: Child tables written by hand, keyed by the parent doctype that owns them.
CHILD_TABLES = {
	"GP Discussion": ("GP Reaction", "GP Tag Link"),
	"GP Comment": ("GP Reaction", "GP Tag Link"),
	"GP Poll": ("GP Reaction", "GP Poll Option", "GP Poll Vote"),
	"GP Project": ("GP Member",),
	"GP Team": ("GP Member",),
}


def chunked(values, size=500):
	values = list(values)
	for start in range(0, len(values), size):
		yield values[start : start + size]


def delete_rows(doctype, filters):
	frappe.db.delete(doctype, filters)


def delete_children(parent_doctype, parents):
	for child in CHILD_TABLES.get(parent_doctype, ()):
		for batch in chunked(parents):
			delete_rows(child, {"parenttype": parent_doctype, "parent": ["in", batch]})


def clear_data(include_users=False, include_files=True):
	"""Undo an import, children before parents, driven by the ID map.

	Bulk deletes only: one `delete_doc` per document runs the bookmark sweep, the
	unread-record delete and the cascade queries every time, which is unusable at
	import scale. Files are the exception — they own bytes on disk.

	Users stay by default: deleting them fires `delete_user_profile` and User's own
	heavy `on_trash`, and they are cheap to keep.
	"""
	frappe.flags.in_import = True

	discussions = list(load_map("topics").values())
	polls = list(load_map("polls").values())
	spaces = list(load_map("categories").values())
	teams = list(load_map("categories_team").values())
	tags = list(load_map("tags").values())
	files = list(load_map("uploads_sha1").values())

	comments = []
	for batch in chunked(discussions):
		comments.extend(
			frappe.db.get_all(
				"GP Comment",
				{"reference_doctype": "GP Discussion", "reference_name": ["in", batch]},
				pluck="name",
			)
		)

	deleted = frappe._dict()

	delete_children("GP Comment", comments)
	delete_children("GP Poll", polls)
	delete_children("GP Discussion", discussions)

	for batch in chunked(comments):
		delete_rows("GP Comment", {"name": ["in", batch]})
	deleted.comments = len(comments)

	for batch in chunked(polls):
		delete_rows("GP Poll", {"name": ["in", batch]})
	deleted.polls = len(polls)

	for batch in chunked(discussions):
		delete_rows("GP Discussion Visit", {"discussion": ["in", batch]})
		delete_rows("GP Activity", {"reference_doctype": "GP Discussion", "reference_name": ["in", batch]})
		delete_rows("GP Unread Record", {"discussion": ["in", batch]})
		delete_rows("GP Discussion", {"name": ["in", batch]})
	deleted.discussions = len(discussions)

	for batch in chunked(tags):
		delete_rows("GP Tag Link", {"tag": ["in", batch]})
		delete_rows("GP Tag", {"name": ["in", batch]})
	deleted.tags = len(tags)

	delete_children("GP Project", spaces)
	for batch in chunked(spaces):
		delete_rows("GP Project Visit", {"project": ["in", batch]})
		delete_rows("GP Followed Project", {"project": ["in", batch]})
		delete_rows("GP Pinned Project", {"project": ["in", batch]})
		delete_rows("GP Project", {"name": ["in", batch]})
	deleted.spaces = len(spaces)

	delete_children("GP Team", teams)
	for batch in chunked(teams):
		delete_rows("GP Team", {"name": ["in", batch]})
	deleted.teams = len(teams)

	frappe.db.commit()

	if include_files:
		for name in files:
			try:
				frappe.delete_doc("File", name, force=True, ignore_permissions=True, delete_permanently=True)
			except Exception:
				print(f"could not delete File {name}: {frappe.get_traceback(with_context=False)}")
		frappe.db.commit()
	deleted.files = len(files) if include_files else 0

	tables = ["topics", "polls", "categories", "categories_team", "tags"]
	if include_files:
		tables.append("uploads_sha1")

	if include_users:
		users = list(load_map("users").values())
		for name in users:
			try:
				frappe.delete_doc("User", name, force=True, ignore_permissions=True)
			except Exception:
				print(f"could not delete User {name}")
		deleted.users = len(users)
		tables.append("users")

	for table in tables:
		frappe.db.delete("Discourse ID Map", {"discourse_table": table})
	frappe.db.commit()

	print(f"cleared: {deleted}")
	return deleted


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def execute(
	phases=None,
	categories=None,
	limit=None,
	start_after=0,
	batch_size=200,
	commit_every=25,
	clear=False,
	include_users_in_clear=False,
):
	"""Import discuss.frappe.io content into this Gameplan site.

	Phases run in order and are individually resumable: everything already in
	`Discourse ID Map` is skipped, so a re-run costs a scan and inserts nothing.

		bench --site <site> execute gameplan.migrate_from_discourse.execute
		bench --site <site> execute gameplan.migrate_from_discourse.execute \\
			--kwargs "{'categories': [83], 'phases': 'categories,users,posts,backfill'}"

	Args:
		phases: subset of ("categories", "users", "posts", "backfill", "links"),
			as a list or a comma-separated string. Default: all of them, in order.
		categories: Discourse category ids to limit the run to (smoke tests).
			Ancestors are still created so subcategories have a team.
		limit: stop after this many new discussions.
		start_after: resume the topic keyset scan after this Discourse topic id.
		batch_size: topics fetched per keyset batch.
		commit_every: commit after this many discussions.
		clear: run `clear_data()` first instead of importing.
		include_users_in_clear: also delete imported Users when clearing.

	Rebuild search afterwards. `db_insert` bypasses every indexing hook, so nothing
	imported is searchable until you run:

		bench --site <site> execute gameplan.search_sqlite.rebuild_index

	(that is `GameplanSearch().drop_index()` followed by
	`GameplanSearch.build_index`.)
	"""
	frappe.flags.in_import = True
	frappe.flags.mute_emails = True

	if clear:
		return clear_data(include_users=include_users_in_clear)

	if isinstance(phases, str):
		phases = [p.strip() for p in phases.split(",") if p.strip()]
	phases = list(phases or PHASES)
	unknown = [p for p in phases if p not in PHASES]
	if unknown:
		frappe.throw(f"Unknown phases: {unknown}. Valid: {list(PHASES)}")

	if isinstance(categories, str):
		categories = [c.strip() for c in categories.split(",") if c.strip()]
	categories = [cint(c) for c in categories] if categories else None

	try:
		for phase in PHASES:
			if phase not in phases:
				continue
			print(f"--- phase: {phase} ---")
			if phase == "categories":
				migrate_categories(only=categories)
			elif phase == "users":
				migrate_users(only=categories)
			elif phase == "posts":
				migrate_posts(
					only=categories,
					limit=limit,
					start_after=start_after,
					batch_size=cint(batch_size) or 200,
					commit_every=cint(commit_every) or 25,
				)
			elif phase == "backfill":
				backfill_denormalized_fields()
			elif phase == "links":
				rewrite_links()
	finally:
		close_pg()

	print("done. Rebuild search: bench execute gameplan.search_sqlite.rebuild_index")
