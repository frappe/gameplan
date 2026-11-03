import frappe

from gameplan.permissions import (
	get_content_project,
	is_global_admin,
)


def can_moderate_community(community, user=None, *, for_update=False):
	import gameplan

	user = user or frappe.session.user
	if gameplan.is_anonymous(user) or gameplan.is_guest(user):
		return False
	if is_global_admin(user):
		return True
	member = frappe.db.get_value(
		"GP Member",
		{"parenttype": "GP Team", "parent": community, "user": user},
		["is_admin", "is_moderator"],
		as_dict=True,
		for_update=for_update,
	)
	return bool(member and (member.is_admin or member.is_moderator))


def is_banned(community, user=None, *, for_update=False):
	user = user or frappe.session.user
	if not community or user == "Guest" or is_global_admin(user):
		return False
	from gameplan.restrictions import active, current_state

	return active(current_state(user, community))


def banned_communities(user):
	if is_global_admin(user):
		return []
	from gameplan.restrictions import active_condition

	Restriction = frappe.qb.DocType("GP User Restriction")
	return (
		frappe.qb.from_(Restriction)
		.select(Restriction.community)
		.where((Restriction.user == user) & (Restriction.community != "") & active_condition(Restriction))
		.run(pluck=True)
	)


def content_is_banned(doc, user=None):
	project = get_content_project(doc)
	return bool(project and is_banned(frappe.db.get_value("GP Project", project, "team"), user))


def require_participation(doc):
	from gameplan.mixins.moderation import discussion_is_removed, is_removed, parent_discussion

	if content_is_banned(doc):
		frappe.throw("You are banned from participating in this community", frappe.PermissionError)
	if is_removed(doc) or discussion_is_removed(parent_discussion(doc)):
		frappe.throw("Restore this content before participating", frappe.PermissionError)


def validate_participation(doc, method=None):
	if doc.doctype not in {"GP Discussion", "GP Comment", "GP Poll", "GP Page", "GP Task"}:
		return
	before = doc.get_doc_before_save()
	# Ignore server-maintained counters, but guard both ends of moves and all user edits.
	fields = {
		"title",
		"content",
		"description",
		"project",
		"reference_doctype",
		"reference_name",
		"discussion",
		"closed_at",
		"pinned_at",
		"stopped_at",
		"options",
		"votes",
		"status",
	}
	if doc.is_new() or any(doc.has_value_changed(field) for field in fields if doc.meta.has_field(field)):
		require_participation(doc)
		if before:
			require_participation(before)


@frappe.whitelist(methods=["POST"])
def set_ban(
	community: str,
	user: str,
	banned: int,
	reason: str = "",
	expires_at: str = "",
	expected_modified: str | None = None,
):
	"""Set, change or lift a Community participation ban with an optional expiry."""
	from gameplan.restrictions import set_restriction

	return set_restriction(user, banned, reason, community, expires_at, expected_modified)
