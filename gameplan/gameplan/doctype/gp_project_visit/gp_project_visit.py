# Copyright (c) 2022, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class GPProjectVisit(Document):
	@staticmethod
	def get_list_query(query):
		ProjectVisit = frappe.qb.DocType("GP Project Visit")
		query = query.where(ProjectVisit.user == frappe.session.user)
		return query
