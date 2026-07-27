# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

from unittest.mock import patch

import frappe

from gameplan.gameplan.doctype.gp_discussion.gp_discussion import GPDiscussion
from gameplan.mixins.on_delete import delete_linked_records
from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import (
	create_comment,
	create_community,
	create_discussion,
	create_space,
	grant_guest_access,
)


class TestDeleteCascadeFlags(GameplanTestCase):
	def test_sibling_cascade_identifies_its_parent_doctype(self):
		community = create_community("Cascade Community", members=[self.member])
		space = create_space("Cascade Space", community)
		guest_access = grant_guest_access(self.guest, space)

		with patch("gameplan.mixins.on_delete.frappe.delete_doc") as delete_doc:
			delete_linked_records("User", self.guest.name, ["GP Guest Access"])

		delete_doc.assert_called_once_with(
			"GP Guest Access",
			guest_access.name,
			flags={"from_gameplan_delete_cascade": "User"},
		)


class TestCascadeChildrenLeaveNoResidue(GameplanTestCase):
	"""A cascaded child must not write rows back onto the parent while it is being deleted.

	`update_discussion_meta` calls `track_visit`, which inserts a GP Discussion Visit row.
	Run during the discussion's own cascade it re-creates a row the cascade has already
	swept — or is about to — and `check_if_doc_is_linked` then refuses the parent delete.
	GP Poll hit exactly that. GP Comment survives today only because "GP Comment" happens
	to precede "GP Discussion Visit" in GPDiscussion.on_delete_cascade, so these assert the
	outcome directly rather than trusting the ordering to stay put.
	"""

	def setUp(self):
		super().setUp()
		self.community = create_community("Cascade Community", members=[self.member, self.second_member])
		self.space = create_space("Cascade Space", self.community)
		self.discussion = create_discussion("Cascade thread", self.space, owner=self.member)

	def test_a_cascaded_comment_delete_does_not_depend_on_the_cascade_order(self):
		"""Sweep the visits BEFORE the comments, which is what makes the hazard visible.

		In the shipped order a re-created visit row is swept moments later, so this passes
		with or without the guard — a test that cannot fail. Reversing the two entries is
		the smallest change that puts GP Comment where GP Poll already sits, and it fails
		with `LinkExistsError` if `after_delete` refreshes the discussion during its own
		cascade.
		"""
		comment = create_comment(self.discussion, owner=self.second_member)
		reordered = ["GP Discussion Visit", "GP Comment", "GP Activity", "GP Poll"]

		with patch.object(GPDiscussion, "on_delete_cascade", reordered), self.as_user(self.member):
			frappe.delete_doc("GP Discussion", self.discussion.name)

		self.assertFalse(frappe.db.exists("GP Comment", comment.name))
		self.assertFalse(frappe.db.exists("GP Discussion", self.discussion.name))
		self.assertFalse(frappe.db.exists("GP Discussion Visit", {"discussion": self.discussion.name}))

	def test_deleting_a_comment_on_its_own_still_refreshes_the_discussion(self):
		"""The guard must be scoped to the cascade — a direct delete still updates counters."""
		comment = create_comment(self.discussion, owner=self.member)

		with self.as_user(self.member):
			frappe.delete_doc("GP Comment", comment.name)

		self.discussion.reload()
		self.assertEqual(self.discussion.comments_count, 0)
