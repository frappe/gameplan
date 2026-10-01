# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""The permission rules with the Anonymous tier in them.

`expected_space_access` below is the access matrix of the public communities spec, written
out on its own. The rules must match it for every kind of user and every tier combination,
and three independent implementations of "can this user read this space" must agree with
each other: the single-document check, the SQL list filter, and the batched form used for
notification audiences. Those drifting apart is how "can open it but not list it", or the
other way round, happens.

The role layer grants the Guest role read access to the doctypes a public thread needs, so
for those these rules are what decides.
"""

from unittest.mock import patch

import frappe

import gameplan
from gameplan.per_user_state import (
	discussion_visit_query_conditions,
	notification_has_permission,
	notification_query_conditions,
	pinned_project_has_permission,
	project_visit_query_conditions,
)
from gameplan.permissions import (
	bookmark_has_permission,
	bookmark_query_conditions,
	can_create_content,
	can_delete_content,
	can_edit_content,
	can_interact_with_content,
	can_invite_guest,
	can_manage_community,
	can_manage_space,
	can_view_community,
	can_view_content,
	can_view_space,
	can_write_content,
	draft_query_conditions,
	project_access_criterion,
	team_access_criterion,
	users_who_can_view_space,
)
from gameplan.public_access import (
	PUBLIC_ACCESS_CONFIG_KEY,
	VISIBILITY_ANONYMOUS,
	VISIBILITY_GENERAL,
	VISIBILITY_MEMBER_ACCESS,
)
from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import (
	create_comment,
	create_community,
	create_discussion,
	create_guest,
	create_space,
	grant_guest_access,
)

ANONYMOUS = "Guest"
TIERS = (VISIBILITY_ANONYMOUS, VISIBILITY_GENERAL, VISIBILITY_MEMBER_ACCESS)


def switch(on):
	return patch.dict(frappe.conf, {PUBLIC_ACCESS_CONFIG_KEY: 1 if on else 0})


def listed_spaces(user):
	Project = frappe.qb.DocType("GP Project")
	query = frappe.qb.from_(Project).select(Project.name)
	criterion = project_access_criterion(Project, user)
	if criterion is not None:
		query = query.where(criterion)
	return {str(name) for name in query.run(pluck=True)}


def listed_communities(user):
	Team = frappe.qb.DocType("GP Team")
	query = frappe.qb.from_(Team).select(Team.name)
	criterion = team_access_criterion(Team, user)
	if criterion is not None:
		query = query.where(criterion)
	return set(query.run(pluck=True))


class ResolverTestCase(GameplanTestCase):
	"""Every tier combination, archived cases, and one space of each kind of membership."""

	def setUp(self):
		super().setUp()
		self.granted_guest = create_guest("granted-guest@example.com", "Granted Guest")
		self.users = {
			"anonymous": ANONYMOUS,
			"guest": self.guest.name,
			"granted guest": self.granted_guest.name,
			"member": self.member.name,
			"outsider": self.outsider.name,
			"admin": self.admin.name,
		}
		# member is on every member list; outsider is on none.
		self.communities = {}
		self.spaces = []
		for community_tier in TIERS:
			community = create_community(
				f"Resolver {community_tier} Community", visibility=community_tier, members=[self.member]
			)
			self.communities[community.name] = community
			for space_tier in TIERS:
				space = create_space(
					f"Resolver {community_tier}/{space_tier}",
					community,
					visibility=space_tier,
					members=[self.member],
				)
				grant_guest_access(self.granted_guest, space)
				self.spaces.append(space)

		archived_community = create_community(
			"Resolver Archived Community", visibility=VISIBILITY_ANONYMOUS, members=[self.member]
		)
		archived_community_space = create_space(
			"Resolver In Archived Community", archived_community, visibility=VISIBILITY_ANONYMOUS
		)
		public_community = next(c for c in self.communities.values() if c.visibility == VISIBILITY_ANONYMOUS)
		archived_space = create_space(
			"Resolver Archived Space", public_community, visibility=VISIBILITY_ANONYMOUS
		)
		with self.as_user(self.admin):
			frappe.get_doc("GP Team", archived_community.name).archive()
			frappe.get_doc("GP Project", archived_space.name).archive()
		self.communities[archived_community.name] = frappe.get_doc("GP Team", archived_community.name)
		self.spaces += [frappe.get_doc("GP Project", archived_community_space.name)]
		self.spaces += [frappe.get_doc("GP Project", archived_space.name)]
		self.spaces = [frappe.get_doc("GP Project", space.name) for space in self.spaces]

	def expected_space_access(self, kind, space, switch_on):
		"""The spec's access matrix, written out independently of the code."""
		community = frappe.get_doc("GP Team", space.team)
		public = (
			switch_on
			and space.visibility == VISIBILITY_ANONYMOUS
			and community.visibility == VISIBILITY_ANONYMOUS
			and not space.archived_at
			and not community.archived_at
		)
		if kind == "admin" or public:
			return True
		if kind in ("anonymous", "guest"):
			return False
		if kind == "granted guest":
			return frappe.db.exists(
				"GP Guest Access", {"user": self.granted_guest.name, "project": space.name}
			)
		on_member_list = kind == "member"
		if space.visibility == VISIBILITY_MEMBER_ACCESS:
			return on_member_list
		if community.visibility == VISIBILITY_MEMBER_ACCESS:
			return on_member_list
		return True

	def expected_community_access(self, kind, community, switch_on):
		public = switch_on and community.visibility == VISIBILITY_ANONYMOUS and not community.archived_at
		if kind == "admin" or public:
			return True
		if kind in ("anonymous", "guest"):
			return False
		if kind == "granted guest":
			spaces = frappe.get_all("GP Project", filters={"team": community.name}, pluck="name")
			return bool(
				spaces
				and frappe.db.exists(
					"GP Guest Access", {"user": self.granted_guest.name, "project": ["in", spaces]}
				)
			)
		if community.visibility == VISIBILITY_MEMBER_ACCESS:
			return kind == "member"
		return True


class TestSpaceAccess(ResolverTestCase):
	def test_every_rule_matches_the_access_matrix_and_each_other(self):
		for switch_on in (True, False):
			with switch(switch_on):
				for kind, user in self.users.items():
					listed = listed_spaces(user)
					for space in self.spaces:
						with self.subTest(switch=switch_on, user=kind, space=space.title):
							expected = bool(self.expected_space_access(kind, space, switch_on))
							self.assertEqual(can_view_space(user, space.name), expected, "can_view_space")
							self.assertEqual(str(space.name) in listed, expected, "SQL list filter")
							self.assertEqual(
								user in users_who_can_view_space([user], space.name),
								expected,
								"users_who_can_view_space",
							)

	def test_the_tier_combinations_from_the_spec(self):
		# Spec section 8, the anonymous column, with the public access switch on.
		cases = {
			(VISIBILITY_ANONYMOUS, VISIBILITY_ANONYMOUS): True,
			(VISIBILITY_ANONYMOUS, VISIBILITY_GENERAL): False,
			(VISIBILITY_ANONYMOUS, VISIBILITY_MEMBER_ACCESS): False,
			(VISIBILITY_GENERAL, VISIBILITY_ANONYMOUS): False,
			(VISIBILITY_MEMBER_ACCESS, VISIBILITY_ANONYMOUS): False,
		}
		with switch(True):
			for (community_tier, space_tier), expected in cases.items():
				space = next(s for s in self.spaces if s.title == f"Resolver {community_tier}/{space_tier}")
				with self.subTest(community=community_tier, space=space_tier):
					self.assertEqual(can_view_space(ANONYMOUS, space.name), expected)

			for title in ("Resolver Archived Space", "Resolver In Archived Community"):
				space = next(s for s in self.spaces if s.title == title)
				with self.subTest(archived=title):
					self.assertFalse(can_view_space(ANONYMOUS, space.name))

	def test_the_switch_closes_everything(self):
		public = next(
			s for s in self.spaces if s.title == f"Resolver {VISIBILITY_ANONYMOUS}/{VISIBILITY_ANONYMOUS}"
		)
		with switch(False):
			self.assertFalse(can_view_space(ANONYMOUS, public.name))
			self.assertFalse(can_view_space(self.guest.name, public.name))
			self.assertEqual(listed_spaces(ANONYMOUS), set())

	def test_the_role_layer_agrees_with_the_rules(self):
		# The Guest role reads communities, spaces, discussions, comments and polls, so a
		# public discussion is readable all the way through, and a General one is not.
		public = next(
			s for s in self.spaces if s.title == f"Resolver {VISIBILITY_ANONYMOUS}/{VISIBILITY_ANONYMOUS}"
		)
		general = next(
			s for s in self.spaces if s.title == f"Resolver {VISIBILITY_ANONYMOUS}/{VISIBILITY_GENERAL}"
		)
		public_discussion = create_discussion("Resolver Public Discussion", public, owner=self.member)
		general_discussion = create_discussion("Resolver General Discussion", general, owner=self.member)
		with switch(True):
			self.assert_allowed(public_discussion, "read", ANONYMOUS)
			self.assert_allowed(public, "read", ANONYMOUS)
			self.assert_not_allowed(general_discussion, "read", ANONYMOUS)
		with switch(False):
			self.assert_not_allowed(public_discussion, "read", ANONYMOUS)


class TestCommunityAccess(ResolverTestCase):
	def test_every_rule_matches_the_access_matrix_and_each_other(self):
		for switch_on in (True, False):
			with switch(switch_on):
				for kind, user in self.users.items():
					listed = listed_communities(user)
					for community in self.communities.values():
						with self.subTest(switch=switch_on, user=kind, community=community.title):
							expected = bool(self.expected_community_access(kind, community, switch_on))
							self.assertEqual(
								can_view_community(user, community.name), expected, "can_view_community"
							)
							self.assertEqual(community.name in listed, expected, "SQL list filter")


class TestAnonymousVisitorsWriteNothing(ResolverTestCase):
	def setUp(self):
		super().setUp()
		self.public = next(
			s for s in self.spaces if s.title == f"Resolver {VISIBILITY_ANONYMOUS}/{VISIBILITY_ANONYMOUS}"
		)
		self.discussion = create_discussion("Resolver Write Discussion", self.public, owner=self.member)
		self.comment = create_comment(self.discussion, owner=self.member)

	def test_every_write_rule_refuses_even_on_a_public_space(self):
		community = frappe.get_doc("GP Team", self.public.team)
		new_comment = frappe.get_doc(
			doctype="GP Comment", reference_doctype="GP Discussion", reference_name=self.discussion.name
		)
		with switch(True):
			self.assertTrue(can_view_content(ANONYMOUS, self.discussion))
			for rule, doc in (
				(can_create_content, new_comment),
				(can_interact_with_content, self.discussion),
				(can_write_content, self.discussion),
				(can_edit_content, self.comment),
				(can_delete_content, self.comment),
				(can_manage_space, self.public),
				(can_manage_community, community),
				(can_invite_guest, self.public),
			):
				with self.subTest(rule=rule.__name__):
					self.assertFalse(rule(ANONYMOUS, doc))

	def test_personal_rows_are_never_an_anonymous_visitors(self):
		# Rows are matched by user or owner, and "Guest" must not match one by name.
		for conditions in (
			draft_query_conditions,
			bookmark_query_conditions,
			notification_query_conditions,
			project_visit_query_conditions,
			discussion_visit_query_conditions,
		):
			with self.subTest(conditions=conditions.__name__):
				self.assertEqual(conditions(ANONYMOUS), "1=0")

		bookmark = frappe.get_doc(doctype="GP Bookmark", user=ANONYMOUS, discussion=self.discussion.name)
		notification = frappe.get_doc(doctype="GP Notification", to_user=ANONYMOUS)
		pin = frappe.get_doc(doctype="GP Pinned Project", user=ANONYMOUS, project=self.public.name)
		self.assertFalse(bookmark_has_permission(bookmark, "read", ANONYMOUS))
		self.assertFalse(notification_has_permission(notification, "read", ANONYMOUS))
		for ptype in ("create", "read", "delete"):
			self.assertFalse(pinned_project_has_permission(pin, ptype, ANONYMOUS))

	def test_is_anonymous_is_what_the_rules_ask(self):
		self.assertTrue(gameplan.is_anonymous(ANONYMOUS))
