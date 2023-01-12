# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe


def execute():
	doctypes = {
		'Team': 'GP Team',
		'Team Project': 'GP Project',
		'Team Discussion': 'GP Discussion',
	}
	for old in doctypes:
		new = doctypes[old]
		if not frappe.db.exists('DocType', new):
			print('Renaming {0} to {1}'.format(old, new))
			frappe.rename_doc('DocType', old, new, force=True, ignore_if_exists=True)
