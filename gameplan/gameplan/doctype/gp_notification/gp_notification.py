# Copyright (c) 2022, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

import gameplan


class GPNotification(Document):
	def after_insert(self):
		gameplan.refetch_resource("Unread Notifications Count", user=self.to_user)

	def on_update(self):
		# When a notification's read status changes, inform clients to refetch
		try:
			# Prefer precise invalidation only when read flag toggles
			if hasattr(self, "has_value_changed") and self.has_value_changed("read"):
				gameplan.refetch_resource("Unread Notifications Count", user=self.to_user)
			elif self.read:
				# Fallback: if API version doesn't support has_value_changed, still refetch when read is set
				gameplan.refetch_resource("Unread Notifications Count", user=self.to_user)
		except Exception:
			# Avoid breaking save flow due to realtime errors
			frappe.log_error(title="GPNotification on_update refetch failed")

	@staticmethod
	def clear_notifications(discussion=None, comment=None, task=None, user=None):
		if not user:
			user = frappe.session.user
		filters = {"to_user": user}
		if discussion:
			filters["discussion"] = discussion
		if comment:
			filters["comment"] = comment
		if task:
			filters["task"] = task

		for notification in frappe.get_all("GP Notification", filters=filters):
			doc = frappe.get_doc("GP Notification", notification.name)
			doc.read = 1
			doc.save()

		gameplan.refetch_resource("Unread Notifications Count", user=user)
