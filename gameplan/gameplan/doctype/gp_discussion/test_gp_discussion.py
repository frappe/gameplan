# Copyright (c) 2023, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from gameplan.gameplan.doctype.gp_discussion.api import clause_discussions_commented_by_user


class TestGPDiscussion(FrappeTestCase):
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
		self.assertIsInstance(result, list)

		# Cleanup
		frappe.db.rollback()
