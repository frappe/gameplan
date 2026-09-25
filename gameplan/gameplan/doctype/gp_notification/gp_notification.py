# Copyright (c) 2022, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from gameplan.realtime import notify_notification_changed


class GPNotification(Document):
	def before_insert(self):
		# A new row is one event, happening now. Writers that merge repeat events into an
		# existing row move this forward themselves (see HasReactions.notify_reactions).
		if not self.last_event_at:
			self.last_event_at = frappe.utils.now()
		if not self.event_count:
			self.event_count = 1

	def on_update(self):
		# Not `after_insert`: a reaction REUSES the existing row and resets `read` to 0
		# (see HasReactions.notify_reactions), and the bell's mark-as-read is a PUT that
		# updates in place. Both are UPDATEs, so an insert-only hook left the unread badge
		# stale in every open tab until a full reload. `has_value_changed` is True when
		# there is no doc-before-save, so inserts still announce themselves.
		#
		# `event_count` too: a repeat event merging into a row that is *already* unread
		# changes neither `read` nor the unread count, yet an open inbox has to move from
		# "1 new comment" to "2 new comments".
		if self.has_value_changed("read") or self.has_value_changed("event_count"):
			notify_notification_changed(self.to_user, self)

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

		notify_notification_changed(user)


def on_doctype_update():
	# The inbox lists one user's rows newest-event-first. `read` is left out on purpose: it is a
	# reserved word in MariaDB and add_index does not quote column names.
	frappe.db.add_index("GP Notification", ["to_user", "last_event_at"])
