# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""Invitation lifecycle: create, accept, expire.

Security-sensitive — an invitation mints a User account and grants it a role
(and, for guests, space access). The admin gate / role allowlist on the public
`invite_by_email` endpoint is covered in `test_members.py`; this file owns the
domain behavior underneath it:

- creation rules (guest needs a space, non-guest roles never carry space links,
  de-duplication against existing members and pending invites),
- `accept()` (idempotent user creation, role assignment, guest access grants),
- the `accept_invitation` public endpoint's key guard and post-accept routing,
- `expire_invitations` housekeeping.
"""

from unittest.mock import MagicMock, patch

import frappe
from frappe.utils import add_days, now

from gameplan.api import _invite_by_email, accept_invitation
from gameplan.gameplan.doctype.gp_invitation.gp_invitation import expire_invitations
from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import create_community, create_member, create_space


class InvitationTestCase(GameplanTestCase):
	def setUp(self):
		super().setUp()
		# after_insert emails the invitee; every test here creates invitations, so
		# mute the send once for the whole case rather than wrapping each call.
		sendmail = patch("frappe.sendmail")
		sendmail.start()
		self.addCleanup(sendmail.stop)

	def make_invitation(self, email, role="Gameplan Member", projects=None):
		return frappe.get_doc(
			doctype="GP Invitation",
			email=email,
			role=role,
			projects=frappe.as_json(projects) if projects else None,
		).insert(ignore_permissions=True)


class TestInvitationCreation(InvitationTestCase):
	def test_new_invitation_is_pending_with_key_and_inviter(self):
		with self.as_user(self.admin):
			invitation = self.make_invitation("invitee@example.com")

		self.assertEqual(invitation.status, "Pending")
		self.assertTrue(invitation.key)
		self.assertEqual(invitation.invited_by, self.admin.name)
		self.assertEqual(invitation.role, "Gameplan Member")

	def test_guest_invitation_requires_a_space(self):
		with self.assertRaises(frappe.ValidationError):
			self.make_invitation("guest-no-space@example.com", role="Gameplan Guest")

		self.assertFalse(frappe.db.exists("GP Invitation", {"email": "guest-no-space@example.com"}))

	def test_guest_invitation_keeps_its_space(self):
		community = create_community("Guest Invite Community")
		space = create_space("Guest Invite Space", community, is_private=1)

		invitation = self.make_invitation(
			"scoped-guest@example.com", role="Gameplan Guest", projects=[space.name]
		)

		self.assertEqual(frappe.parse_json(invitation.projects), [space.name])

	def test_non_guest_invitation_never_carries_a_space(self):
		"""Space links are meaningful only for guests; a Member/Admin invite must
		drop them so accept() can't silently mint guest access for a full member."""
		community = create_community("Member Invite Community")
		space = create_space("Member Invite Space", community)

		invitation = self.make_invitation(
			"full-member@example.com", role="Gameplan Member", projects=[space.name]
		)

		self.assertIsNone(invitation.projects)

	def test_invite_skips_existing_member(self):
		create_member("already-member@example.com")

		_invite_by_email("already-member@example.com", role="Gameplan Member")

		self.assertFalse(frappe.db.exists("GP Invitation", {"email": "already-member@example.com"}))

	def test_invite_skips_duplicate_pending_invite(self):
		_invite_by_email("dup@example.com", role="Gameplan Member")
		_invite_by_email("dup@example.com", role="Gameplan Member")

		count = frappe.db.count("GP Invitation", {"email": "dup@example.com"})
		self.assertEqual(count, 1)

	def test_guest_invite_is_allowed_for_an_existing_user(self):
		"""A guest can already have an account (e.g. invited to another space);
		unlike member invites, an existing User must not block a guest invite."""
		create_member("existing-then-guest@example.com")
		community = create_community("Second Guest Community")
		space = create_space("Second Guest Space", community, is_private=1)

		_invite_by_email("existing-then-guest@example.com", role="Gameplan Guest", projects=[space.name])

		self.assertTrue(
			frappe.db.exists("GP Invitation", {"email": "existing-then-guest@example.com"})
		)


class TestInvitationAccept(InvitationTestCase):
	def test_accept_creates_website_user_with_role(self):
		invitation = self.make_invitation("fresh@example.com", role="Gameplan Member")

		invitation.accept()

		self.assertTrue(frappe.db.exists("User", "fresh@example.com"))
		self.assertEqual(frappe.db.get_value("User", "fresh@example.com", "user_type"), "Website User")
		self.assertIn("Gameplan Member", frappe.get_roles("fresh@example.com"))
		self.assertEqual(invitation.status, "Accepted")
		self.assertTrue(invitation.accepted_at)

	def test_accept_reuses_existing_user_and_adds_role(self):
		existing = create_member("recycle@example.com")
		invitation = self.make_invitation("recycle@example.com", role="Gameplan Admin")

		invitation.accept()

		self.assertEqual(frappe.db.count("User", {"email": "recycle@example.com"}), 1)
		roles = frappe.get_roles(existing.name)
		self.assertIn("Gameplan Admin", roles)
		self.assertIn("Gameplan Member", roles)

	def test_accept_as_guest_grants_space_access(self):
		community = create_community("Access Community")
		space = create_space("Access Space", community, is_private=1)
		invitation = self.make_invitation(
			"guest-accept@example.com", role="Gameplan Guest", projects=[space.name]
		)

		invitation.accept()

		self.assertTrue(
			frappe.db.exists(
				"GP Guest Access", {"user": "guest-accept@example.com", "project": space.name}
			)
		)

	def test_accept_expired_invitation_is_rejected(self):
		invitation = self.make_invitation("too-late@example.com")
		invitation.db_set("status", "Expired")
		invitation.reload()

		with self.assertRaises(frappe.ValidationError):
			invitation.accept()

		self.assertFalse(frappe.db.exists("User", "too-late@example.com"))


class TestAcceptInvitationEndpoint(InvitationTestCase):
	def test_missing_key_is_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			accept_invitation(key=None)

	def test_unknown_key_is_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			accept_invitation(key="does-not-exist")

	def test_new_user_is_routed_to_password_setup(self):
		"""A freshly minted account has no password yet, so the endpoint must send
		them to set one rather than logging them straight in."""
		invitation = self.make_invitation("needs-password@example.com", role="Gameplan Member")

		# get_password_link commits a reset-key write; stub it to keep the test
		# transaction rolled back and to pin the redirect target deterministically.
		with patch.object(
			type(invitation), "get_password_link", return_value="/update-password?key=stub"
		):
			accept_invitation(key=invitation.key)

		self.assertEqual(frappe.local.response.get("type"), "redirect")
		self.assertEqual(frappe.local.response.get("location"), "/update-password?key=stub")

	def test_existing_user_with_password_is_logged_in(self):
		create_member("has-password@example.com")
		frappe.db.set_value("User", "has-password@example.com", "last_password_reset_date", now())
		invitation = self.make_invitation("has-password@example.com", role="Gameplan Admin")

		previous = getattr(frappe.local, "login_manager", None)
		frappe.local.login_manager = MagicMock()
		try:
			accept_invitation(key=invitation.key)
			frappe.local.login_manager.login_as.assert_called_once_with("has-password@example.com")
		finally:
			frappe.local.login_manager = previous

		self.assertEqual(frappe.local.response.get("type"), "redirect")
		self.assertEqual(frappe.local.response.get("location"), "/g")


class TestExpireInvitations(InvitationTestCase):
	def _age(self, invitation, days):
		invitation.db_set("creation", add_days(now(), -days), update_modified=False)

	def test_old_pending_invitations_expire(self):
		invitation = self.make_invitation("stale@example.com")
		self._age(invitation, 4)

		expire_invitations()

		self.assertEqual(frappe.db.get_value("GP Invitation", invitation.name, "status"), "Expired")

	def test_recent_pending_invitations_survive(self):
		invitation = self.make_invitation("recent@example.com")
		self._age(invitation, 1)

		expire_invitations()

		self.assertEqual(frappe.db.get_value("GP Invitation", invitation.name, "status"), "Pending")

	def test_accepted_invitations_are_left_alone(self):
		invitation = self.make_invitation("done@example.com")
		invitation.accept()
		self._age(invitation, 10)

		expire_invitations()

		self.assertEqual(frappe.db.get_value("GP Invitation", invitation.name, "status"), "Accepted")
