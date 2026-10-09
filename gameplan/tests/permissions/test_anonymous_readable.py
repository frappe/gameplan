# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""Saves recompute public readability from both tiers and archive states, excluding the site switch."""

from unittest.mock import patch

import frappe
from frappe.api.v2 import update_doc

from gameplan.public_access import (
	VISIBILITY_ANONYMOUS,
	VISIBILITY_GENERAL,
	VISIBILITY_MEMBER_ACCESS,
	find_anonymous_readable_drift,
)
from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import create_community, create_discussion, create_space

TIERS = (VISIBILITY_GENERAL, VISIBILITY_MEMBER_ACCESS, VISIBILITY_ANONYMOUS)


def readable(space):
	return bool(frappe.db.get_value("GP Project", space.name, "is_anonymous_readable"))


class AnonymousReadableTestCase(GameplanTestCase):
	def save_as_admin(self, doc, **values):
		with self.as_user(self.admin):
			doc = frappe.get_doc(doc.doctype, doc.name)
			doc.update(values)
			doc.save()
		return doc

	def run_as_admin(self, doc, method, *args):
		with self.as_user(self.admin):
			doc = frappe.get_doc(doc.doctype, doc.name)
			getattr(doc, method)(*args)
		return doc


class TestTheRule(AnonymousReadableTestCase):
	def test_a_member_cannot_publish_a_private_space_by_writing_the_computed_flag(self):
		space = create_space(
			"Submitted Public Flag",
			create_community("Submitted Flag Community"),
			visibility=VISIBILITY_MEMBER_ACCESS,
			members=[self.member],
		)
		with (
			self.as_user(self.member),
			patch.object(frappe.local, "form_dict", frappe._dict(is_anonymous_readable=1), create=True),
		):
			update_doc("GP Project", str(space.name))
		self.assertFalse(readable(space))

	def test_only_an_anonymous_space_in_an_anonymous_community_qualifies(self):
		for community_tier in TIERS:
			community = create_community(f"Rule {community_tier} Community", visibility=community_tier)
			for space_tier in TIERS:
				with self.subTest(community=community_tier, space=space_tier):
					space = create_space(f"Rule {space_tier} Space", community, visibility=space_tier)
					expected = community_tier == space_tier == VISIBILITY_ANONYMOUS
					self.assertEqual(readable(space), expected)

	def test_a_new_space_with_default_settings_does_not_qualify(self):
		space = create_space("Rule Default Space", create_community("Rule Default Community"))

		self.assertFalse(readable(space))

	def test_a_space_outside_every_community_never_qualifies(self):
		space = frappe.get_doc(
			doctype="GP Project", title="Rule Uncategorized Space", visibility=VISIBILITY_ANONYMOUS
		).insert(ignore_permissions=True)

		self.assertIsNone(space.team)
		self.assertFalse(readable(space))

	def test_a_value_set_by_hand_is_corrected_on_the_next_save(self):
		space = create_space("Rule Hand Set Space", create_community("Rule Hand Set Community"))
		frappe.db.set_value("GP Project", space.name, "is_anonymous_readable", 1)

		self.save_as_admin(space, visibility=VISIBILITY_MEMBER_ACCESS)

		self.assertFalse(readable(space))


class TestItFollowsEveryChange(AnonymousReadableTestCase):
	def setUp(self):
		super().setUp()
		self.community = create_community("Follow Community", visibility=VISIBILITY_ANONYMOUS)
		self.space = create_space("Follow Space", self.community, visibility=VISIBILITY_ANONYMOUS)
		self.sibling = create_space("Follow Sibling", self.community, visibility=VISIBILITY_ANONYMOUS)
		self.assertTrue(readable(self.space))

	def test_changing_the_space_tier(self):
		self.save_as_admin(self.space, visibility=VISIBILITY_GENERAL)
		self.assertFalse(readable(self.space))

		self.save_as_admin(self.space, visibility=VISIBILITY_ANONYMOUS)
		self.assertTrue(readable(self.space))

	def test_changing_the_community_tier_reaches_every_space_in_it(self):
		self.save_as_admin(self.community, visibility=VISIBILITY_GENERAL)
		self.assertFalse(readable(self.space))
		self.assertFalse(readable(self.sibling))

		self.save_as_admin(self.community, visibility=VISIBILITY_ANONYMOUS)
		self.assertTrue(readable(self.space))
		self.assertTrue(readable(self.sibling))

	def test_archiving_and_unarchiving_the_space(self):
		self.run_as_admin(self.space, "archive")
		self.assertFalse(readable(self.space))
		self.assertTrue(readable(self.sibling))

		self.run_as_admin(self.space, "unarchive")
		self.assertTrue(readable(self.space))

	def test_archiving_and_unarchiving_the_community(self):
		# Archiving a community does not archive its spaces, so the cascade does the work.
		self.run_as_admin(self.community, "archive")
		self.assertFalse(readable(self.space))
		self.assertFalse(readable(self.sibling))

		self.run_as_admin(self.community, "unarchive")
		self.assertTrue(readable(self.space))
		self.assertTrue(readable(self.sibling))

	def test_moving_the_space_to_another_community(self):
		closed = create_community("Follow Closed Community", visibility=VISIBILITY_GENERAL)
		self.run_as_admin(self.space, "move_to_team", closed.name)
		self.assertFalse(readable(self.space))

		self.run_as_admin(self.space, "move_to_team", self.community.name)
		self.assertTrue(readable(self.space))

	def test_the_flag_never_drifts_across_a_sequence_of_changes(self):
		other = create_community("Follow Other Community", visibility=VISIBILITY_GENERAL)
		steps = [
			(self.save_as_admin, self.space, {"visibility": VISIBILITY_MEMBER_ACCESS}),
			(self.run_as_admin, self.community, ("archive",)),
			(self.run_as_admin, self.sibling, ("move_to_team", other.name)),
			(self.save_as_admin, other, {"visibility": VISIBILITY_ANONYMOUS}),
			(self.run_as_admin, self.community, ("unarchive",)),
			(self.save_as_admin, self.space, {"visibility": VISIBILITY_ANONYMOUS}),
			(self.run_as_admin, self.sibling, ("archive",)),
			(self.save_as_admin, self.community, {"visibility": VISIBILITY_MEMBER_ACCESS}),
		]
		for step, doc, arguments in steps:
			if isinstance(arguments, dict):
				step(doc, **arguments)
			else:
				step(doc, *arguments)
			self.assertEqual(find_anonymous_readable_drift(), [], f"after {step.__name__}{arguments}")


class TestPublicImpact(AnonymousReadableTestCase):
	def setUp(self):
		super().setUp()
		self.community = create_community("Public Impact Community", visibility=VISIBILITY_ANONYMOUS)
		self.space = create_space("Public Impact Space", self.community)
		for index in range(2):
			create_discussion(f"Public Impact Discussion {index}", self.space, owner=self.member)

	def impact(self, doc, visibility):
		with self.as_user(self.admin):
			return frappe.get_doc(doc.doctype, doc.name).get_visibility_change_impact(visibility)

	def test_publishing_a_space_counts_the_discussions_made_public(self):
		impact = self.impact(self.space, VISIBILITY_ANONYMOUS)

		self.assertEqual(impact["discussions_made_public"], 2)
		self.assertEqual(impact["discussions_no_longer_public"], 0)
		self.assertFalse(readable(self.space))

	def test_a_space_in_a_community_that_is_not_public_publishes_nothing(self):
		closed = create_community("Public Impact Closed Community", visibility=VISIBILITY_GENERAL)
		space = create_space("Public Impact Closed Space", closed)
		create_discussion("Public Impact Closed Discussion", space, owner=self.member)

		self.assertEqual(self.impact(space, VISIBILITY_ANONYMOUS)["discussions_made_public"], 0)

	def test_closing_a_public_community_counts_the_discussions_no_longer_public(self):
		self.save_as_admin(self.space, visibility=VISIBILITY_ANONYMOUS)

		impact = self.impact(self.community, VISIBILITY_GENERAL)

		self.assertEqual(impact["discussions_no_longer_public"], 2)
		self.assertTrue(impact["leaving_anonymous"])
		self.assertTrue(readable(self.space))
