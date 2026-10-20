import frappe
from frappe import _
from frappe.model.document import Document


class ParentManagedChild(Document):
	def before_validate(self):
		self.require_parent_save()

	def on_trash(self):
		self.require_parent_save()

	def require_parent_save(self):
		# Parent saves write child rows directly without running their controller hooks.
		if not self.flags.ignore_permissions:
			frappe.throw(_("Save child rows through their parent document"), frappe.PermissionError)
