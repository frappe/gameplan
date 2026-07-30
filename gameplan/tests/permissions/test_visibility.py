# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""Who can see a community or a space at all.

The permission matrix covers content *inside* a space. This file covers the
containers, and the queries that must honour the same rules: a private community
or space has to be invisible both to a direct `has_permission` check and to every
list/feed/search path, or it leaks through the back door.
"""

import frappe

from gameplan.extends.client import get_list as get_client_list
from gameplan.gameplan.doctype.gp_discussion.api import get_discussions
from gameplan.gameplan.doctype.gp_team.gp_team import GPTeam
from gameplan.permissions import (
	apply_accessible_project_filter,
	bookmark_has_permission,
	bookmark_query_conditions,
	comment_query_conditions,
	discussion_query_conditions,
	draft_query_conditions,
	page_query_conditions,
	poll_query_conditions,
	project_query_conditions,
	task_query_conditions,
	team_query_conditions,
)
from gameplan.search_sqlite import GameplanSearch
from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import create_community, create_discussion, create_member, create_space

# Shared content: a global admin sees everything, so these hand back "no condition".
ADMIN_EXEMPT_CONDITIONS = (
	team_query_conditions,
	project_query_conditions,
	discussion_query_conditions,
	task_query_conditions,
	page_query_conditions,
	comment_query_conditions,
	poll_query_conditions,
)

# Personal rows: scoped to their owner with no global-admin exception (see
# bookmark_query_conditions' "Decision 4").
PERSONAL_ROW_CONDITIONS = (draft_query_conditions, bookmark_query_conditions)


class TestCommunityVisibility(GameplanTestCase):
	def test_community_creator_becomes_community_admin(self):
		with self.as_user(self.member):
			community = frappe.get_doc(doctype="GP Team", title="Creator Admin Community").insert()

		community.reload()
		self.assertTrue(any(row.user == self.member.name and row.is_admin for row in community.members))

	def test_private_community_is_visible_only_to_members_and_global_admins(self):
		public = create_community("Visible Public Community")
		private = create_community("Hidden Private Community", is_private=1, members=[self.member])

		self.assert_allowed(public, "read", self.second_member)
		self.assert_allowed(private, "read", self.member)
		self.assert_allowed(private, "read", self.admin)
		self.assert_not_allowed(private, "read", self.second_member)

	def test_private_community_is_filtered_from_lists_for_non_members(self):
		public = create_community("Listed Public Community")
		private = create_community("Unlisted Private Community", is_private=1, members=[self.member])

		with self.as_user(self.second_member):
			communities = frappe.get_list("GP Team", fields=["name"], pluck="name")

		self.assertIn(public.name, communities)
		self.assertNotIn(private.name, communities)


class TestSpaceVisibility(GameplanTestCase):
	def test_private_space_is_visible_only_to_space_members_and_global_admins(self):
		community = create_community("Private Space Community", members=[self.member, self.second_member])
		private_space = create_space("Hidden Private Space", community, is_private=1, members=[self.member])

		self.assert_allowed(private_space, "read", self.member)
		self.assert_allowed(private_space, "read", self.admin)
		self.assert_not_allowed(private_space, "read", self.second_member)

	def test_private_spaces_are_filtered_from_lists_for_non_members(self):
		community = create_community("List Space Community", members=[self.member, self.second_member])
		public_space = create_space("Listed Public Space", community)
		private_space = create_space("Unlisted Private Space", community, is_private=1, members=[self.member])

		with self.as_user(self.second_member):
			spaces = frappe.get_list("GP Project", fields=["name"], pluck="name")

		self.assertIn(public_space.name, spaces)
		self.assertNotIn(private_space.name, spaces)

	def test_public_space_in_private_community_is_visible_only_to_community_members(self):
		community = create_community("Private Parent Community", is_private=1, members=[self.member])
		space = create_space("Public Child Space", community)

		self.assert_allowed(space, "read", self.member)
		self.assert_not_allowed(space, "read", self.second_member)

		with self.as_user(self.second_member):
			spaces = frappe.get_list("GP Project", fields=["name"], pluck="name")

		self.assertNotIn(space.name, spaces)

	def test_client_list_filters_public_space_in_private_community_for_non_members(self):
		community = create_community("Private Parent Client Community", is_private=1, members=[self.member])
		space = create_space("Public Client Child Space", community)

		with self.as_user(self.second_member):
			spaces = get_client_list(doctype="GP Project", fields=["name"], limit=50)

		self.assertNotIn(space.name, [row.name for row in spaces])

	def test_client_list_can_fetch_space_visibility_with_team_title(self):
		community = create_community("Joined Field Community", members=[self.member, self.second_member])
		space = create_space("Joined Field Space", community)

		with self.as_user(self.second_member):
			spaces = get_client_list(
				doctype="GP Project",
				fields=["name", "is_private", "team.title as team_title"],
				limit=50,
			)

		self.assertIn(space.name, [row.name for row in spaces])


class TestPermissionAwareQueries(GameplanTestCase):
	def test_discussion_feed_filters_public_space_in_private_community(self):
		community = create_community("Private Feed Community", is_private=1, members=[self.member])
		space = create_space("Public Feed Space", community)
		hidden = create_discussion("Hidden Feed Discussion", space, owner=self.member)

		with self.as_user(self.second_member):
			discussions = get_discussions(limit=20)

		self.assertNotIn(hidden.name, [row.name for row in discussions])

	def test_search_accessible_projects_filters_public_space_in_private_community(self):
		community = create_community("Private Search Community", is_private=1, members=[self.member])
		space = create_space("Public Search Space", community)

		with self.as_user(self.second_member):
			accessible_projects = GameplanSearch()._get_accessible_projects()

		self.assertNotIn(str(space.name), accessible_projects)


class TestContainerManagement(GameplanTestCase):
	"""Who may EDIT or DELETE a community/space, as opposed to merely see it.

	The rest of this file (and the permission matrix) asks who can *read* what. This asks
	who can destroy it, which is where a regression costs the most: deleting a community
	takes every space, discussion and comment under it along with it.
	"""

	def setUp(self):
		super().setUp()
		self.community_admin = create_member("container_admin@example.com", "Container Admin")
		self.community = create_community(
			"Container Community",
			members=[self.member, self.second_member],
			admins=[self.community_admin],
		)
		self.public_space = create_space("Container Public Space", self.community)
		self.private_space = create_space(
			"Container Private Space", self.community, is_private=1, members=[self.member]
		)

	def assert_managed_by(self, doc, *, managers, others):
		for action in ("write", "delete"):
			for user in managers:
				with self.subTest(action=action, user=user.name, expected=True):
					self.assert_allowed(doc, action, user)
			for user in others:
				with self.subTest(action=action, user=user.name, expected=False):
					self.assert_not_allowed(doc, action, user)

	def test_only_community_admins_may_edit_or_delete_a_community(self):
		self.assert_managed_by(
			self.community,
			managers=[self.admin, self.community_admin],
			others=[self.member, self.second_member, self.outsider],
		)

	def test_a_public_space_is_managed_by_its_community_admins(self):
		self.assert_managed_by(
			self.public_space,
			managers=[self.admin, self.community_admin],
			others=[self.member, self.second_member, self.outsider],
		)

	def test_a_private_space_is_managed_by_its_own_members(self):
		# Space membership REPLACES the community-admin rule here rather than adding to
		# it: the community admin is not in this space, so it is not theirs to manage.
		self.assert_managed_by(
			self.private_space,
			managers=[self.admin, self.member],
			others=[self.community_admin, self.second_member, self.outsider],
		)

	def test_a_member_may_create_a_space_in_a_community_they_can_see(self):
		"""Creating a space is not managing one — any member may start one.

		Asserted through a real insert because that is the only path that runs the
		create branch of project_has_permission.
		"""
		with self.as_user(self.member):
			space = frappe.get_doc(
				doctype="GP Project", title="Member Created Space", team=self.community.name
			).insert()

		self.assertTrue(space.name)


class TestPermissionQueriesUseTheGivenUser(GameplanTestCase):
	"""Permission filters must answer for the user they are HANDED, not the session user.

	Every list and feed in the app runs inside the session of the user being served, so a
	filter that quietly fell back to `frappe.session.user` would still look correct there.
	What breaks is the code that serves one user from another's session: the weekly digest
	builds each recipient's query while the scheduler runs as Administrator
	(email_digest.get_unread_discussions). There the fallback does not merely pick the
	wrong user — it picks a global admin, and a global admin is exempt from every content
	filter, so the recipient's digest would be built from the whole site.

	Every test here therefore stays in the Administrator session on purpose.
	"""

	def setUp(self):
		super().setUp()
		self.open_community = create_community("Open Query Community", members=[self.second_member])
		self.open_space = create_space("Open Query Space", self.open_community)
		self.visible_discussion = create_discussion(
			"Visible Query Discussion", self.open_space, owner=self.second_member
		)
		self.closed_community = create_community(
			"Closed Query Community", is_private=1, members=[self.member]
		)
		self.closed_space = create_space("Closed Query Space", self.closed_community)
		self.hidden_discussion = create_discussion(
			"Hidden Query Discussion", self.closed_space, owner=self.member
		)

	def discussion_names_for(self, user):
		"""The digest's query shape: built for `user` from someone else's session."""
		Discussion = frappe.qb.DocType("GP Discussion")
		query = apply_accessible_project_filter(
			frappe.qb.from_(Discussion).select(Discussion.name), Discussion.project, user
		)
		return {str(row[0]) for row in query.run()}

	def test_a_query_built_for_another_user_uses_that_users_access(self):
		self.assertEqual(frappe.session.user, "Administrator", "the session must not be the served user")

		names = self.discussion_names_for(self.second_member.name)

		self.assertIn(str(self.visible_discussion.name), names)
		self.assertNotIn(str(self.hidden_discussion.name), names)

	def test_a_query_built_for_a_global_admin_is_handed_back_unfiltered(self):
		names = self.discussion_names_for(self.admin.name)

		self.assertIn(str(self.hidden_discussion.name), names)

	def test_permission_query_conditions_answer_for_the_user_they_are_given(self):
		for condition in ADMIN_EXEMPT_CONDITIONS + PERSONAL_ROW_CONDITIONS:
			with self.subTest(condition=condition.__name__):
				self.assertIsNotNone(
					condition(user=self.member.name),
					"a non-admin must always be filtered, whoever holds the session",
				)

	def test_a_global_admin_is_exempt_from_the_shared_content_filters(self):
		for condition in ADMIN_EXEMPT_CONDITIONS:
			with self.subTest(condition=condition.__name__):
				self.assertIsNone(condition(user=self.admin.name))

	def test_personal_rows_stay_scoped_to_their_owner_even_for_a_global_admin(self):
		for condition in PERSONAL_ROW_CONDITIONS:
			with self.subTest(condition=condition.__name__):
				self.assertIn(self.member.name, condition(user=self.member.name))
				self.assertNotIn("Administrator", condition(user=self.member.name))
				self.assertIn(self.admin.name, condition(user=self.admin.name))

	def test_bookmark_permission_answers_for_the_user_it_is_given(self):
		bookmark = frappe.get_doc(
			doctype="GP Bookmark",
			user=self.member.name,
			discussion=self.visible_discussion.name,
		).insert(ignore_permissions=True)

		self.assertIs(bookmark_has_permission(bookmark, "read", self.member.name), True)
		self.assertIs(bookmark_has_permission(bookmark, "read", self.second_member.name), False)
		self.assertIs(bookmark_has_permission(bookmark, "read", self.admin.name), False)

	def test_the_community_list_query_filter_hides_private_communities(self):
		Team = frappe.qb.DocType("GP Team")

		def listed_for(user):
			with self.as_user(user):
				query = GPTeam.get_list_query(frappe.qb.from_(Team).select(Team.name))
				return {str(row[0]) for row in query.run()}

		self.assertIn(self.open_community.name, listed_for(self.second_member))
		self.assertNotIn(self.closed_community.name, listed_for(self.second_member))
		# A global admin has no criterion at all: the filter must hand the query back
		# untouched rather than filter on nothing.
		self.assertIn(self.closed_community.name, listed_for(self.admin))
