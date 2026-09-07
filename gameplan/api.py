# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt


import json

import frappe
from frappe import _
from frappe.query_builder.functions import Count
from frappe.utils import cint, split_emails, validate_email_address

import gameplan
from gameplan.gameplan.doctype.gp_invitation.gp_invitation import grant_access
from gameplan.realtime import notify_notification_count_changed, unread_notification_count
from gameplan.roles import GAMEPLAN_ROLES
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
			# Fall back to User.user_image when the profile has none, so an account that
			# only ever set an avatar through Frappe keeps it. Email digests already
			# resolve avatars this way (see gameplan.email_digest.get_user_avatar_map).
			user.user_image = user_profile.image or user.user_image
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
		# GAMEPLAN_ROLES is ordered by privilege, so the last match is the effective role.
		for role in GAMEPLAN_ROLES:
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
	if role not in GAMEPLAN_ROLES:
		frappe.throw(_("Invalid role: {0}").format(role), frappe.ValidationError)
	return _invite_by_email(emails, role, projects)


def _invite_by_email(emails: str, role: str, projects: list = None) -> dict:
	"""Core invite logic, callable from trusted server code (e.g. onboarding).

	The public invite_by_email wrapper adds the admin gate + role allowlist; this
	helper assumes the caller has already authorized the invite and validated role.

	Two outcomes, split on whether the person already has an account here:

	No account: send the invitation email. Its link is what mints the User.

	An enabled account with no Gameplan role: grant the role now. The email link would
	create nothing and set no password, and an OAuth account (which is how people reach
	this state) would be sent to /update-password for no reason.

	Returns the three buckets so the caller can tell the admin what happened.
	"""
	result = {"granted": [], "invited": [], "skipped": []}
	if not emails:
		return result
	email_string = validate_email_address(emails, throw=False)
	email_list = split_emails(email_string)
	if not email_list:
		return result
	already_in_gameplan = emails_holding_a_gameplan_role(email_list)
	existing_invites = frappe.db.get_all(
		"GP Invitation",
		filters={
			"email": ["in", email_list],
			"role": ["in", ["Gameplan Admin", "Gameplan Member"]],
		},
		pluck="email",
	)

	if role == "Gameplan Guest":
		to_invite = set(email_list) - set(existing_invites)
	else:
		to_invite = set(email_list) - set(already_in_gameplan) - set(existing_invites)

	accounts = existing_accounts(to_invite)
	grantable = {email for email, enabled in accounts.items() if enabled}
	# A disabled account is neither granted nor invited. The role would change nothing
	# while the account cannot sign in, and mailing it an invite link is worse: accept()
	# would hand the role to an account someone deliberately switched off.
	to_invite -= set(accounts) - grantable

	result["skipped"] = sorted(set(email_list) - to_invite)
	if projects:
		projects = frappe.as_json(projects, indent=None)

	for email in sorted(to_invite):
		if email in grantable:
			grant_access(email, role, projects)
			result["granted"].append(email)
		else:
			frappe.get_doc(doctype="GP Invitation", email=email, role=role, projects=projects).insert(
				ignore_permissions=True
			)
			result["invited"].append(email)

	return result


def existing_accounts(email_list) -> dict:
	"""Map each email that already has a User on this site to whether it is enabled.

	An enabled account can sign in today, so its owner needs a role, not an invitation.
	A disabled one needs neither.
	"""
	email_list = list(email_list)
	if not email_list:
		return {}
	rows = frappe.qb.get_query(
		"User",
		filters={"email": ["in", email_list]},
		fields=["email", "enabled"],
	).run(as_dict=True)
	return {row.email: bool(row.enabled) for row in rows}


def emails_holding_a_gameplan_role(email_list: list) -> list:
	"""The subset of `email_list` whose User already holds a Gameplan role.

	A member invite skips these, because the invitation would grant a role they have.
	It must not skip every existing User: signing in through OAuth mints a Website User
	with no role at all, so an account can exist on the site while its owner has no way
	into Gameplan. Those people need the invite; `accept()` adds the role to the account
	they already have.
	"""
	User = frappe.qb.DocType("User")
	HasRole = frappe.qb.DocType("Has Role")
	return (
		frappe.qb.from_(User)
		.join(HasRole)
		.on((HasRole.parent == User.name) & (HasRole.parenttype == "User"))
		.select(User.email)
		.where(User.email.isin(email_list))
		.where(HasRole.role.isin(GAMEPLAN_ROLES))
		.run(pluck=True)
	)


@frappe.whitelist()
def unread_notifications():
	return unread_notification_count(frappe.session.user)


# Invitation emails open in a browser navigation, so this endpoint must remain GET-reachable.
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
	notify_notification_count_changed(frappe.session.user)


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
	allowed_roles = {"System Manager", *GAMEPLAN_ROLES}
	if roles.intersection(allowed_roles):
		return True

	return False


CLIENT_ERROR_QUOTA = 20
CLIENT_ERROR_QUOTA_WINDOW = 60 * 60
CLIENT_ERROR_FIELD_LIMIT = 4000


@frappe.whitelist(methods=["POST"])
@validate_type
def log_client_error(message: str, context: dict = None):
	"""Record a browser-side error in the Error Log.

	The UI catches most request failures and shows a message instead of raising, so a
	report like "it did not post the first time" leaves no trace on the server. The
	frontend sends those caught errors here together with the stack and the action that
	failed, which is what makes them diagnosable after the fact.

	The payload is attacker-controlled: it is truncated, stored as plain text, and each
	user gets an hourly quota so a looping client cannot fill the Error Log.
	"""
	if _client_error_quota_spent():
		return

	action = _error_action(context)
	title = f"Gameplan client error: {action}" if action else "Gameplan client error"

	body = [_truncate(message)]
	if context:
		body.append("Context:\n" + _truncate(json.dumps(context, indent=2, default=str)))
	frappe.log_error(title=title, message="\n\n".join(body))


def _error_action(context: dict | None) -> str:
	"""The action label for the log title. Kept to one short line: frappe.log_error treats a
	multi-line title as a traceback and swaps its arguments."""
	action = context.get("action") if isinstance(context, dict) else None
	if not isinstance(action, str):
		return ""
	return " ".join(action.split())[:100]


def _client_error_quota_spent() -> bool:
	"""Whether this user has already used up their hourly client-error budget.

	Read-then-write rather than an atomic counter: two reports racing can slip one past
	the cap, which is fine for a throttle whose only job is to bound the row count.
	"""
	key = f"gameplan:client-error-count:{frappe.session.user}"
	cache = frappe.cache()
	count = cint(cache.get_value(key))
	if count >= CLIENT_ERROR_QUOTA:
		return True
	cache.set_value(key, count + 1, expires_in_sec=CLIENT_ERROR_QUOTA_WINDOW)
	return False


def _truncate(value: str, limit: int = CLIENT_ERROR_FIELD_LIMIT) -> str:
	value = str(value or "")
	return value if len(value) <= limit else value[:limit] + "… (truncated)"
