# Copyright (c) 2023, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class GPFollowedProject(Document):
	def before_insert(self):
		if not self.user:
			self.user = frappe.session.user

	@staticmethod
	def get_list_query(query):
		FollowedProject = frappe.qb.DocType('GP Followed Project')
		query = query.where(FollowedProject.user == frappe.session.user)
		return query
