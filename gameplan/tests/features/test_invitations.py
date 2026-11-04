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
from frappe.utils import add_days, now, today

from gameplan.api import _invite_by_email, accept_invitation
from gameplan.gameplan.doctype.gp_invitation.gp_invitation import GPInvitation, expire_invitations
from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import (
	create_community,
	create_guest,
	create_member,
	create_space,
	create_user,
)
from gameplan.visibility import (
	VISIBILITY_ANONYMOUS,
	VISIBILITY_GENERAL,
	VISIBILITY_MEMBER_ACCESS,
)


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
		space = create_space("Guest Invite Space", community, visibility=VISIBILITY_MEMBER_ACCESS)

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

	def test_an_existing_account_is_granted_access_without_the_email(self):
		"""Signing in through OAuth mints a Website User with no role, so an account can
		exist while its owner has no way into Gameplan. The email link would create no
		user and set no password, so skip it and hand over the role now."""
		user = create_user("oauth-signup@example.com", "Oauth Signup")

		result = _invite_by_email("oauth-signup@example.com", role="Gameplan Member")

		self.assertIn("Gameplan Member", frappe.get_roles(user.name))
		self.assertEqual(result["granted"], ["oauth-signup@example.com"])
		self.assertEqual(result["invited"], [])
		self.assertEqual(frappe.db.count("User", {"email": "oauth-signup@example.com"}), 1)

	def test_granting_access_leaves_an_accepted_invitation_as_the_audit_trail(self):
		create_user("oauth-audit@example.com", "Oauth Audit")

		with self.as_user(self.admin):
			_invite_by_email("oauth-audit@example.com", role="Gameplan Member")

		invitation = frappe.get_doc("GP Invitation", {"email": "oauth-audit@example.com"})
		self.assertEqual(invitation.status, "Accepted")
		self.assertTrue(invitation.accepted_at)
		self.assertEqual(invitation.invited_by, self.admin.name)

	def test_granting_access_never_sends_the_accept_link(self):
		"""The key is spent before the mail could arrive; sending it would ask for a
		step that is already done."""
		create_user("oauth-nomail@example.com", "Oauth No Mail")

		with patch.object(GPInvitation, "invite_via_email") as invite_mail:
			_invite_by_email("oauth-nomail@example.com", role="Gameplan Member")

		invite_mail.assert_not_called()

	def test_a_guest_granted_access_gets_the_space_immediately(self):
		"""accept() owns the GP Guest Access rows, so the direct path must not lose
		them. This is why grant_access reuses accept() instead of setting the role."""
		create_user("oauth-guest@example.com", "Oauth Guest")
		community = create_community("Direct Guest Community")
		space = create_space("Direct Guest Space", community, visibility=VISIBILITY_MEMBER_ACCESS)

		_invite_by_email("oauth-guest@example.com", role="Gameplan Guest", projects=[space.name])

		self.assertIn("Gameplan Guest", frappe.get_roles("oauth-guest@example.com"))
		self.assertTrue(
			frappe.db.exists("GP Guest Access", {"user": "oauth-guest@example.com", "project": space.name})
		)

	def test_a_directly_granted_member_joins_general_and_anonymous_communities(self):
		"""The direct path runs through accept(), so it inherits the join for free."""
		create_user("oauth-joiner@example.com", "Oauth Joiner")
		communities = [
			create_community(f"Direct Join {tier} Community", visibility=tier)
			for tier in (VISIBILITY_GENERAL, VISIBILITY_ANONYMOUS)
		]

		_invite_by_email("oauth-joiner@example.com", role="Gameplan Member")

		for community in communities:
			self.assertTrue(
				frappe.db.exists(
					"GP Member",
					{"parenttype": "GP Team", "parent": community.name, "user": "oauth-joiner@example.com"},
				)
			)

	def test_an_email_with_no_account_still_gets_the_invitation(self):
		result = _invite_by_email("brand-new@example.com", role="Gameplan Member")

		invitation = frappe.get_doc("GP Invitation", {"email": "brand-new@example.com"})
		self.assertEqual(invitation.status, "Pending")
		self.assertEqual(result["invited"], ["brand-new@example.com"])
		self.assertEqual(result["granted"], [])
		self.assertFalse(frappe.db.exists("User", "brand-new@example.com"))

	def test_a_disabled_account_is_skipped_not_invited(self):
		"""Granting a role changes nothing while the account cannot sign in, and an
		invite link would hand the role to an account someone switched off."""
		user = create_user("disabled-user@example.com", "Disabled User")
		user.enabled = 0
		user.save(ignore_permissions=True)

		result = _invite_by_email("disabled-user@example.com", role="Gameplan Member")

		self.assertEqual(result["skipped"], ["disabled-user@example.com"])
		self.assertEqual(result["granted"], [])
		self.assertEqual(result["invited"], [])
		self.assertFalse(frappe.db.exists("GP Invitation", {"email": "disabled-user@example.com"}))
		self.assertNotIn("Gameplan Member", frappe.get_roles(user.name))

	def test_one_call_splits_a_mixed_list_into_its_three_buckets(self):
		create_user("mixed-account@example.com", "Mixed Account")
		create_member("mixed-member@example.com")

		result = _invite_by_email(
			"mixed-account@example.com, mixed-new@example.com, mixed-member@example.com",
			role="Gameplan Member",
		)

		self.assertEqual(result["granted"], ["mixed-account@example.com"])
		self.assertEqual(result["invited"], ["mixed-new@example.com"])
		self.assertEqual(result["skipped"], ["mixed-member@example.com"])

	def test_invite_skips_a_user_who_already_holds_a_gameplan_role(self):
		create_guest("already-guest@example.com")

		_invite_by_email("already-guest@example.com", role="Gameplan Member")

		self.assertFalse(frappe.db.exists("GP Invitation", {"email": "already-guest@example.com"}))

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
		space = create_space("Second Guest Space", community, visibility=VISIBILITY_MEMBER_ACCESS)

		_invite_by_email("existing-then-guest@example.com", role="Gameplan Guest", projects=[space.name])

		self.assertTrue(frappe.db.exists("GP Invitation", {"email": "existing-then-guest@example.com"}))


class TestWhoCanInvite(InvitationTestCase):
	def test_members_create_invitations_only_through_invite_actions(self):
		with self.as_user(self.member), self.assertRaises(frappe.PermissionError):
			frappe.get_doc(
				doctype="GP Invitation", email="direct@example.com", role="Gameplan Member"
			).insert()

		self.assertFalse(frappe.db.exists("GP Invitation", {"email": "direct@example.com"}))

	def test_only_admins_invite_admins(self):
		with self.as_user(self.member), self.assertRaises(frappe.PermissionError):
			self.make_invitation("new-admin@example.com", role="Gameplan Admin")

		with self.as_user(self.admin):
			self.make_invitation("new-admin@example.com", role="Gameplan Admin")

		self.assertTrue(frappe.db.exists("GP Invitation", {"email": "new-admin@example.com"}))

	def test_space_manager_removes_a_pending_guest_invitation(self):
		community = create_community("Guest Invite Community", members=[self.member])
		space = create_space(
			"Guest Invite Space", community, visibility=VISIBILITY_MEMBER_ACCESS, members=[self.member]
		)
		with self.as_user(self.member):
			space.invite_guest("pending-guest@example.com")
			invitation = frappe.db.get_value("GP Invitation", {"email": "pending-guest@example.com"})
			space.remove_guest_invitation(invitation)

		self.assertFalse(frappe.db.exists("GP Invitation", invitation))


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
		space = create_space("Access Space", community, visibility=VISIBILITY_MEMBER_ACCESS)
		invitation = self.make_invitation(
			"guest-accept@example.com", role="Gameplan Guest", projects=[space.name]
		)

		invitation.accept()

		self.assertTrue(
			frappe.db.exists("GP Guest Access", {"user": "guest-accept@example.com", "project": space.name})
		)

	def joined_communities(self, email):
		return set(
			frappe.db.get_all(
				"GP Member",
				filters={"parenttype": "GP Team", "user": email},
				pluck="parent",
			)
		)

	def test_accept_joins_general_and_anonymous_communities(self):
		"""A new member should land in a populated app, not an empty shell.

		Membership does not gate either open tier. It decides what the sidebar lists.
		"""
		first = create_community("General One", visibility=VISIBILITY_GENERAL)
		second = create_community("Anonymous One", visibility=VISIBILITY_ANONYMOUS)
		invitation = self.make_invitation("joiner@example.com")

		invitation.accept()

		joined = self.joined_communities("joiner@example.com")
		self.assertIn(first.name, joined)
		self.assertIn(second.name, joined)

	def test_accept_leaves_private_communities_alone(self):
		private = create_community("Private One", visibility=VISIBILITY_MEMBER_ACCESS)
		invitation = self.make_invitation("no-private@example.com")

		invitation.accept()

		self.assertNotIn(private.name, self.joined_communities("no-private@example.com"))

	def test_accept_leaves_archived_communities_alone(self):
		archived = create_community("Archived One")
		archived.db_set("archived_at", now())
		invitation = self.make_invitation("no-archived@example.com")

		invitation.accept()

		self.assertNotIn(archived.name, self.joined_communities("no-archived@example.com"))

	def test_a_guest_joins_nothing(self):
		"""A guest's reach is the spaces they were granted, and nothing wider."""
		community = create_community("Guest Blind Community")
		space = create_space("Guest Blind Space", community, visibility=VISIBILITY_MEMBER_ACCESS)
		invitation = self.make_invitation(
			"guest-no-join@example.com", role="Gameplan Guest", projects=[space.name]
		)

		invitation.accept()

		self.assertEqual(self.joined_communities("guest-no-join@example.com"), set())

	def test_accept_does_not_duplicate_an_existing_membership(self):
		member = create_member("already-in@example.com")
		community = create_community("Already Joined", members=[member])
		invitation = self.make_invitation("already-in@example.com", role="Gameplan Admin")

		invitation.accept()

		rows = frappe.db.count(
			"GP Member",
			{"parenttype": "GP Team", "parent": community.name, "user": "already-in@example.com"},
		)
		self.assertEqual(rows, 1)

	def test_accept_expired_invitation_is_rejected(self):
		invitation = self.make_invitation("too-late@example.com")
		invitation.db_set("status", "Expired")
		invitation.reload()

		with self.assertRaises(frappe.ValidationError):
			invitation.accept()

		self.assertFalse(frappe.db.exists("User", "too-late@example.com"))


class TestAcceptInvitationEndpoint(InvitationTestCase):
	def setUp(self):
		super().setUp()
		# The endpoint commits, because an email link arrives as a GET request. Stub the
		# commit so each test's rows roll back with it.
		commit = patch.object(frappe.db, "commit")
		commit.start()
		self.addCleanup(commit.stop)
		# The endpoint writes its redirect or message page to the shared response, which
		# outlives the test.
		previous_response = frappe.local.response
		frappe.local.response = frappe._dict()
		self.addCleanup(setattr, frappe.local, "response", previous_response)

	def assert_message_page(self, http_status_code):
		self.assertEqual(frappe.local.response.get("type"), "page")
		self.assertEqual(frappe.local.response.get("http_status_code"), http_status_code)

	def test_missing_key_shows_a_message(self):
		accept_invitation(key=None)
		self.assert_message_page(404)

	def test_unknown_key_shows_a_message(self):
		accept_invitation(key="does-not-exist")
		self.assert_message_page(404)

	def test_expired_key_shows_a_message(self):
		invitation = self.make_invitation("expired-link@example.com")
		invitation.db_set("status", "Expired")

		accept_invitation(key=invitation.flags.invite_key)

		self.assert_message_page(404)
		self.assertFalse(frappe.db.exists("User", "expired-link@example.com"))

	def test_new_user_is_routed_to_password_setup(self):
		"""A freshly minted account has no password yet, so the endpoint must send
		them to set one rather than logging them straight in."""
		invitation = self.make_invitation("needs-password@example.com", role="Gameplan Member")

		# Stub the password link to pin the redirect target.
		with patch.object(type(invitation), "get_password_link", return_value="/update-password?key=stub"):
			accept_invitation(key=invitation.flags.invite_key)

		self.assertEqual(frappe.local.response.get("type"), "redirect")
		self.assertEqual(frappe.local.response.get("location"), "/update-password?key=stub")

	def test_existing_user_is_sent_to_the_app_to_sign_in(self):
		"""An account that was here before the invitation signs in the way it always has."""
		create_member("has-password@example.com")
		# A Date field, so it must hold a date. MariaDB coerces a datetime silently, but the
		# SQLite backend stores the string as given and frappe's `date` converter then fails
		# to parse it on every subsequent read of the row.
		frappe.db.set_value("User", "has-password@example.com", "last_password_reset_date", today())
		invitation = self.make_invitation("has-password@example.com", role="Gameplan Admin")

		previous = getattr(frappe.local, "login_manager", None)
		frappe.local.login_manager = MagicMock()
		try:
			accept_invitation(key=invitation.flags.invite_key)
			frappe.local.login_manager.login_as.assert_not_called()
		finally:
			frappe.local.login_manager = previous

		self.assertEqual(frappe.local.response.get("type"), "redirect")
		self.assertEqual(frappe.local.response.get("location"), "/g")
		self.assertIn("Gameplan Admin", frappe.get_roles("has-password@example.com"))

	def test_a_new_invitee_who_opens_the_link_again_gets_a_new_password_link(self):
		"""The first password link may be lost. Until a password is set, the invite link
		gives a new one; after that it only shows a message."""
		invitation = self.make_invitation("opens-twice@example.com")
		key = invitation.flags.invite_key
		accept_invitation(key=key)
		first_link = frappe.local.response.get("location")

		accept_invitation(key=key)

		self.assertEqual(frappe.local.response.get("type"), "redirect")
		self.assertTrue(frappe.local.response.get("location").startswith("/update-password?key="))
		self.assertNotEqual(frappe.local.response.get("location"), first_link)
		self.assertEqual(frappe.db.get_value("GP Invitation", invitation.name, "status"), "Accepted")

		frappe.db.set_value("User", "opens-twice@example.com", "last_password_reset_date", today())
		accept_invitation(key=key)

		self.assert_message_page(410)

	def test_an_existing_account_that_opens_the_link_again_gets_a_message(self):
		create_member("existing-twice@example.com")
		invitation = self.make_invitation("existing-twice@example.com", role="Gameplan Admin")
		accept_invitation(key=invitation.flags.invite_key)

		previous = getattr(frappe.local, "login_manager", None)
		frappe.local.login_manager = MagicMock()
		try:
			accept_invitation(key=invitation.flags.invite_key)
			frappe.local.login_manager.login_as.assert_not_called()
		finally:
			frappe.local.login_manager = previous

		self.assert_message_page(410)
		self.assertFalse(frappe.db.get_value("User", "existing-twice@example.com", "reset_password_key"))

	def test_an_account_made_before_accepting_gets_a_message_when_it_opens_the_link_again(self):
		"""An account created after the invitation was sent, but not by accepting it,
		signs in the way it always has, and a reopened link only shows a message."""
		invitation = self.make_invitation("joined-meanwhile@example.com")
		create_member("joined-meanwhile@example.com")
		key = invitation.flags.invite_key

		accept_invitation(key=key)
		self.assertEqual(frappe.local.response.get("location"), "/g")

		accept_invitation(key=key)

		self.assert_message_page(410)
		self.assertFalse(frappe.db.get_value("User", "joined-meanwhile@example.com", "reset_password_key"))

	def test_stored_key_does_not_open_the_invitation(self):
		"""The link carries the key; the row keeps only its hash."""
		invitation = self.make_invitation("stored-key@example.com")

		self.assertNotEqual(invitation.key, invitation.flags.invite_key)
		accept_invitation(key=invitation.key)

		self.assert_message_page(404)
		self.assertEqual(frappe.db.get_value("GP Invitation", invitation.name, "status"), "Pending")

	def test_accept_invitation_succeeds_when_signed_in_as_ordinary_member(self):
		"""Accepting an invitation while logged in as a normal member must provision the
		new user profile without failing ownership validation."""
		member = create_member("ordinary-member@example.com")
		invitation = self.make_invitation("invited-member@example.com", role="Gameplan Member")

		frappe.set_user(member.name)
		with patch.object(type(invitation), "get_password_link", return_value="/update-password?key=stub"):
			accept_invitation(key=invitation.flags.invite_key)

		self.assertTrue(frappe.db.exists("GP User Profile", {"user": "invited-member@example.com"}))


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
