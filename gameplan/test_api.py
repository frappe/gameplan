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
def clear_data():
    doctypes = frappe.get_all("DocType", filters={"module": "Gameplan"}, pluck="name")
    for doctype in doctypes:
        frappe.db.delete(doctype)
