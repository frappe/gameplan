# Copyright (c) 2022, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class TeamProjectDiscussion(Document):
	def on_trash(self):
		for name in frappe.db.get_all('Team Comment', {
			'reference_doctype': self.doctype,
			'reference_name': self.name
		}, pluck='name'):
			frappe.delete_doc('Team Comment', name)
