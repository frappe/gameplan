import frappe

import gameplan
from gameplan.permissions import (
	apply_accessible_project_filter,
	can_moderate_space,
	can_view_space,
	criterion_sql,
)


def submission_project(doc, *, for_update=False):
	if doc.discussion:
		return frappe.db.get_value("GP Discussion", doc.discussion, "project", for_update=for_update)
	return doc.project if frappe.db.exists("GP Project", doc.project) else None


def can_read_submission(doc, user=None, *, project=None):
	user = user or frappe.session.user
	project = project or submission_project(doc)
	return bool(
		project
		and not gameplan.is_anonymous(user)
		and can_view_space(user, project)
		and (doc.owner == user or can_moderate_space(user, project))
	)


def has_permission(doc, ptype=None, user=None, **kwargs):
	allowed = can_read_submission(doc, user)
	if not allowed and ptype in {"read", "select", "print", "export", "email", "share", "report"}:
		# Explicit shares must not override the submission's restricted audience.
		frappe.throw("This submission is unavailable", frappe.PermissionError)
	return ptype == "read" and allowed


def target_criterion(projects):
	Submission, Discussion = frappe.qb.DocType("GP Submission"), frappe.qb.DocType("GP Discussion")
	parents = frappe.qb.from_(Discussion).select(Discussion.name).where(Discussion.project.isin(projects))
	return (
		(Submission.discussion.isnull() | (Submission.discussion == "")) & Submission.project.isin(projects)
	) | Submission.discussion.isin(parents)


def query_conditions(user=None, **kwargs):
	return criterion_sql(read_criterion(user or frappe.session.user))


def file_query_conditions(user=None, **kwargs):
	File, Submission = frappe.qb.DocType("File"), frappe.qb.DocType("GP Submission")
	readable = (
		frappe.qb.from_(Submission).select(Submission.name).where(read_criterion(user or frappe.session.user))
	)
	return criterion_sql(
		File.attached_to_doctype.isnull()
		| (File.attached_to_doctype != "GP Submission")
		| File.attached_to_name.isin(readable)
	)


def read_criterion(user):
	Submission, Project, Member = [
		frappe.qb.DocType(dt) for dt in ("GP Submission", "GP Project", "GP Member")
	]
	projects = apply_accessible_project_filter(
		frappe.qb.from_(Project).select(Project.name), Project.name, user
	)
	if gameplan.is_anonymous(user):
		return Submission.name == ""
	if gameplan.is_admin(user):
		return target_criterion(projects)
	communities = (
		frappe.qb.from_(Member)
		.select(Member.parent)
		.where((Member.user == user) & (Member.parenttype == "GP Team"))
		.where((Member.is_admin == 1) | (Member.is_moderator == 1))
	)
	return ((Submission.owner == user) & target_criterion(projects)) | target_criterion(
		projects.where(Project.team.isin(communities))
	)
