# Copyright (c) 2025, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class GPDraft(Document):
	@staticmethod
	def get_list(query):
		GPDraft = frappe.qb.DocType("GP Draft")
		query = query.where(GPDraft.owner == frappe.session.user)
		return query
