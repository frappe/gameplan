# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt


import frappe


def execute():
	HasRole = frappe.qb.DocType("Has Role")
	query = frappe.qb.update(HasRole).set(HasRole.role, "Gameplan Member").where(HasRole.role == "Teams User")
	query.run()

	frappe.delete_doc_if_exists("Role", "Teams User")
