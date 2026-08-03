import frappe
from frappe.query_builder import DocType


def execute():
	"""Give every pre-existing pin the community-wide scope.

	This originally wrote "Global", which `rename_global_pin_scope_to_category` (a later
	entry in patches.txt) then flipped to "Category". "Global" is no longer one of the
	field's Select options, so it is written as "Category" here directly — the end state
	is identical on sites that have already run both patches.
	"""
	GPDiscussion = DocType("GP Discussion")

	frappe.qb.update(GPDiscussion).set(GPDiscussion.pin_scope, "Category").where(
		(GPDiscussion.pinned_at.isnotnull())
		& ((GPDiscussion.pin_scope.isnull()) | (GPDiscussion.pin_scope == ""))
	).run()
