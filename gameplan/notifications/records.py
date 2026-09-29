# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt


import frappe

from gameplan.notifications.away import get_active_away_period

TARGET_FIELDS = ("discussion", "comment", "poll", "task")
ROW_FIELDS = TARGET_FIELDS + ("project", "team")


def target_fields(doc) -> dict:
	"""The columns a notification about `doc` fills: what it points at, and the Space it
	sits in when that cannot be fetched from a discussion."""
	if doc.doctype == "GP Discussion":
		return {"discussion": doc.name}
	if doc.doctype == "GP Poll":
		return {"poll": doc.name, "discussion": doc.discussion}
	if doc.doctype == "GP Task":
		return {"task": doc.name, "project": doc.project}
	if doc.doctype == "GP Comment":
		if doc.reference_doctype == "GP Discussion":
			return {"comment": doc.name, "discussion": doc.reference_name}
		if doc.reference_doctype == "GP Task":
			return {
				"comment": doc.name,
				"task": doc.reference_name,
				"project": frappe.db.get_value("GP Task", doc.reference_name, "project"),
			}
		return {"comment": doc.name}
	return {}


def content_key(doc) -> dict:
	"""Filters that find the row about `doc` itself. A discussion excludes its polls and
	comments, whose rows carry the discussion too so the inbox can route them."""
	if doc.doctype == "GP Discussion":
		return {"discussion": doc.name, "poll": ["is", "not set"], "comment": ["is", "not set"]}
	if doc.doctype == "GP Poll":
		return {"poll": doc.name, "discussion": doc.discussion}
	if doc.doctype == "GP Comment":
		return {"comment": doc.name}
	raise ValueError(f"no notification identity for {doc.doctype}")


def write_or_merge(
	*,
	to_user: str,
	type: str,
	message: str,
	merge: bool = False,
	merged_message: str | None = None,
	from_user: str | None = None,
	**targets,
):
	"""Write a notification row, or fold this event into the unread one already there.

	`targets` names what the row points at (TARGET_FIELDS) and may carry the Space and
	Community; both are derived from the discussion when they are not given.
	"""
	unknown = set(targets) - set(ROW_FIELDS)
	if unknown:
		raise TypeError(f"unexpected notification fields: {sorted(unknown)}")

	points_at = {field: targets.get(field) for field in TARGET_FIELDS}
	project, team = space_for(points_at["discussion"], targets.get("project"), targets.get("team"))
	existing = _unread_row_for(to_user, type, points_at) if merge else None

	if existing:
		doc = frappe.get_doc("GP Notification", existing)
		doc.event_count = (doc.event_count or 1) + 1
		doc.message = (merged_message or message).replace("{count}", str(doc.event_count))
		doc.from_user = None
	else:
		doc = frappe.get_doc(doctype="GP Notification", to_user=to_user, type=type, **points_at)
		doc.event_count = 1
		doc.message = message
		doc.from_user = from_user

	doc.project = project
	doc.team = team
	doc.last_event_at = frappe.utils.now()
	doc.read = 0
	doc.email_sent_at = None
	doc.email_skipped_at = None
	doc.away_period = get_active_away_period(to_user)
	doc.flags.ignore_permissions = True
	doc.save()
	return doc


def space_for(discussion: str | None, project=None, team=None) -> tuple:
	if discussion and not project:
		project = frappe.db.get_value("GP Discussion", discussion, "project")
	if project and not team:
		team = frappe.db.get_value("GP Project", project, "team")
	return project, team


def repoint_discussion(discussion: str, project, team) -> None:
	Notification = frappe.qb.DocType("GP Notification")
	(
		frappe.qb.update(Notification)
		.set(Notification.project, project)
		.set(Notification.team, team)
		.where(Notification.discussion == str(discussion))
	).run()


def _unread_row_for(to_user: str, type: str, points_at: dict) -> str | None:
	filters = {"to_user": to_user, "type": type, "read": 0}
	for field in TARGET_FIELDS:
		filters[field] = points_at[field] or ["is", "not set"]
	return frappe.db.get_value("GP Notification", filters, "name")
