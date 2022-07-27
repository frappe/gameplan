# Copyright (c) 2022, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class TeamComment(Document):
	def after_insert(self):
		if self.reference_doctype == "Team Project Discussion":
			frappe.db.set_value(
				self.reference_doctype,
				self.reference_name,
				"last_post_at",
				frappe.utils.now()
			)
