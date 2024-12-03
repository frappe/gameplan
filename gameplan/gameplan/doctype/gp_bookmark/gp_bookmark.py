# Copyright (c) 2024, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
from frappe.utils import cint


class GPBookmark(Document):
	def remove_bookmark(self, discussion):
		for row in self.bookmarks:
			if cint(row.discussion) == cint(discussion):
				self.remove(row)
				self.save()
				break
