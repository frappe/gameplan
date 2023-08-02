# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe
import gameplan
from pypika.terms import ExistsCriterion


@frappe.whitelist()
def get_discussions(filters=None, order_by=None, limit_start=None, limit_page_length=None):
	if not frappe.has_permission("GP Discussion", "read"):
		frappe.throw("Insufficient Permission for GP Discussion", frappe.PermissionError)

	filters = frappe.parse_json(filters) if filters else None
	feed_type = filters.pop("feed_type", None) if filters else None
	participator = filters.pop("participator", None) if filters else None
	order_by = order_by or "last_post_at desc"
	order_field, order_direction = order_by.split(" ", 1)

	Discussion = frappe.qb.DocType("GP Discussion")
	Visit = frappe.qb.DocType("GP Discussion Visit")
	Project = frappe.qb.DocType("GP Project")
	Team = frappe.qb.DocType("GP Team")
	Member = frappe.qb.DocType("GP Member")
	member_exists = (
		frappe.qb.from_(Member)
		.select(Member.name)
		.where(Member.parenttype == "GP Team")
		.where(Member.parent == Project.team)
		.where(Member.user == frappe.session.user)
	)
	query = (
		frappe.qb.from_(Discussion)
		.select(Discussion.star, Visit.last_visit, Project.title.as_("project_title"), Team.title.as_("team_title"))
		.left_join(Visit)
		.on((Discussion.name == Visit.discussion) & (Visit.user == frappe.session.user))
		.left_join(Project)
		.on(Discussion.project == Project.name)
		.left_join(Team)
		.on(Discussion.team == Team.name)
		.where((Project.is_private == 0) | ((Project.is_private == 1) & ExistsCriterion(member_exists)))
		.limit(limit_page_length)
		.offset(limit_start or 0)
	)
	if filters:
		for key in filters:
			query = query.where(Discussion[key] == filters[key])

		# order by pinned_at desc if project is selected
		if filters.get("project"):
			query = query.orderby(Discussion.pinned_at, order=frappe._dict(value="desc"))

	if participator:
		replies = frappe.db.get_all(
			"GP Comment",
			fields=["reference_name"],
			filters={"reference_doctype": "GP Discussion", "owner": participator},
			pluck="reference_name",
		)
		if not replies:
			return []
		replies = list(set(replies))
		query = query.where(Discussion.name.isin(replies))

	if feed_type == "unread":
		query = query.where((Visit.last_visit < Discussion.last_post_at) | (Visit.last_visit.isnull()))

	if feed_type == "following":
		FollowedProject = frappe.qb.DocType("GP Followed Project")
		followed_projects = FollowedProject.select(FollowedProject.project).where(FollowedProject.user == frappe.session.user)
		query = query.where(Discussion.project.isin(followed_projects))

	# default order by last_post_at desc
	query = query.orderby(Discussion[order_field], order=frappe._dict(value=order_direction))

	is_guest = gameplan.is_guest()
	if is_guest:
		GuestAccess = frappe.qb.DocType("GP Guest Access")
		project_list = GuestAccess.select(GuestAccess.project).where(GuestAccess.user == frappe.session.user)
		query = query.where(Discussion.project.isin(project_list))

	discussions = query.run(as_dict=1)
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
