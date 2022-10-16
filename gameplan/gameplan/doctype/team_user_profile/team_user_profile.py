# Copyright (c) 2022, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.website.utils import cleanup_page_name
from frappe.model.naming import append_number_if_name_exists


class TeamUserProfile(Document):
	def autoname(self):
		self.name = self.generate_name()

	def generate_name(self):
		full_name = frappe.db.get_value("User", self.user, "full_name")
		return append_number_if_name_exists(self.doctype, cleanup_page_name(full_name))


def create_user_profile(doc, method=None):
	if not frappe.db.exists("Team User Profile", {"user": doc.name}):
		frappe.get_doc(doctype="Team User Profile", user=doc.name).insert(ignore_permissions=True)
		frappe.db.commit()

def delete_user_profile(doc, method=None):
	return frappe.get_doc("Team User Profile", {"user": doc.name}).delete()

def on_user_update(doc, method=None):
	create_user_profile(doc)
	if any(doc.has_value_changed(field) for field in ["full_name", "enabled"]):
		profile = frappe.get_doc("Team User Profile", {"user": doc.name})
		profile.enabled = doc.enabled
		profile.full_name = doc.full_name
		profile.save(ignore_permissions=True)

def add_roles(doc, method=None):
	doc.append_roles("Teams User")
