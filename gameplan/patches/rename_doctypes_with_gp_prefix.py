# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe


def execute():
	doctypes = {
		'Team': 'GP Team',
		'Team Project': 'GP Project',
		'Team Discussion': 'GP Discussion',
		'Team Task': 'GP Task',
		'Team Comment': 'GP Comment',
		'Team Member': 'GP Member',
		'Team Discussion Visit': 'GP Discussion Visit',
		'Team Notification': 'GP Notification',
		'Team User Profile': 'GP User Profile',
	}
	for old in doctypes:
		new = doctypes[old]
		if not frappe.db.exists('DocType', new):
			print('Renaming {0} to {1}'.format(old, new))
			frappe.rename_doc('DocType', old, new, force=True, ignore_if_exists=True)
