# Copyright (c) 2022, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class GPDiscussionVisit(Document):
	def after_insert(self):
		frappe.publish_realtime('gameplan:unread_items', user=self.user, after_commit=True)

	def on_change(self):
		if self.has_value_changed('last_visit'):
			frappe.publish_realtime('gameplan:unread_items', user=self.user, after_commit=True)
