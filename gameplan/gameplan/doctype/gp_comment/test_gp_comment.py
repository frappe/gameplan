# Copyright (c) 2022, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from gameplan.gameplan.doctype.gp_comment.gp_comment import has_permission
from gameplan.tests.fixtures import (
	create_community,
	create_discussion,
	create_guest,
	create_member,
	create_space,
	grant_guest_access,
)


class TestGPCommentPermissions(FrappeTestCase):
	def setUp(self):
		self.member = create_member("test_comment_member@example.com")
		self.guest = create_guest("test_comment_guest@example.com")
		self.team = create_community("Comment Perm Team")
		self.project = create_space("Comment Perm Project", self.team.name)
		self.discussion = create_discussion("Comment Perm Discussion", self.project.name)

	def tearDown(self):
		frappe.set_user("Administrator")

	def _comment(self):
		doc = frappe.new_doc("GP Comment")
		doc.reference_doctype = "GP Discussion"
		doc.reference_name = self.discussion.name
		doc.content = "A comment"
		return doc

	def test_member_can_access(self):
		self.assertTrue(has_permission(self._comment(), "read", self.member.name))

	def test_guest_without_access_denied(self):
		self.assertFalse(has_permission(self._comment(), "read", self.guest.name))

	def test_guest_with_access_allowed(self):
		grant_guest_access(self.guest.name, self.project.name)
		self.assertTrue(has_permission(self._comment(), "read", self.guest.name))
