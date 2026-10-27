# Copyright (c) 2025, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

"""Thin whitelisted unread-count endpoints.

Called from the frontend via `useDoctype('GP Unread Record').runMethod` (no dotted
module paths). The query logic lives on the GPUnreadRecord controller; these are
re-exported from gp_unread_record.py so they resolve under `GP Unread Record/<method>`.
"""

import frappe


@frappe.whitelist(methods=["GET", "POST"])
def get_unread_count(projects: list[str] = None):
	"""Return unread discussion counts for Spaces in `projects` (all if omitted)."""
	from gameplan.gameplan.doctype.gp_unread_record.gp_unread_record import GPUnreadRecord

	return GPUnreadRecord.get_unread_count_for_projects(frappe.session.user, projects)


@frappe.whitelist(methods=["GET", "POST"])
def get_participating_unread_count(team=None):
	"""Return unread counts for discussions the user takes part in, optionally in Community `team`."""
	from gameplan.gameplan.doctype.gp_unread_record.gp_unread_record import GPUnreadRecord

	return GPUnreadRecord.get_participating_unread_count(frappe.session.user, team)


@frappe.whitelist(methods=["POST"])
def mark_all_as_read_for_team(team=None, before=None):
	"""Mark discussions in a team as read.

	`before` (optional, YYYY-MM-DD) limits the action to discussions last active on or
	before that day. When omitted, every unread discussion is marked read.
	"""
	from gameplan.gameplan.doctype.gp_unread_record.gp_unread_record import GPUnreadRecord

	if not team:
		return []

	if before:
		# Reject a malformed cutoff with a controlled error instead of a 500, then clamp to
		# today so a client can't push the read watermark into the future (which would mark
		# not-yet-posted discussions read).
		try:
			before = frappe.utils.getdate(before)
		except Exception:
			frappe.throw(frappe._("Invalid date for 'before': {0}").format(before))
		before = str(min(before, frappe.utils.getdate()))

	return GPUnreadRecord.mark_all_as_read_for_team(team, frappe.session.user, before)
