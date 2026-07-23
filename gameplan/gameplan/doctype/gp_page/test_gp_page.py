# Copyright (c) 2023, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from gameplan.gameplan.doctype.gp_page.gp_page import has_permission
from gameplan.tests.fixtures import (
	create_community,
	create_guest,
	create_member,
	create_space,
	grant_guest_access,
)


class TestGPPagePermissions(FrappeTestCase):
	def setUp(self):
		self.member = create_member("test_page_member@example.com")
		self.other = create_member("test_page_other@example.com")
		self.guest = create_guest("test_page_guest@example.com")
		self.team = create_community("Page Perm Team")
		self.project = create_space("Page Perm Project", self.team.name)

	def tearDown(self):
		frappe.set_user("Administrator")

	def _page(self, project=None, owner=None):
		doc = frappe.new_doc("GP Page")
		doc.title = "Sample page"
		doc.project = project
		doc.owner = owner or self.member.name
		return doc

	def test_member_can_access_project_page(self):
		page = self._page(project=self.project.name)
		self.assertTrue(has_permission(page, "read", self.member.name))

	def test_member_can_access_own_private_page(self):
		page = self._page(project=None, owner=self.member.name)
		self.assertTrue(has_permission(page, "read", self.member.name))

	def test_member_cannot_access_others_private_page(self):
		page = self._page(project=None, owner=self.other.name)
		self.assertFalse(has_permission(page, "read", self.member.name))

	def test_guest_without_access_denied(self):
		page = self._page(project=self.project.name)
		self.assertFalse(has_permission(page, "read", self.guest.name))

	def test_guest_with_access_allowed(self):
		grant_guest_access(self.guest.name, self.project.name)
		page = self._page(project=self.project.name)
		self.assertTrue(has_permission(page, "read", self.guest.name))
