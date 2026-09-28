# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt


from datetime import timedelta

import frappe
from frappe.utils import format_datetime, get_datetime, get_url, now_datetime

from gameplan.email_digest import (
	GAMEPLAN_LOGO_PATH,
	format_notification_item,
	get_digest_preferences_url,
	get_signed_digest_url,
	get_user_avatar_map,
)
from gameplan.notifications.away import (
	is_away,
	local_time,
	mark_recap_sent,
	pending_recap_periods,
	profile_prefs,
	scheduled_off_window,
	user_timezone,
)
from gameplan.permissions import can_view_space

MENTION_TYPES = ("Mention", "Rich Quote")
TICK_MINUTES = 5

# Past this many rows the mail stops listing and starts counting. A backlog builds whenever
# nobody was owed mail for a while — the reader was on In-app, or their account was off, or
# the sender itself stopped — and listing it in full is the thing worth avoiding, not the
# age of any one row. Dropping old rows instead used to destroy mail whenever the sender had
# simply missed its window.
SUMMARY_FROM = 20

# Plural first: a summary line only ever names a count, and one is the uncommon case.
TYPE_LABELS = {
	"Mention": ("mentions", "mention"),
	"Rich Quote": ("quotes", "quote"),
	"Comment": ("comments", "comment"),
	"New Discussion": ("new discussions", "new discussion"),
	"Reaction": ("reactions", "reaction"),
	"Poll Vote": ("poll votes", "poll vote"),
	"Added": ("spaces you were added to", "space you were added to"),
	"Moved": ("things moved", "thing moved"),
}
SPACE_SCOPED = ("New Discussion", "Added", "Moved")


def send_batches(now=None):
	now = now or now_datetime()
	users = frappe.get_all(
		"GP User Profile", filters={"notification_channel": "Email", "enabled": 1}, pluck="user"
	)
	for user in users:
		if not frappe.db.get_value("User", user, "enabled"):
			continue
		if should_send(user, now):
			send_batch(user)


def should_send(user: str, now) -> bool:
	prefs = profile_prefs(user)
	tz = user_timezone(user)
	kind = is_away(prefs, now, tz)
	if kind is None:
		return now.minute < TICK_MINUTES
	if kind == "Active hours":
		window_end, _ = scheduled_off_window(prefs, now, tz)
		return now - window_end < timedelta(minutes=TICK_MINUTES)
	return False


def send_batch(user: str) -> list:
	send_away_recap(user)
	rows = deliverable_rows(user)
	if rows:
		send_batch_email(user, rows)
		_stamp_sent(rows)
	return rows


def send_away_recap(user: str) -> list:
	periods = pending_recap_periods(user)
	if not periods:
		return []
	rows = deliverable_rows(user, away=[p.name for p in periods])
	if rows:
		frappe.sendmail(
			recipients=[user],
			subject=recap_subject(rows),
			template="notification_batch",
			args=recap_context(user, rows, periods),
		)
		_stamp_sent(rows)
	mark_recap_sent([p.name for p in periods])
	return rows


def pending_rows(user: str, away: list | None = None) -> list:
	return frappe.qb.get_query(
		"GP Notification",
		fields=[
			"name",
			"type",
			"message",
			"creation",
			"last_event_at",
			"event_count",
			"from_user",
			"from_user.full_name as from_user_full_name",
			"discussion",
			"discussion.title as discussion_title",
			"discussion.slug as discussion_slug",
			"comment",
			"poll",
			"task",
			"task.title as task_title",
			"project",
			"project.title as project_title",
			"team",
			"team.title as team_title",
		],
		filters={
			"to_user": user,
			"read": 0,
			"email_sent_at": ["is", "not set"],
			"email_skipped_at": ["is", "not set"],
			"away_period": ["in", away] if away else ["is", "not set"],
		},
		order_by="last_event_at desc",
		ignore_permissions=True,
	).run(as_dict=True)


def deliverable_rows(user: str, away: list | None = None) -> list:
	keep, skip = [], []
	viewable = {}
	for row in pending_rows(user, away):
		if not (row.discussion or row.task or row.poll or row.project or row.team):
			skip.append(row)
			continue
		if row.project:
			if row.project not in viewable:
				viewable[row.project] = can_view_space(user, row.project)
			if not viewable[row.project]:
				skip.append(row)
				continue
		keep.append(row)
	_stamp_skipped(skip)
	_stamp_read(user)
	return keep


def send_batch_email(user: str, rows: list):
	frappe.sendmail(
		recipients=[user],
		subject=batch_subject(rows),
		template="notification_batch",
		args=batch_context(user, rows),
	)


def batch_subject(rows: list) -> str:
	count = len(rows)
	return f"{count} new notification{'' if count == 1 else 's'} in Gameplan"


def recap_subject(rows: list) -> str:
	count = len(rows)
	return f"While you were away: {count} notification{'' if count == 1 else 's'} in Gameplan"


def recap_context(user: str, rows: list, periods: list) -> dict:
	tz = user_timezone(user)
	starts_at = reader_time(min(get_datetime(p.starts_at) for p in periods), tz)
	ends_at = reader_time(max(get_datetime(p.ends_at) for p in periods), tz)
	window = (
		f"{format_datetime(starts_at, 'EEE d MMM, h:mm a')} – {format_datetime(ends_at, 'EEE d MMM, h:mm a')}"
	)
	return {**batch_context(user, rows), "title": "While you were away", "window": window}


def reader_time(system_naive, tz):
	return local_time(system_naive, tz).replace(tzinfo=None)


def summarise(rows: list) -> list[str]:
	"""Count a backlog by kind instead of listing it: "2 mentions in 1 discussion"."""
	lines = []
	for type_name, (plural, singular) in TYPE_LABELS.items():
		group = [row for row in rows if row.type == type_name]
		if not group:
			continue
		# A merged row stands for several events, and the reader is owed the true number.
		count = sum(row.event_count or 1 for row in group)
		line = f"{count} {singular if count == 1 else plural}"
		scope = _scope(type_name, group)
		lines.append(f"{line} {scope}" if scope else line)
	return lines


def _scope(type_name: str, group: list) -> str:
	if type_name in SPACE_SCOPED:
		spaces = {row.project for row in group if row.project}
		return f"across {len(spaces)} spaces" if len(spaces) > 1 else ""
	discussions = {row.discussion for row in group if row.discussion}
	if not discussions:
		return ""
	return f"in {len(discussions)} discussions" if len(discussions) > 1 else "in 1 discussion"


def batch_context(user: str, rows: list) -> dict:
	base = {
		"logo_url": get_url(GAMEPLAN_LOGO_PATH),
		"site_url": get_url(),
		"open_gameplan_url": get_signed_digest_url(user, "/g/notifications"),
		"preferences_url": get_digest_preferences_url(user),
	}
	if len(rows) >= SUMMARY_FROM:
		return {**base, "summary": summarise(rows), "mentions": [], "others": []}

	avatar_map = get_user_avatar_map(row.from_user for row in rows)
	mentions = [row for row in rows if row.type in MENTION_TYPES]
	others = [row for row in rows if row.type not in MENTION_TYPES]
	return {
		**base,
		"summary": [],
		"mentions": [format_notification_item(row, avatar_map, user) for row in mentions],
		"others": [format_notification_item(row, avatar_map, user) for row in others],
	}


def _stamp_sent(rows: list):
	_stamp(rows, "email_sent_at")


def _stamp_skipped(rows: list):
	"""Deliberately not emailed, and never will be: the reader lost the Space, or the row
	points at nothing left to open. Kept apart from email_sent_at so the record does not
	claim a mail that was never sent."""
	_stamp(rows, "email_skipped_at")


def _stamp(rows: list, field: str):
	if not rows:
		return
	Notification = frappe.qb.DocType("GP Notification")
	(
		frappe.qb.update(Notification)
		.set(Notification[field], now_datetime())
		.where(Notification.name.isin([row.name for row in rows]))
	).run()


def _stamp_read(user: str):
	"""Read in the app before the mail went out, so there is nothing left to send."""
	Notification = frappe.qb.DocType("GP Notification")
	(
		frappe.qb.update(Notification)
		.set(Notification.email_skipped_at, now_datetime())
		.where(
			(Notification.to_user == user)
			& (Notification.read == 1)
			& Notification.email_sent_at.isnull()
			& Notification.email_skipped_at.isnull()
		)
	).run()
