# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe


def execute():
    for d in frappe.db.get_all('GP Discussion', pluck='name'):
        doc = frappe.get_doc('GP Discussion', d)
        doc.update_slug()
        doc.db_set('slug', doc.slug)
