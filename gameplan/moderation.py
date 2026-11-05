import frappe
from frappe.query_builder.functions import Count
from frappe.utils import cint
from pypika.terms import ExistsCriterion

from gameplan.community_bans import can_moderate_community
from gameplan.moderation_logs import latest_logs
from gameplan.permissions import moderatable_project_names

BAN_CANDIDATE_PAGE_SIZE = 20


@frappe.whitelist(methods=["GET", "POST"])
def removed_content(community: str, doctype: str = "GP Discussion", start: int = 0):
	"""List removed content in Spaces the moderator can access."""
	if not can_moderate_community(community):
		frappe.throw("Only community moderators can perform this action", frappe.PermissionError)
	if doctype not in {"GP Discussion", "GP Comment"}:
		frappe.throw("Unsupported moderation target")
	projects = moderatable_project_names(community)
	Target = frappe.qb.DocType(doctype)
	Discussion = frappe.qb.DocType("GP Discussion")
	query = frappe.qb.from_(Target)
	if doctype == "GP Comment":
		query = query.join(Discussion).on(
			(Target.reference_doctype == "GP Discussion") & (Target.reference_name == Discussion.name)
		)
	else:
		Discussion = Target
	rows = (
		query.select(
			Target.name,
			Target.hidden_at,
			Target.spam_removed_at,
			Target.owner,
			Discussion.name.as_("discussion"),
			Discussion.project,
			Discussion.slug,
		)
		.where(Discussion.project.isin(projects))
		.where(Target.hidden_at.isnotnull() | Target.spam_removed_at.isnotnull())
		.orderby(Target.modified, order=frappe.qb.desc)
		.offset(max(0, cint(start)))
		.limit(41)
	).run(as_dict=True)
	field = "comment" if doctype == "GP Comment" else "discussion"
	Log = frappe.qb.DocType("GP Moderation Log")
	logs = (
		latest_logs([field], ["Hide", "Delete Spam"])
		.select(Log[field], Log.reason, Log.title)
		.where(Log[field].isin([str(row.name) for row in rows]))
		.run(as_dict=True)
		if rows
		else []
	)
	latest = {}
	for log in logs:
		latest.setdefault(log.get(field), log)
	for row in rows:
		log = latest.get(str(row.name), {})
		row.update(doctype=doctype, title=log.get("title") or "Reply", reason=log.get("reason"))
	return {"items": rows[:40], "has_more": len(rows) > 40}


@frappe.whitelist(methods=["GET", "POST"])
def community_bans(community: str, start: int = 0):
	"""List one page of active bans for an authorized Community moderator."""
	if not can_moderate_community(community):
		frappe.throw("Only community moderators can perform this action", frappe.PermissionError)
	Log = frappe.qb.DocType("GP Moderation Log")
	return (
		latest_logs(["community", "user"], ["Ban", "Unban"])
		.select(Log.user, Log.action, Log.reason, Log.creation)
		.where((Log.community == community) & (Log.action == "Ban"))
		.orderby(Log.creation, order=frappe.qb.desc)
		.orderby(Log.name, order=frappe.qb.desc)
		.offset(max(0, cint(start)))
		.limit(41)
		.run(as_dict=True)
	)


@frappe.whitelist(methods=["GET", "POST"])
def ban_candidates(community: str, query: str = "", after: str = ""):
	"""Return one cursor-paged list of eligible users for Community bans."""
	if not can_moderate_community(community):
		frappe.throw("Only community moderators can perform this action", frappe.PermissionError)
	query = (query or "").strip()
	if len(query) > 100:
		frappe.throw("Search text must be at most 100 characters")
	if query and len(query) < 2:
		return {"items": [], "has_more": False, "next_cursor": ""}

	User = frappe.qb.DocType("User")
	HasRole = frappe.qb.DocType("Has Role")
	Member = frappe.qb.DocType("GP Member")
	Log = frappe.qb.DocType("GP Moderation Log")

	def has_role(roles):
		# Grouping keeps MariaDB from materializing every user's roles before applying the page limit.
		return ExistsCriterion(
			frappe.qb.from_(HasRole)
			.select(HasRole.parent)
			.where((HasRole.parent == User.name) & (HasRole.parenttype == "User") & HasRole.role.isin(roles))
			.groupby(HasRole.parent)
			.having(Count(HasRole.name) > 0)
		)

	community_staff = (
		frappe.qb.from_(Member)
		.select(Member.user)
		.where((Member.parenttype == "GP Team") & (Member.parent == community))
		.where((Member.is_admin == 1) | (Member.is_moderator == 1))
	)
	active_bans = (
		latest_logs(["community", "user"], ["Ban", "Unban"])
		.select(Log.user)
		.where((Log.community == community) & (Log.action == "Ban"))
	)
	users = (
		frappe.qb.from_(User)
		.select(User.name, User.full_name, User.user_image)
		.where(has_role(["Gameplan Guest", "Gameplan Member"]))
		.where(User.name != "Administrator")
		.where(~has_role(["Gameplan Admin", "System Manager"]))
		.where(User.name.notin(community_staff))
		.where(User.name.notin(active_bans))
	)
	if query:
		escaped_query = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
		prefix = f"{escaped_query}%"
		users = users.where(
			(User.full_name.like(prefix)) | (User.email.like(prefix)) | (User.name.like(prefix))
		)
	if after:
		users = users.where(User.name > after)

	rows = users.orderby(User.name).limit(BAN_CANDIDATE_PAGE_SIZE + 1).run(as_dict=True)
	has_more = len(rows) > BAN_CANDIDATE_PAGE_SIZE
	items = rows[:BAN_CANDIDATE_PAGE_SIZE]
	return {
		"items": items,
		"has_more": has_more,
		"next_cursor": items[-1].name if has_more else "",
	}


def filter_removed_search_results(results):
	from gameplan.mixins.moderation import is_removed

	comments = {
		str(row.name): row
		for row in frappe.get_all(
			"GP Comment",
			filters={"name": ["in", [r["name"] for r in results if r["doctype"] == "GP Comment"]]},
			fields=[
				"name",
				"reference_doctype",
				"reference_name",
				"hidden_at",
				"spam_removed_at",
				"deleted_at",
			],
		)
	}
	threads = {str(r["name"]) for r in results if r["doctype"] == "GP Discussion"}
	threads.update(str(c.reference_name) for c in comments.values() if c.reference_doctype == "GP Discussion")
	visible = (
		set(
			str(name)
			for name in frappe.get_all(
				"GP Discussion",
				filters={
					"name": ["in", list(threads)],
					"hidden_at": ["is", "not set"],
					"spam_removed_at": ["is", "not set"],
				},
				pluck="name",
			)
		)
		if threads
		else set()
	)
	out = []
	for result in results:
		name = str(result["name"])
		if result["doctype"] == "GP Discussion" and name not in visible:
			continue
		if result["doctype"] == "GP Comment":
			comment = comments.get(name)
			if not comment or is_removed(comment) or comment.deleted_at:
				continue
			if comment.reference_doctype == "GP Discussion" and str(comment.reference_name) not in visible:
				continue
		out.append(result)
	return out
