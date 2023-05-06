# Copyright (c) 2023, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
from gameplan.utils import url_safe_slug


class GPPage(Document):
	def before_save(self):
		self.slug = url_safe_slug(self.title)
