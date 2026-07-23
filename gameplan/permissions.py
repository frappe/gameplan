import frappe
from frappe import _
from frappe.utils import cint

import gameplan

READ_PERMISSIONS = {"read", "select", "print", "email", "export", "share", "report"}


def require_can_manage_community(team, user=None):
	user = user or frappe.session.user
	if not can_manage_community(user, team):
		frappe.throw(_("Only community admins can perform this action"), frappe.PermissionError)


def require_can_manage_space_members(project, user=None):
	user = user or frappe.session.user
	if not can_manage_space(user, project):
		frappe.throw(_("Only space managers can perform this action"), frappe.PermissionError)


def require_can_invite_guest(project, user=None):
	user = user or frappe.session.user
	if not can_invite_guest(user, project):
		frappe.throw(_("Only space managers can invite guests"), frappe.PermissionError)


def team_has_permission(doc, ptype="read", user=None, **kwargs):
	user = user or frappe.session.user
	if ptype in READ_PERMISSIONS:
		return can_view_community(user, doc)
	if ptype in {"write", "delete"}:
		return can_manage_community(user, doc)
	return True


def project_has_permission(doc, ptype="read", user=None, **kwargs):
	user = user or frappe.session.user
	if ptype in READ_PERMISSIONS:
		return can_view_space(user, doc)
	if ptype in {"write", "delete"}:
		return can_manage_space(user, doc)
	return True


def content_has_permission(doc, ptype="read", user=None, **kwargs):
	user = user or frappe.session.user
	if ptype in READ_PERMISSIONS:
		return can_view_content(user, doc)
	if ptype == "create":
		return can_create_content(user, doc)
	if ptype == "write":
		return can_edit_content(user, doc)
	if ptype == "delete":
		return can_delete_content(user, doc)
	return True


def can_manage_community(user, team):
	if is_global_admin(user):
		return True
	team_name = get_doc_name(team)
	return is_community_admin(user, team_name)


def can_view_community(user, team):
	if is_global_admin(user):
		return True
	if gameplan.is_guest(user):
		return False
	team_name = get_doc_name(team)
	is_private = (
		team.is_private
		if hasattr(team, "doctype")
		else frappe.db.get_value("GP Team", team_name, "is_private")
	)
	if not cint(is_private):
		return True
	return is_community_member(user, team_name)


def can_view_space(user, project):
	if is_global_admin(user):
		return True
	project = get_project_info(project)
	if not project:
		return False
	if gameplan.is_guest(user):
		return has_guest_access(user, project.name)
	if cint(project.is_private):
		return is_space_member(user, project.name)
	return can_view_community(user, project.team)


def can_manage_space(user, project):
	if is_global_admin(user):
		return True
	project = get_project_info(project)
	if not project:
		return False
	if cint(project.is_private):
		return is_space_member(user, project.name)
	return is_community_admin(user, project.team)


def can_invite_guest(user, project):
	if gameplan.is_guest(user):
		return False
	return can_manage_space(user, project)


def can_view_content(user, doc):
	project = get_content_project(doc)
	if project:
		return can_view_space(user, project)
	if is_global_admin(user):
		return True
	return get_doc_value(doc, "owner") == user


def can_create_content(user, doc):
	if gameplan.is_guest(user):
		return doc.doctype == "GP Comment" and can_view_content(user, doc)
	if not get_content_project(doc):
		return is_global_admin(user) or not get_doc_value(doc, "owner") or get_doc_value(doc, "owner") == user
	return can_view_content(user, doc)


def can_edit_content(user, doc):
	if is_global_admin(user):
		return True
	if not can_view_content(user, doc):
		return False
	if gameplan.is_guest(user):
		# Guests are participants in the spaces they're granted, but only on their
		# OWN content — they may edit posts/comments they authored, never anyone
		# else's. (Reacting is a view-level action, gated in HasReactions.react,
		# not an edit — so it is not routed through this write gate.)
		return get_doc_value(doc, "owner") == user
	# Gameplan is community-driven: content inside a space is owned by the
	# community, so any member who can access the space may edit it (and run
	# lifecycle actions like pin/close that route through the write gate).
	# Personal content with no space stays editable only by its owner.
	if get_content_project(doc):
		return True
	return get_doc_value(doc, "owner") == user


def can_delete_content(user, doc):
	if is_global_admin(user):
		return True
	if gameplan.is_guest(user):
		return False
	if not can_view_content(user, doc):
		return False
	if get_doc_value(doc, "owner") == user:
		return True
	project = get_content_project(doc)
	if not project:
		return False
	project_info = get_project_info(project)
	return bool(project_info and is_community_admin(user, project_info.team))


def team_query_conditions(user=None, **kwargs):
	user = user or frappe.session.user
	Team = frappe.qb.DocType("GP Team")
	return criterion_sql(team_access_criterion(Team, user))


def project_query_conditions(user=None, **kwargs):
	user = user or frappe.session.user
	Project = frappe.qb.DocType("GP Project")
	return criterion_sql(project_access_criterion(Project, user))


def discussion_query_conditions(user=None, **kwargs):
	return content_project_query_conditions("GP Discussion", user)


def task_query_conditions(user=None, **kwargs):
	return content_project_query_conditions("GP Task", user)


def page_query_conditions(user=None, **kwargs):
	user = user or frappe.session.user
	if is_global_admin(user):
		return None
	Page = frappe.qb.DocType("GP Page")
	criterion = (Page.project.isnull() & (Page.owner == user)) | accessible_project_criterion(
		Page.project, user
	)
	return criterion_sql(criterion)


def comment_query_conditions(user=None, **kwargs):
	user = user or frappe.session.user
	if is_global_admin(user):
		return None

	Comment = frappe.qb.DocType("GP Comment")
	Discussion = frappe.qb.DocType("GP Discussion")
	Task = frappe.qb.DocType("GP Task")
	discussion_query = (
		frappe.qb.from_(Discussion)
		.select(Discussion.name)
		.where(accessible_project_criterion(Discussion.project, user))
	)
	task_query = (
		frappe.qb.from_(Task).select(Task.name).where(accessible_project_criterion(Task.project, user))
	)
	criterion = (
		(Comment.reference_doctype == "GP Discussion") & Comment.reference_name.isin(discussion_query)
	) | ((Comment.reference_doctype == "GP Task") & Comment.reference_name.isin(task_query))
	return criterion_sql(criterion)


def draft_query_conditions(user=None, **kwargs):
	# Drafts are private to their owner in list/report queries. Share-by-link still works:
	# that reads a single draft by name through the doctype's open `read` permission, which
	# this does not touch — only enumeration (list/report) is scoped. Mirrors GPDraft.get_list
	# (the v2 query path); this closes the v1 frappe.client.get_list path, which does not invoke
	# the controller get_list for non-virtual doctypes and so was returning every user's drafts.
	user = user or frappe.session.user
	Draft = frappe.qb.DocType("GP Draft")
	return criterion_sql(Draft.owner == user)


def content_project_query_conditions(doctype, user=None):
	user = user or frappe.session.user
	if is_global_admin(user):
		return None
	DocType = frappe.qb.DocType(doctype)
	return criterion_sql(accessible_project_criterion(DocType.project, user))


def team_access_criterion(Team, user=None):
	user = user or frappe.session.user
	if is_global_admin(user):
		return None
	if gameplan.is_guest(user):
		return Team.name == ""
	return (Team.is_private == 0) | is_member_parent("GP Team", Team.name, user)


def project_access_criterion(Project, user=None):
	user = user or frappe.session.user
	if is_global_admin(user):
		return None
	if gameplan.is_guest(user):
		GuestAccess = frappe.qb.DocType("GP Guest Access")
		return Project.name.isin(
			frappe.qb.from_(GuestAccess).select(GuestAccess.project).where(GuestAccess.user == user)
		)
	return ((Project.is_private == 0) & Project.team.isin(accessible_team_query(user))) | is_member_parent(
		"GP Project", Project.name, user
	)


def accessible_project_criterion(project_field, user=None):
	user = user or frappe.session.user
	if is_global_admin(user):
		return None
	return project_field.isin(accessible_project_query(user))


def apply_accessible_project_filter(query, project_field, user=None):
	criterion = accessible_project_criterion(project_field, user)
	if criterion is None:
		return query
	return query.where(criterion)


def apply_team_query_filter(query, user=None):
	"""Restrict a GP Team list query to the teams the user may see."""
	Team = frappe.qb.DocType("GP Team")
	criterion = team_access_criterion(Team, user)
	return query.where(criterion) if criterion is not None else query


def apply_project_query_filter(query, user=None):
	"""Restrict a GP Project list query to the projects the user may see."""
	Project = frappe.qb.DocType("GP Project")
	criterion = project_access_criterion(Project, user)
	return query.where(criterion) if criterion is not None else query


def accessible_project_query(user=None):
	user = user or frappe.session.user
	Project = frappe.qb.DocType("GP Project")
	query = frappe.qb.from_(Project).select(Project.name)
	criterion = project_access_criterion(Project, user)
	if criterion is not None:
		query = query.where(criterion)
	return query


def accessible_team_query(user=None):
	user = user or frappe.session.user
	Team = frappe.qb.DocType("GP Team")
	query = frappe.qb.from_(Team).select(Team.name)
	criterion = team_access_criterion(Team, user)
	if criterion is not None:
		query = query.where(criterion)
	return query


def is_member_parent(parenttype, parent_field, user):
	Member = frappe.qb.DocType("GP Member")
	member_query = (
		frappe.qb.from_(Member)
		.select(Member.parent)
		.where(Member.parenttype == parenttype)
		.where(Member.user == user)
	)
	return parent_field.isin(member_query)


def criterion_sql(criterion):
	return criterion.get_sql(quote_char="`", with_namespace=True) if criterion is not None else None


def is_global_admin(user):
	return gameplan.is_admin(user)


def is_community_member(user, team):
	return bool(frappe.db.exists("GP Member", {"parenttype": "GP Team", "parent": team, "user": user}))


def is_community_admin(user, team):
	return bool(
		frappe.db.exists(
			"GP Member",
			{"parenttype": "GP Team", "parent": team, "user": user, "is_admin": 1},
		)
	)


def is_space_member(user, project):
	return bool(frappe.db.exists("GP Member", {"parenttype": "GP Project", "parent": project, "user": user}))


def has_guest_access(user, project):
	return bool(frappe.db.exists("GP Guest Access", {"user": user, "project": project}))


def get_content_project(doc):
	if doc.doctype in {"GP Discussion", "GP Task", "GP Page"}:
		return get_doc_value(doc, "project")
	if doc.doctype != "GP Comment":
		return None
	if doc.reference_doctype in {"GP Discussion", "GP Task"}:
		return frappe.db.get_value(doc.reference_doctype, doc.reference_name, "project")
	return None


def get_project_info(project):
	if hasattr(project, "doctype"):
		return frappe._dict(
			name=project.name,
			team=project.team,
			is_private=project.is_private,
		)
	if not project:
		return None
	return frappe.db.get_value("GP Project", project, ["name", "team", "is_private"], as_dict=True)


def get_doc_name(doc_or_name):
	return doc_or_name.name if hasattr(doc_or_name, "doctype") else doc_or_name


def get_doc_value(doc, fieldname):
	if hasattr(doc, "doctype"):
		return doc.get(fieldname)
	return None
