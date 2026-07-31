# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt


import frappe
from frappe import _
from frappe.query_builder.functions import Count
from frappe.utils import cint, cstr
from pypika.terms import ExistsCriterion

from gameplan.gameplan.doctype.gp_poll.gp_poll import ongoing_polls_clause
from gameplan.permissions import apply_accessible_project_filter
from gameplan.utils import html_to_text_preview

# `order_by` arrives from the client and both halves of it end up in the SQL — the field
# as a column and the direction as a bare keyword — so only these get through. The list
# is exactly what the app sorts feeds by: the three choices in the "Sort by" select
# (Discussions.vue), the pinned strip's `pinned_at desc` (DiscussionList.vue), and `name`
# as the stable order a pager needs when two rows share a timestamp.
SORTABLE_FIELDS = frozenset({"last_post_at", "creation", "pinned_at", "name"})
SORT_DIRECTIONS = frozenset({"asc", "desc"})

DEFAULT_ORDER_BY = "last_post_at desc"


def parse_order_by(order_by) -> tuple[str, str]:
	"""Split a client-supplied `<field> [asc|desc]` into a pair that is safe to splice in.

	Anything else is a rejected request, not a traceback. The old `order_by.split(" ", 1)`
	failed in two different ways: a bare field (`last_post_at`) had nothing to unpack and
	raised a 500, while a third token never burst the unpack at all — maxsplit kept it in
	the direction half, so `last_post_at desc, name asc` quietly reached the database as
	trailing ORDER BY SQL. Both halves are now checked against a fixed list, and a bare
	field means descending, which is how Frappe's own query engine reads a directionless
	`order_by` (`frappe.database.query.Engine._validate_order_by`). The query string can
	also hand us a list rather than a string, so the value is stringified first.
	"""
	tokens = cstr(order_by).split()
	if len(tokens) == 1:
		tokens.append("desc")

	if len(tokens) == 2 and tokens[0] in SORTABLE_FIELDS and tokens[1].lower() in SORT_DIRECTIONS:
		return tokens[0], tokens[1].lower()

	frappe.throw(
		_("Discussions can only be sorted by {0}, ascending or descending.").format(
			", ".join(sorted(SORTABLE_FIELDS))
		)
	)


def parse_offset(start) -> int:
	"""Turn the client's `start` into a number that is safe to splice into OFFSET.

	It used to go in as whatever the client sent, so `start="1); DROP TABLE ..."` was
	spliced into the statement verbatim and the database refused the query. A negative
	offset is a syntax error on MariaDB — invisible to a SQLite test run — so it is
	clamped here rather than sent.
	"""
	return max(cint(start), 0)


def parse_filters(filters) -> dict:
	"""Decode the client's `filters` into the mapping the rest of this endpoint assumes.

	`feed_type` and `participator` are lifted out by key before the remainder is handed
	to the query builder, so a JSON list — a shape the query builder itself accepts —
	used to reach `.pop()` and raise a 500. Field names, operators and values inside the
	mapping are the query builder's own business: it rejects fieldnames outside
	`[A-Za-z0-9_]`, looks operators up in a fixed map, and escapes values.
	"""
	filters = frappe.parse_json(filters) if filters else None
	if filters is None:
		return {}

	if not isinstance(filters, dict):
		frappe.throw(_("Discussion filters must be an object of field names and values."))

	return filters


@frappe.whitelist()
def get_discussions(filters=None, order_by=None, start=None, limit=None):
	if not frappe.has_permission("GP Discussion", "read"):
		frappe.throw("Insufficient Permission for GP Discussion", frappe.PermissionError)

	filters = parse_filters(filters)
	feed_type = filters.pop("feed_type", None) if filters else None
	participator = filters.pop("participator", None) if filters else None
	limit = cint(limit)
	start = parse_offset(start)
	order_field, order_direction = parse_order_by(order_by or DEFAULT_ORDER_BY)

	Discussion = frappe.qb.DocType("GP Discussion")
	Project = frappe.qb.DocType("GP Project")
	Member = frappe.qb.DocType("GP Member")
	UnreadRecord = frappe.qb.DocType("GP Unread Record")

	member_exists = (
		frappe.qb.from_(Member)
		.select(Member.name)
		.where(Member.parenttype == "GP Project")
		.where(Member.parent == Project.name)
		.where(Member.user == frappe.session.user)
	)
	query = (
		frappe.qb.get_query(
			Discussion,
			fields=[Discussion.star, Project.title.as_("project_title")],
			filters=filters,
		)
		.left_join(Project)
		.on(Discussion.project == Project.name)
		.where(Project.archived_at.isnull())
		.limit(limit + 1)
		.offset(start)
	)
	query = apply_accessible_project_filter(query, Discussion.project)

	if participator:
		query = query.where(clause_discussions_commented_by_user(participator))

	if feed_type == "bookmarks":
		query = query.where(clause_discussions_bookmarked_by_user(frappe.session.user))

	if feed_type == "unread":
		unread_record_exists = (
			frappe.qb.from_(UnreadRecord)
			.select(UnreadRecord.name)
			.where(
				(UnreadRecord.user == frappe.session.user)
				& (UnreadRecord.discussion == Discussion.name)
				& (UnreadRecord.is_unread == 1)
			)
		)
		query = query.where(ExistsCriterion(unread_record_exists))

	if feed_type == "following":
		query = query.where(ExistsCriterion(member_exists))

	if feed_type == "participating":
		query = query.where(
			(Discussion.owner == frappe.session.user)
			| clause_discussions_commented_by_user(frappe.session.user)
		)

	query = query.orderby(Discussion[order_field], order=frappe._dict(value=order_direction))

	discussions = query.run(as_dict=1)
	has_next_page = len(discussions) > limit
	discussions = discussions[:limit]

	discussions = include_unread_counts(discussions)
	discussions = include_ongoing_polls(discussions)
	discussions = include_last_post_content(discussions)

	frappe.response["has_next_page"] = has_next_page
	return discussions


def include_unread_counts(discussions):
	"""Add unread counts to discussions with a single query"""
	if not discussions:
		return discussions

	discussion_names = [d.name for d in discussions]
	UnreadRecord = frappe.qb.DocType("GP Unread Record")

	# Get unread counts for all discussions in one query
	unread_counts = (
		frappe.qb.from_(UnreadRecord)
		.select(UnreadRecord.discussion, Count(UnreadRecord.name).as_("unread_count"))
		.where(
			(UnreadRecord.user == frappe.session.user)
			& (UnreadRecord.discussion.isin(discussion_names))
			& (UnreadRecord.is_unread == 1)
		)
		.groupby(UnreadRecord.discussion)
		.run(as_dict=1)
	)

	unread_map = {str(row.discussion): row.unread_count for row in unread_counts}

	# Add unread counts to discussions
	for discussion in discussions:
		discussion["unread"] = unread_map.get(str(discussion.name), 0)

	return discussions


def include_ongoing_polls(discussions):
	Poll = frappe.qb.DocType("GP Poll")
	discussion_names = [d.name for d in discussions]
	ongoing_polls = (
		(
			frappe.qb.from_(Poll)
			.select(Poll.name, Poll.owner, Poll.discussion)
			.where(ongoing_polls_clause(Poll))
			.where(Poll.discussion.isin(discussion_names))
			.orderby(Poll.creation, order=frappe._dict(value="asc"))
			.run(as_dict=1)
		)
		if discussion_names
		else []
	)
	for discussion in discussions:
		discussion["ongoing_polls"] = [p for p in ongoing_polls if str(p.discussion) == str(discussion.name)]
	return discussions


def include_last_post_content(discussions):
	"""Attach a one-line preview of each discussion's newest post.

	The two sides of the lookup are keyed differently by the schema, so the `cint` below
	is load-bearing rather than defensive. `GP Comment` and `GP Poll` are `autoincrement`
	doctypes, so their `name` comes back from the database as an integer, while
	`GP Discussion.last_post` is a Dynamic Link — a varchar — and comes back as `"41"`.
	Keying the maps on the raw name and coercing the discussion side is what makes the
	two meet; normalising the other direction instead would work equally well, but doing
	neither silently drops every preview.
	"""
	Comment = frappe.qb.DocType("GP Comment")

	last_comments_name = [d.last_post for d in discussions if d.last_post_type == "GP Comment"]
	last_comments_content = (
		frappe.qb.from_(Comment)
		.select(Comment.content, Comment.name)
		.where(Comment.name.isin(last_comments_name))
		.run(as_dict=1)
		if last_comments_name
		else []
	)
	last_comments_content_map = {c.name: c.content for c in last_comments_content}

	Poll = frappe.qb.DocType("GP Poll")
	last_polls_name = [d.last_post for d in discussions if d.last_post_type == "GP Poll"]
	last_poll_title = (
		frappe.qb.from_(Poll)
		.select(Poll.name, Poll.title)
		.where(Poll.name.isin(last_polls_name))
		.run(as_dict=1)
		if last_polls_name
		else []
	)
	last_poll_title_map = {p.name: p.title for p in last_poll_title}

	for discussion in discussions:
		if discussion.last_post_type == "GP Comment":
			discussion.last_comment_content = html_to_text_preview(
				last_comments_content_map.get(cint(discussion.last_post))
			)
		if discussion.last_post_type == "GP Poll":
			discussion.last_poll_title = last_poll_title_map.get(cint(discussion.last_post))

		if not discussion.last_post:
			discussion.last_post_by = discussion.owner
			discussion.last_comment_content = html_to_text_preview(discussion.content)

	return discussions


def clause_discussions_commented_by_user(user):
	Discussion = frappe.qb.DocType("GP Discussion")
	Comment = frappe.qb.DocType("GP Comment")
	commented_in = (
		frappe.qb.from_(Comment)
		.select(Comment.reference_name)
		.where((Comment.reference_doctype == "GP Discussion") & (Comment.owner == user))
	)
	return Discussion.name.isin(commented_in)


def clause_discussions_bookmarked_by_user(user):
	Discussion = frappe.qb.DocType("GP Discussion")
	Bookmark = frappe.qb.DocType("GP Bookmark")
	bookmarked_discussions = Bookmark.select(Bookmark.discussion).where(Bookmark.user == user)
	return Discussion.name.isin(bookmarked_discussions)
