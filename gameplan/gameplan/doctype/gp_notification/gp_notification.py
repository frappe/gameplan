# Copyright (c) 2022, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
import gameplan
from frappe.model.document import Document

class GPNotification(Document):
	def after_insert(self):
		gameplan.refetch_resource('Unread Notifications Count', user=self.to_user)
