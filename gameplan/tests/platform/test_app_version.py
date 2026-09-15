# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""The About-dialog version read, which `/g` runs on every page render.

A deployed checkout is usually shallow and carries no tags, so `git describe` fails on
every call. That used to write an Error Log row per failed git call per page load,
which drowned real tracebacks in "Git Command Error" noise and made a broken login look
like it produced no traceback at all.
"""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from gameplan.www.g import (
	APP_VERSION_CACHE_KEY,
	get_app_version,
	read_app_version,
	run_git_command,
)


class TestAppVersion(FrappeTestCase):
	def setUp(self):
		super().setUp()
		frappe.cache.delete_value(APP_VERSION_CACHE_KEY)
		self.addCleanup(frappe.cache.delete_value, APP_VERSION_CACHE_KEY)

	def test_a_failing_git_command_returns_empty_and_writes_no_error_log(self):
		before = frappe.db.count("Error Log")
		self.assertEqual(run_git_command("git -C /nonexistent-path rev-parse HEAD"), "")
		self.assertEqual(frappe.db.count("Error Log"), before)

	def test_git_being_unreachable_is_quiet_too(self):
		before = frappe.db.count("Error Log")
		with patch("subprocess.check_output", side_effect=OSError("no such executable")):
			self.assertEqual(run_git_command("git rev-parse HEAD"), "")
		self.assertEqual(frappe.db.count("Error Log"), before)

	def test_an_unexpected_failure_keeps_its_traceback(self):
		"""Only the expected git failures are silent. Anything else still gets logged,
		and is still swallowed: `get_boot` must not take /g down over version info."""
		before = frappe.db.count("Error Log")
		with patch("subprocess.check_output", side_effect=MemoryError("boom")):
			self.assertEqual(run_git_command("git rev-parse HEAD"), "")
		self.assertEqual(frappe.db.count("Error Log"), before + 1)

	def test_the_version_read_survives_a_checkout_git_cannot_answer_for(self):
		with patch("gameplan.www.g.run_git_command", return_value=""):
			version = read_app_version()

		self.assertEqual(version["branch"], "")
		self.assertEqual(version["tag"], "")
		self.assertFalse(version["dirty"])

	def test_the_version_is_read_once_and_then_served_from_cache(self):
		with patch("gameplan.www.g.read_app_version", return_value={"branch": "test"}) as read:
			self.assertEqual(get_app_version(), {"branch": "test"})
			self.assertEqual(get_app_version(), {"branch": "test"})

		self.assertEqual(read.call_count, 1)
