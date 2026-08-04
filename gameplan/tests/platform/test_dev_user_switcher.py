# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""The gates on the password-less dev user switcher.

`switch_user` hands out somebody else's session with no credential, so what is
worth testing is not that it works — it is that every way of reaching it from a
server that should not allow it is closed.
"""

from unittest.mock import MagicMock, patch

import frappe

from gameplan.dev_user_switcher import CONFIG_KEY, switch_user
from gameplan.tests.base import GameplanTestCase


class TestDevUserSwitcher(GameplanTestCase):
	def setUp(self):
		super().setUp()
		# `login_as` reaches for the request-scoped login manager, which no test
		# request has. Recording the call is all the assertions here need.
		self.login_manager = MagicMock()
		previous = getattr(frappe.local, "login_manager", None)
		frappe.local.login_manager = self.login_manager
		self.addCleanup(lambda: setattr(frappe.local, "login_manager", previous))

	def enabled(self, value=1):
		"""Turn the site config key on (or to some other value) for one test."""
		patcher = patch.dict(frappe.conf, {CONFIG_KEY: value})
		self.addCleanup(patcher.stop)
		patcher.start()

	def test_switches_to_a_gameplan_user(self):
		self.enabled()

		result = switch_user(self.second_member.name)

		self.assertEqual(result, {"user": self.second_member.name})
		self.login_manager.login_as.assert_called_once_with(self.second_member.name)

	def test_switches_to_a_guest(self):
		"""The whole reason this exists instead of frappe's `impersonate`: a guest
		has no elevated permission to switch back with, so the endpoint must not
		depend on one."""
		self.enabled()

		switch_user(self.guest.name)

		self.login_manager.login_as.assert_called_once_with(self.guest.name)

	def test_refuses_without_the_config_key(self):
		self.enabled(0)

		with self.assertRaises(frappe.ValidationError) as caught:
			switch_user(self.second_member.name)

		self.assertIn(CONFIG_KEY, str(caught.exception))
		self.login_manager.login_as.assert_not_called()

	def test_refuses_a_truthy_looking_string(self):
		"""`site_config.json` is hand-edited, so "false" and "0" arrive as strings.
		Read as plain Python truth they would each enable this."""
		for value in ("false", "0", "true"):
			with self.subTest(value=value):
				self.enabled(value)

				with self.assertRaises(frappe.ValidationError):
					switch_user(self.second_member.name)

				self.login_manager.login_as.assert_not_called()

	def test_refuses_off_a_dev_server(self):
		self.enabled()

		with patch.object(frappe, "in_test", False), patch.object(frappe, "_dev_server", 0):
			with self.assertRaises(frappe.ValidationError) as caught:
				switch_user(self.second_member.name)

		self.assertIn("development server", str(caught.exception))
		self.login_manager.login_as.assert_not_called()

	def test_refuses_an_unknown_user(self):
		self.enabled()

		with self.assertRaises(frappe.ValidationError):
			switch_user("nobody@example.com")

		self.login_manager.login_as.assert_not_called()

	def test_refuses_a_user_without_a_gameplan_role(self):
		"""On a bench running other apps too, their users are not switch targets —
		and this matches what the switcher lists, which is the same filter."""
		self.enabled()

		with self.assertRaises(frappe.ValidationError):
			switch_user("Guest")

		self.login_manager.login_as.assert_not_called()

	def test_refuses_a_disabled_user(self):
		self.enabled()
		frappe.db.set_value("User", self.second_member.name, "enabled", 0)

		with self.assertRaises(frappe.ValidationError):
			switch_user(self.second_member.name)

		self.login_manager.login_as.assert_not_called()
