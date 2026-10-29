import frappe
from frappe.utils import cint

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
	if not community or is_global_admin(user):
		return False
	# Membership is deliberately not involved: leaving and rejoining cannot clear a ban.
	return (
		frappe.db.get_value(
			"GP Moderation Log",
			{"community": community, "user": user, "action": ["in", ["Ban", "Unban"]]},
			"action",
			order_by="creation desc, name desc",
			for_update=for_update,
		)
		== "Ban"
	)


def banned_communities(user):
	if is_global_admin(user):
		return []
	rows = frappe.get_all(
		"GP Moderation Log",
		filters={"user": user, "action": ["in", ["Ban", "Unban"]]},
		fields=["community", "action"],
		order_by="creation desc, name desc",
	)
	latest = {}
	for row in rows:
		latest.setdefault(row.community, row.action)
	return [community for community, action in latest.items() if action == "Ban"]


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
def set_ban(community: str, user: str, banned: int, reason: str = ""):
	if not can_moderate_community(community):
		frappe.throw("Only community moderators can perform this action", frappe.PermissionError)
	frappe.get_doc("GP Team", community, for_update=True)
	if not can_moderate_community(community, for_update=True):
		frappe.throw("Only community moderators can perform this action", frappe.PermissionError)
	if not frappe.db.exists("User", user) or user == "Guest":
		frappe.throw("Choose an existing user")
	if cint(banned) and can_moderate_community(community, user, for_update=True):
		frappe.throw("Remove the community staff role before banning this user")
	if bool(cint(banned)) == is_banned(community, user, for_update=True):
		return
	if cint(banned) and (not isinstance(reason, str) or not reason.strip() or len(reason) > 500):
		frappe.throw("Enter a reason of at most 500 characters")
	frappe.get_doc(
		doctype="GP Moderation Log",
		community=community,
		user=user,
		action="Ban" if cint(banned) else "Unban",
		reason=reason.strip(),
	).insert(ignore_permissions=True)

	from gameplan.realtime import USERS_CHANGED

	frappe.realtime.publish_realtime(USERS_CHANGED, user=user, after_commit=True)
