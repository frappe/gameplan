# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""Bulk endpoints behind "Download for offline".

One index call says which discussions the device should hold; bundles then carry them a page
at a time, read through the same permission-checked queries the app uses. The scope is every
Space the user can open in the communities they have joined.
"""

from datetime import datetime

import frappe
from frappe import _
from frappe.api.v2 import read_doc
from frappe.utils import add_days, now_datetime

from gameplan.gameplan.doctype.gp_discussion.api import get_discussions
from gameplan.permissions import apply_project_query_filter, is_member_parent

PAGE_SIZE = 20
MAX_WINDOW_DAYS = 90
# A full 90-day download is a few dozen requests; this only stops a runaway client.
REQUESTS_PER_HOUR = 200
# Visited discussions checked for lost access per request.
MAX_CACHED = 2000
# The newest discussions a device keeps, so a busy site cannot hand it an unbounded backlog.
MAX_DISCUSSIONS = 500
CHILD_LISTS = {"comments": "GP Comment", "activities": "GP Activity", "polls": "GP Poll"}
# The field that points each child row at its discussion.
PARENT_FIELD = {"GP Comment": "reference_name", "GP Activity": "reference_name", "GP Poll": "discussion"}
# What the app's own timeline lists request (frontend/src/data/discussionTimeline.ts); nothing
# else is projected, whatever the device asks for.
ALLOWED_FIELDS = {
	"comments": {"name", "content", "owner", "creation", "modified", "edited_at", "deleted_at", "reactions"},
	"activities": {"name", "user", "action", "data", "creation"},
	"polls": {
		"name",
		"title",
		"anonymous",
		"multiple_answers",
		"creation",
		"owner",
		"stopped_at",
		"options",
		"votes",
		"reactions",
	},
}
# A child list's fields as the device asks for them: names, or a child table with its own.
FieldList = list[str | dict[str, list[str]]]
ALLOWED_CHILD_FIELDS = {
	"reactions": {"name", "user", "emoji"},
	"options": {"name", "title", "idx", "percentage"},
	"votes": {"user", "option"},
}


@frappe.whitelist(methods=["POST"])
def get_offline_index(
	window_days: int, cached: list[str | int] | None = None, since: datetime | None = None
) -> dict:
	"""Discussions the device should hold, newest activity first.

	`changed` lists what changed after `since`, `places` where each one sits now, and
	`revoked` which of the `cached` visited discussions the user can no longer read. The
	arguments are type-checked by frappe from these annotations before the body runs.
	"""
	_check_rate_limit()
	window = _allowed_window(window_days)
	synced_at = now_datetime()
	# The app sends back the server's own naive timestamp; one with a zone is read the same way.
	since = since and since.replace(tzinfo=None)
	visited = [str(name) for name in (cached or [])[:MAX_CACHED]]
	rows = _discussions_in_window(window)
	return {
		"discussions": [row.name for row in rows],
		"places": {row.name: _place(row) for row in rows},
		"changed": [row.name for row in _changed_since(rows, since)] if since else [],
		"revoked": _revoked(visited),
		"synced_at": str(synced_at),
	}


@frappe.whitelist(methods=["POST"])
def get_offline_bundle(window_days: int, fields: dict[str, FieldList], names: list[str | int]) -> dict:
	"""A page of discussions with their comments, activity and polls, plus the rows the feeds
	render. `names` outside the window or the user's reach are skipped, and `fields` is held
	to ALLOWED_FIELDS.
	"""
	_check_rate_limit()
	window = _allowed_window(window_days)
	wanted = [str(name) for name in names[:PAGE_SIZE]]
	names = [row.name for row in _discussions_in_window(window, names=wanted)]

	bundle = {
		"discussions": [read_doc("GP Discussion", name) for name in names],
		"rows": _feed_rows(names),
	}
	for key, doctype in CHILD_LISTS.items():
		bundle[key] = _rows_by_discussion(doctype, _allowed_fields(key, fields.get(key)), names)
	return bundle


def _allowed_fields(key: str, fields: FieldList | None) -> list:
	"""The requested columns of one child list that ALLOWED_FIELDS permits, in order."""
	allowed = ALLOWED_FIELDS[key]
	kept = []
	for field in fields or []:
		if isinstance(field, str):
			if field in allowed:
				kept.append(field)
			continue
		for child, columns in field.items():
			columns = (
				[c for c in columns if c in ALLOWED_CHILD_FIELDS.get(child, ())] if child in allowed else []
			)
			if columns:
				kept.append({child: columns})
	return kept


def _allowed_window(window: int) -> int:
	if window <= 0:
		frappe.throw(_("Choose how many days to download."), frappe.ValidationError)
	return min(window, MAX_WINDOW_DAYS)


def _check_rate_limit() -> None:
	# Per user, which frappe.rate_limiter.rate_limit cannot key on. SET NX so two requests
	# arriving together cannot both reset the hour.
	key = rate_limit_key(frappe.session.user)
	frappe.cache.set(key, 0, ex=60 * 60, nx=True)
	if frappe.cache.incrby(key, 1) > REQUESTS_PER_HOUR:
		frappe.throw(
			_("Too many offline download requests. Try again later."),
			frappe.RateLimitExceededError,
		)


def rate_limit_key(user: str) -> bytes:
	return frappe.cache.make_key(f"gameplan:offline-downloads:{user}")


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
		filters=[filters, frappe.qb.DocType("GP Discussion").project.isin(_downloadable_spaces())],
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


def _downloadable_spaces():
	"""Unarchived Spaces the user can open in the communities they joined, as a subquery.

	Not a list of ids: with thousands of Spaces that IN clause costs MariaDB the
	`last_post_at` index and a filesort (1,009 ms against 5).
	"""
	Project = frappe.qb.DocType("GP Project")
	query = (
		frappe.qb.from_(Project)
		.select(Project.name)
		.where(is_member_parent("GP Team", Project.team, frappe.session.user))
		.where(Project.archived_at.isnull())
	)
	return apply_project_query_filter(query)


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


def _rows_by_discussion(doctype: str, fields: list, names: list[str]) -> dict[str, list]:
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
