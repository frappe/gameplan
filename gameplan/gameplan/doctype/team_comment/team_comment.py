# Copyright (c) 2022, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from gameplan.utils import extract_mentions
from frappe.utils import get_fullname

class TeamComment(Document):
	on_delete_set_null = ["Team Notification"]

	def after_insert(self):
		if self.reference_doctype not in ["Team Discussion", "Team Task"]:
			return
		reference_doc = frappe.get_doc(self.reference_doctype, self.reference_name)
		if reference_doc.meta.has_field("last_post_at"):
			reference_doc.set("last_post_at", frappe.utils.now())
		if reference_doc.meta.has_field("last_post_by"):
			reference_doc.set("last_post_by", frappe.session.user)
		if reference_doc.meta.has_field("comments_count"):
			reference_doc.set("comments_count", reference_doc.comments_count + 1)
		reference_doc.save(ignore_permissions=True)

	def on_trash(self):
		if self.reference_doctype not in ["Team Discussion", "Team Task"]:
			return
		reference_doc = frappe.get_doc(self.reference_doctype, self.reference_name)
		if reference_doc.meta.has_field("comments_count"):
			reference_doc.db_set("comments_count", reference_doc.comments_count - 1)

	def on_update(self):
		mentions = extract_mentions(self.content)
		for mention in mentions:
			values = frappe._dict(
				from_user=self.owner,
				to_user=mention.email,
				comment=self.name,
			)
			if self.reference_doctype == "Team Discussion":
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
