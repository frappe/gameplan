# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt


import frappe

from gameplan.notifications.away import get_active_away_period

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
		doc.message = (merged_message or message).replace("{count}", str(doc.event_count))
		doc.from_user = None
		doc.read = 0
		doc.project = project
		doc.team = team
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
		filters[field] = values[field] if values[field] else ["is", "not set"]
	return frappe.db.get_value("GP Notification", filters, "name")
