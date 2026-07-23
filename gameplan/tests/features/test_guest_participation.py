# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""Executable spec for the guest participation policy (Faris, 2026-07-24).

Guests are participants, not read-only viewers. In a space they've been granted
access to, a guest CAN:
  (a) edit their OWN content,
  (b) delete their OWN content,
  (c) react to posts and comments (anyone's — reacting is interaction, not editing),
  (d) comment on discussions.

A guest can NOT edit or delete anyone else's content, and gets nothing at all
outside the spaces they were granted.

Permission model (see gameplan/permissions.py): the doctype `write` permission
means "may interact with this document" and is held by anyone who can reach the
space, guests included — that is what lets react()'s plain save() through. Editing
*someone else's* content is a separate business rule (can_edit_content) enforced on
the modified document at save time by content_has_permission's write branch, which
allows a non-editor's save only when nothing beyond interaction-safe fields
(reactions) changed.
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

	# --- (d) comment on discussions -------------------------------------------------

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

	# --- members keep the permissive edit model (regression) ------------------------

	def test_member_can_edit_others_content_in_space(self):
		"""The write=interact model must not narrow member editing: any member who can
		reach a space may still edit content there, even another member's post."""
		# Give second_member access to the space, then have them edit member's post.
		space = frappe.get_doc("GP Project", self.space.name)
		space.append("members", {"user": self.second_member.name})
		space.save()
		with self.as_user(self.second_member):
			discussion = frappe.get_doc("GP Discussion", self.discussion.name)
			discussion.title = "Edited by another member"
			discussion.save()
			discussion.reload()
		self.assertEqual(discussion.title, "Edited by another member")

	# --- (c) react to posts and comments (plain save / doc-method path) -------------

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

	def test_guest_holds_write_on_members_content_in_granted_space(self):
		"""write == "may interact": a guest holds it on a member's post in a granted
		space (a clean-doc permission check reports no protected changes). This is the
		gate the react doc-method passes through before react() runs."""
		self.assertTrue(
			frappe.has_permission("GP Discussion", "write", doc=self.discussion.name, user=self.guest.name)
		)

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

	def test_guest_has_no_write_in_ungranted_space(self):
		self.assertFalse(
			frappe.has_permission(
				"GP Discussion", "write", doc=self.other_discussion.name, user=self.guest.name
			)
		)

	# --- (b) delete own content -----------------------------------------------------

	def test_guest_can_delete_own_comment(self):
		with self.as_user(self.guest):
			comment = frappe.get_doc(
				doctype="GP Comment",
				reference_doctype="GP Discussion",
				reference_name=self.discussion.name,
				content="Guest reply to delete",
			).insert()
			frappe.delete_doc("GP Comment", comment.name)
		self.assertFalse(frappe.db.exists("GP Comment", comment.name))

	def test_guest_cannot_delete_members_comment(self):
		with self.as_user(self.guest):
			with self.assertRaises(frappe.PermissionError):
				frappe.delete_doc("GP Comment", self.member_comment.name)
