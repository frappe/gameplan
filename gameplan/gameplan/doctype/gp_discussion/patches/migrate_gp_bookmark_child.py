# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors


import frappe


def execute():
	if not frappe.db.get_value("DocType", "GP Bookmark"):
		return
	frappe.reload_doctype("GP Bookmark")
	for d in frappe.db.get_all("GP Bookmark"):
		try:
			doc = frappe.get_doc("GP Bookmark", d.name)
			for row in doc.bookmarks:
				bdoc = frappe.new_doc("GP Bookmark", discussion=row.discussion, user=doc.user).insert()
				bdoc.db_set("creation", row.date_added)
			doc.delete()
		except Exception as e:
			print(f"Could not migrate bookmark {d.name}: {e}")
			frappe.db.rollback()
