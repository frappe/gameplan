# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

"""The email channel: one mail an hour, per user who asked for email, with everything
that arrived since the last one.

Every notification is a `GP Notification` row first; this only decides which rows also
go out by mail. A row is sent once (`email_sent_at`), and a row that no longer needs
sending — read in the app already, written while the user was away (the card covers
those), older than the horizon, or pointing at something the user can no longer open —
is stamped without a mail so the next run does not pick it up again.
"""

import frappe
from frappe.utils import add_to_date, get_url, now_datetime

from gameplan.email_digest import (
	GAMEPLAN_LOGO_PATH,
	format_notification_item,
	get_digest_preferences_url,
	get_signed_digest_url,
	get_user_avatar_map,
)
from gameplan.permissions import can_view_space

HORIZON_HOURS = 24
MENTION_TYPES = ("Mention", "Rich Quote")


def send_hourly_batches():
	"""Scheduler entry: a batch for every user whose channel is Email."""
	users = frappe.get_all(
		"GP User Profile", filters={"notification_channel": "Email", "enabled": 1}, pluck="user"
	)
	for user in users:
		if not frappe.db.get_value("User", user, "enabled"):
			continue
		send_batch(user)


def send_batch(user: str) -> list:
	"""Send `user` their pending rows in one mail. Returns the rows that were sent."""
	rows = deliverable_rows(user)
	if rows:
		send_batch_email(user, rows)
		_stamp(rows)
	return rows


def pending_rows(user: str) -> list:
	"""Unsent, unread rows that did not arrive during an away stretch."""
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
			"away_period": ["is", "not set"],
		},
		order_by="last_event_at desc",
		ignore_permissions=True,
	).run(as_dict=True)


def deliverable_rows(user: str) -> list:
	"""`pending_rows` minus the ones not worth a mail, which are stamped on the way out:
	too old to be news, or pointing at nothing the user can open (target deleted, access
	lost)."""
	horizon = add_to_date(now_datetime(), hours=-HORIZON_HOURS)
	keep, drop = [], []
	viewable = {}
	for row in pending_rows(user):
		if row.last_event_at and row.last_event_at < horizon:
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
