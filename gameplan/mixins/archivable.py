# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe


class Archivable:
	'''
	Mixin to add archive and unarchive methods to a DocType. `archived_at` (Datetime) and
	`archived_by` (Link to User) fields are required for this mixin to work.
	'''
	@frappe.whitelist()
	def archive(self):
		self.archived_at = frappe.utils.now()
		self.archived_by = frappe.session.user
		self.save()

	@frappe.whitelist()
	def unarchive(self):
		self.archived_at = None
		self.archived_by = None
		self.save()