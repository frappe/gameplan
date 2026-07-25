# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""Bookmarks: a private, per-user reading list of discussions.

A bookmark (GP Bookmark) is a personal row — like a draft, not like community
content. Whoever created it is the only one who may see it, and the only one who
may remove it. Everything a user does with bookmarks goes through the two
GP Discussion doc-methods (`add_bookmark` / `remove_bookmark`), so the doctype's
own read permission on the discussion is what gates *what* can be bookmarked.
"""

import frappe

from gameplan.gameplan.doctype.gp_discussion.api import get_discussions
from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import create_community, create_discussion, create_space


def bookmark_rows(user=None, discussion=None):
	"""All GP Bookmark rows in the database, ignoring permissions.

	Used to assert the stored state, so a test never confuses "the row is gone"
	with "the row is hidden from this user".
	"""
	filters = {}
	if user is not None:
		filters["user"] = user.name
	if discussion is not None:
		filters["discussion"] = discussion.name
	return frappe.get_all("GP Bookmark", filters=filters, fields=["name", "user", "discussion"])


class BookmarkTestCase(GameplanTestCase):
	def setUp(self):
		super().setUp()
		self.community = create_community("Acme", members=[self.member, self.second_member])
		self.space = create_space("Engineering", self.community)
		self.discussion = create_discussion("Welcome thread", self.space, owner=self.member)
		self.other_discussion = create_discussion("Second thread", self.space, owner=self.second_member)

	def add_bookmark(self, discussion, user):
		with self.as_user(user):
			frappe.get_doc("GP Discussion", discussion.name).add_bookmark()

	def remove_bookmark(self, discussion, user):
		with self.as_user(user):
			frappe.get_doc("GP Discussion", discussion.name).remove_bookmark()


class TestAddAndRemoveBookmark(BookmarkTestCase):
	def test_add_bookmark_records_the_discussion_for_the_acting_user(self):
		self.add_bookmark(self.discussion, self.member)

		rows = bookmark_rows()
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0].user, self.member.name)
		self.assertEqual(str(rows[0].discussion), str(self.discussion.name))

	def test_add_bookmark_twice_creates_only_one_row(self):
		self.add_bookmark(self.discussion, self.member)
		self.add_bookmark(self.discussion, self.member)

		self.assertEqual(len(bookmark_rows(user=self.member)), 1)

	def test_remove_bookmark_deletes_the_row(self):
		self.add_bookmark(self.discussion, self.member)
		self.remove_bookmark(self.discussion, self.member)

		self.assertEqual(bookmark_rows(user=self.member), [])

	def test_remove_bookmark_without_one_does_nothing(self):
		self.remove_bookmark(self.discussion, self.member)

		self.assertEqual(bookmark_rows(), [])

	def test_removing_a_bookmark_leaves_the_other_users_bookmark_alone(self):
		self.add_bookmark(self.discussion, self.member)
		self.add_bookmark(self.discussion, self.second_member)

		self.remove_bookmark(self.discussion, self.member)

		self.assertEqual(bookmark_rows(user=self.member), [])
		self.assertEqual(len(bookmark_rows(user=self.second_member)), 1)

	def test_bookmarking_one_discussion_does_not_bookmark_another(self):
		self.add_bookmark(self.discussion, self.member)

		self.assertEqual(len(bookmark_rows(discussion=self.discussion)), 1)
		self.assertEqual(bookmark_rows(discussion=self.other_discussion), [])

	def test_is_bookmarked_is_per_user(self):
		self.add_bookmark(self.discussion, self.member)

		with self.as_user(self.member):
			self.assertTrue(frappe.get_doc("GP Discussion", self.discussion.name).as_dict().is_bookmarked)
		with self.as_user(self.second_member):
			self.assertFalse(frappe.get_doc("GP Discussion", self.discussion.name).as_dict().is_bookmarked)

	def test_deleting_a_discussion_removes_every_users_bookmark(self):
		"""A bookmark points at a discussion with a Link field, so a leftover row both
		blocks the delete (link check) and dangles for the user who bookmarked it."""
		self.add_bookmark(self.discussion, self.member)
		self.add_bookmark(self.discussion, self.second_member)

		with self.as_user(self.admin):
			frappe.delete_doc("GP Discussion", self.discussion.name)

		self.assertEqual(bookmark_rows(), [])


class TestBookmarkPrivacy(BookmarkTestCase):
	"""Bookmarks are private to the user who made them (see GPDraft for the same rule).

	Nothing in Gameplan enumerates another user's bookmarks, so scoping is by the
	`user` field for everyone — there is no admin view of a user's reading list.
	"""

	def setUp(self):
		super().setUp()
		self.add_bookmark(self.discussion, self.member)
		self.add_bookmark(self.other_discussion, self.second_member)
		self.member_bookmark = bookmark_rows(user=self.member)[0].name
		self.other_bookmark = bookmark_rows(user=self.second_member)[0].name

	def test_a_user_lists_only_their_own_bookmarks(self):
		with self.as_user(self.member):
			names = [row.name for row in frappe.get_list("GP Bookmark", fields=["name"])]

		self.assertEqual(names, [self.member_bookmark])

	def test_a_user_can_read_their_own_bookmark(self):
		self.assertTrue(
			frappe.has_permission("GP Bookmark", "read", doc=self.member_bookmark, user=self.member.name)
		)

	def test_a_user_cannot_read_another_users_bookmark(self):
		self.assertFalse(
			frappe.has_permission("GP Bookmark", "read", doc=self.other_bookmark, user=self.member.name)
		)

	def test_a_user_cannot_delete_another_users_bookmark(self):
		with self.as_user(self.member):
			with self.assertRaises(frappe.PermissionError):
				frappe.delete_doc("GP Bookmark", self.other_bookmark)

		self.assertEqual(len(bookmark_rows(user=self.second_member)), 1)

	def test_a_user_cannot_create_a_bookmark_for_someone_else(self):
		with self.as_user(self.member):
			bookmark = frappe.get_doc(
				doctype="GP Bookmark", user=self.second_member.name, discussion=self.discussion.name
			)
			with self.assertRaises(frappe.PermissionError):
				bookmark.insert()

	def test_a_guest_only_sees_their_own_bookmarks(self):
		with self.as_user(self.guest):
			self.assertEqual(frappe.get_list("GP Bookmark", fields=["name"]), [])


class TestBookmarksFeed(BookmarkTestCase):
	"""The Bookmarks page is `get_discussions(filters={"feed_type": "bookmarks"})`."""

	def bookmarks_feed(self, user):
		with self.as_user(user):
			return [str(d.name) for d in get_discussions(filters={"feed_type": "bookmarks"}, limit=20)]

	def test_feed_returns_the_bookmarked_discussion(self):
		self.add_bookmark(self.discussion, self.member)

		self.assertEqual(self.bookmarks_feed(self.member), [str(self.discussion.name)])

	def test_feed_is_empty_without_bookmarks(self):
		self.assertEqual(self.bookmarks_feed(self.member), [])

	def test_feed_never_shows_another_users_bookmarks(self):
		self.add_bookmark(self.other_discussion, self.second_member)

		self.assertEqual(self.bookmarks_feed(self.member), [])

	def test_removing_a_bookmark_drops_it_from_the_feed(self):
		self.add_bookmark(self.discussion, self.member)
		self.remove_bookmark(self.discussion, self.member)

		self.assertEqual(self.bookmarks_feed(self.member), [])

	def test_feed_hides_a_bookmarked_discussion_in_a_space_the_user_lost_access_to(self):
		private_space = create_space("Secret Plans", self.community, is_private=1, members=[self.member])
		private_discussion = create_discussion("Secret thread", private_space, owner=self.member)
		self.add_bookmark(private_discussion, self.member)
		self.assertEqual(self.bookmarks_feed(self.member), [str(private_discussion.name)])

		space = frappe.get_doc("GP Project", private_space.name)
		space.members = []
		space.save(ignore_permissions=True)

		self.assertEqual(self.bookmarks_feed(self.member), [])
