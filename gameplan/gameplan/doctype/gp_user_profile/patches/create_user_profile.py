# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe


def execute():
	for user in frappe.get_all("User"):
		if user.name in ["Administrator", "Guest"]:
			continue
		frappe.get_doc(doctype="GP User Profile", user=user.name).insert(ignore_if_duplicate=True)
