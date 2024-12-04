# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt


import frappe


def execute():
	for d in frappe.db.get_all("GP Discussion", pluck="name"):
		doc = frappe.get_doc("GP Discussion", d)
		doc.update_slug()
		doc.db_set("slug", doc.slug)
