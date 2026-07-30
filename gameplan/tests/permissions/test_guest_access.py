# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""What a guest can reach.

A guest never joins a community; their access is exactly the spaces they were
explicitly granted. What a guest may DO inside a granted space is the guest
participation policy, specced in features/test_guest_participation.py.
"""

import frappe

from gameplan.extends.client import get_list as get_client_list
from gameplan.gameplan.doctype.gp_discussion.api import get_discussions
from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import (
	create_community,
	create_discussion,
	create_guest,
	create_space,
	grant_guest_access,
)


class TestGuestAccess(GameplanTestCase):
	def setUp(self):
		super().setUp()
		self.community = create_community("Guest Space Community", members=[self.member])
		self.public_space = create_space("Guest Public Space", self.community)
		self.granted_space = create_space("Guest Granted Space", self.community, is_private=1)
		grant_guest_access(self.guest, self.granted_space)

	def test_guest_sees_only_explicitly_granted_spaces(self):
		# A public space is still invisible: guests get grants, not community membership.
		self.assert_not_allowed(self.public_space, "read", self.guest)
		self.assert_allowed(self.granted_space, "read", self.guest)

	def test_guest_space_list_contains_only_granted_spaces(self):
		"""The sidebar is a GP Project list, so the grant has to hold at query level too —
		a `has_permission` check alone would still leave every space in the guest's rail."""
		with self.as_user(self.guest):
			rows = get_client_list(
				doctype="GP Project",
				fields=["name", "team.title as team_title"],
				limit=99999,
			)
			listed = {str(row.name) for row in rows}
			team_titles = {str(row.name): row.team_title for row in rows}

		# Expected set is computed from the guest's own grants, so the assertion stays
		# exact on a shared site that may hold other committed GP Guest Access rows.
		# GP Project autonames to an integer, so compare everything as strings.
		granted = frappe.get_all("GP Guest Access", filters={"user": self.guest.name}, pluck="project")
		self.assertEqual(listed, {str(space) for space in granted})
		self.assertIn(str(self.granted_space.name), listed)
		self.assertNotIn(str(self.public_space.name), listed)
		self.assertEqual(team_titles[str(self.granted_space.name)], self.community.title)

	def test_guest_community_list_contains_only_communities_holding_a_granted_space(self):
		"""A guest joins no community, so their community list is derived entirely from
		their space grants. Unfiltered, this hands a guest the title of every community
		on the site — the one thing a per-space grant is supposed to keep from them."""
		ungranted_community = create_community("Guest Ungranted Community")
		create_space("Guest Ungranted Space", ungranted_community)

		with self.as_user(self.guest):
			communities = frappe.get_list("GP Team", pluck="name", limit_page_length=0)

		self.assertIn(self.community.name, communities)
		self.assertNotIn(ungranted_community.name, communities)

	def test_one_guests_community_list_does_not_leak_another_guests_community(self):
		"""The grant is per guest, not per site: holding a grant somewhere must not put
		every other guest's community in your list."""
		other_guest = create_guest("second_guest@example.com", "Second Guest")
		other_community = create_community("Second Guest Community")
		other_space = create_space("Second Guest Space", other_community, is_private=1)
		grant_guest_access(other_guest, other_space)

		with self.as_user(self.guest):
			communities = frappe.get_list("GP Team", pluck="name", limit_page_length=0)
		with self.as_user(other_guest):
			other_communities = frappe.get_list("GP Team", pluck="name", limit_page_length=0)

		self.assertIn(self.community.name, communities)
		self.assertNotIn(other_community.name, communities)
		self.assertIn(other_community.name, other_communities)
		self.assertNotIn(self.community.name, other_communities)

	def test_guest_discussion_feed_contains_only_posts_in_granted_spaces(self):
		"""What the guest clicks through to: the feed must drop posts from spaces they
		were never granted, even public ones in the same community."""
		granted_post = create_discussion("Granted post", self.granted_space, owner=self.member)
		public_post = create_discussion("Public post", self.public_space, owner=self.member)

		with self.as_user(self.guest):
			names = [row.name for row in get_discussions(limit=20)]

		self.assertIn(granted_post.name, names)
		self.assertNotIn(public_post.name, names)
