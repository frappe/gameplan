# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

from unittest.mock import MagicMock, patch

import frappe
from frappe.client import delete, insert, set_value
from frappe.utils import today

from gameplan.api import accept_invitation
from gameplan.extends.client import get_list as get_client_list
from gameplan.gameplan.doctype.gp_invitation.gp_invitation import GPInvitation
from gameplan.tests.base import GameplanTestCase


class TestProfileSecurity(GameplanTestCase):
	def test_set_value_cannot_change_another_bio(self):
		profile = frappe.get_doc("GP User Profile", {"user": self.member.name})
		with self.as_user(self.second_member):
			with self.assertRaises(frappe.PermissionError):
				set_value("GP User Profile", profile.name, "bio", "tampered")

	def test_member_cannot_take_over_profile_by_changing_user(self):
		profile = frappe.get_doc("GP User Profile", {"user": self.member.name})
		own_profile = frappe.get_doc("GP User Profile", {"user": self.second_member.name})
		with self.as_user(self.second_member):
			delete("GP User Profile", own_profile.name)
			with self.assertRaises(frappe.PermissionError):
				set_value(
					"GP User Profile", profile.name, {"user": self.second_member.name, "bio": "tampered"}
				)
		self.assertEqual(frappe.db.get_value("GP User Profile", profile.name, "user"), self.member.name)

	def test_member_cannot_give_own_profile_to_another_user(self):
		profile = frappe.get_doc("GP User Profile", {"user": self.member.name})
		other_profile = frappe.get_doc("GP User Profile", {"user": self.second_member.name})
		other_profile.delete(ignore_permissions=True)
		with self.as_user(self.member):
			with self.assertRaises(frappe.PermissionError):
				profile.user = self.second_member.name
				profile.save(ignore_permissions=True)

	def test_generic_list_cannot_read_account_fields_through_profile_link(self):
		frappe.db.set_value("User", self.second_member.name, "last_ip", "203.0.113.7")
		with self.as_user(self.member):
			rows = get_client_list(
				"GP User Profile", fields=["name", "user.last_ip"], filters={"user": self.second_member.name}
			)
			self.assertTrue(rows)
			self.assertIsNone(rows[0].get("last_ip"))
			self.assertEqual(
				get_client_list(
					"GP User Profile", fields=["name"], filters={"user.last_ip": ["like", "203.%"]}
				),
				[],
			)


class TestInvitationSecurity(GameplanTestCase):
	def setUp(self):
		super().setUp()
		sendmail = patch("frappe.sendmail")
		sendmail.start()
		self.addCleanup(sendmail.stop)

	def invitation(self, user=None):
		return frappe.get_doc(
			doctype="GP Invitation", email=user or self.member.name, role="Gameplan Admin"
		).insert()

	def test_member_cannot_create_admin_invitation_through_client(self):
		with self.as_user(self.member):
			with self.assertRaises(frappe.PermissionError):
				insert({"doctype": "GP Invitation", "email": self.member.name, "role": "Gameplan Admin"})

	def test_members_and_guests_cannot_read_invitation_keys(self):
		invitation = self.invitation()
		for user in (self.member, self.guest):
			with self.subTest(user=user.name), self.as_user(user):
				for get_list in (frappe.get_list, get_client_list):
					rows = get_list(
						"GP Invitation", fields=["name", "email", "key"], filters={"name": invitation.name}
					)
					self.assertTrue(rows)
					self.assertNotIn("key", rows[0])
				invitation.reload()
				invitation.apply_fieldlevel_read_permissions()
				self.assertFalse(invitation.get("key"))

	def test_member_cannot_rewrite_invitation_recipient_or_role(self):
		invitation = self.invitation(self.second_member.name)
		with self.as_user(self.member):
			with self.assertRaises(frappe.PermissionError):
				set_value(
					"GP Invitation", invitation.name, {"email": self.member.name, "role": "Gameplan Admin"}
				)

	def test_accepted_invitation_cannot_log_in_again(self):
		frappe.db.set_value("User", self.member.name, "last_password_reset_date", today())
		invitation = self.invitation()
		invitation.accept()
		login_manager = MagicMock()
		with patch.object(frappe.local, "login_manager", login_manager, create=True):
			with self.as_user("Guest"), self.assertRaises(frappe.ValidationError):
				accept_invitation(invitation.key)
		login_manager.login_as.assert_not_called()

	def test_accepted_invitation_cannot_issue_another_password_reset(self):
		invitation = self.invitation()
		invitation.accept()
		with patch.object(GPInvitation, "get_password_link") as password_link:
			with self.as_user("Guest"), self.assertRaises(frappe.ValidationError):
				accept_invitation(invitation.key)
		password_link.assert_not_called()

	def test_new_user_acceptance_does_not_commit_before_consuming_key(self):
		invitation = self.invitation("atomic-invitee@example.com")
		with patch.object(frappe.db, "commit") as commit:
			invitation.accept()
		commit.assert_not_called()
		self.assertEqual(invitation.status, "Accepted")

	def test_custom_permissions_cannot_restore_invitation_escalation(self):
		from frappe.permissions import update_permission_property

		invitation = self.invitation(self.second_member.name)
		for action in ("create", "write"):
			update_permission_property("GP Invitation", "Gameplan Member", 0, action, 1)
		self.addCleanup(frappe.clear_cache, doctype="GP Invitation")
		with self.as_user(self.member):
			self.assertTrue(frappe.has_permission("GP Invitation", "create"))
			with self.assertRaises(frappe.PermissionError):
				insert({"doctype": "GP Invitation", "email": self.member.name, "role": "Gameplan Admin"})
			with self.assertRaises(frappe.PermissionError):
				set_value("GP Invitation", invitation.name, "email", self.member.name)
