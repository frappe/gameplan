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
	try:
		return frappe.get_doc(doctype="Team User Profile", user=doc.name).insert()
	except:
		pass

def delete_user_profile(doc, method=None):
	return frappe.get_doc("Team User Profile", {"user": doc.name}).delete()
