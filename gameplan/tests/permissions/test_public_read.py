# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""Reading a public space without signing in, end to end through the role layer.

The Guest role has read access to communities, spaces, discussions, comments and polls, so
these go through every layer a real request does: the role check, the has_permission
hooks, the list conditions and the endpoints. With public access switched on, an anonymous
visitor reads a space that is on the Anonymous tier inside a community on the Anonymous
tier, and nothing else. Switched off, nothing at all.
"""

from unittest.mock import patch

import frappe
import frappe.api.v2

from gameplan.extends.client import get_list as get_client_list
from gameplan.gameplan.doctype.gp_discussion.api import get_discussions
from gameplan.public_access import PUBLIC_ACCESS_CONFIG_KEY, VISIBILITY_ANONYMOUS, VISIBILITY_MEMBER_ACCESS
from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import (
	create_comment,
	create_community,
	create_discussion,
	create_poll,
	create_space,
)

ANONYMOUS = "Guest"


def switched(on):
	return patch.dict(frappe.conf, {PUBLIC_ACCESS_CONFIG_KEY: 1 if on else 0})


class TestPublicRead(GameplanTestCase):
	def setUp(self):
		super().setUp()
		self.public_community = create_community("Public Read Community", visibility=VISIBILITY_ANONYMOUS)
		self.public_space = create_space(
			"Public Read Space", self.public_community, visibility=VISIBILITY_ANONYMOUS
		)
		self.general_space = create_space("Public Read General Space", self.public_community)
		self.private_space = create_space(
			"Public Read Private Space",
			self.public_community,
			visibility=VISIBILITY_MEMBER_ACCESS,
			members=[self.member],
		)
		self.public_discussion = create_discussion(
			"Public Read Discussion", self.public_space, owner=self.member
		)
		self.public_comment = create_comment(self.public_discussion, owner=self.member)
		self.public_poll = create_poll("Public Read Poll", self.public_discussion, owner=self.member)
		self.hidden = []
		for space in (self.general_space, self.private_space):
			discussion = create_discussion(f"Hidden In {space.title}", space, owner=self.member)
			self.hidden += [discussion, create_comment(discussion, owner=self.member)]
		self.public = [self.public_space, self.public_discussion, self.public_comment, self.public_poll]

	def listed_by(self, lister, doctype):
		with self.as_user(ANONYMOUS):
			return {str(name) for name in lister(doctype)}

	def test_documents_follow_the_tier_through_the_role_layer(self):
		with switched(True):
			for doc in [*self.public, self.public_community]:
				self.assert_allowed(doc, "read", ANONYMOUS)
			for doc in [*self.hidden, self.general_space, self.private_space]:
				self.assert_not_allowed(doc, "read", ANONYMOUS)

	def test_every_list_path_shows_public_rows_only(self):
		listers = {
			"frappe.get_list": lambda dt: frappe.get_list(dt, pluck="name", limit_page_length=0),
			"extends.client.get_list": lambda dt: [
				row.name for row in get_client_list(doctype=dt, fields=["name"], limit=0)
			],
			"api/v2 document_list": v2_document_list,
		}
		with switched(True):
			for label, lister in listers.items():
				for doctype in ("GP Discussion", "GP Comment"):
					with self.subTest(path=label, doctype=doctype):
						listed = self.listed_by(lister, doctype)
						public_names = {str(d.name) for d in self.public if d.doctype == doctype}
						hidden_names = {str(d.name) for d in self.hidden if d.doctype == doctype}
						self.assertLessEqual(public_names, listed)
						self.assertFalse(listed & hidden_names)
				with self.subTest(path=label, doctype="GP Project"):
					self.assertEqual(self.listed_by(lister, "GP Project"), {str(self.public_space.name)})

	def test_the_feed_shows_public_discussions_only(self):
		with switched(True), self.as_user(ANONYMOUS):
			feed = {str(row.name) for row in get_discussions(limit=100)}
		self.assertIn(str(self.public_discussion.name), feed)
		self.assertFalse(feed & {str(d.name) for d in self.hidden if d.doctype == "GP Discussion"})

	def test_switched_off_nothing_is_readable(self):
		with switched(False):
			for doc in self.public:
				self.assert_not_allowed(doc, "read", ANONYMOUS)
			with self.as_user(ANONYMOUS):
				self.assertEqual(frappe.get_list("GP Discussion", pluck="name", limit_page_length=0), [])
				self.assertEqual(get_discussions(limit=100), [])

	def test_writing_is_still_refused(self):
		with switched(True), self.as_user(ANONYMOUS):
			with self.assertRaises(frappe.PermissionError):
				frappe.get_doc(
					doctype="GP Comment",
					reference_doctype="GP Discussion",
					reference_name=self.public_discussion.name,
					content="Hello from nobody",
				).insert()
			with self.assertRaises(frappe.PermissionError):
				discussion = frappe.get_doc("GP Discussion", self.public_discussion.name)
				discussion.title = "Defaced"
				discussion.save()


def v2_document_list(doctype):
	"""The /api/v2/document/<doctype> list route, as frappe's REST handler calls it."""
	frappe.form_dict.update({"fields": '["name"]', "limit": 500})
	try:
		return [row["name"] for row in frappe.api.v2.document_list(doctype)]
	finally:
		frappe.form_dict.pop("fields", None)
		frappe.form_dict.pop("limit", None)
