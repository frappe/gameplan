# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.core.doctype.user.user import User
from frappe.utils import add_to_date

from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import create_member


class TestUserFixtures(GameplanTestCase):
	def test_role_assignment_reloads_the_user_after_insert(self):
		insert = User.insert

		def insert_with_newer_timestamp(user, *args, **kwargs):
			user = insert(user, *args, **kwargs)
			# Reproduce the timestamp mismatch seen between insert and add_roles on v16.
			frappe.db.set_value(
				"User", user.name, "modified", add_to_date(user.modified, seconds=1), update_modified=False
			)
			return user

		with patch.object(User, "insert", insert_with_newer_timestamp):
			user = create_member(f"fixture-{frappe.generate_hash(length=8)}@example.com", "Fixture User")

		self.assertIn("Gameplan Member", frappe.get_roles(user.name))
