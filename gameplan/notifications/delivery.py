# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt


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
	local_time,
	mark_recap_sent,
	pending_recap_periods,
	profile_prefs,
	scheduled_off_window,
	user_timezone,
)
from gameplan.permissions import can_view_space

HORIZON_HOURS = 24
MENTION_TYPES = ("Mention", "Rich Quote")
TICK_MINUTES = 5


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
		_stamp(rows)
	return rows


def send_away_recap(user: str) -> list:
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


def batch_context(user: str, rows: list) -> dict:
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
