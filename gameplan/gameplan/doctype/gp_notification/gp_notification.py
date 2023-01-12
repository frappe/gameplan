# Copyright (c) 2022, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class GPNotification(Document):
	def after_insert(self):
		frappe.publish_realtime("gameplan:new_notification", user=self.to_user)
