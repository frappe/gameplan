# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""Authorization tests for the user-management endpoints in gameplan.api and
gameplan's GP User Profile doctype.

These guard the privilege-escalation / account-takeover holes where any
authenticated Gameplan user (incl. a Guest) could change roles, disable
accounts, or send invites. The contract: only admins may call them.
"""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from gameplan.api import get_user_info, invite_by_email
from gameplan.tests.fixtures import (
	create_community,
	create_guest,
	create_member,
	create_space,
	create_user,
)


class TestMemberManagement(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def test_member_cannot_change_user_role(self):
		"""A plain Member must not be able to promote anyone (incl. self) to Admin."""
		member = create_member("sec_member@example.com")
		victim = create_member("sec_victim@example.com")

		frappe.set_user(member.name)
		victim_profile = frappe.get_doc("GP User Profile", {"user": victim.name})
		with self.assertRaises(frappe.PermissionError):
			victim_profile.change_user_role(role="Gameplan Admin")

	def test_admin_can_change_user_role(self):
		"""An admin retains the ability to change roles."""
		admin = create_user("sec_admin@example.com", "Admin", "Gameplan Admin")
		target = create_member("sec_target@example.com")

		frappe.set_user(admin.name)
		target_profile = frappe.get_doc("GP User Profile", {"user": target.name})
		target_profile.change_user_role(role="Gameplan Admin")

		self.assertIn("Gameplan Admin", frappe.get_roles(target.name))

	def test_changing_role_removes_all_previous_gameplan_roles(self):
		admin = create_user("sec_multi_role_admin@example.com", "Admin", "Gameplan Admin")
		target = create_member("sec_multi_role_target@example.com")
		target.add_roles("Gameplan Guest")

		frappe.set_user(admin.name)
		target_profile = frappe.get_doc("GP User Profile", {"user": target.name})
		user_info = target_profile.change_user_role(role="Gameplan Admin")

		gameplan_roles = [role for role in frappe.get_roles(target.name) if role.startswith("Gameplan ")]
		self.assertEqual(gameplan_roles, ["Gameplan Admin"])
		self.assertEqual(user_info.role, "Gameplan Admin")

	def test_member_cannot_disable_user(self):
		"""A Member must not be able to disable another account."""
		member = create_member("sec_member2@example.com")
		victim = create_member("sec_victim2@example.com")

		frappe.set_user(member.name)
		victim_profile = frappe.get_doc("GP User Profile", {"user": victim.name})
		with self.assertRaises(frappe.PermissionError):
			victim_profile.disable_user()

		frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value("User", victim.name, "enabled"), 1)

	def test_member_cannot_invite_by_email(self):
		"""A Member must not be able to send invites (esp. with an Admin role)."""
		member = create_member("sec_member3@example.com")

		frappe.set_user(member.name)
		with self.assertRaises(frappe.PermissionError):
			invite_by_email("outsider@example.com", role="Gameplan Admin")

		frappe.set_user("Administrator")
		self.assertFalse(frappe.db.exists("GP Invitation", {"email": "outsider@example.com"}))

	def test_invite_rejects_unknown_role(self):
		"""Even an admin cannot invite with a role outside the allowlist."""
		with self.assertRaises(frappe.ValidationError):
			invite_by_email("someone@example.com", role="System Manager")

		self.assertFalse(frappe.db.exists("GP Invitation", {"email": "someone@example.com"}))

	def test_member_can_invite_guest_to_project(self):
		"""Gating invite_by_email must not break a private-space member inviting a guest.

		invite_guest hardcodes the Gameplan Guest role (non-escalating), so it routes
		through the trusted internal helper rather than the admin-gated endpoint.
		"""
		member = create_member("sec_space_member@example.com")
		team = create_community("Sec Team")
		project = create_space("Sec Space", team.name, is_private=1)
		project.append("members", {"user": member.name})
		project.save(ignore_permissions=True)

		frappe.set_user(member.name)
		# GP Invitation.after_insert emails the invitee, so without this the assertion
		# under test would hinge on the site having an outgoing Email Account (CI mutes
		# mail via site config; a plain dev site raises OutgoingEmailError). Same mute as
		# InvitationTestCase in test_invitations.py.
		with patch("frappe.sendmail"):
			project.invite_guest("invited_guest@example.com")

		frappe.set_user("Administrator")
		invitation = frappe.db.get_value(
			"GP Invitation",
			{"email": "invited_guest@example.com"},
			["role", "projects"],
			as_dict=True,
		)
		self.assertIsNotNone(invitation)
		self.assertEqual(invitation.role, "Gameplan Guest")
		self.assertEqual(frappe.parse_json(invitation.projects), [project.name])

	def test_get_user_info_hides_email_from_guest(self):
		"""A Guest caller must not receive other members' email addresses."""
		create_member("sec_directory_member@example.com")
		guest = create_guest("sec_guest@example.com")

		frappe.set_user(guest.name)
		users = get_user_info()

		self.assertTrue(users)
		for user in users:
			self.assertNotIn("email", user)

	def test_get_user_info_exposes_email_to_admin(self):
		"""An admin still receives email (member directory management)."""
		create_member("sec_directory_member2@example.com")

		frappe.set_user("Administrator")
		users = get_user_info()

		self.assertTrue(users)
		self.assertTrue(any(user.get("email") for user in users))
