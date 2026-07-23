# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""Content permission cases the matrix cannot express.

test_permission_matrix.py walks saved content that lives in a space. Two things
fall outside that shape and are covered here:

- **Personal content** (a page with no space) is owner-only, and never inherits
  anything from a community.
- **Unsaved content**, which is the surface the create-time gate runs against:
  the per-doctype `has_permission` hooks are called with a doc that has no name
  yet, so they must resolve the space from the in-memory field alone.
"""

import frappe

from gameplan.gameplan.doctype.gp_comment.gp_comment import has_permission as comment_has_permission
from gameplan.gameplan.doctype.gp_page.gp_page import has_permission as page_has_permission
from gameplan.gameplan.doctype.gp_task.gp_task import has_permission as task_has_permission
from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import (
	create_community,
	create_discussion,
	create_page,
	create_space,
	grant_guest_access,
)


class TestPersonalContent(GameplanTestCase):
	def test_private_page_is_owner_only_and_space_page_inherits_space(self):
		community = create_community("Page Permission Community", members=[self.member, self.second_member])
		private_space = create_space("Page Private Space", community, is_private=1, members=[self.member])
		private_page = create_page("Private Page", owner=self.member)
		space_page = create_page("Space Page", private_space, owner=self.member)

		# No space: only the owner, whatever the community says.
		self.assert_allowed(private_page, "read", self.member)
		self.assert_not_allowed(private_page, "read", self.second_member)
		# In a space: visibility is the space's, not the owner's.
		self.assert_allowed(space_page, "read", self.member)
		self.assert_not_allowed(space_page, "read", self.second_member)


class TestUnsavedContent(GameplanTestCase):
	"""The doctype hooks run before a doc has a name — they must still resolve the space."""

	def setUp(self):
		super().setUp()
		self.community = create_community("Unsaved Content Community", members=[self.member])
		self.space = create_space("Unsaved Content Space", self.community)
		self.discussion = create_discussion("Unsaved Content Discussion", self.space, owner=self.member)

	def _unsaved(self, doctype, **values):
		doc = frappe.new_doc(doctype)
		doc.update(values)
		return doc

	def _unsaved_content(self):
		return {
			"GP Comment": (
				comment_has_permission,
				self._unsaved(
					"GP Comment",
					reference_doctype="GP Discussion",
					reference_name=self.discussion.name,
					content="A comment",
				),
			),
			"GP Page": (
				page_has_permission,
				self._unsaved("GP Page", title="A page", project=self.space.name),
			),
			"GP Task": (
				task_has_permission,
				self._unsaved("GP Task", title="A task", project=self.space.name),
			),
		}

	def test_member_can_read_unsaved_content_in_a_visible_space(self):
		for doctype, (has_permission, doc) in self._unsaved_content().items():
			with self.subTest(doctype=doctype):
				self.assertTrue(has_permission(doc, "read", self.member.name))

	def test_guest_can_read_unsaved_content_only_in_a_granted_space(self):
		for doctype, (has_permission, doc) in self._unsaved_content().items():
			with self.subTest(doctype=doctype, granted=False):
				self.assertFalse(has_permission(doc, "read", self.guest.name))

		grant_guest_access(self.guest, self.space)

		for doctype, (has_permission, doc) in self._unsaved_content().items():
			with self.subTest(doctype=doctype, granted=True):
				self.assertTrue(has_permission(doc, "read", self.guest.name))
