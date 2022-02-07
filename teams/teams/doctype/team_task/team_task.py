# Copyright (c) 2022, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class TeamTask(Document):
	def on_update(self):
		self.update_project_progress()

	def on_trash(self):
		self.update_project_progress()

	def update_project_progress(self):
		if self.project and self.has_value_changed("is_completed"):
			frappe.get_doc("Team Project", self.project).update_progress()