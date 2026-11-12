# Copyright (c) 2022, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from gameplan.realtime import notify_notification_count_changed


class GPNotification(Document):
	def before_save(self):
		# `modified` is when the row last had news: its insert, or a reaction re-lighting it.
		# The bell sorts and dates rows by it, so marking a row read must not move it.
		if self.is_marked_read_only():
			self.modified = self.get_doc_before_save().modified

	def is_marked_read_only(self):
		before = self.get_doc_before_save()
		if not before or not (self.read and not before.read):
			return False
		# Compared as text: links to autoincrement doctypes load as int but arrive as str.
		changed = [
			f.fieldname
			for f in self.meta.fields
			if str(before.get(f.fieldname) or "") != str(self.get(f.fieldname) or "")
		]
		return changed == ["read"]

	def on_update(self):
		# Not `after_insert`: a reaction REUSES the existing row and resets `read` to 0
		# (see HasReactions.notify_reactions), and the bell's mark-as-read is a PUT that
		# updates in place. Both are UPDATEs, so an insert-only hook left the unread badge
		# stale in every open tab until a full reload. `has_value_changed` is True when
		# there is no doc-before-save, so inserts still announce themselves.
		if self.has_value_changed("read"):
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
