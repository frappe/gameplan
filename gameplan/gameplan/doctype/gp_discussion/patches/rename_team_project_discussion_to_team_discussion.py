# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.rename_doc import rename_doc


def execute():
	if frappe.db.exists("DocType", "Team Project Discussion") and not frappe.db.exists(
		"DocType", "Team Discussion"
	):
		rename_doc("DocType", "Team Project Discussion", "Team Discussion")
