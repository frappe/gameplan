import frappe
from frappe.model.document import Document


class GPUserRestriction(Document):
	def validate(self):
		if not frappe.flags.restriction_action:
			frappe.throw("Use the moderation restriction actions", frappe.PermissionError)

	def on_trash(self):
		frappe.throw("Lift restrictions through moderation", frappe.PermissionError)


def on_doctype_update():
	frappe.db.add_unique("GP User Restriction", ["community", "user"], "unique_scope_subject")
	frappe.db.add_index("GP User Restriction", ["community", "active", "user"], "scope_active_user")
	frappe.db.add_index("GP User Restriction", ["active", "expires_at"], "restriction_expiry")
	frappe.db.add_index("GP User Restriction", ["community", "active", "expires_at"], "scope_due_expiry")
	frappe.db.add_index("GP User Restriction", ["user", "active", "community"], "subject_active_scope")
	frappe.db.add_index("User", ["full_name", "name"], "moderation_name_search")
