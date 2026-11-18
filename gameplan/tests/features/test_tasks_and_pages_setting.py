# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""The site-wide GP Settings switch that brings back the deprecated Tasks and Pages."""

import frappe

from gameplan.tests.base import GameplanTestCase
from gameplan.www.g import get_boot


class TestTasksAndPagesSetting(GameplanTestCase):
	def test_off_by_default_and_boot_follows_the_saved_value(self):
		# Start from a site that never saved the setting; the test rolls this back.
		frappe.db.delete("Singles", {"doctype": "GP Settings"})
		self.assertFalse(get_boot().enable_tasks_and_pages)

		with self.as_user(self.admin):
			settings = frappe.get_doc("GP Settings")
			settings.enable_tasks_and_pages = 1
			settings.save()

		with self.as_user(self.member):
			self.assertTrue(get_boot().enable_tasks_and_pages)

	def test_only_admins_can_change_it(self):
		for user in (self.member, self.guest):
			with self.as_user(user):
				settings = frappe.get_doc("GP Settings")
				settings.enable_tasks_and_pages = 1
				self.assertRaises(frappe.PermissionError, settings.save)
