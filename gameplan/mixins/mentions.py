# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt


import frappe
from frappe.utils import get_fullname

from gameplan.utils import extract_mentions


class HasMentions:
	def notify_mentions(self):
		mentions_field = getattr(self, "mentions_field", None)
		if not mentions_field:
			return

		mentions = extract_mentions(self.get(mentions_field))
		for mention in mentions:
			# Handle special "everyone" mention
			if mention.email == "_everyone_":
				self._notify_everyone_mention()
				continue

			self._notify_user(mention.email, is_everyone=False)

	def _notify_everyone_mention(self):
		"""Handle @everyone mentions by notifying all relevant users"""
		users_to_notify = self._get_all_active_gameplan_users()

		for user_email in users_to_notify:
			# Skip notifying the author
			if user_email == self.owner:
				continue
			# Create notifications for each user
			self._notify_user(user_email, is_everyone=True)

	def _notify_user(self, user_email, is_everyone=False):
		"""Create a notification for a specific user"""
		values = frappe._dict(
			from_user=self.owner,
			to_user=user_email,
		)

		if self.doctype == "GP Discussion":
			values.discussion = self.name
		elif self.doctype == "GP Task":
			values.task = self.name
			values.project = self.project
		elif self.doctype == "GP Comment":
			values.comment = self.name
			if self.reference_doctype == "GP Discussion":
				values.discussion = self.reference_name
			elif self.reference_doctype == "GP Task":
				values.task = self.reference_name
				values.project = frappe.db.get_value("GP Task", self.reference_name, "project")

		# Skip if notification already exists
		if frappe.db.exists("GP Notification", values):
			return

		notification = frappe.get_doc(doctype="GP Notification")

		if "GP Task" in [self.doctype, self.get("reference_doctype")]:
			if is_everyone:
				notification.message = f"{get_fullname(self.owner)} mentioned everyone in a task"
			else:
				notification.message = f"{get_fullname(self.owner)} mentioned you in a task"
		elif "GP Discussion" in [self.doctype, self.get("reference_doctype")]:
			if is_everyone:
				notification.message = f"{get_fullname(self.owner)} mentioned everyone in a post"
			else:
				notification.message = f"{get_fullname(self.owner)} mentioned you in a post"

		notification.update(values)
		notification.insert(ignore_permissions=True)

	def _get_all_active_gameplan_users(self):
		"""Get all active Gameplan users except guests"""
		return frappe.qb.get_query(
			"User", filters={"enabled": 1, "roles.role": ["in", ["Gameplan Admin", "Gameplan Member"]]}
		).run(pluck="name")
