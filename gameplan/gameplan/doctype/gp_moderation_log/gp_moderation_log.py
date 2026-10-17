import frappe
from frappe.model.document import Document


class GPModerationLog(Document):
	def validate(self):
		if not self.is_new():
			frappe.throw("Moderation history cannot be changed", frappe.PermissionError)

	def on_trash(self):
		frappe.throw("Moderation history cannot be deleted", frappe.PermissionError)
