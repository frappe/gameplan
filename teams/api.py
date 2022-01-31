# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe


@frappe.whitelist()
def create_team(name):
	return frappe.get_doc(doctype="Team", title=name).insert()


@frappe.whitelist()
def get_teams():
	return frappe.db.get_all("Team", fields=["name", "title", "modified", "creation"])


@frappe.whitelist()
def get_team(name):
	return frappe.get_doc("Team", name)


@frappe.whitelist()
def get_documents(team):
	return frappe.db.get_all(
		"Team Document",
		fields=["name", "title", "modified", "creation"],
		filters={"team": team},
		order_by="creation desc",
	)


@frappe.whitelist()
def new_document(team):
	return frappe.get_doc(doctype="Team Document", team=team).insert()


@frappe.whitelist()
def get_document(name):
	return frappe.get_doc("Team Document", name)


@frappe.whitelist()
def update_document(name, title, content):
	doc = frappe.get_doc("Team Document", name)
	doc.title = title
	doc.content = content
	doc.save()


@frappe.whitelist()
def get_user_info(email):
	return (
		frappe.db.get_values(
			"User", email, fieldname=["name", "email", "user_image", "full_name"], as_dict=True
		)
		or None
	)


@frappe.whitelist()
def invite_member(email, team):
	team = frappe.get_doc("Team", team)
	team.send_invitation(email)


@frappe.whitelist(allow_guest=True)
def accept_invitation(key=None):
	if not key:
		frappe.throw("Invalid or expired key")

	result = frappe.db.get_all(
		"Team Member", filters={"key": key}, fields=["email", "parent"]
	)
	if not result:
		frappe.throw("Invalid or expired key")

	team = frappe.get_doc("Team", result[0].parent)
	user = team.accept_invitation(key)

	if user:
		frappe.local.login_manager.login_as(user.name)
		frappe.local.response["type"] = "redirect"
		frappe.local.response["location"] = "/teams"


@frappe.whitelist()
def get_unsplash_photos(keyword=None):
	if not "unsplash_access_key" in frappe.conf:
		frappe.throw("Please set unsplash_access_key in site_config.json")

	def _get():
		import requests

		base_url = "https://api.unsplash.com"
		path = f"/search/photos?query={keyword}" if keyword else "/photos"
		res = requests.get(
			f"{base_url}{path}",
			headers={
				"Accept-Version": "v1",
				"Authorization": f"Client-ID {frappe.conf.unsplash_access_key}",
			},
		)
		res.raise_for_status()
		data = res.json()
		if isinstance(data, list):
			return data
		return data.get("results")

	if not keyword:
		return frappe.cache().get_value("unsplash_photos", generator=_get)
	return _get()
