# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe

def whitelist(fn):
	if not frappe.conf.enable_ui_tests:
		frappe.throw("Cannot run UI tests. Set 'enable_ui_tests' in site_config.json to continue.")

	whitelisted = frappe.whitelist()(fn)
	return whitelisted


@whitelist
def clear_data(onboard=None):
	doctypes = frappe.get_all("DocType", filters={"module": "Gameplan"}, pluck="name")
	for doctype in doctypes:
		frappe.db.delete(doctype)

	admin = frappe.get_doc('User', 'Administrator')
	admin.add_roles('Gameplan Admin')

	if not frappe.db.exists('User', 'john@example.com'):
		frappe.get_doc(
			doctype='User',
			email='john@example.com',
			first_name='John',
			last_name='Doe',
			send_welcome_email=0,
			roles=[{'role': 'Gameplan Member'}]
		).insert()

	if not frappe.db.exists('User', 'system@example.com'):
		frappe.get_doc(
			doctype='User',
			email='system@example.com',
			first_name='System',
			last_name='User',
			send_welcome_email=0,
			roles=[{'role': 'Gameplan Admin'},{'role': 'System Manager'}]
		).insert()

	keep_users = ['Administrator', 'Guest', 'john@example.com', 'system@example.com']
	for user in frappe.get_all("User", filters={"name": ["not in", keep_users]}):
		frappe.delete_doc("User", user.name)

	if onboard:
		frappe.get_doc(doctype='GP Team', title='Test Team').insert()