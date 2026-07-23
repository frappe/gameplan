# Copyright (c) 2023, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from gameplan.gameplan.doctype.gp_discussion.api import (
	clause_discussions_commented_by_user,
	get_discussions,
)
from gameplan.gameplan.doctype.gp_discussion.gp_discussion import has_permission
from gameplan.tests.fixtures import (
	create_community,
	create_discussion,
	create_guest,
	create_member,
	create_space,
	grant_guest_access,
)


class TestDiscussions(FrappeTestCase):
	def test_get_discussions_excludes_archived_spaces(self):
		team = create_community("Archived Discussion Filter Team")
		active_project = create_space("Active Discussion Filter Space", team.name)
		archived_project = create_space("Archived Discussion Filter Space", team.name)
		active_discussion = create_discussion("Visible discussion", active_project.name)
		archived_discussion = create_discussion("Hidden discussion", archived_project.name)

		# Creating a discussion bumps the parent Space's `modified` timestamp via
		# discussion hooks, so reload before archiving to avoid a TimestampMismatchError.
		archived_project.reload()
		archived_project.archive()

		discussions = get_discussions(filters={"team": team.name}, limit=50)
		discussion_names = [discussion.name for discussion in discussions]

		self.assertIn(active_discussion.name, discussion_names)
		self.assertNotIn(archived_discussion.name, discussion_names)

	def test_clause_discussions_commented_by_user_with_no_comments(self):
		"""Test that clause_discussions_commented_by_user handles users with no comments gracefully"""
		# Create a test user who has no comments
		test_user = "test_no_comments@example.com"
		if not frappe.db.exists("User", test_user):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": test_user,
					"first_name": "Test",
					"last_name": "NoComments",
					"send_welcome_email": 0,
				}
			).insert(ignore_permissions=True)

		# Ensure the user has no comments
		frappe.db.delete("GP Comment", {"owner": test_user})

		# This should not raise an SQL error (MariaDB error 1064)
		clause = clause_discussions_commented_by_user(test_user)

		# The clause should be valid and can be used in a query
		Discussion = frappe.qb.DocType("GP Discussion")
		query = frappe.qb.from_(Discussion).select(Discussion.name).where(clause).limit(1)

		# This should execute without error
		result = query.run()
		self.assertIsInstance(result, (list, tuple))

		# Cleanup
		frappe.db.rollback()


class TestDiscussionPermissions(FrappeTestCase):
	def setUp(self):
		self.member = create_member("test_disc_member@example.com")
		self.guest = create_guest("test_disc_guest@example.com")
		self.team = create_community("Discussion Perm Team")
		self.project = create_space("Discussion Perm Project", self.team.name)

	def tearDown(self):
		frappe.set_user("Administrator")

	def _discussion(self):
		doc = frappe.new_doc("GP Discussion")
		doc.title = "Sample discussion"
		doc.project = self.project.name
		return doc

	def test_member_can_access(self):
		self.assertTrue(has_permission(self._discussion(), "read", self.member.name))
		self.assertTrue(has_permission(self._discussion(), "write", self.member.name))

	def test_guest_without_access_denied(self):
		self.assertFalse(has_permission(self._discussion(), "read", self.guest.name))

	def test_guest_with_access_allowed(self):
		grant_guest_access(self.guest.name, self.project.name)
		self.assertTrue(has_permission(self._discussion(), "read", self.guest.name))
