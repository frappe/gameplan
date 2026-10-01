# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""Changing a community's or a space's visibility tier after creation.

Only a Gameplan Admin may change a tier, through any route: a document method, a plain save
(which is what the Desk form does) or the generic REST routes. A change that takes access
away also takes away the per-user state that points at the space: unread records, legacy
pins and follows.
"""

import frappe
from frappe.client import set_value

from gameplan.gameplan.doctype.gp_team.gp_team import join_team
from gameplan.public_access import VISIBILITY_ANONYMOUS, VISIBILITY_GENERAL, VISIBILITY_MEMBER_ACCESS
from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import (
	create_community,
	create_discussion,
	create_space,
	grant_guest_access,
)

TIERS = (VISIBILITY_GENERAL, VISIBILITY_MEMBER_ACCESS, VISIBILITY_ANONYMOUS)
TRANSITIONS = [(before, after) for before in TIERS for after in TIERS if before != after]

# Per-user rows that point at a space, keyed by doctype.
SPACE_STATE_DOCTYPES = ("GP Unread Record", "GP Pinned Project", "GP Followed Project")


def stored_visibility(doc):
	return frappe.db.get_value(doc.doctype, doc.name, "visibility")


class TestWhoMayChangeATier(GameplanTestCase):
	def setUp(self):
		super().setUp()
		self.community = create_community(
			"Tier Guard Community", members=[self.member, self.second_member], admins=[self.second_member]
		)
		self.private_space = create_space(
			"Tier Guard Private Space",
			self.community,
			visibility=VISIBILITY_MEMBER_ACCESS,
			members=[self.member],
		)
		self.general_space = create_space("Tier Guard General Space", self.community)

	def assert_change_refused(self, user, doc, visibility):
		with self.as_user(user), self.assertRaises(frappe.PermissionError):
			fresh = frappe.get_doc(doc.doctype, doc.name)
			fresh.visibility = visibility
			fresh.save()
		with self.as_user(user), self.assertRaises(frappe.PermissionError):
			set_value(doc.doctype, doc.name, "visibility", visibility)
		self.assertEqual(stored_visibility(doc), doc.visibility)

	def test_a_member_of_a_private_space_cannot_open_it_up(self):
		# Membership of a Member Access space grants write on it (can_manage_space), so the
		# tier needs a guard of its own. Otherwise one member exposes the whole history.
		self.assert_change_refused(self.member, self.private_space, VISIBILITY_GENERAL)
		self.assert_change_refused(self.member, self.private_space, VISIBILITY_ANONYMOUS)

	def test_a_community_admin_cannot_change_a_space_tier(self):
		self.assert_change_refused(self.second_member, self.general_space, VISIBILITY_MEMBER_ACCESS)
		self.assert_change_refused(self.second_member, self.general_space, VISIBILITY_ANONYMOUS)

	def test_a_community_admin_cannot_change_the_community_tier(self):
		self.assert_change_refused(self.second_member, self.community, VISIBILITY_MEMBER_ACCESS)
		self.assert_change_refused(self.second_member, self.community, VISIBILITY_ANONYMOUS)

	def test_a_member_cannot_create_a_space_on_the_anonymous_tier(self):
		with self.as_user(self.member), self.assertRaises(frappe.PermissionError):
			frappe.get_doc(
				doctype="GP Project",
				title="Born Public Space",
				team=self.community.name,
				visibility=VISIBILITY_ANONYMOUS,
			).insert()

	def test_a_member_can_still_create_general_and_member_access_spaces(self):
		with self.as_user(self.member):
			for visibility in (VISIBILITY_GENERAL, VISIBILITY_MEMBER_ACCESS):
				space = frappe.get_doc(
					doctype="GP Project",
					title=f"Member Made {visibility} Space",
					team=self.community.name,
					visibility=visibility,
				).insert()
				self.assertEqual(space.visibility, visibility)

	def test_a_save_that_leaves_the_tier_alone_is_unaffected(self):
		with self.as_user(self.member):
			space = frappe.get_doc("GP Project", self.private_space.name)
			space.title = "Renamed By A Member"
			space.save()

		self.assertEqual(stored_visibility(self.private_space), VISIBILITY_MEMBER_ACCESS)

	def test_a_gameplan_admin_can_make_every_transition_on_both_doctypes(self):
		for doctype in ("GP Team", "GP Project"):
			for before, after in TRANSITIONS:
				with self.subTest(doctype=doctype, before=before, after=after):
					if doctype == "GP Team":
						doc = create_community(f"Admin {before} to {after}", visibility=before)
					else:
						doc = create_space(f"Admin {before} to {after}", self.community, visibility=before)

					with self.as_user(self.admin):
						doc = frappe.get_doc(doctype, doc.name)
						doc.visibility = after
						doc.save()

					self.assertEqual(stored_visibility(doc), after)
					self.assertEqual(doc.visibility_set_by, self.admin.name)


class TestAccessStateFollowsATierChange(GameplanTestCase):
	def setUp(self):
		super().setUp()
		self.community = create_community("Reconcile Community", members=[self.member, self.second_member])
		self.space = create_space("Reconcile Space", self.community, members=[self.member])
		self.discussion = create_discussion("Reconcile Discussion", self.space, owner=self.member)
		for user in (self.member, self.second_member):
			add_space_state(user, self.space)

	def change_tier(self, doc, visibility):
		with self.as_user(self.admin):
			doc = frappe.get_doc(doc.doctype, doc.name)
			doc.visibility = visibility
			doc.save()

	def test_tightening_a_space_drops_state_for_exactly_the_users_who_lost_access(self):
		self.change_tier(self.space, VISIBILITY_MEMBER_ACCESS)

		self.assertEqual(space_state(self.second_member, self.space), set())
		self.assertEqual(space_state(self.member, self.space), set(SPACE_STATE_DOCTYPES))

	def test_tightening_a_community_drops_state_in_its_general_spaces(self):
		outsider_community = create_community("Reconcile Outsider Community", members=[self.outsider])
		self.assertTrue(outsider_community)
		add_space_state(self.outsider, self.space)

		self.change_tier(self.community, VISIBILITY_MEMBER_ACCESS)

		self.assertEqual(space_state(self.outsider, self.space), set())
		self.assertEqual(space_state(self.second_member, self.space), set(SPACE_STATE_DOCTYPES))
		with self.as_user(self.outsider), self.assertRaises(frappe.PermissionError):
			join_team(self.community.name)

	def test_loosening_drops_nothing(self):
		self.change_tier(self.space, VISIBILITY_MEMBER_ACCESS)
		add_space_state(self.second_member, self.space)
		before = {user: space_state(user, self.space) for user in (self.member, self.second_member)}

		self.change_tier(self.space, VISIBILITY_GENERAL)

		for user, state in before.items():
			self.assertEqual(space_state(user, self.space), state, user)

	def test_guest_access_survives_every_transition(self):
		grant_guest_access(self.guest, self.space)
		for before, after in TRANSITIONS:
			with self.subTest(before=before, after=after):
				self.change_tier(self.space, before)
				self.change_tier(self.space, after)
				self.assertTrue(
					frappe.db.exists("GP Guest Access", {"user": self.guest.name, "project": self.space.name})
				)


class TestVisibilityChangeImpact(GameplanTestCase):
	"""The counts the confirmation dialog shows before a tier changes."""

	def setUp(self):
		super().setUp()
		self.community = create_community("Impact Community", members=[self.member, self.second_member])
		self.space = create_space("Impact Space", self.community, members=[self.member])
		for index in range(3):
			create_discussion(f"Impact Discussion {index}", self.space, owner=self.member)

	def impact(self, doc, visibility):
		with self.as_user(self.admin):
			return frappe.get_doc(doc.doctype, doc.name).get_visibility_change_impact(visibility)

	def test_only_a_gameplan_admin_may_ask(self):
		with self.as_user(self.member), self.assertRaises(frappe.PermissionError):
			frappe.get_doc("GP Project", self.space.name).get_visibility_change_impact(
				VISIBILITY_MEMBER_ACCESS
			)

	def test_an_unknown_tier_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			self.impact(self.space, "Public")

	def test_it_does_not_change_anything(self):
		self.impact(self.space, VISIBILITY_MEMBER_ACCESS)

		self.assertEqual(stored_visibility(self.space), VISIBILITY_GENERAL)

	def test_tightening_a_space_counts_the_users_who_lose_it(self):
		impact = self.impact(self.space, VISIBILITY_MEMBER_ACCESS)

		# Everyone but the one space member, the admin (who sees everything) and the guest
		# (who never had a grant here).
		self.assertEqual(impact["users_losing_access"], 2)  # second_member, outsider
		self.assertEqual(impact["users_gaining_access"], 0)
		self.assertEqual(impact["spaces_losing_readers"], 1)
		self.assertEqual(impact["discussions_revealed"], 0)

	def test_loosening_a_space_counts_the_discussions_revealed(self):
		self.change_to_member_access()

		impact = self.impact(self.space, VISIBILITY_GENERAL)

		self.assertEqual(impact["users_gaining_access"], 2)
		self.assertEqual(impact["users_losing_access"], 0)
		self.assertEqual(impact["discussions_revealed"], 3)

	def test_tightening_a_community_counts_its_general_spaces(self):
		create_space("Impact Private Space", self.community, visibility=VISIBILITY_MEMBER_ACCESS)

		impact = self.impact(self.community, VISIBILITY_MEMBER_ACCESS)

		# The outsider loses Impact Space and the community's auto-created General space.
		# The Member Access space had no readers to lose.
		self.assertEqual(impact["users_losing_access"], 1)
		self.assertEqual(impact["spaces_losing_readers"], 2)

	def test_leaving_the_anonymous_tier_is_flagged(self):
		with self.as_user(self.admin):
			space = frappe.get_doc("GP Project", self.space.name)
			space.visibility = VISIBILITY_ANONYMOUS
			space.save()

		self.assertTrue(self.impact(self.space, VISIBILITY_GENERAL)["leaving_anonymous"])
		self.assertFalse(self.impact(self.community, VISIBILITY_MEMBER_ACCESS)["leaving_anonymous"])

	def change_to_member_access(self):
		with self.as_user(self.admin):
			space = frappe.get_doc("GP Project", self.space.name)
			space.visibility = VISIBILITY_MEMBER_ACCESS
			space.save()


def add_space_state(user, space):
	"""An unread record, a legacy pin and a follow for `user` on `space`."""
	user = getattr(user, "name", user)
	team = frappe.db.get_value("GP Project", space.name, "team")
	for doctype in SPACE_STATE_DOCTYPES:
		if frappe.db.exists(doctype, {"user": user, "project": str(space.name)}):
			continue
		values = {"doctype": doctype, "user": user, "project": space.name}
		if doctype != "GP Unread Record":
			values["team"] = team
		# GP Pinned Project stamps the session user as the pin's owner.
		previous = frappe.session.user
		frappe.set_user(user)
		try:
			frappe.get_doc(values).insert(ignore_permissions=True)
		finally:
			frappe.set_user(previous)


def space_state(user, space):
	"""The SPACE_STATE_DOCTYPES in which `user` holds a row for `space`."""
	user = getattr(user, "name", user)
	return {
		doctype
		for doctype in SPACE_STATE_DOCTYPES
		if frappe.db.exists(doctype, {"user": user, "project": str(space.name)})
	}


class TestSetVisibility(GameplanTestCase):
	"""set_visibility is the route the app uses to change a tier."""

	def setUp(self):
		super().setUp()
		self.community = create_community("Set Visibility Community", admins=[self.second_member])
		self.space = create_space("Set Visibility Space", self.community, members=[self.member])

	def test_a_gameplan_admin_moves_a_space_and_a_community(self):
		with self.as_user(self.admin):
			frappe.get_doc("GP Team", self.community.name).set_visibility(VISIBILITY_ANONYMOUS)
			frappe.get_doc("GP Project", self.space.name).set_visibility(VISIBILITY_ANONYMOUS)

		self.assertEqual(stored_visibility(self.community), VISIBILITY_ANONYMOUS)
		self.assertEqual(stored_visibility(self.space), VISIBILITY_ANONYMOUS)
		self.assertTrue(frappe.db.get_value("GP Project", self.space.name, "is_anonymous_readable"))
		self.assertEqual(
			frappe.db.get_value("GP Project", self.space.name, "visibility_set_by"), self.admin.name
		)

	def test_nobody_else_may(self):
		for user, doc in (
			(self.member, self.space),
			(self.second_member, self.space),
			(self.second_member, self.community),
			(self.guest, self.space),
		):
			with self.subTest(user=user.name, doctype=doc.doctype):
				with self.as_user(user), self.assertRaises(frappe.PermissionError):
					frappe.get_doc(doc.doctype, doc.name).set_visibility(VISIBILITY_MEMBER_ACCESS)
				self.assertEqual(stored_visibility(doc), VISIBILITY_GENERAL)

	def test_an_unknown_tier_is_refused(self):
		with self.as_user(self.admin), self.assertRaises(frappe.ValidationError):
			frappe.get_doc("GP Project", self.space.name).set_visibility("Public")
