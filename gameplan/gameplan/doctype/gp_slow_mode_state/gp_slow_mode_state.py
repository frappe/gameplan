# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class GPSlowModeState(Document):
	def notify_update(self):
		# Cooldown records are private metadata, not shared document updates.
		pass
