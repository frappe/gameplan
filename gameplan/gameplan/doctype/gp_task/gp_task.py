# Copyright (c) 2022, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from gameplan.gameplan.doctype.gp_notification.gp_notification import GPNotification
from gameplan.mixins.activity import HasActivity
from gameplan.mixins.mentions import HasMentions


class GPTask(HasMentions, HasActivity, Document):
	on_delete_cascade = ["GP Comment", "GP Activity"]
	on_delete_set_null = ["GP Notification"]
	activities = ['Task Value Changed']
	mentions_field = 'description'

	def before_insert(self):
		if not self.status:
			self.status = 'Backlog'

	def after_insert(self):
		self.update_tasks_count(1)

	def on_update(self):
		self.update_project_progress()
		self.notify_mentions()
		self.log_value_updates()

	def log_value_updates(self):
		fields = ['title', 'description', 'status', 'priority', 'assigned_to', 'due_date', 'project']
		for field in fields:
			prev_doc = self.get_doc_before_save()
			if prev_doc and str(self.get(field)) != str(prev_doc.get(field)):
				self.log_activity('Task Value Changed', data={
					'field': field,
					'field_label': self.meta.get_label(field),
					'old_value': prev_doc.get(field),
					'new_value': self.get(field)
				})

	def on_trash(self):
		self.update_tasks_count(-1)

	def update_tasks_count(self, delta=1):
		if not self.project:
			return
		current_tasks_count = frappe.db.get_value("GP Project", self.project, "tasks_count") or 0
		frappe.db.set_value("GP Project", self.project, "tasks_count", current_tasks_count + delta)

	def update_project_progress(self):
		if self.project and self.has_value_changed("is_completed"):
			frappe.get_doc("GP Project", self.project).update_progress()

	@frappe.whitelist()
	def track_visit(self):
		GPNotification.clear_notifications(task=self.name)
