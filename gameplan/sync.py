"""Gameplan sync views — the enriched queries that back list pages.

Each view is a normal Python query decorated with `@view(name, depends_on=[...])`.
Depends-on doctypes auto-join Sync Log so any change to them notifies subscribers.

Phase 4 migration wires the discussion feed first (see GAMEPLAN-MIGRATION.md).
"""

from __future__ import annotations

import frappe
from frappe.sync import view


@view(
	"gameplan.discussion_feed",
	depends_on=["GP Discussion", "GP Comment", "GP Poll", "GP Project"],
)
def discussion_feed(filters=None, order_by=None, start=None, limit=None):
	"""Wraps the existing get_discussions logic but returns rows with a `name` key.

	This is intentionally minimal for the first migration — the view exists to prove
	the plumbing (subscribe, change → notify → pull, cursor catch-up) against a
	real, permission-aware enriched query.
	"""
	from gameplan.gameplan.doctype.gp_discussion.api import get_discussions

	return get_discussions(
		filters=filters,
		order_by=order_by,
		start=start,
		limit=limit,
	)
