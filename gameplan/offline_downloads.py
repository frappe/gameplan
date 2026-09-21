# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""Bulk endpoints behind "Download for offline" (Settings > Preferences).

One index call tells the device which discussions to keep, then the bundle is fetched a page
at a time. Each page carries a page of discussions with their comments, activity and polls,
plus the rows the discussion lists render, read through the same permission-checked queries
the app itself uses, so the device can file them straight into the caches the pages already
read from.

The scope is a community the user has joined: every Space in it they can open, whether or
not they are a member of that Space, because a Space joined later is one they could already
read.
"""

import frappe
from frappe import _
from frappe.api.v2 import read_doc
from frappe.model.base_document import get_controller
from frappe.utils import add_days, cint, get_datetime, now_datetime

from gameplan.gameplan.doctype.gp_discussion.api import get_discussions
from gameplan.permissions import apply_project_query_filter

PAGE_SIZE = 20
# The longest window the app offers (3 months).
MAX_WINDOW_DAYS = 90
# A 90-day download of a busy site is a few dozen pages. This only stops a runaway client.
REQUESTS_PER_HOUR = 200
# Visited discussions checked for lost access in one request.
MAX_CACHED = 2000
CHILD_LISTS = {
	"comments": ("GP Comment", "reference"),
	"activities": ("GP Activity", "reference"),
	"polls": ("GP Poll", "discussion"),
}


@frappe.whitelist(methods=["POST"])
def get_offline_index(window_days, cached=None, since=None):
	"""Discussions the device should hold for this window, newest activity first.

	`since` is when the device last finished a sync: what has changed after it comes back as
	`changed`, so a device that is already up to date asks for no bundles at all.

	`cached` names other discussions the device holds from the user's own visits; the ones they
	can no longer read (deleted, or access taken away) come back as `revoked` to be removed.
	"""
	window = _allowed_window(window_days)
	synced_at = now_datetime()
	rows = _discussions_in_window(window)
	return {
		"discussions": [row.name for row in rows],
		"changed": [row.name for row in _changed_since(rows, get_datetime(since))] if since else [],
		"revoked": _revoked(frappe.parse_json(cached) or []),
		"synced_at": str(synced_at),
	}


@frappe.whitelist(methods=["POST"])
def get_offline_bundle(window_days, fields, names):
	"""A page of the window's discussions, each with its comments, activity and polls.

	`names` is what the device asked for, a page's worth at a time, taken from the index:
	what it does not hold yet and what the index reported as changed. Names outside the
	window, or outside the user's reach, simply do not come back.

	`fields` maps comments/activities/polls to the field lists the app's own lists request,
	so the rows come back in exactly the shape those lists cache. `rows` carries the same
	discussions in the shape the feeds render, so a Space the user has never opened still
	lists them offline.
	"""
	window = _allowed_window(window_days)
	fields = frappe.parse_json(fields)
	wanted = {str(name) for name in frappe.parse_json(names)[:PAGE_SIZE]}
	names = [row.name for row in _discussions_in_window(window) if row.name in wanted]

	bundle = {
		"discussions": [read_doc("GP Discussion", name) for name in names],
		"rows": _feed_rows(names),
	}
	for key, (doctype, link) in CHILD_LISTS.items():
		bundle[key] = _rows_by_discussion(doctype, link, fields.get(key), names)
	return bundle


def _allowed_window(window_days):
	_check_rate_limit()
	window = cint(window_days)
	if window <= 0:
		frappe.throw(_("Choose how many days to download."), frappe.ValidationError)
	return min(window, MAX_WINDOW_DAYS)


def _check_rate_limit():
	# Per user rather than frappe's per-IP limiter: a whole office shares one address.
	key = rate_limit_key(frappe.session.user)
	if not frappe.cache.get(key):
		frappe.cache.setex(key, 60 * 60, 0)
	if frappe.cache.incrby(key, 1) > REQUESTS_PER_HOUR:
		frappe.throw(
			_("Too many offline download requests. Try again later."),
			frappe.RateLimitExceededError,
		)


def rate_limit_key(user):
	return frappe.cache.make_key(f"gameplan:offline-downloads:{user}")


def _discussions_in_window(window):
	spaces = _downloadable_spaces()
	if not spaces:
		return []
	rows = _query(
		"GP Discussion",
		fields=["name", "modified", "last_post_at"],
		filters={
			"project": ["in", spaces],
			"last_post_at": [">=", add_days(now_datetime(), -window)],
		},
		# Pages are cut from this order, so it must not shift between requests.
		order_by="last_post_at desc, name desc",
	)
	for row in rows:
		row.name = str(row.name)
	return rows


def _feed_rows(names):
	"""The page's discussions as the feeds list them, from the feeds' own endpoint."""
	if not names:
		return []
	return get_discussions(filters={"name": ["in", names]}, limit=len(names))


def _downloadable_spaces():
	"""Spaces inside the user's communities that they can open.

	Joining a community is what puts its content on the device; Space membership is not
	required. Access still is, so a private Space they are not in never reaches the query.
	"""
	communities = frappe.get_all(
		"GP Member",
		filters={"parenttype": "GP Team", "user": frappe.session.user},
		pluck="parent",
	)
	if not communities:
		return []
	Project = frappe.qb.DocType("GP Project")
	query = (
		frappe.qb.from_(Project)
		.select(Project.name)
		.where(Project.team.isin(communities))
		.where(Project.archived_at.isnull())
	)
	return [str(name) for name in apply_project_query_filter(query).run(pluck=True)]


def _revoked(names):
	names = [str(name) for name in names[:MAX_CACHED]]
	if not names:
		return []
	readable = {str(row.name) for row in _query("GP Discussion", ["name"], {"name": ["in", names]})}
	return [name for name in names if name not in readable]


def _changed_since(rows, since):
	"""Discussions edited, replied to or reacted in after `since`.

	A reaction or poll vote saves the comment or poll it belongs to, not the discussion.
	"""
	names = [row.name for row in rows]
	if not names:
		return []
	changed = {str(name) for name in _changed_children("GP Comment", "reference_name", names, since)}
	changed |= {str(name) for name in _changed_children("GP Poll", "discussion", names, since)}
	return [
		row
		for row in rows
		if row.name in changed or row.modified > since or (row.last_post_at and row.last_post_at > since)
	]


def _changed_children(doctype, link_field, names, since):
	filters = {link_field: ["in", names], "modified": [">", since]}
	if doctype == "GP Comment":
		filters["reference_doctype"] = "GP Discussion"
	return frappe.get_all(doctype, filters=filters, pluck=link_field, distinct=True)


def _rows_by_discussion(doctype, link, fields, names):
	grouped = {name: [] for name in names}
	if not names or not fields:
		return grouped
	if link == "reference":
		filters = {"reference_doctype": "GP Discussion", "reference_name": ["in", names]}
		link_field = "reference_name"
	else:
		filters = {link: ["in", names]}
		link_field = link
	# The link column is read separately so it's there to group by even when the app's own
	# field list leaves it out; it's dropped again before the rows are handed back.
	for row in _query(doctype, fields=[*fields, f"{link_field} as _offline_parent"], filters=filters):
		parent = str(row.pop("_offline_parent"))
		if parent in grouped:
			grouped[parent].append(row)
	return grouped


def _query(doctype, fields, filters, order_by="creation asc"):
	"""The permission-checked list query `/api/v2/document/<doctype>` runs, without paging."""
	query = frappe.qb.get_query(
		table=doctype,
		fields=fields,
		filters=filters,
		order_by=order_by,
		ignore_permissions=False,
	)
	controller = get_controller(doctype)
	if hasattr(controller, "get_list"):
		query = controller.get_list(query) or query
	return query.run(as_dict=True)
