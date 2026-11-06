import frappe
from frappe.query_builder import Criterion

from gameplan.community_bans import can_moderate_community
from gameplan.paging import page_start
from gameplan.permissions import moderatable_project_names

BAN_HISTORY_USER_PAGE_SIZE = 20


@frappe.whitelist(methods=["GET", "POST"])
def ban_users(community: str, query: str = "", after: str = ""):
	if not can_moderate_community(community):
		frappe.throw("Only community moderators can perform this action", frappe.PermissionError)
	query = (query or "").strip()
	if len(query) > 100:
		frappe.throw("Search text must be at most 100 characters")
	if query and len(query) < 2:
		return {"items": [], "has_more": False, "next_cursor": ""}

	User = frappe.qb.DocType("User")
	Log = frappe.qb.DocType("GP Moderation Log")
	community_bans = (
		frappe.qb.from_(Log)
		.select(Log.user)
		.where((Log.community == community) & Log.action.isin(["Ban", "Unban"]))
	)
	users = frappe.qb.from_(User).select(User.name, User.full_name, User.user_image).where(
		User.name.isin(community_bans)
	)
	if query:
		escaped_query = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
		prefix = f"{escaped_query}%"
		users = users.where(
			(User.full_name.like(prefix)) | (User.email.like(prefix)) | (User.name.like(prefix))
		)
	if after:
		users = users.where(User.name > after)

	rows = users.orderby(User.name).limit(BAN_HISTORY_USER_PAGE_SIZE + 1).run(as_dict=True)
	has_more = len(rows) > BAN_HISTORY_USER_PAGE_SIZE
	items = rows[:BAN_HISTORY_USER_PAGE_SIZE]
	return {
		"items": items,
		"has_more": has_more,
		"next_cursor": items[-1].name if has_more else "",
	}


@frappe.whitelist(methods=["GET", "POST"])
def history(community: str, kind: str = "all", target: str = "", start: int = 0):
	if not can_moderate_community(community):
		frappe.throw("Only Community moderators can perform this action", frappe.PermissionError)
	if not isinstance(kind, str) or kind not in {"all", "discussion", "reply", "user"}:
		frappe.throw("Unsupported history target")
	if not isinstance(target, str) or (target and kind == "all"):
		frappe.throw("Choose a target type before filtering history")
	projects = moderatable_project_names(community)
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
		.offset(page_start(start))
		.limit(41)
	).run(as_dict=True)
	return {"items": rows[:40], "has_more": len(rows) > 40}
