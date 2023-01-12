# Copyright (c) 2022, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from gameplan.mixins.mentions import HasMentions


class GPTask(HasMentions, Document):
	on_delete_cascade = ["Team Comment"]
	on_delete_set_null = ["Team Notification"]
	mentions_field = 'description'

	def after_insert(self):
		self.update_tasks_count(1)

	def on_update(self):
		self.update_project_progress()

	def on_trash(self):
		self.update_tasks_count(-1)

	def update_tasks_count(self, delta=1):
		current_tasks_count = frappe.db.get_value("GP Project", self.project, "tasks_count")
		frappe.db.set_value("GP Project", self.project, "tasks_count", current_tasks_count + delta)

	def update_project_progress(self):
		if self.project and self.has_value_changed("is_completed"):
			frappe.get_doc("GP Project", self.project).update_progress()

	def on_update(self):
		self.notify_mentions()
