# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""Tier changes require a Gameplan Admin and reconcile unread records, pins, and follows."""

from unittest.mock import patch

import frappe
from frappe.client import set_value

from gameplan.gameplan.doctype.gp_discussion.gp_discussion import move_discussions
from gameplan.gameplan.doctype.gp_team.gp_team import join_team
from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import (
	create_comment,
	create_community,
	create_discussion,
	create_poll,
	create_space,
	create_task,
	grant_guest_access,
)
from gameplan.visibility import (
	VISIBILITY_ANONYMOUS,
	VISIBILITY_GENERAL,
	VISIBILITY_MEMBER_ACCESS,
)

TIERS = (VISIBILITY_GENERAL, VISIBILITY_MEMBER_ACCESS, VISIBILITY_ANONYMOUS)
TRANSITIONS = [(before, after) for before in TIERS for after in TIERS if before != after]

# Per-user rows that point at a space, keyed by doctype.
SPACE_STATE_DOCTYPES = ("GP Unread Record", "GP Pinned Project", "GP Followed Project")


def stored_visibility(doc):
	return frappe.db.get_value(doc.doctype, doc.name, "visibility")


class TestPublicationTransitions(GameplanTestCase):
	def setUp(self):
		super().setUp()
		self.community = create_community(
			"Publication Guard", visibility=VISIBILITY_ANONYMOUS, admins=[self.second_member]
		)
		self.public = create_space("Public Destination", self.community, visibility=VISIBILITY_ANONYMOUS)
		self.private = create_space(
			"Private History",
			self.community,
			visibility=VISIBILITY_MEMBER_ACCESS,
			members=[self.member, self.second_member],
		)
		self.discussion = create_discussion("Private Conversation", self.private, owner=self.member)

	def test_unarchive_requires_admin_on_both_methods_and_plain_saves_even_when_switch_is_off(self):
		for doc in (self.public, self.community):
			doc.archive()
			for enabled in (0, 1):
				for method in ("unarchive", "save"):
					with self.subTest(doctype=doc.doctype, enabled=enabled, method=method):
						with (
							patch.dict(frappe.conf, gameplan_public_access_enabled=enabled),
							self.as_user(self.second_member),
						):
							fresh = frappe.get_doc(doc.doctype, doc.name)
							with self.assertRaises(frappe.PermissionError):
								if method == "save":
									fresh.archived_at = fresh.archived_by = None
								getattr(fresh, method)()
						self.assertTrue(frappe.db.get_value(doc.doctype, doc.name, "archived_at"))
			with self.as_user(self.admin):
				frappe.get_doc(doc.doctype, doc.name).unarchive()
			self.assertFalse(frappe.db.get_value(doc.doctype, doc.name, "archived_at"))

	def test_private_discussion_cannot_be_published_by_method_plain_save_or_bulk_move(self):
		with self.as_user(self.member):
			with self.assertRaises(frappe.PermissionError):
				frappe.get_doc("GP Discussion", self.discussion.name).move_to_project(self.public.name)
			with self.assertRaises(frappe.PermissionError):
				set_value("GP Discussion", self.discussion.name, "project", self.public.name)
			response = move_discussions([{"name": self.discussion.name, "project": self.public.name}])
			self.assertEqual(response["failure_count"], 1)
		self.assertEqual(
			frappe.db.get_value("GP Discussion", self.discussion.name, "project"), str(self.private.name)
		)
		with self.as_user(self.admin):
			frappe.get_doc("GP Discussion", self.discussion.name).move_to_project(self.public.name)
		self.assertEqual(
			frappe.db.get_value("GP Discussion", self.discussion.name, "project"), str(self.public.name)
		)

	def test_private_space_merge_cannot_publish_history_without_admin(self):
		with self.as_user(self.second_member), self.assertRaises(frappe.PermissionError):
			frappe.get_doc("GP Project", self.private.name).merge_with_project(self.public.name)
		self.assertTrue(frappe.db.exists("GP Project", self.private.name))
		with self.as_user(self.admin):
			frappe.get_doc("GP Project", self.private.name).merge_with_project(self.public.name)
		self.assertEqual(
			frappe.db.get_value("GP Discussion", self.discussion.name, "project"), str(self.public.name)
		)

	def test_public_posting_and_moves_between_already_public_spaces_remain_allowed(self):
		other = create_space("Already Public", self.community, visibility=VISIBILITY_ANONYMOUS)
		with self.as_user(self.member):
			post = frappe.get_doc(
				doctype="GP Discussion", project=self.public.name, title="Public Post", content="Hello"
			).insert()
			post.move_to_project(other.name)
		self.assertEqual(frappe.db.get_value("GP Discussion", post.name, "project"), str(other.name))

	def test_private_comment_cannot_be_published_without_admin(self):
		public_discussion = create_discussion("Public Conversation", self.public, owner=self.member)
		comment = create_comment(self.discussion, content="Private Comment", owner=self.member)
		with self.as_user(self.member):
			with self.assertRaises(frappe.PermissionError):
				fresh = frappe.get_doc("GP Comment", comment.name)
				fresh.reference_name = public_discussion.name
				fresh.save()
		self.assertEqual(
			frappe.db.get_value("GP Comment", comment.name, "reference_name"), str(self.discussion.name)
		)
		with self.as_user(self.admin):
			fresh = frappe.get_doc("GP Comment", comment.name)
			fresh.reference_name = public_discussion.name
			fresh.save()
		self.assertEqual(
			frappe.db.get_value("GP Comment", comment.name, "reference_name"), str(public_discussion.name)
		)

	def test_private_poll_cannot_be_published_without_admin(self):
		public_discussion = create_discussion("Public Conversation", self.public, owner=self.member)
		poll = create_poll("Private Poll", self.discussion, owner=self.member)
		with self.as_user(self.member):
			with self.assertRaises(frappe.PermissionError):
				fresh = frappe.get_doc("GP Poll", poll.name)
				fresh.discussion = public_discussion.name
				fresh.save()
		self.assertEqual(frappe.db.get_value("GP Poll", poll.name, "discussion"), str(self.discussion.name))
		with self.as_user(self.admin):
			fresh = frappe.get_doc("GP Poll", poll.name)
			fresh.discussion = public_discussion.name
			fresh.save()
		self.assertEqual(frappe.db.get_value("GP Poll", poll.name, "discussion"), str(public_discussion.name))

	def test_public_comment_and_poll_moves_between_already_public_discussions_remain_allowed(self):
		public_discussion_1 = create_discussion("Public Conversation 1", self.public, owner=self.member)
		public_discussion_2 = create_discussion("Public Conversation 2", self.public, owner=self.member)
		comment = create_comment(public_discussion_1, content="Public Comment", owner=self.member)
		poll = create_poll("Public Poll", public_discussion_1, owner=self.member)
		with self.as_user(self.member):
			c = frappe.get_doc("GP Comment", comment.name)
			c.reference_name = public_discussion_2.name
			c.save()
			p = frappe.get_doc("GP Poll", poll.name)
			p.discussion = public_discussion_2.name
			p.save()
		self.assertEqual(
			frappe.db.get_value("GP Comment", comment.name, "reference_name"), str(public_discussion_2.name)
		)
		self.assertEqual(
			frappe.db.get_value("GP Poll", poll.name, "discussion"), str(public_discussion_2.name)
		)

	def test_task_comment_cannot_be_published_without_admin(self):
		task = create_task("Public Space Task", space=self.public.name, owner=self.member)
		task_comment = frappe.get_doc(
			doctype="GP Comment",
			reference_doctype="GP Task",
			reference_name=task.name,
			content="Task Comment",
		).insert()
		public_discussion = create_discussion("Public Conversation", self.public, owner=self.member)
		with self.as_user(self.member):
			with self.assertRaises(frappe.PermissionError):
				fresh = frappe.get_doc("GP Comment", task_comment.name)
				fresh.reference_doctype = "GP Discussion"
				fresh.reference_name = public_discussion.name
				fresh.save()
		self.assertEqual(frappe.db.get_value("GP Comment", task_comment.name, "reference_doctype"), "GP Task")


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
		# Space membership grants write, but must not grant permission to publish its history.
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

	def test_moving_an_anonymous_space_cannot_bypass_publication_approval(self):
		target = create_community(
			"Public Move Target", visibility=VISIBILITY_ANONYMOUS, admins=[self.second_member]
		)
		space = create_space("Unpublished Anonymous Space", self.community, visibility=VISIBILITY_ANONYMOUS)
		with self.as_user(self.second_member), self.assertRaises(frappe.PermissionError):
			frappe.get_doc("GP Project", space.name).move_to_team(target.name)
		with self.as_user(self.second_member), self.assertRaises(frappe.PermissionError):
			set_value("GP Project", space.name, "team", target.name)
		self.assertEqual(frappe.db.get_value("GP Project", space.name, "team"), self.community.name)
		with self.as_user(self.admin):
			frappe.get_doc("GP Project", space.name).move_to_team(target.name)
		self.assertTrue(frappe.db.get_value("GP Project", space.name, "is_anonymous_readable"))

	def test_a_community_admin_can_move_between_already_public_communities(self):
		source = create_community(
			"Public Move Source", visibility=VISIBILITY_ANONYMOUS, admins=[self.second_member]
		)
		target = create_community(
			"Other Public Community", visibility=VISIBILITY_ANONYMOUS, admins=[self.second_member]
		)
		space = create_space("Already Public Space", source, visibility=VISIBILITY_ANONYMOUS)
		with self.as_user(self.second_member):
			frappe.get_doc("GP Project", space.name).move_to_team(target.name)
		self.assertEqual(frappe.db.get_value("GP Project", space.name, "team"), target.name)

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

		# The outsider loses both general spaces, not the Member Access space.
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
