# Copyright (c) 2022, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from gameplan.gameplan.doctype.gp_task.gp_task import has_permission
from gameplan.tests.fixtures import (
	create_community,
	create_guest,
	create_member,
	create_space,
	grant_guest_access,
)


class TestGPTaskPermissions(FrappeTestCase):
	def setUp(self):
		self.member = create_member("test_task_member@example.com")
		self.guest = create_guest("test_task_guest@example.com")
		self.team = create_community("Task Perm Team")
		self.project = create_space("Task Perm Project", self.team.name)

	def tearDown(self):
		frappe.set_user("Administrator")

	def _task(self):
		doc = frappe.new_doc("GP Task")
		doc.title = "Sample task"
		doc.project = self.project.name
		return doc

	def test_member_can_access(self):
		self.assertTrue(has_permission(self._task(), "read", self.member.name))
		self.assertTrue(has_permission(self._task(), "write", self.member.name))

	def test_guest_without_access_denied(self):
		self.assertFalse(has_permission(self._task(), "read", self.guest.name))

	def test_guest_with_access_allowed(self):
		grant_guest_access(self.guest.name, self.project.name)
		self.assertTrue(has_permission(self._task(), "read", self.guest.name))
