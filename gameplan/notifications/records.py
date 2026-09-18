# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

"""Writing GP Notification rows, including the merge of repeat events into one row."""

import frappe

from gameplan.notifications.away import get_active_away_period

# The link columns that make up a row's identity for merging. `from_user` and `message`
# are deliberately not part of it: a second commenter merges into the first one's row.
TARGET_FIELDS = ("discussion", "comment", "poll", "task")


def write_or_merge(
	*,
	to_user: str,
	type: str,
	message: str,
	merge: bool,
	merged_message: str | None = None,
	from_user: str | None = None,
	discussion: str | None = None,
	comment: str | None = None,
	poll: str | None = None,
	task: str | None = None,
	project: str | None = None,
	team: str | None = None,
):
	"""Write a notification row for `to_user`, or fold the event into an existing one.

	With `merge`, an UNREAD row for the same `(to_user, type, target)` is reused: its
	`event_count` and `last_event_at` move forward, `message` becomes `merged_message`
	with `{count}` filled in (so it describes the row as it now stands), and `from_user`
	is dropped because the row no longer belongs to one sender. A row the user has already
	read is left alone and a fresh row starts — "2 new comments" must never quietly absorb
	the five they read last week.

	`project` and `team` are derived from `discussion` when not given so every row can be
	filtered by space and community; `GP Notification` declares them as fetch_from, but
	that only fires when the row is inserted through a document, and callers pass them
	explicitly anyway to keep merged rows honest after a discussion moves.

	Returns the saved document.
	"""
	values = frappe._dict(
		to_user=to_user,
		type=type,
		discussion=discussion,
		comment=comment,
		poll=poll,
		task=task,
	)
	if discussion and not project:
		project = frappe.db.get_value("GP Discussion", discussion, "project")
	if project and not team:
		team = frappe.db.get_value("GP Project", project, "team")

	now = frappe.utils.now()
	existing = _unread_row_for(values) if merge else None
	if existing:
		doc = frappe.get_doc("GP Notification", existing)
		doc.event_count = (doc.event_count or 1) + 1
		doc.last_event_at = now
		# `replace`, not `str.format`: a discussion title can legitimately contain braces.
		doc.message = (merged_message or message).replace("{count}", str(doc.event_count))
		doc.from_user = None
		doc.read = 0
		doc.project = project
		doc.team = team
		# A row that started while the user was reachable keeps saying so; one that
		# started away stays with its stretch even if that stretch has since ended.
		if not doc.away_period:
			doc.away_period = get_active_away_period(to_user)
		doc.flags.ignore_permissions = True
		doc.save()
		return doc

	doc = frappe.get_doc(doctype="GP Notification")
	doc.update(values)
	doc.from_user = from_user
	doc.message = message
	doc.project = project
	doc.team = team
	doc.last_event_at = now
	doc.event_count = 1
	doc.away_period = get_active_away_period(to_user)
	doc.insert(ignore_permissions=True)
	return doc


def _unread_row_for(values: frappe._dict) -> str | None:
	filters = {"to_user": values.to_user, "type": values.type, "read": 0}
	for field in TARGET_FIELDS:
		# "is not set" rather than == None: a NULL target has to match a NULL target, and
		# a plain None filter is dropped by the query builder.
		filters[field] = values[field] if values[field] else ["is", "not set"]
	return frappe.db.get_value("GP Notification", filters, "name")
