# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""Gameplan's roles are created from code, not from a Role fixture.

The fixture was re-inserted on every `bench migrate`, which fired `Role.on_update` and
re-saved users. On frappe v16 that re-save crashed migrate outright: `User.on_update`
enqueues `create_contact` with the lazily-loaded user doc, and the dynamically built
`LazyUser` class is not picklable. The tests here pin both halves — no fixture, and a
sync that stays silent when nothing drifted.
"""

from unittest.mock import patch

import frappe
from frappe.core.doctype.role.role import Role
from frappe.tests.utils import FrappeTestCase

from gameplan.roles import GAMEPLAN_ROLES, sync_roles

TEST_ROLE = "Gameplan Test Role"


class TestGameplanRoles(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_no_role_fixture_is_shipped(self):
		"""A Role fixture would reintroduce the per-migrate churn this module removed."""
		fixtures = frappe.get_hooks("fixtures", app_name="gameplan") or []
		self.assertEqual([f for f in fixtures if f.get("dt") == "Role"], [])

	def test_gameplan_roles_have_no_desk_access(self):
		for role in GAMEPLAN_ROLES:
			with self.subTest(role=role):
				self.assertEqual(frappe.db.get_value("Role", role, "desk_access"), 0)

	def test_missing_role_is_created_without_desk_access(self):
		with patch("gameplan.roles.GAMEPLAN_ROLES", (TEST_ROLE,)):
			sync_roles()

		self.assertEqual(frappe.db.get_value("Role", TEST_ROLE, "desk_access"), 0)

	def test_desk_access_drift_is_corrected(self):
		"""frappe recreates roles named in doctype permissions with desk_access = 1."""
		frappe.get_doc(doctype="Role", role_name=TEST_ROLE, desk_access=1).insert()

		with patch("gameplan.roles.GAMEPLAN_ROLES", (TEST_ROLE,)):
			sync_roles()

		self.assertEqual(frappe.db.get_value("Role", TEST_ROLE, "desk_access"), 0)

	def test_sync_does_not_touch_roles_that_are_already_correct(self):
		"""The regression guard: a repeat sync must not re-save the Role.

		Saving it runs Role.update_user_type_on_change over every user holding the role,
		which is what broke migrate on frappe v16.
		"""
		with patch.object(Role, "on_update", autospec=True) as on_update:
			sync_roles()

		on_update.assert_not_called()
