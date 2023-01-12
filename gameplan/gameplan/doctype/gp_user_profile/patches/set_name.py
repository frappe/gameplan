# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe


def execute():
	for user in frappe.get_all("GP User Profile"):
		doc = frappe.get_doc("GP User Profile", user.name)
		doc.rename(doc.generate_name())
