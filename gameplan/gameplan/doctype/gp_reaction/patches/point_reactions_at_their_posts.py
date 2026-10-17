# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors

import frappe


def execute():
	"""GP Reaction was a child table of each post. Point every row at its post.

	The child-table columns stay in the table after the doctype sync, so the post is
	copied from `parenttype` and `parent`. They are left in place, unused."""
	if not frappe.db.has_column("GP Reaction", "parent"):
		return

	frappe.db.sql(
		"""
		update `tabGP Reaction`
		set reference_doctype = parenttype, reference_name = parent
		where coalesce(reference_name, '') = ''
		"""
	)
	frappe.db.delete("GP Reaction", {"reference_name": ("is", "not set")})
