# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""Bulk endpoints behind "Download for offline".

One index call says which discussions the device should hold; bundles then carry them a page
at a time, read through the same permission-checked queries the app uses. The scope is every
Space the user can open in the communities they have joined.
"""

from datetime import datetime
from typing import Literal

import frappe
from frappe.api.v2 import read_doc
from frappe.rate_limiter import rate_limit
from frappe.utils import add_days, add_to_date, now_datetime

from gameplan.gameplan.doctype.gp_discussion.api import get_discussions
from gameplan.permissions import is_member_parent

PAGE_SIZE = 20
# Visited discussions checked for lost access per request.
MAX_CACHED = 2000
# The newest discussions a device keeps, so a busy site cannot hand it an unbounded backlog.
MAX_DISCUSSIONS = 500
# Per endpoint and IP address: frappe has no per-user limiter. A first 3-month download is at
# most 26 requests, so an office of about 40 behind one address can all download in the same
# hour, and a client stuck in a loop is still stopped. The counter is keyed on `cmd`, which the
# app's `/api/method/` calls set; `/api/v2/method/` calls would share one counter.
REQUESTS_PER_HOUR = 1000
CHILD_LISTS = {"comments": "GP Comment", "activities": "GP Activity", "polls": "GP Poll"}
# The field that points each child row at its discussion.
PARENT_FIELD = {"GP Comment": "reference_name", "GP Activity": "reference_name", "GP Poll": "discussion"}

Window = Literal[7, 30, 90]
# A child list's fields as the app's timeline lists ask for them: names, or a child table's.
FieldList = list[str | dict[str, list[str]]]


@frappe.whitelist(methods=["POST"])
@rate_limit(limit=lambda: REQUESTS_PER_HOUR, seconds=60 * 60)
def get_offline_index(
	window_days: Window, cached: list[str | int] | None = None, since: datetime | None = None
) -> dict:
	"""Discussions the device should hold, newest activity first.

	`changed` lists what changed after `since`, `places` where each one sits now, and
	`revoked` which of the `cached` visited discussions the user can no longer read. `user`
	names whose answer this is, so a device never files it under another account.
	"""
	# A minute early, so a change committed while this request reads is caught next time.
	synced_at = add_to_date(now_datetime(), minutes=-1)
	# The app sends back the server's own naive timestamp; one with a zone is read the same way.
	since = since and since.replace(tzinfo=None)
	rows = _discussions_in_window(window_days)
	return {
		"user": frappe.session.user,
		"discussions": [row.name for row in rows],
		"places": {row.name: _place(row) for row in rows},
		"changed": [row.name for row in _changed_since(rows, since)] if since else [],
		"revoked": _revoked([str(name) for name in (cached or [])[:MAX_CACHED]]),
		"synced_at": str(synced_at),
	}


@frappe.whitelist(methods=["POST"])
@rate_limit(limit=lambda: REQUESTS_PER_HOUR, seconds=60 * 60)
def get_offline_bundle(window_days: Window, fields: dict[str, FieldList], names: list[str | int]) -> dict:
	"""A page of discussions with their comments, activity and polls, plus the rows the feeds
	render. `names` outside the window or the user's reach are skipped. `user` is as for the
	index.
	"""
	wanted = [str(name) for name in names[:PAGE_SIZE]]
	names = [row.name for row in _discussions_in_window(window_days, names=wanted)]

	bundle = {
		"user": frappe.session.user,
		"discussions": [read_doc("GP Discussion", name) for name in names],
		"rows": _feed_rows(names),
	}
	for key, doctype in CHILD_LISTS.items():
		bundle[key] = _rows_by_discussion(doctype, fields.get(key), names)
	return bundle


def _discussions_in_window(window: int, names: list[str] | None = None) -> list:
	"""The window's discussions, newest activity first, or just `names` from inside it."""
	if names is not None and not names:
		return []
	filters = {"last_post_at": [">=", add_days(now_datetime(), -window)]}
	if names is not None:
		filters["name"] = ["in", names]
	rows = frappe.get_list(
		"GP Discussion",
		fields=["name", "project", "team", "modified", "last_post_at"],
		filters=[filters, frappe.qb.DocType("GP Discussion").project.isin(_joined_spaces())],
		# Pages are cut from this order, so it must not shift between requests.
		order_by="last_post_at desc, name desc",
		limit=len(names) if names is not None else MAX_DISCUSSIONS,
	)
	for row in rows:
		row.name = str(row.name)
	return rows


def _place(row) -> str:
	"""Where a discussion sits. Moving or merging a Space rewrites this without touching
	`modified`, so the device compares it to catch those moves."""
	return f"{row.project}/{row.team or ''}"


def _feed_rows(names: list[str]) -> list:
	"""The page's discussions as the feeds' own endpoint lists them."""
	if not names:
		return []
	return get_discussions(filters={"name": ["in", names]}, limit=len(names))


def _joined_spaces():
	"""Unarchived Spaces in the communities the user joined, as a subquery. `get_list`
	applies the permission to read each discussion on top.

	Not a list of ids: with thousands of Spaces that IN clause costs MariaDB the
	`last_post_at` index and a filesort (1,009 ms against 5).
	"""
	Project = frappe.qb.DocType("GP Project")
	return (
		frappe.qb.from_(Project)
		.select(Project.name)
		.where(is_member_parent("GP Team", Project.team, frappe.session.user))
		.where(Project.archived_at.isnull())
	)


def _revoked(names: list[str]) -> list[str]:
	"""The visited discussions the user can no longer read. Held to read access rather than
	download scope: a public community they never joined is still theirs to read."""
	if not names:
		return []
	readable = {
		str(name) for name in frappe.get_list("GP Discussion", filters={"name": ["in", names]}, pluck="name")
	}
	return [name for name in names if name not in readable]


def _changed_since(rows: list, since: datetime) -> list:
	"""Discussions edited, replied to or reacted in after `since`. A reaction or vote saves
	the comment or poll, not the discussion, so those are checked too."""
	names = [row.name for row in rows]
	if not names:
		return []
	changed = {
		str(name)
		for doctype in ("GP Comment", "GP Poll")
		for name in _changed_children(doctype, names, since)
	}
	return [
		row
		for row in rows
		if row.name in changed or row.modified > since or (row.last_post_at and row.last_post_at > since)
	]


def _child_filters(doctype: str, names: list[str]) -> tuple[str, dict]:
	"""The field pointing `doctype` rows at their discussion, and a filter for `names`."""
	parent = PARENT_FIELD[doctype]
	filters = {parent: ["in", names]}
	if parent == "reference_name":
		filters["reference_doctype"] = "GP Discussion"
	return parent, filters


def _changed_children(doctype: str, names: list[str], since: datetime) -> list[str]:
	# No permission check needed: `names` already came from the permission-checked window.
	parent, filters = _child_filters(doctype, names)
	filters["modified"] = [">", since]
	return frappe.get_all(doctype, filters=filters, pluck=parent, distinct=True)


def _rows_by_discussion(doctype: str, fields: FieldList | None, names: list[str]) -> dict[str, list]:
	grouped = {name: [] for name in names}
	if not names or not fields:
		return grouped
	parent, filters = _child_filters(doctype, names)
	# Read under an alias to group by, whether or not the requested fields include it.
	rows = frappe.get_list(
		doctype, fields=[*fields, f"{parent} as _offline_parent"], filters=filters, order_by="creation asc"
	)
	for row in rows:
		discussion = str(row.pop("_offline_parent"))
		if discussion in grouped:
			grouped[discussion].append(row)
	return grouped
