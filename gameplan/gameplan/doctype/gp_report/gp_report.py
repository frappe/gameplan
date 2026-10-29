import frappe
from frappe.model.document import Document


class GPReport(Document):
	def validate(self):
		if not self.is_new():
			frappe.throw("Report evidence and decisions cannot be edited", frappe.PermissionError)

	def on_trash(self):
		frappe.throw("Report evidence and decisions cannot be deleted", frappe.PermissionError)


def on_doctype_update():
	frappe.db.add_unique("GP Report", ["review", "owner"])
	frappe.db.add_index("GP Report", ["owner", "creation"], "reporter_quota")
	frappe.db.add_index("GP Report", ["review", "creation"], "review_reports")
