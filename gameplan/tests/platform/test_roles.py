# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""Gameplan's roles are created from code, and existing roles are left alone.

The roles used to ship as a fixture, which frappe re-inserts on every `bench migrate`.
That fired `Role.on_update` -> `update_user_type_on_change()` -> `user.save()`, and on
frappe v16 the user save crashes migrate: `User.on_update` enqueues `create_contact` with
the lazily-loaded user doc, and the dynamically built `LazyUser` class is not picklable.

Because the crash aborts and rolls back migrate, *any* Role write from a migrate hook is a
deadlock, not a one-off error — the write never lands, so the next migrate retries it. The
tests here pin the one rule that avoids it: create what is missing, touch nothing else.
"""

import io
from contextlib import redirect_stdout
from unittest.mock import patch

import frappe
from frappe.core.doctype.role.role import Role
from frappe.tests.utils import FrappeTestCase

from gameplan.roles import GAMEPLAN_ROLES, setup_roles, sync_roles

TEST_ROLE = "Gameplan Test Role"


class TestGameplanRoles(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_no_role_fixture_is_shipped(self):
		"""A Role fixture would reintroduce the per-migrate delete/re-insert churn."""
		fixtures = frappe.get_hooks("fixtures", app_name="gameplan") or []
		self.assertEqual([f for f in fixtures if f.get("dt") == "Role"], [])

	def test_missing_role_is_created_without_desk_access(self):
		with patch("gameplan.roles.GAMEPLAN_ROLES", (TEST_ROLE,)):
			sync_roles()

		self.assertEqual(frappe.db.get_value("Role", TEST_ROLE, "desk_access"), 0)

	def test_install_clears_desk_access_frappe_already_granted(self):
		"""install_app syncs doctypes before after_install, so make_module_and_roles wins
		the race and creates every role named in a permission with desk_access = 1. Install
		has to correct that, or a fresh site makes every Gameplan member a System User."""
		frappe.get_doc(doctype="Role", role_name=TEST_ROLE, desk_access=1).insert()

		with patch("gameplan.roles.GAMEPLAN_ROLES", (TEST_ROLE,)):
			setup_roles()

		self.assertEqual(frappe.db.get_value("Role", TEST_ROLE, "desk_access"), 0)

	def test_install_creates_a_missing_role_without_desk_access(self):
		with patch("gameplan.roles.GAMEPLAN_ROLES", (TEST_ROLE,)):
			setup_roles()

		self.assertEqual(frappe.db.get_value("Role", TEST_ROLE, "desk_access"), 0)

	def test_desk_access_on_an_existing_role_is_left_alone(self):
		"""desk_access is the operator's call once the role exists.

		gameplan.frappe.cloud runs Gameplan Member with desk_access = 1 by deliberate
		choice; resetting it here would demote ~80 accounts to Website User.
		"""
		frappe.get_doc(doctype="Role", role_name=TEST_ROLE, desk_access=1).insert()

		with patch("gameplan.roles.GAMEPLAN_ROLES", (TEST_ROLE,)), redirect_stdout(io.StringIO()):
			sync_roles()

		self.assertEqual(frappe.db.get_value("Role", TEST_ROLE, "desk_access"), 1)

	def test_sync_never_saves_an_existing_role(self):
		"""The regression guard for the migrate deadlock.

		Saving a Role runs update_user_type_on_change over every user holding it, which is
		what kills migrate on frappe v16. Neither a correct role nor a drifted one may save.
		"""
		frappe.get_doc(doctype="Role", role_name=TEST_ROLE, desk_access=1).insert()

		with patch.object(Role, "on_update", autospec=True) as on_update, redirect_stdout(io.StringIO()):
			sync_roles()
			with patch("gameplan.roles.GAMEPLAN_ROLES", (TEST_ROLE,)):
				sync_roles()

		on_update.assert_not_called()

	def test_a_role_granting_desk_access_is_reported_not_corrected(self):
		"""Deleting a Gameplan role gets it recreated by make_module_and_roles with
		desk_access = 1 during the same migrate. We cannot fix that silently, so it has to
		at least show up in the migrate output."""
		frappe.get_doc(doctype="Role", role_name=TEST_ROLE, desk_access=1).insert()

		output = io.StringIO()
		with patch("gameplan.roles.GAMEPLAN_ROLES", (TEST_ROLE,)), redirect_stdout(output):
			sync_roles()

		self.assertIn(TEST_ROLE, output.getvalue())
		self.assertEqual(frappe.db.get_value("Role", TEST_ROLE, "desk_access"), 1)

	def test_nothing_is_reported_when_no_role_grants_desk_access(self):
		output = io.StringIO()
		with patch("gameplan.roles.GAMEPLAN_ROLES", (TEST_ROLE,)), redirect_stdout(output):
			sync_roles()

		self.assertEqual(output.getvalue(), "")

	def test_all_gameplan_roles_exist(self):
		for role in GAMEPLAN_ROLES:
			with self.subTest(role=role):
				self.assertTrue(frappe.db.exists("Role", role))
