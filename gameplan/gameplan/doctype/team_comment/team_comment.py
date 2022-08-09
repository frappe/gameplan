# Copyright (c) 2022, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from gameplan.utils import extract_mentions
from frappe.utils import get_fullname

class TeamComment(Document):
	def after_insert(self):
		if self.reference_doctype == "Team Project Discussion":
			frappe.db.set_value(
				self.reference_doctype,
				self.reference_name,
				"last_post_at",
				frappe.utils.now()
			)

	def on_change(self):
		mentions = extract_mentions(self.content)
		for mention in mentions:
			values = frappe._dict(
				from_user=self.owner,
				to_user=mention.email,
				comment=self.name,
			)
			if self.reference_doctype == "Team Project Discussion":
				values.discussion = self.reference_name
			elif self.reference_doctype == "Team Task":
				values.task = self.reference_name
				values.project = frappe.db.get_value("Team Task", self.reference_name, "project")

			if frappe.db.exists("Team Notification", values):
				continue

			notification = frappe.get_doc(doctype="Team Notification")
			notification.message = f'{get_fullname(self.owner)} mentioned you in a comment',
			notification.update(values)
			notification.insert(ignore_permissions=True)
