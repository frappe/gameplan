# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe


def execute():
	rename_doctypes()
	create_sequences()


def rename_doctypes():
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
		'Team Activity': 'GP Activity',
		'Team Reaction': 'GP Reaction',
	}
	for old in doctypes:
		new = doctypes[old]
		if not frappe.db.exists('DocType', new):
			print('Renaming {0} to {1}'.format(old, new))
			frappe.rename_doc('DocType', old, new, force=True, ignore_if_exists=True)

def create_sequences():
	doctypes = [
		'GP Discussion',
		'GP Comment',
		'GP Project',
		'GP Notification',
		'GP Task',
		'GP Discussion Visit',
		'GP Member',
		'GP Reaction',
	]
	for doctype in doctypes:
		sequence_name = frappe.scrub(doctype + '_id_seq')
		frappe.db.sql_ddl('drop sequence if exists {0}'.format(sequence_name))
		last_name = frappe.db.get_all(doctype, fields=['max(name) as last'])[0].last
		start_value = last_name + 1
		print('Creating sequence for {0} starting at {1}'.format(doctype, start_value))
		frappe.db.create_sequence(doctype, start_value=start_value, check_not_exists=True, cache=frappe.db.SEQUENCE_CACHE)
