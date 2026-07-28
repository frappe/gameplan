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
from gameplan.search_sqlite import GameplanSearch
from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import create_community, create_discussion, create_space


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
