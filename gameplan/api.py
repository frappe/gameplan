# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from __future__ import unicode_literals
import frappe
from gameplan.utils import validate_type


@frappe.whitelist(allow_guest=True)
def get_user_info():
	if frappe.session.user == "Guest":
		frappe.throw("Authentication failed", exc=frappe.AuthenticationError)

	users = frappe.db.get_all(
		"User",
		filters=[["Has Role", "role", "=", "Teams User"]],
		fields=["name", "email", "user_image", "full_name", "user_type"],
		order_by="full_name asc"
	)
	user_profile_names = frappe.db.get_all('Team User Profile',
		fields=['user', 'name'],
		filters={'user': ['in', [u.name for u in users]]}
	)
	user_profile_names_map = {u.user: u.name for u in user_profile_names}
	for user in users:
		if frappe.session.user == user.name:
			user.session_user = True
		user.user_profile = user_profile_names_map.get(user.name)
	return users

@frappe.whitelist()
def unread_notifications():
	res = frappe.db.get_all('Team Notification', 'count(name) as count', {'to_user': frappe.session.user, 'read': 0})
	return res[0].count


@frappe.whitelist(allow_guest=True)
@validate_type
def accept_invitation(key: str = None):
	if not key:
		frappe.throw("Invalid or expired key")

	result = frappe.db.get_all(
		"Team Member", filters={"key": key}, fields=["email", "parent", "parenttype"]
	)
	if not result:
		frappe.throw("Invalid or expired key")

	# valid key, now set the user as Administrator
	frappe.set_user("Administrator")
	doctype = result[0].parenttype
	doc = frappe.get_doc(doctype, result[0].parent)
	user = doc.accept_invitation(key)

	if doctype == "Team":
		redirect_location = f"/teams/{doc.name}"
	elif doctype == "Team Project":
		redirect_location = f"/teams/{doc.team}/projects/{doc.name}"
	else:
		redirect_location = "/teams"

	if user:
		frappe.local.login_manager.login_as(user.name)
		frappe.local.response["type"] = "redirect"
		frappe.local.response["location"] = redirect_location


@frappe.whitelist()
def get_unsplash_photos(keyword=None):
	from gameplan.unsplash import get_list, get_by_keyword

	if keyword:
		return get_by_keyword(keyword)

	return frappe.cache().get_value("unsplash_photos", generator=get_list)


@frappe.whitelist()
def get_unread_items():
    from frappe.query_builder.functions import Count
    Discussion = frappe.qb.DocType("Team Discussion")
    Visit = frappe.qb.DocType("Team Discussion Visit")
    query = (
		frappe.qb.from_(Discussion)
	        .select(Discussion.team, Count(Discussion.team).as_("count"))
            .left_join(Visit)
	        .on((Visit.discussion == Discussion.name) & (Visit.user == frappe.session.user))
	        .where((Visit.last_visit.isnull()) | (Visit.last_visit < Discussion.last_post_at))
            .groupby(Discussion.team)
    )
    data = query.run(as_dict=1)
    out = {}
    for d in data:
        out[d.team] = d.count
    return out















@frappe.whitelist()
def onboarding(data):
	data = frappe.parse_json(data)
	team = frappe.get_doc(doctype='Team', title=data.team).insert()
	frappe.get_doc(doctype='Team Project', team=team.name, title=data.project).insert()
	team.invite_members(data.emails)
	return team.name

@frappe.whitelist(allow_guest=True)
def oauth_providers():
	from frappe.utils.html_utils import get_icon_html
	from frappe.utils.password import get_decrypted_password
	from frappe.utils.oauth import get_oauth2_authorize_url, get_oauth_keys

	out = []
	providers = frappe.get_all(
		"Social Login Key",
		filters={"enable_social_login": 1},
		fields=["name", "client_id", "base_url", "provider_name", "icon"],
		order_by="name",
	)

	for provider in providers:
		client_secret = get_decrypted_password("Social Login Key", provider.name, "client_secret")
		if not client_secret:
			continue

		icon = None
		if provider.icon:
			if provider.provider_name == "Custom":
				icon = get_icon_html(provider.icon, small=True)
			else:
				icon = f"<img src='{provider.icon}' alt={provider.provider_name}>"

		if provider.client_id and provider.base_url and get_oauth_keys(provider.name):
			out.append(
				{
					"name": provider.name,
					"provider_name": provider.provider_name,
					"auth_url": get_oauth2_authorize_url(provider.name, '/g/home'),
					"icon": icon,
				}
			)
	return out
