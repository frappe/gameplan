# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt


import frappe
from frappe.utils import get_fullname

from gameplan.utils import extract_mentions, extract_rich_quote_authors


class HasMentions:
	def notify_mentions(self):
		mentions_field = getattr(self, "mentions_field", None)
		if not mentions_field:
			return

		mentions = extract_mentions(self.get(mentions_field))
		notified_users = set()
		for mention in mentions:
			# Handle special "everyone" mention
			if mention.email == "_everyone_":
				self._notify_everyone_mention()
				continue

			self._notify_user(mention.email, is_everyone=False)
			notified_users.add(mention.email)
		self._notify_rich_quote_authors(mentions_field, notified_users)

	def _notify_rich_quote_authors(self, mentions_field, notified_users):
		authors = extract_rich_quote_authors(self.get(mentions_field))
		for author in authors:
			if author in notified_users:
				continue
			self._notify_user(author, is_everyone=False, notification_type="Rich Quote")

	def _notify_everyone_mention(self):
		"""Handle @everyone mentions by notifying all relevant users"""
		for user_email in self._get_all_active_gameplan_users():
			self._notify_user(user_email, is_everyone=True)

	def _can_notify(self, user_email):
		"""Nobody gets notified about their own post, or about content they cannot open.

		The mention autocomplete offers every active user and @everyone fans out to all
		of them, so both can address people outside the space. A notification row links
		the discussion/task and the bell shows its title, so notifying someone without
		access would leak that title and hand them a dead link.
		"""
		from gameplan.permissions import can_view_content

		if user_email == self.owner:
			return False
		return can_view_content(user_email, self)

	def _notify_user(self, user_email, is_everyone=False, notification_type="Mention"):
		"""Create a notification for a specific user"""
		if not self._can_notify(user_email):
			return

		values = frappe._dict(
			from_user=self.owner,
			to_user=user_email,
			type=notification_type,
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
		notification.message = self._get_notification_message(is_everyone, notification_type)
		notification.update(values)
		notification.insert(ignore_permissions=True)

	def _get_notification_message(self, is_everyone, notification_type):
		author = get_fullname(self.owner)
		post_label = "task" if self._is_task_context() else "post"
		if notification_type == "Rich Quote":
			return f"{author} quoted you in a {post_label}"
		if is_everyone:
			return f"{author} mentioned everyone in a {post_label}"
		return f"{author} mentioned you in a {post_label}"

	def _is_task_context(self):
		return "GP Task" in [self.doctype, self.get("reference_doctype")]

	def _get_all_active_gameplan_users(self):
		"""Get all active Gameplan users except guests"""
		return frappe.qb.get_query(
			"User", filters={"enabled": 1, "roles.role": ["in", ["Gameplan Admin", "Gameplan Member"]]}
		).run(pluck="name")
