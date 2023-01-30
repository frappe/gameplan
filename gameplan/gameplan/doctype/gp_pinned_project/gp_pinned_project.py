# Copyright (c) 2023, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class GPPinnedProject(Document):
	def before_insert(self):
		self.user = frappe.session.user
		self.order = frappe.db.count('GP Pinned Project', {'user': self.user}) + 1

		if frappe.db.exists('GP Pinned Project', {'user': self.user, 'project': self.project}):
			frappe.throw('This project is already pinned')

	@staticmethod
	def get_list_query(query):
		Pin = frappe.qb.DocType('GP Pinned Project')
		query = query.where(Pin.user == frappe.session.user)
		return query
