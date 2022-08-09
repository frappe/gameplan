# Copyright (c) 2022, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from gameplan.utils import extract_mentions
from frappe.utils import get_fullname


class TeamTask(Document):
	def before_insert(self):
		total_tasks_in_section = frappe.db.count(
			"Team Task", {"project": self.project, "project_section": self.project_section}
		)
		self.idx = total_tasks_in_section + 1

	def on_update(self):
		self.update_project_progress()

	def on_trash(self):
		self.update_project_progress()

	def update_project_progress(self):
		if self.project and self.has_value_changed("is_completed"):
			frappe.get_doc("Team Project", self.project).update_progress()

	def on_change(self):
		mentions = extract_mentions(self.description)
		for mention in mentions:
			values = frappe._dict(
				from_user=self.owner,
				to_user=mention.email,
				task=self.name,
				project=self.project
			)
			if frappe.db.exists("Team Notification", values):
				continue
			notification = frappe.get_doc(doctype='Team Notification')
			notification.message = f'{get_fullname(self.owner)} mentioned you in a task',
			notification.update(values)
			notification.insert(ignore_permissions=True)
