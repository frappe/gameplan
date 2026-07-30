# Copyright (c) 2022, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from gameplan.realtime import notify_notification_count_changed


class GPNotification(Document):
	def after_insert(self):
		notify_notification_count_changed(self.to_user)

	@staticmethod
	def clear_notifications(discussion=None, comment=None, poll=None, task=None, user=None):
		if not user:
			user = frappe.session.user
		filters = {"to_user": user}
		if discussion:
			filters["discussion"] = str(discussion)
		if comment:
			filters["comment"] = str(comment)
		if poll:
			filters["poll"] = str(poll)
		if task:
			filters["task"] = str(task)

		Notification = frappe.qb.DocType("GP Notification")
		query = frappe.qb.update(Notification).set(Notification.read, 1)
		for field, value in filters.items():
			query = query.where(Notification[field] == value)
		query.run()

		notify_notification_count_changed(user)
