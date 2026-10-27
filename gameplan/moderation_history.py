import frappe
from frappe.query_builder import Criterion
from frappe.utils import cint

from gameplan.community_bans import can_moderate_community
from gameplan.permissions import can_moderate_space


@frappe.whitelist(methods=["GET", "POST"])
def history(community: str, kind: str = "all", target: str = "", start: int = 0):
	if not can_moderate_community(community):
		frappe.throw("Only Community moderators can perform this action", frappe.PermissionError)
	if not isinstance(kind, str) or kind not in {"all", "discussion", "reply", "user"}:
		frappe.throw("Unsupported history target")
	if not isinstance(target, str) or (target and kind == "all"):
		frappe.throw("Choose a target type before filtering history")
	projects = [
		name
		for name in frappe.get_all("GP Project", filters={"team": community}, pluck="name")
		if can_moderate_space(frappe.session.user, name)
	]
	Discussion = frappe.qb.DocType("GP Discussion")
	Comment = frappe.qb.DocType("GP Comment")
	Log = frappe.qb.DocType("GP Moderation Log")
	discussions = frappe.qb.from_(Discussion).select(Discussion.name).where(Discussion.project.isin(projects))
	replies = (
		frappe.qb.from_(Comment)
		.select(Comment.name)
		.where((Comment.reference_doctype == "GP Discussion") & Comment.reference_name.isin(discussions))
	)
	post_actions = Log.action.isin(["Hide", "Restore", "Delete Spam"])
	sources = {
		"discussion": (Log.discussion.isin(discussions) & post_actions, Log.discussion),
		"reply": (Log.comment.isin(replies) & post_actions, Log.comment),
		"user": ((Log.community == community) & Log.action.isin(["Ban", "Unban"]), Log.user),
	}
	if kind == "all":
		criterion = Criterion.any(source[0] for source in sources.values())
	else:
		criterion, field = sources[kind]
		if target:
			criterion &= field == target
	# Resolve current targets before pagination. Orphan logs retain their restricted storage.
	rows = (
		frappe.qb.from_(Log)
		.select(
			Log.name, Log.action, Log.owner, Log.creation, Log.reason, Log.discussion, Log.comment, Log.user
		)
		.where(criterion)
		.orderby(Log.creation, order=frappe.qb.desc)
		.orderby(Log.name, order=frappe.qb.desc)
		.offset(max(0, cint(start)))
		.limit(41)
	).run(as_dict=True)
	return {"items": rows[:40], "has_more": len(rows) > 40}
