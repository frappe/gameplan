# Copyright (c) 2022, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class TeamUserProfile(Document):
	pass


def create_user_profile(doc, method=None):
	return frappe.get_doc(doctype="Team User Profile", user=doc.name).insert()
