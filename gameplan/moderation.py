import frappe
from frappe.utils import cint

from gameplan.community_bans import can_moderate_community
from gameplan.permissions import can_moderate_space


@frappe.whitelist(methods=["GET", "POST"])
def removed_content(community: str, doctype: str = "GP Discussion", start: int = 0):
	"""List removed content in Spaces the moderator can access."""
	if not can_moderate_community(community):
		frappe.throw("Only community moderators can perform this action", frappe.PermissionError)
	if doctype not in {"GP Discussion", "GP Comment"}:
		frappe.throw("Unsupported moderation target")
	projects = [
		name
		for name in frappe.get_all("GP Project", filters={"team": community}, pluck="name")
		if can_moderate_space(frappe.session.user, name)
	]
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
	logs = (
		frappe.get_all(
			"GP Moderation Log",
			filters={
				field: ["in", [str(row.name) for row in rows]],
				"action": ["in", ["Hide", "Delete Spam"]],
			},
			fields=[field, "reason", "title"],
			order_by="creation desc, name desc",
		)
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
def community_bans(community: str):
	"""List active participation bans for an authorized Community moderator."""
	if not can_moderate_community(community):
		frappe.throw("Only community moderators can perform this action", frappe.PermissionError)
	logs = frappe.get_all(
		"GP Moderation Log",
		filters={"community": community, "action": ["in", ["Ban", "Unban"]]},
		fields=["user", "action", "reason", "creation"],
		order_by="creation desc, name desc",
	)
	latest = {}
	for row in logs:
		latest.setdefault(row.user, row)
	return [row for row in latest.values() if row.action == "Ban"]


def reindex_discussion_replies(discussion):
	from frappe.search.sqlite_search import update_doc_index

	for name in frappe.get_all(
		"GP Comment",
		filters={"reference_doctype": "GP Discussion", "reference_name": discussion},
		pluck="name",
	):
		update_doc_index(frappe.get_doc("GP Comment", name))


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
