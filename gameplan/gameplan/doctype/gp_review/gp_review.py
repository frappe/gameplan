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
	frappe.db.add_index("GP Review", ["status", "report_count"], "review_report_count")
	# The most-reported queue orders by all three; with the full order in the index MariaDB stops
	# after one page instead of sorting every pending review (1.1 s with 93,000).
	frappe.db.add_index("GP Review", ["status", "report_count", "last_reported_at"], "review_most_reported")
	frappe.db.add_index("GP Review", ["status", "last_reported_at"], "review_last_reported")
