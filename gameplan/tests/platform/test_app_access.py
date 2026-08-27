# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""The /g gate: a signed-in user with no Gameplan role gets a 403, not the SPA.

Every Gameplan doctype grants read to a Gameplan role, so such a user is denied on the
first list call the SPA makes. The frontend cannot tell that 403 apart from an empty
result: it reads the site as brand new and shows onboarding, which then fails on create.
Users land in this state through OAuth, which mints a Website User with no role.
"""

import frappe
from frappe.utils import set_request
from frappe.website.serve import get_response

from gameplan.roles import has_app_access
from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import create_user
from gameplan.www.g import require_app_access


class TestAppAccess(GameplanTestCase):
	def setUp(self):
		super().setUp()
		self.roleless = create_user("roleless@example.com", "Roleless")

	def test_a_user_with_no_gameplan_role_has_no_app_access(self):
		self.assertFalse(has_app_access(self.roleless.name))

	def test_every_gameplan_role_grants_app_access(self):
		for user in (self.admin, self.member, self.guest):
			self.assertTrue(has_app_access(user.name), user.name)

	def test_administrator_always_has_app_access(self):
		self.assertTrue(has_app_access("Administrator"))

	def test_require_app_access_raises_for_a_user_with_no_role(self):
		with self.as_user(self.roleless), self.assertRaises(frappe.PermissionError):
			require_app_access()

	def test_require_app_access_allows_a_member(self):
		with self.as_user(self.member):
			require_app_access()

	def test_require_app_access_lets_guest_through_to_the_login_redirect(self):
		"""Someone who has not signed in yet must reach the SPA, which sends them to
		/login. Telling them they lack a role would be both wrong and a dead end."""
		with self.as_user("Guest"):
			require_app_access()

	def test_g_responds_403_with_the_message(self):
		# NotPermittedPage builds its login link from `frappe.request.path`, and a unit
		# test has no bound request. `set_request` is frappe's own helper for calling the
		# renderer outside HTTP (see frappe.utils.get_html_for_route). Delete it again
		# afterwards: frappe.local outlives the transaction rollback, so a request left
		# bound here would change how a later test in the same shard behaves.
		#
		# Only the denied path is driven through the real renderer. `get_context` calls
		# frappe.db.commit() once it is past the gate, which would write this test's
		# personas onto the site for good; the throw lands before that line.
		set_request(method="GET", path="/g")
		self.addCleanup(delattr, frappe.local, "request")

		with self.as_user(self.roleless):
			response = get_response("/g")

		self.assertEqual(response.status_code, 403)
		self.assertIn("Ask an admin to invite you", response.get_data(as_text=True))
