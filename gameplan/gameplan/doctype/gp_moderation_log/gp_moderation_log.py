import frappe
from frappe.model.document import Document


class GPModerationLog(Document):
	def validate(self):
		if not self.is_new():
			frappe.throw("Moderation history cannot be changed", frappe.PermissionError)

	def on_trash(self):
		frappe.throw("Moderation history cannot be deleted", frappe.PermissionError)


def on_doctype_update():
	frappe.db.add_index("GP Moderation Log", ["community", "user", "creation"], "community_user_history")
