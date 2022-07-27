# Copyright (c) 2022, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class TeamDiscussionView(Document):
	def before_insert(self):
		if not self.viewed_at:
			self.viewed_at = frappe.utils.now()

		if not self.viewed_by:
			self.viewed_by = frappe.session.user

