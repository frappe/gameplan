# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import get_fullname
from gameplan.utils import extract_mentions

class HasMentions:
	def notify_mentions(self):
		mentions_field = getattr(self, 'mentions_field', None)
		if not mentions_field:
			return

		mentions = extract_mentions(self.get(mentions_field))
		for mention in mentions:
			values = frappe._dict(
				from_user=self.owner,
				to_user=mention.email,
			)
			if self.doctype == "GP Discussion":
				values.discussion = self.name
			if self.doctype == "GP Task":
				values.task = self.name
				values.project = self.project
			elif self.doctype == "GP Comment":
				values.comment = self.name
				if self.reference_doctype == "GP Discussion":
					values.discussion = self.reference_name
				elif self.reference_doctype == "GP Task":
					values.task = self.reference_name
					values.project = frappe.db.get_value("GP Task", self.reference_name, "project")

			if frappe.db.exists("GP Notification", values):
				continue
			notification = frappe.get_doc(doctype='GP Notification')
			if "GP Task" in [self.doctype, self.get('reference_doctype')]:
				notification.message = f'{get_fullname(self.owner)} mentioned you in a task'
			elif "GP Discussion" in [self.doctype, self.get('reference_doctype')]:
				notification.message = f'{get_fullname(self.owner)} mentioned you in a post'
			notification.update(values)
			notification.insert(ignore_permissions=True)
