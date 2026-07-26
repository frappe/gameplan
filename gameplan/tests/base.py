# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""Shared base for all Gameplan tests: personas + permission assertions."""

from contextlib import contextmanager

import frappe
from frappe.tests.utils import FrappeTestCase

from gameplan.tests.fixtures import _name, create_admin, create_guest, create_member
from gameplan.tests.search_isolation import guard_real_index


class GameplanTestCase(FrappeTestCase):
	"""Base test case wiring up the standard persona cast and permission helpers.

	Personas (created fresh in every test, rolled back in tearDown):
	- admin: Gameplan Admin (global admin)
	- member: Gameplan Member, the owner of test content
	- second_member: another Gameplan Member
	- guest: Gameplan Guest
	- outsider: Gameplan Member outside every community/space
	"""

	def setUp(self):
		frappe.set_user("Administrator")
		# The SQLite search index is a file outside the MariaDB transaction, so a leak
		# into it survives rollback. Guarding here rather than only in the search tests is
		# deliberate: the leak arrives through frappe's update_doc_index doc_event, so any
		# test that saves a discussion, comment, task or page can cause it.
		guard_real_index(self)
		self.admin = create_admin()
		self.member = create_member("member@example.com", "Member")
		self.second_member = create_member("member2@example.com", "Second Member")
		self.guest = create_guest("guest@example.com", "Guest")
		self.outsider = create_member("outsider@example.com", "Outsider")

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	@contextmanager
	def as_user(self, user):
		"""Run a block as the given user (doc or name), restoring the session user after."""
		previous = frappe.session.user
		frappe.set_user(_name(user))
		try:
			yield
		finally:
			frappe.set_user(previous)

	def assert_permission(self, doc, action, user, allowed):
		"""Assert frappe.has_permission(doc, action, user) equals `allowed`."""
		user_name = _name(user)
		actual = frappe.has_permission(doc.doctype, action, doc=doc.name, user=user_name)
		verb = "should have" if allowed else "should not have"
		message = f"{user_name} {verb} {action} on {doc.doctype} {doc.name}"
		self.assertEqual(bool(actual), bool(allowed), message)

	def assert_allowed(self, doc, action, user):
		self.assert_permission(doc, action, user, True)

	def assert_not_allowed(self, doc, action, user):
		self.assert_permission(doc, action, user, False)
