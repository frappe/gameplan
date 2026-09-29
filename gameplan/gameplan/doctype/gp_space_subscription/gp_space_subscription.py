# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class GPSpaceSubscription(Document):
	def before_insert(self):
		if not self.user:
			self.user = frappe.session.user


def on_doctype_update():
	frappe.db.add_unique("GP Space Subscription", ["user", "project"])
	frappe.db.add_index("GP Space Subscription", ["project"])
