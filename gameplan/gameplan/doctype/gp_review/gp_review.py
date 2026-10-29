import frappe
from frappe.model.document import Document


class GPReview(Document):
	def validate(self):
		if not self.is_new():
			frappe.throw("Report evidence and decisions cannot be edited", frappe.PermissionError)

	def on_trash(self):
		frappe.throw("Report evidence and decisions cannot be deleted", frappe.PermissionError)


def on_doctype_update():
	frappe.db.add_index("GP Review", ["reference_doctype", "reference_name", "status"], "target_review")
	frappe.db.add_index("GP Review", ["status", "creation"], "review_queue")
