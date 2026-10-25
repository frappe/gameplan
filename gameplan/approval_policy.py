import frappe
from frappe.query_builder.functions import Count
from frappe.utils import cint

from gameplan.approval_files import publishing_submission
from gameplan.community_bans import can_moderate_community
from gameplan.permissions import get_content_project, require_can_manage_community


@frappe.whitelist(methods=["GET", "POST"])
def get_policy(community: str):
	require_can_manage_community(community)
	return cint(frappe.db.get_value("GP Team", community, "approval_post_count"))


@frappe.whitelist(methods=["POST"])
def set_policy(community: str, count: int):
	require_can_manage_community(community)
	if not 0 <= count <= 100:
		frappe.throw("Choose an approval threshold between 0 and 100")
	frappe.get_doc("GP Team", community, for_update=True).db_set("approval_post_count", count)
	return count


def needs_approval(doc):
	project = get_content_project(doc)
	if not project:
		return False
	community = frappe.db.get_value("GP Project", project, "team")
	threshold = cint(frappe.db.get_value("GP Team", community, "approval_post_count"))
	if not threshold or can_moderate_community(community):
		return False
	return counter(community).accepted < threshold


def guard_publication(doc, method=None):
	if not supports_approval(doc):
		return
	publication = publishing_submission.get()
	if publication and publication[0] is doc:
		return
	if needs_approval(doc):
		frappe.throw("Submit this content through the approval queue", frappe.PermissionError)


def record_accepted(doc, method=None):
	if not supports_approval(doc):
		return
	community = frappe.db.get_value("GP Project", get_content_project(doc), "team")
	if not community:
		return
	# Existing counters keep earning contributions even while the policy is disabled.
	if not frappe.db.exists("GP Approval Counter", {"community": community, "user": frappe.session.user}):
		return
	row = counter(community)
	frappe.db.set_value("GP Approval Counter", row.name, "accepted", row.accepted + 1)


def supports_approval(doc):
	return doc.doctype == "GP Discussion" or (
		doc.doctype == "GP Comment" and doc.reference_doctype == "GP Discussion"
	)


def counter(community):
	user = frappe.session.user
	frappe.db.get_value("User", user, "name", for_update=True)
	row = frappe.db.get_value(
		"GP Approval Counter",
		{"community": community, "user": user},
		["name", "accepted"],
		as_dict=True,
		for_update=True,
	)
	if row:
		return row
	Project, Discussion, Comment = [
		frappe.qb.DocType(dt) for dt in ("GP Project", "GP Discussion", "GP Comment")
	]
	projects = frappe.qb.from_(Project).select(Project.name).where(Project.team == community)
	discussions = (
		frappe.qb.from_(Discussion)
		.where(Discussion.project.isin(projects))
		.where(Discussion.hidden_at.isnull() & Discussion.spam_removed_at.isnull())
	)
	accepted = (
		discussions.select(Count(Discussion.name)).where(Discussion.owner == user).for_update().run()[0][0]
	)
	accepted += (
		frappe.qb.from_(Comment)
		.select(Count(Comment.name))
		.where(
			(Comment.reference_doctype == "GP Discussion")
			& Comment.reference_name.isin(discussions.select(Discussion.name))
		)
		.where(
			(Comment.owner == user)
			& Comment.deleted_at.isnull()
			& Comment.hidden_at.isnull()
			& Comment.spam_removed_at.isnull()
		)
		.for_update()
		.run()[0][0]
	)
	row = frappe.get_doc(doctype="GP Approval Counter", community=community, user=user, accepted=accepted)
	row.insert(ignore_permissions=True)
	return frappe._dict(name=row.name, accepted=accepted)


def delete_counters(doc, method=None):
	field = "community" if doc.doctype == "GP Team" else "user"
	frappe.db.delete("GP Approval Counter", {field: doc.name})
