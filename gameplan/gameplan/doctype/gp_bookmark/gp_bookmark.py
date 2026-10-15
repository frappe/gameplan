# Copyright (c) 2024, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class GPBookmark(Document):
	def validate(self):
		if not self.comment:
			return
		reference = frappe.db.get_value("GP Comment", self.comment, ["reference_doctype", "reference_name"])
		if not reference or reference[0] != "GP Discussion" or str(reference[1]) != str(self.discussion):
			frappe.throw(_("A bookmarked comment must belong to the bookmarked discussion."))
