# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

"""The email channel: one mail an hour, per user who asked for email, with everything
that arrived since the last one — and a closing mail as the user's active hours end, so
nothing that arrived inside the window is left for the next day.

Every notification is a `GP Notification` row first; this only decides which rows also
go out by mail. A row is sent once (`email_sent_at`), and a row that no longer needs
sending — read in the app already, written while the user was away (the card covers
those), older than the horizon, or pointing at something the user can no longer open —
is stamped without a mail so the next run does not pick it up again.
"""

from datetime import timedelta

import frappe
from frappe.utils import add_to_date, format_datetime, get_datetime, get_url, now_datetime

from gameplan.email_digest import (
	GAMEPLAN_LOGO_PATH,
	format_notification_item,
	get_digest_preferences_url,
	get_signed_digest_url,
	get_user_avatar_map,
)
from gameplan.notifications.away import (
	is_away,
	mark_recap_sent,
	pending_recap_periods,
	profile_prefs,
	scheduled_off_window,
	user_timezone,
)
from gameplan.permissions import can_view_space

HORIZON_HOURS = 24
MENTION_TYPES = ("Mention", "Rich Quote")
# How often the scheduler calls send_batches (hooks.py); the closing mail lands in the
# first tick after the window ends, so this is also how late it can be.
TICK_MINUTES = 5


def send_batches(now=None):
	"""Scheduler entry, every TICK_MINUTES: a batch for every Email user whose clock says
	it is time (`should_send`)."""
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
	"""The top of the hour while inside active hours, or the first tick after they end —
	the closing mail. Evaluated in the user's own timezone, like the away stamp. A user
	without a schedule is always inside; a user with the toggle off gets nothing."""
	prefs = profile_prefs(user)
	tz = user_timezone(user)
	kind = is_away(prefs, now, tz)
	if kind is None:
		return now.minute < TICK_MINUTES
	if kind == "Active hours":
		# The off stretch we are in began when the window closed.
		window_end, _ = scheduled_off_window(prefs, now, tz)
		return now - window_end < timedelta(minutes=TICK_MINUTES)
	return False


def send_batch(user: str) -> list:
	"""Send `user` their pending rows in one mail. Returns the rows that were sent.

	A stretch the user was away for is caught up first, in its own mail, so what they
	missed is not mixed into the ordinary hourly one."""
	send_away_recap(user)
	rows = deliverable_rows(user)
	if rows:
		send_batch_email(user, rows)
		_stamp(rows)
	return rows


def send_away_recap(user: str) -> list:
	"""One catch-up mail for everything that arrived while `user` had notifications off or
	was outside their active hours. Sent once per stretch (`recap_sent_at`), and the
	stretch is stamped either way so an empty one is not looked at again."""
	periods = pending_recap_periods(user)
	if not periods:
		return []
	rows = deliverable_rows(user, away=[p.name for p in periods], horizon=False)
	if rows:
		frappe.sendmail(
			recipients=[user],
			subject=recap_subject(rows),
			template="notification_batch",
			args=recap_context(user, rows, periods),
		)
		_stamp(rows)
	mark_recap_sent([p.name for p in periods])
	return rows


def pending_rows(user: str, away: list | None = None) -> list:
	"""Unsent, unread rows — the ones that arrived during `away` stretches, or, without
	`away`, the ones that did not arrive during any."""
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
			"away_period": ["in", away] if away else ["is", "not set"],
		},
		order_by="last_event_at desc",
		ignore_permissions=True,
	).run(as_dict=True)


def deliverable_rows(user: str, away: list | None = None, horizon: bool = True) -> list:
	"""`pending_rows` minus the ones not worth a mail, which are stamped on the way out:
	too old to be news, or pointing at nothing the user can open (target deleted, access
	lost). A catch-up has no horizon — being days old is the whole point of it."""
	cutoff = add_to_date(now_datetime(), hours=-HORIZON_HOURS)
	keep, drop = [], []
	viewable = {}
	for row in pending_rows(user, away):
		if horizon and row.last_event_at and row.last_event_at < cutoff:
			drop.append(row)
			continue
		if not (row.discussion or row.task or row.poll or row.project or row.team):
			drop.append(row)
			continue
		if row.project:
			if row.project not in viewable:
				viewable[row.project] = can_view_space(user, row.project)
			if not viewable[row.project]:
				drop.append(row)
				continue
		keep.append(row)
	_stamp(drop)
	# Read rows are not pending any more either; stamp them so the query stays small.
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
	"""The batch mail with its own heading and the stretch it covers."""
	starts_at = min(get_datetime(p.starts_at) for p in periods)
	ends_at = max(get_datetime(p.ends_at) for p in periods)
	window = (
		f"{format_datetime(starts_at, 'EEE d MMM, h:mm a')} – {format_datetime(ends_at, 'EEE d MMM, h:mm a')}"
	)
	return {**batch_context(user, rows), "title": "While you were away", "window": window}


def batch_context(user: str, rows: list) -> dict:
	"""Mentions first, then everything else — the same item shape the digest renders."""
	avatar_map = get_user_avatar_map(row.from_user for row in rows)
	mentions = [row for row in rows if row.type in MENTION_TYPES]
	others = [row for row in rows if row.type not in MENTION_TYPES]
	return {
		"logo_url": get_url(GAMEPLAN_LOGO_PATH),
		"site_url": get_url(),
		"open_gameplan_url": get_signed_digest_url(user, "/g/notifications"),
		"preferences_url": get_digest_preferences_url(user),
		"mentions": [format_notification_item(row, avatar_map, user) for row in mentions],
		"others": [format_notification_item(row, avatar_map, user) for row in others],
	}


def _stamp(rows: list):
	if not rows:
		return
	Notification = frappe.qb.DocType("GP Notification")
	(
		frappe.qb.update(Notification)
		.set(Notification.email_sent_at, now_datetime())
		.where(Notification.name.isin([row.name for row in rows]))
	).run()


def _stamp_read(user: str):
	Notification = frappe.qb.DocType("GP Notification")
	(
		frappe.qb.update(Notification)
		.set(Notification.email_sent_at, now_datetime())
		.where(
			(Notification.to_user == user) & (Notification.read == 1) & Notification.email_sent_at.isnull()
		)
	).run()
