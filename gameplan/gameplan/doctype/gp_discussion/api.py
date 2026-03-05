# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt


import frappe
from frappe.query_builder.functions import Count
from frappe.utils import cint
from pypika.terms import ExistsCriterion

import gameplan
from gameplan.utils import html_to_text_preview


@frappe.whitelist()
def get_discussions(filters: dict | str = None, order_by: str = None, start: int = None, limit: int = None):
	if not frappe.has_permission("GP Discussion", "read"):
		frappe.throw("Insufficient Permission for GP Discussion", frappe.PermissionError)

	filters = frappe.parse_json(filters) if filters else None
	feed_type = filters.pop("feed_type", None) if filters else None
	participator = filters.pop("participator", None) if filters else None
	limit = cint(limit)
	order_by = order_by or "last_post_at desc"
	order_field, order_direction = order_by.split(" ", 1)

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
		.where((Project.is_private == 0) | ((Project.is_private == 1) & ExistsCriterion(member_exists)))
		.limit(limit + 1)
		.offset(start or 0)
	)

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

	# default order by last_post_at desc
	query = query.orderby(Discussion[order_field], order=frappe._dict(value=order_direction))

	is_guest = gameplan.is_guest()
	if is_guest:
		GuestAccess = frappe.qb.DocType("GP Guest Access")
		project_list = GuestAccess.select(GuestAccess.project).where(GuestAccess.user == frappe.session.user)
		query = query.where(Discussion.project.isin(project_list))

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
			.where(Poll.stopped_at.isnull() | (Poll.stopped_at > frappe.utils.now()))
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
	commented_in = list(
		set(
			frappe.db.get_all(
				"GP Comment",
				fields=["reference_name"],
				filters={"reference_doctype": "GP Discussion", "owner": user},
				pluck="reference_name",
			)
		)
	)
	return Discussion.name.isin(commented_in)


def clause_discussions_bookmarked_by_user(user):
	Discussion = frappe.qb.DocType("GP Discussion")
	Bookmark = frappe.qb.DocType("GP Bookmark")
	bookmarked_discussions = Bookmark.select(Bookmark.discussion).where(Bookmark.user == user)
	return Discussion.name.isin(bookmarked_discussions)
