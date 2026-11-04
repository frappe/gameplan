# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
import frappe


def execute():
	for doctype in ("GP Discussion", "GP Comment"):
		for name in frappe.get_all(doctype, filters={"content": ["like", "%discussion/%"]}, pluck="name"):
			doc = frappe.get_doc(doctype, name)
			doc.update_backlinks()
			for row in doc.backlinks:
				row.db_insert()
