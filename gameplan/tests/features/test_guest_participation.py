# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""Executable spec for the guest participation policy (Faris, 2026-07-24).

Guests are participants, not read-only viewers. In a space they've been granted
access to, a guest CAN:
  (a) edit their OWN content,
  (b) react to posts and comments (anyone's, since reacting is a view-level action),
  (c) comment on discussions.

A guest can NOT edit anyone else's content, and gets nothing at all outside the
spaces they were granted. Deleting one's own content is NOT part of the spec; the
current behaviour is characterised here and flagged as an open product question.
"""

import frappe

from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import (
	create_comment,
	create_community,
	create_discussion,
	create_space,
	grant_guest_access,
)

REACTION_ADD = [{"emoji": "\U0001f44d", "operation": "add"}]


class TestGuestParticipation(GameplanTestCase):
	def setUp(self):
		super().setUp()
		self.community = create_community("Guest Community", members=[self.member])

		# The space the guest is granted access to.
		self.space = create_space("Granted Space", self.community, is_private=1, members=[self.member])
		grant_guest_access(self.guest, self.space)

		# A second space the guest has NO access to.
		self.other_space = create_space(
			"Ungranted Space", self.community, is_private=1, members=[self.member]
		)

		# Member-owned content the guest can see in the granted space.
		self.discussion = create_discussion("Granted discussion", self.space, owner=self.member)
		self.member_comment = create_comment(self.discussion, owner=self.member)

		# Member-owned content in the space the guest cannot reach.
		self.other_discussion = create_discussion("Ungranted discussion", self.other_space, owner=self.member)

	# --- (c) comment on discussions -------------------------------------------------

	def test_guest_can_create_comment_in_granted_space(self):
		with self.as_user(self.guest):
			comment = frappe.get_doc(
				doctype="GP Comment",
				reference_doctype="GP Discussion",
				reference_name=self.discussion.name,
				content="Guest reply",
			).insert()
		self.assertEqual(comment.owner, self.guest.name)

	# --- (a) edit own content -------------------------------------------------------

	def test_guest_can_edit_own_comment(self):
		with self.as_user(self.guest):
			comment = frappe.get_doc(
				doctype="GP Comment",
				reference_doctype="GP Discussion",
				reference_name=self.discussion.name,
				content="Original",
			).insert()
			comment.content = "Edited by guest"
			comment.save()  # a real save as the guest, not just a has_permission probe
			comment.reload()
		self.assertEqual(comment.content.strip(), "Edited by guest")

	# --- guest can NOT edit others' content -----------------------------------------

	def test_guest_cannot_edit_members_comment(self):
		with self.as_user(self.guest):
			comment = frappe.get_doc("GP Comment", self.member_comment.name)
			comment.content = "Guest tampering"
			with self.assertRaises(frappe.PermissionError):
				comment.save()

	def test_guest_cannot_edit_members_discussion(self):
		with self.as_user(self.guest):
			discussion = frappe.get_doc("GP Discussion", self.discussion.name)
			discussion.title = "Guest tampering"
			with self.assertRaises(frappe.PermissionError):
				discussion.save()

	# --- (b) react to posts and comments --------------------------------------------

	def test_guest_can_react_to_discussion(self):
		with self.as_user(self.guest):
			discussion = frappe.get_doc("GP Discussion", self.discussion.name)
			discussion.react(operations=REACTION_ADD)
			discussion.reload()
		self.assertTrue(any(r.user == self.guest.name for r in discussion.reactions))

	def test_guest_can_react_to_comment(self):
		with self.as_user(self.guest):
			comment = frappe.get_doc("GP Comment", self.member_comment.name)
			comment.react(operations=REACTION_ADD)
			comment.reload()
		self.assertTrue(any(r.user == self.guest.name for r in comment.reactions))

	# --- nothing outside granted spaces ---------------------------------------------

	def test_guest_cannot_comment_in_ungranted_space(self):
		with self.as_user(self.guest):
			comment = frappe.get_doc(
				doctype="GP Comment",
				reference_doctype="GP Discussion",
				reference_name=self.other_discussion.name,
				content="Should be blocked",
			)
			with self.assertRaises(frappe.PermissionError):
				comment.insert()

	def test_guest_cannot_react_in_ungranted_space(self):
		with self.as_user(self.guest):
			discussion = frappe.get_doc("GP Discussion", self.other_discussion.name)
			with self.assertRaises(frappe.PermissionError):
				discussion.react(operations=REACTION_ADD)

	# --- characterization: guest deleting their OWN content -------------------------

	def test_guest_delete_own_comment_characterization(self):
		"""Characterises current behaviour only: a guest currently CANNOT delete
		even their own comment (GP Comment has no `delete` DocPerm for Gameplan
		Guest, and can_delete_content denies guests outright).

		OPEN PRODUCT QUESTION (2026-07-24 guest participation spec): should a guest
		be allowed to delete content they authored? Not specified, so behaviour is
		left unchanged and merely pinned here. Update this test if the policy is
		decided.
		"""
		with self.as_user(self.guest):
			comment = frappe.get_doc(
				doctype="GP Comment",
				reference_doctype="GP Discussion",
				reference_name=self.discussion.name,
				content="Guest reply to delete",
			).insert()
			with self.assertRaises(frappe.PermissionError):
				frappe.delete_doc("GP Comment", comment.name)
