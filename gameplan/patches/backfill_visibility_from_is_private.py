# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

import frappe

from gameplan.public_access import (
	VISIBILITY_DOCTYPES,
	VISIBILITY_GENERAL,
	VISIBILITY_MEMBER_ACCESS,
)


def execute():
	"""Give every community and space the tier that matches its old `is_private` flag.

	`is_private = 1` becomes Member Access and `is_private = 0` becomes General, so who can
	read what does not change. No row becomes Anonymous: publishing is always a person's
	decision, never a side effect of a migration.

	The restrictive statement runs first. If the second one never runs, every row is Member
	Access and the site is too closed rather than too open. `is_private` itself is left as
	it is, so a rollback needs no data restore.
	"""
	for doctype in VISIBILITY_DOCTYPES:
		table = frappe.qb.DocType(doctype)
		frappe.qb.update(table).set(table.visibility, VISIBILITY_MEMBER_ACCESS).run()
		frappe.qb.update(table).set(table.visibility, VISIBILITY_GENERAL).where(table.is_private == 0).run()
