# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe


def execute():
	Task = frappe.qb.DocType('GP Task')
	frappe.qb.update(Task).where(Task.status.isnull()).set(Task.status, 'Backlog').run()
	frappe.qb.update(Task).where(Task.is_completed == 1).set(Task.status, 'Done').run()
