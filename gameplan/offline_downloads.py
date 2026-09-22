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

from datetime import datetime

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
# The newest discussions a device keeps. A 90-day window on a busy site is otherwise
# unbounded: every sync would list them all, ask the database for their changes in one
# IN clause, and fill the device with a backlog nobody scrolls to.
MAX_DISCUSSIONS = 500
CHILD_LISTS = {
	"comments": ("GP Comment", "reference"),
	"activities": ("GP Activity", "reference"),
	"polls": ("GP Poll", "discussion"),
}
# The columns a bundle will project, per list and per child table of it: what the app's own
# timeline lists ask for (frontend/src/data/discussionTimeline.ts). The device sends its
# field list so rows land in the shape its cache reads back, but only these come back.
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
ALLOWED_CHILD_FIELDS = {
	"reactions": {"name", "user", "emoji"},
	"options": {"name", "title", "idx", "percentage"},
	"votes": {"user", "option"},
}


@frappe.whitelist(methods=["POST"])
def get_offline_index(window_days: int, cached: list | str | None = None, since: str | None = None) -> dict:
	"""Discussions the device should hold for this window, newest activity first.

	`since` is when the device last finished a sync: what has changed after it comes back as
	`changed`, so a device that is already up to date asks for no bundles at all.

	`places` says where each of them sits now, for the moves no timestamp reports (see
	`_place`); a device compares it against where it filed them and fetches what disagrees.

	`cached` names other discussions the device holds from the user's own visits; the ones they
	can no longer read (deleted, or access taken away) come back as `revoked` to be removed.
	"""
	_check_rate_limit()
	window = _allowed_window(window_days)
	synced_at = now_datetime()
	since = _since(since)
	visited = _names(cached, MAX_CACHED)
	rows = _discussions_in_window(window)
	return {
		"discussions": [row.name for row in rows],
		"places": {row.name: _place(row) for row in rows},
		"changed": [row.name for row in _changed_since(rows, since)] if since else [],
		"revoked": _revoked(visited),
		"synced_at": str(synced_at),
	}


@frappe.whitelist(methods=["POST"])
def get_offline_bundle(window_days: int, fields: dict | str, names: list | str) -> dict:
	"""A page of the window's discussions, each with its comments, activity and polls.

	`names` is what the device asked for, a page's worth at a time, taken from the index:
	what it does not hold yet and what the index reported as changed. Names outside the
	window, or outside the user's reach, simply do not come back.

	`fields` maps comments/activities/polls to the field lists the app's own lists request,
	so the rows come back in exactly the shape those lists cache. Only the columns in
	ALLOWED_FIELDS come back, whatever is asked for. `rows` carries the same discussions in
	the shape the feeds render, so a Space the user has never opened still lists them offline.
	"""
	_check_rate_limit()
	window = _allowed_window(window_days)
	fields = frappe.parse_json(fields)
	if not isinstance(fields, dict):
		frappe.throw(_("Expected a field list per child table."), frappe.ValidationError)
	wanted = _names(names, PAGE_SIZE)
	names = [row.name for row in _discussions_in_window(window, names=wanted)]

	bundle = {
		"discussions": [read_doc("GP Discussion", name) for name in names],
		"rows": _feed_rows(names),
	}
	for key, (doctype, link) in CHILD_LISTS.items():
		bundle[key] = _rows_by_discussion(doctype, link, _allowed_fields(key, fields.get(key)), names)
	return bundle


def _since(value: str | None) -> datetime | None:
	"""When the device last finished a sync, or None on its first.

	`get_datetime` answers junk with a different exception for each kind of it, and with
	None for a few, so a timestamp that cannot be read is turned into one message here.
	"""
	if not value:
		return None
	try:
		since = get_datetime(value)
	except Exception:
		since = None
	if since is None:
		frappe.throw(_("Expected the time of the last sync."), frappe.ValidationError)
	return since


def _names(value: list | str | None, limit: int) -> list[str]:
	"""Discussion names as the client sent them: a list, at most `limit` long, stringified.

	A whitelisted argument arrives as whatever was posted, so the shape is checked here
	rather than left to fail somewhere further in as a traceback.
	"""
	names = frappe.parse_json(value) if isinstance(value, str) else value
	if names is None:
		return []
	if not isinstance(names, list):
		frappe.throw(_("Expected a list of discussion names."), frappe.ValidationError)
	return [str(name) for name in names[:limit] if isinstance(name, str | int)]


def _allowed_fields(key: str, fields) -> list:
	"""The columns of one child list this endpoint will project, in the order asked for.

	A name outside the contract is dropped; a value of the wrong shape is a malformed
	request and says so.
	"""
	if fields is None:
		return []  # A list the device did not ask for, which is not the same as a malformed one.
	allowed = ALLOWED_FIELDS[key]
	kept = []
	for field in _field_list(fields):
		if isinstance(field, str):
			if field in allowed:
				kept.append(field)
		elif isinstance(field, dict):
			for child, columns in field.items():
				if child not in allowed or child not in ALLOWED_CHILD_FIELDS:
					continue
				columns = [
					column
					for column in _field_list(columns)
					if isinstance(column, str) and column in ALLOWED_CHILD_FIELDS[child]
				]
				if columns:
					kept.append({child: columns})
	return kept


def _field_list(value) -> list:
	"""A field list as the client sent it. Anything but a list is not one."""
	if not isinstance(value, list):
		frappe.throw(_("Expected a list of field names."), frappe.ValidationError)
	return value


def _allowed_window(window_days: int) -> int:
	window = cint(window_days)
	if window <= 0:
		frappe.throw(_("Choose how many days to download."), frappe.ValidationError)
	return min(window, MAX_WINDOW_DAYS)


def _check_rate_limit() -> None:
	# Per user, which frappe.rate_limiter.rate_limit cannot do: it keys on the IP — a whole
	# office shares one — or on a request parameter, which the caller chooses.
	key = rate_limit_key(frappe.session.user)
	# Started with SET NX, so two requests arriving together cannot both reset the hour.
	frappe.cache.set(key, 0, ex=60 * 60, nx=True)
	if frappe.cache.incrby(key, 1) > REQUESTS_PER_HOUR:
		frappe.throw(
			_("Too many offline download requests. Try again later."),
			frappe.RateLimitExceededError,
		)


def rate_limit_key(user: str) -> bytes:
	return frappe.cache.make_key(f"gameplan:offline-downloads:{user}")


def _discussions_in_window(window: int, names: list[str] | None = None) -> list:
	"""The window's discussions, newest activity first, or only `names` from inside it.

	The index lists the whole window. A bundle only has to hold its page to the same window
	and the same reach, which is that check over the page's own names instead of listing and
	sorting the window again for every one of them.
	"""
	if names is not None and not names:
		return []
	filters = {"last_post_at": [">=", add_days(now_datetime(), -window)]}
	if names is not None:
		filters["name"] = ["in", names]
	rows = _query(
		"GP Discussion",
		fields=["name", "project", "team", "modified", "last_post_at"],
		filters=filters,
		# Pages are cut from this order, so it must not shift between requests.
		order_by="last_post_at desc, name desc",
		limit=len(names) if names is not None else MAX_DISCUSSIONS,
		criterion=frappe.qb.DocType("GP Discussion").project.isin(_downloadable_spaces()),
	)
	for row in rows:
		row.name = str(row.name)
	return rows


def _place(row) -> str:
	"""The Space and community a discussion sits in, as one comparable value.

	Moving a Space rewrites its discussions' `team` in one statement, and a merge rewrites
	their `project` through frappe's rename. Neither touches `modified`, so a device would
	keep listing them where they used to be.
	"""
	return f"{row.project}/{row.team or ''}"


def _feed_rows(names: list[str]) -> list:
	"""The page's discussions as the feeds list them, from the feeds' own endpoint."""
	if not names:
		return []
	return get_discussions(filters={"name": ["in", names]}, limit=len(names))


def _downloadable_spaces():
	"""Spaces inside the user's communities that they can open, as a subquery.

	Joining a community is what puts its content on the device; Space membership is not
	required. Access still is, so a private Space they are not in never reaches the query.

	A subquery, not a list of ids: with thousands of Spaces that IN clause costs MariaDB the
	`last_post_at` index, and it sorts the window instead of stopping at 500 (1,009 ms vs 5).
	"""
	Project = frappe.qb.DocType("GP Project")
	Member = frappe.qb.DocType("GP Member")
	joined = (
		frappe.qb.from_(Member)
		.select(Member.parent)
		.where(Member.parenttype == "GP Team")
		.where(Member.user == frappe.session.user)
	)
	query = (
		frappe.qb.from_(Project)
		.select(Project.name)
		.where(Project.team.isin(joined))
		.where(Project.archived_at.isnull())
	)
	return apply_project_query_filter(query)


def _revoked(names: list[str]) -> list[str]:
	if not names:
		return []
	readable = {str(row.name) for row in _query("GP Discussion", ["name"], {"name": ["in", names]})}
	return [name for name in names if name not in readable]


def _changed_since(rows: list, since: datetime) -> list:
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


def _changed_children(doctype: str, link_field: str, names: list[str], since: datetime) -> list[str]:
	# Permissions are already settled: `names` came from the window query, and all this
	# returns is which of those names a child row points at.
	filters = {link_field: ["in", names], "modified": [">", since]}
	if doctype == "GP Comment":
		filters["reference_doctype"] = "GP Discussion"
	return frappe.get_all(doctype, filters=filters, pluck=link_field, distinct=True)


def _rows_by_discussion(doctype: str, link: str, fields: list, names: list[str]) -> dict[str, list]:
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


def _query(
	doctype: str,
	fields: list,
	filters: dict,
	order_by: str = "creation asc",
	limit: int | None = None,
	criterion=None,
) -> list:
	"""The permission-checked list query `/api/v2/document/<doctype>` runs.

	`criterion` narrows it further, for a scope the filters cannot express.
	"""
	query = frappe.qb.get_query(
		table=doctype,
		fields=fields,
		filters=filters,
		order_by=order_by,
		limit=limit,
		ignore_permissions=False,
	)
	if criterion is not None:
		query = query.where(criterion)
	controller = get_controller(doctype)
	if hasattr(controller, "get_list"):
		query = controller.get_list(query) or query
	return query.run(as_dict=True)
