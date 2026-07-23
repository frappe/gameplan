# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt


import frappe
from frappe import _
from frappe.query_builder.functions import Count
from frappe.utils import split_emails, validate_email_address

import gameplan
from gameplan.utils import validate_type


def require_admin():
	"""Gate an endpoint to admins only. Raises PermissionError (HTTP 403) otherwise."""
	if not gameplan.is_admin():
		frappe.throw(_("Only admins can perform this action"), frappe.PermissionError)


@frappe.whitelist(allow_guest=True)
def get_user_info(user=None):
	if frappe.session.user == "Guest":
		frappe.throw("Authentication failed", exc=frappe.AuthenticationError)

	filters = {"roles.role": ["like", "Gameplan %"]}
	if user:
		filters["name"] = user

	users = frappe.qb.get_query(
		"User",
		filters=filters,
		fields=["name", "email", "enabled", "user_image", "full_name", "user_type", "creation"],
		order_by="full_name asc",
		distinct=True,
	).run(as_dict=1)

	# Get discussion counts for last 3 months
	Discussion = frappe.qb.DocType("GP Discussion")
	discussion_counts = (
		frappe.qb.from_(Discussion)
		.select(Discussion.owner, Count(Discussion.name).as_("count"))
		.where(Discussion.creation >= frappe.utils.add_months(frappe.utils.now(), -3))
		.where(Discussion.owner.isin([u.name for u in users]))
		.groupby(Discussion.owner)
	).run(as_dict=1)
	discussion_count_map = {d.owner: d.count for d in discussion_counts}

	# Get comment counts for last 3 months
	Comment = frappe.qb.DocType("GP Comment")
	comment_counts = (
		frappe.qb.from_(Comment)
		.select(Comment.owner, Count(Comment.name).as_("count"))
		.where(Comment.creation >= frappe.utils.add_months(frappe.utils.now(), -3))
		.where(Comment.owner.isin([u.name for u in users]))
		.groupby(Comment.owner)
	).run(as_dict=1)
	comment_count_map = {c.owner: c.count for c in comment_counts}

	roles = frappe.db.get_all("Has Role", filters={"parenttype": "User"}, fields=["role", "parent"])
	user_profiles = frappe.db.get_all(
		"GP User Profile",
		fields=[
			"user",
			"name",
			"image",
			"image_background_color",
			"is_image_background_removed",
			"bio",
			"community_order",
			"quick_reaction_emojis",
			"sidebar_badge_style",
			"email_digest_frequency",
			"email_digest_day_of_week",
			"email_digest_last_sent_on",
		],
		filters={"user": ["in", [u.name for u in users]]},
	)
	user_profile_map = {u.user: u for u in user_profiles}
	for user in users:
		if frappe.session.user == user.name:
			user.session_user = True
		user_profile = user_profile_map.get(user.name)
		if user_profile:
			user.user_profile = user_profile.name
			user.user_image = user_profile.image
			user.image_background_color = user_profile.image_background_color
			user.is_image_background_removed = user_profile.is_image_background_removed
			user.bio = user_profile.bio
			if frappe.session.user == user.name:
				user.community_order = user_profile.community_order
				user.quick_reaction_emojis = user_profile.quick_reaction_emojis
				user.sidebar_badge_style = user_profile.sidebar_badge_style
				user.email_digest_frequency = user_profile.email_digest_frequency
				user.email_digest_day_of_week = user_profile.email_digest_day_of_week
				user.email_digest_last_sent_on = user_profile.email_digest_last_sent_on
		user_roles = [r.role for r in roles if r.parent == user.name]
		user.role = None
		for role in ["Gameplan Guest", "Gameplan Member", "Gameplan Admin"]:
			if role in user_roles:
				user.role = role

		# Add discussion and comment counts
		user.discussions_count_3m = discussion_count_map.get(user.name, 0)
		user.comments_count_3m = comment_count_map.get(user.name, 0)

	# Guests get the directory for @-mentions/avatars but not other members' emails.
	if gameplan.is_guest():
		for user in users:
			user.pop("email", None)

	return users


@frappe.whitelist(methods=["POST"])
@validate_type
def invite_by_email(emails: str, role: str, projects: list = None):
	require_admin()
	if role not in ["Gameplan Guest", "Gameplan Member", "Gameplan Admin"]:
		frappe.throw(_("Invalid role: {0}").format(role), frappe.ValidationError)
	return _invite_by_email(emails, role, projects)


def _invite_by_email(emails: str, role: str, projects: list = None):
	"""Core invite logic, callable from trusted server code (e.g. onboarding).

	The public invite_by_email wrapper adds the admin gate + role allowlist; this
	helper assumes the caller has already authorized the invite and validated role.
	"""
	if not emails:
		return
	email_string = validate_email_address(emails, throw=False)
	email_list = split_emails(email_string)
	if not email_list:
		return
	existing_members = frappe.db.get_all("User", filters={"email": ["in", email_list]}, pluck="email")
	existing_invites = frappe.db.get_all(
		"GP Invitation",
		filters={
			"email": ["in", email_list],
			"role": ["in", ["Gameplan Admin", "Gameplan Member"]],
		},
		pluck="email",
	)

	if role == "Gameplan Guest":
		to_invite = list(set(email_list) - set(existing_invites))
	else:
		to_invite = list(set(email_list) - set(existing_members) - set(existing_invites))

	if projects:
		projects = frappe.as_json(projects, indent=None)

	for email in to_invite:
		frappe.get_doc(doctype="GP Invitation", email=email, role=role, projects=projects).insert(
			ignore_permissions=True
		)


@frappe.whitelist()
def unread_notifications():
	res = frappe.db.get_all(
		"GP Notification",
		[{"COUNT": "name", "as": "count"}],
		{"to_user": frappe.session.user, "read": 0},
	)
	return res[0].count


@frappe.whitelist(allow_guest=True)
@validate_type
def accept_invitation(key: str = None):
	if not key:
		frappe.throw("Invalid or expired key")

	result = frappe.db.get_all("GP Invitation", filters={"key": key}, pluck="name")
	if not result:
		frappe.throw("Invalid or expired key")

	invitation = frappe.get_doc("GP Invitation", result[0])

	invitation.accept()
	invitation.reload()

	user = frappe.get_doc("User", invitation.email)
	needs_password_setup = user and not user.last_password_reset_date

	if invitation.status == "Accepted":
		if needs_password_setup:
			url = invitation.get_password_link()
			frappe.local.response["type"] = "redirect"
			frappe.local.response["location"] = f"{url}"
		else:
			frappe.local.login_manager.login_as(invitation.email)
			frappe.local.response["type"] = "redirect"
			frappe.local.response["location"] = "/g"


@frappe.whitelist()
def get_unsplash_photos(keyword=None):
	from gameplan.unsplash import get_by_keyword, get_list

	if keyword:
		return get_by_keyword(keyword)

	return frappe.cache().get_value("unsplash_photos", generator=get_list)


@frappe.whitelist(methods=["POST"])
def mark_all_notifications_as_read():
	Notification = frappe.qb.DocType("GP Notification")
	(
		frappe.qb.update(Notification)
		.set(Notification.read, 1)
		.where((Notification.to_user == frappe.session.user) & (Notification.read == 0))
	).run()
	gameplan.refetch_resource("Unread Notifications Count", user=frappe.session.user)


@frappe.whitelist(methods=["POST"])
def onboarding(community, space, icon, emails, is_private=0):
	emails = frappe.parse_json(emails)

	# Create the community. The GP Team after_insert hook auto-creates a public
	# "General" space inside it.
	team = frappe.get_doc(doctype="GP Team", title=community).insert()

	# Join the creator — a freshly inserted GP Team does not add its creator as a
	# member, and the scoped-route guard only sees joined communities.
	team.add_member(frappe.session.user)
	team.save()

	# Create the user-named first space in addition to "General".
	project = frappe.get_doc(
		doctype="GP Project", title=space, icon=icon, team=team.name, is_private=is_private
	).insert()

	# Trusted internal path: the signup creator invites their first teammates as
	# Members. Bypasses the admin gate (the creator isn't an admin yet) but the
	# role is hardcoded, so no escalation is possible.
	_invite_by_email(", ".join(emails), role="Gameplan Member")
	return {"team": team.name, "space": project.name}


@frappe.whitelist()
def search_sqlite(query, filters=None):
	from gameplan.search_sqlite import GameplanSearch

	search = GameplanSearch()

	# Parse filters if provided as JSON string
	if filters and isinstance(filters, str):
		import json

		filters = json.loads(filters)

	result = search.search(query, filters=filters)
	return result


@frappe.whitelist()
def get_search_filter_options():
	"""Get available filter options for advanced search"""
	from gameplan.search_sqlite import GameplanSearch

	search = GameplanSearch()
	return search.get_filter_options()


def can_access_gameplan():
	"""Check if the app should be shown in /apps"""
	from frappe.utils.modules import get_modules_from_all_apps_for_user

	if frappe.session.user == "Administrator":
		return True

	allowed_modules = [x["module_name"] for x in get_modules_from_all_apps_for_user()]
	if "Gameplan" not in allowed_modules:
		return False

	roles = set(frappe.get_roles())
	allowed_roles = set(["System Manager", "Gameplan Admin", "Gameplan Member", "Gameplan Guest"])
	if roles.intersection(allowed_roles):
		return True

	return False
