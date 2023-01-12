# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe


def execute():
	doctypes = {
		'Team': 'GP Team',
	}
	for old in doctypes:
		new = doctypes[old]
		if not frappe.db.table_exists(new):
			print('Renaming {0} to {1}'.format(old, new))
			frappe.db.rename_table(old, new)
