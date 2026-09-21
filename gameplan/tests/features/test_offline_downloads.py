# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""Offline downloads: the index and bundle endpoints behind Settings > Preferences.

A device asks for the discussions in the communities the user has joined with activity
inside a window, then fetches them a page at a time with their comments, activity, polls and
the rows the feeds render.
"""

import json
from unittest.mock import patch

import frappe
from frappe.utils import add_days, add_to_date, now_datetime

from gameplan import offline_downloads
from gameplan.offline_downloads import get_offline_bundle, get_offline_index, rate_limit_key
from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import (
	create_comment,
	create_community,
	create_discussion,
	create_poll,
	create_space,
)

FIELDS = json.dumps(
	{
		"comments": ["name", "content", "owner", "creation", {"reactions": ["name", "user", "emoji"]}],
		"activities": ["name", "user", "action", "data", "creation"],
		"polls": ["name", "title", "creation", {"options": ["name", "title", "idx"]}],
	}
)


def set_last_post_at(discussion, when):
	frappe.db.set_value("GP Discussion", discussion.name, "last_post_at", when, update_modified=False)


def set_modified(doctype, name, when):
	frappe.db.set_value(doctype, name, "modified", when, update_modified=False)


class OfflineDownloadsTestCase(GameplanTestCase):
	def setUp(self):
		super().setUp()
		frappe.cache.delete_value(rate_limit_key(self.member.name), make_keys=False)
		self.addCleanup(frappe.cache.delete_value, rate_limit_key(self.member.name), make_keys=False)
		self.community = create_community("Acme", members=[self.member, self.second_member])
		self.joined = create_space("Engineering", self.community, members=[self.member])
		self.not_joined = create_space("Design", self.community, members=[self.second_member])
		self.recent = create_discussion("Recent thread", self.joined, owner=self.member)
		self.old = create_discussion("Old thread", self.joined, owner=self.member)
		set_last_post_at(self.old, add_days(now_datetime(), -45))
		self.elsewhere = create_discussion("Other space thread", self.not_joined, owner=self.second_member)
		# A community this user never joined, and a Space they cannot open inside their own.
		self.other_community = create_community("Rivals", members=[self.second_member])
		self.other_space = create_space("Strategy", self.other_community, members=[self.second_member])
		self.outside = create_discussion("Rival thread", self.other_space, owner=self.second_member)
		self.secret = create_discussion(
			"Private thread",
			create_space("Secret", self.community, is_private=1, members=[self.second_member]),
			owner=self.second_member,
		)

	def index(self, window):
		with self.as_user(self.member):
			return get_offline_index(window)["discussions"]

	def bundle(self, window, **kwargs):
		with self.as_user(self.member):
			return get_offline_bundle(window, FIELDS, **kwargs)

	def settle_before(self, when):
		"""Backdate every discussion in the window, so only what a test touches is a change."""
		for name in self.index(90):
			set_modified("GP Discussion", name, when)
			frappe.db.set_value("GP Discussion", name, "last_post_at", when, update_modified=False)


class TestOfflineIndex(OfflineDownloadsTestCase):
	def test_lists_every_space_of_a_joined_community(self):
		"""Space membership is not the scope: joining the community is."""
		names = self.index(90)
		self.assertIn(str(self.recent.name), names)
		self.assertIn(str(self.elsewhere.name), names)

	def test_leaves_out_communities_the_user_has_not_joined(self):
		self.assertNotIn(str(self.outside.name), self.index(90))

	def test_leaves_out_a_private_space_the_user_is_not_in(self):
		self.assertNotIn(str(self.secret.name), self.index(90))

	def test_window_excludes_older_activity(self):
		names = self.index(30)
		self.assertIn(str(self.recent.name), names)
		self.assertNotIn(str(self.old.name), names)
		self.assertIn(str(self.old.name), self.index(90))

	def test_window_is_capped_at_three_months(self):
		set_last_post_at(self.old, add_days(now_datetime(), -120))
		self.assertNotIn(str(self.old.name), self.index(365))

	def test_a_discussion_moved_out_of_the_community_drops_out(self):
		frappe.db.set_value("GP Discussion", self.recent.name, "project", self.other_space.name)
		self.assertNotIn(str(self.recent.name), self.index(90))

	def test_a_deleted_discussion_drops_out(self):
		frappe.delete_doc("GP Discussion", self.recent.name, ignore_permissions=True)
		self.assertNotIn(str(self.recent.name), self.index(90))

	def test_leaving_a_private_space_drops_its_discussions(self):
		private = create_space("Secret", self.community, is_private=1, members=[self.member])
		secret = create_discussion("Secret thread", private, owner=self.member)
		self.assertIn(str(secret.name), self.index(90))

		private.reload()
		private.members = [m for m in private.members if m.user != self.member.name]
		private.save(ignore_permissions=True)
		self.assertNotIn(str(secret.name), self.index(90))

	def test_reports_visited_discussions_the_user_can_no_longer_read(self):
		private = create_space("Secret", self.community, is_private=1, members=[self.member])
		secret = create_discussion("Secret thread", private, owner=self.member)
		gone = create_discussion("Gone thread", self.joined, owner=self.member)
		cached = [str(self.elsewhere.name), str(secret.name), str(gone.name)]
		with self.as_user(self.member):
			self.assertEqual(get_offline_index(30, json.dumps(cached))["revoked"], [])

		private.reload()
		private.members = []
		private.save(ignore_permissions=True)
		frappe.delete_doc("GP Discussion", gone.name, ignore_permissions=True)
		with self.as_user(self.member):
			revoked = get_offline_index(30, json.dumps(cached))["revoked"]
		# The public space's discussion stays: reading it never needed membership.
		self.assertEqual(sorted(revoked), sorted([str(secret.name), str(gone.name)]))

	def test_rejects_an_empty_window(self):
		with self.as_user(self.member), self.assertRaises(frappe.ValidationError):
			get_offline_index(0)


class TestOfflineBundle(OfflineDownloadsTestCase):
	def test_carries_the_document_as_the_app_reads_it(self):
		bundle = self.bundle(30)
		self.assertIn(str(self.recent.name), [str(d["name"]) for d in bundle["discussions"]])
		doc = next(d for d in bundle["discussions"] if str(d["name"]) == str(self.recent.name))
		# Fields added by GP Discussion.as_dict, which /api/v2/document returns too.
		for key in ("last_unread_comment", "is_bookmarked", "views"):
			self.assertIn(key, doc)

	def test_groups_comments_and_polls_under_their_discussion(self):
		comment = create_comment(self.recent, content="Hello", owner=self.member)
		poll = create_poll("Lunch?", self.recent)
		create_comment(self.elsewhere, content="Not mine")

		bundle = self.bundle(30)
		key = str(self.recent.name)
		self.assertEqual([row["name"] for row in bundle["comments"][key]], [comment.name])
		self.assertEqual(bundle["comments"][key][0]["reactions"], [])
		self.assertNotIn("_offline_parent", bundle["comments"][key][0])
		self.assertEqual([row["name"] for row in bundle["polls"][key]], [poll.name])
		self.assertEqual(len(bundle["polls"][key][0]["options"]), 2)
		self.assertNotIn(str(self.outside.name), bundle["comments"])

	def test_carries_the_rows_the_feeds_render(self):
		"""A Space the device never opened still needs its list, not just the documents."""
		bundle = self.bundle(30)
		row = next(r for r in bundle["rows"] if str(r["name"]) == str(self.recent.name))
		self.assertEqual(str(row["project"]), str(self.joined.name))
		self.assertEqual(row["project_title"], "Engineering")
		for key in ("last_post_at", "unread", "title"):
			self.assertIn(key, row)
		self.assertEqual(
			{str(r["name"]) for r in bundle["rows"]},
			{str(d["name"]) for d in bundle["discussions"]},
		)

	def test_pages_through_the_window(self):
		for i in range(offline_downloads.PAGE_SIZE):
			create_discussion(f"Thread {i}", self.joined)
		in_window = len(self.index(30))

		first = self.bundle(30)
		second = self.bundle(30, start=offline_downloads.PAGE_SIZE)
		self.assertTrue(first["has_next_page"])
		self.assertFalse(second["has_next_page"])
		names = [d["name"] for d in first["discussions"] + second["discussions"]]
		self.assertEqual(len(names), in_window)
		self.assertEqual(len(set(names)), len(names))

	def test_names_fetches_just_those_within_the_window(self):
		other = create_discussion("Another thread", self.joined, owner=self.member)
		wanted = [str(other.name), str(self.old.name), str(self.outside.name)]
		bundle = self.bundle(30, names=json.dumps(wanted))
		# The old thread is outside 30 days, and the rival community is out of scope.
		self.assertEqual([str(d["name"]) for d in bundle["discussions"]], [str(other.name)])
		self.assertFalse(bundle["has_next_page"])

	def test_since_returns_only_changed_discussions(self):
		since = add_to_date(now_datetime(), minutes=-5)
		self.settle_before(add_to_date(since, minutes=-10))
		self.assertEqual(self.bundle(30, since=str(since))["discussions"], [])

		create_comment(self.recent, content="New reply")
		changed = self.bundle(30, since=str(since))["discussions"]
		self.assertEqual([str(d["name"]) for d in changed], [str(self.recent.name)])

	def test_a_reaction_on_an_old_comment_counts_as_a_change(self):
		comment = create_comment(self.recent, content="Hello")
		since = add_to_date(now_datetime(), minutes=-5)
		earlier = add_to_date(since, minutes=-10)
		self.settle_before(earlier)
		set_modified("GP Comment", comment.name, earlier)
		self.assertEqual(self.bundle(30, since=str(since))["discussions"], [])

		set_modified("GP Comment", comment.name, now_datetime())
		changed = self.bundle(30, since=str(since))["discussions"]
		self.assertEqual([str(d["name"]) for d in changed], [str(self.recent.name)])

	def test_is_post_only(self):
		from gameplan.tests.fixtures import declared_http_methods

		self.assertEqual(declared_http_methods(get_offline_bundle), {"POST"})


class TestOfflineRateLimit(OfflineDownloadsTestCase):
	def test_stops_a_runaway_client(self):
		with patch.object(offline_downloads, "REQUESTS_PER_HOUR", 2):
			self.index(30)
			self.index(30)
			with self.assertRaises(frappe.RateLimitExceededError):
				self.index(30)

	def test_counts_each_user_separately(self):
		frappe.cache.delete_value(rate_limit_key(self.second_member.name), make_keys=False)
		self.addCleanup(frappe.cache.delete_value, rate_limit_key(self.second_member.name), make_keys=False)
		with patch.object(offline_downloads, "REQUESTS_PER_HOUR", 1):
			self.index(30)
			with self.as_user(self.second_member):
				get_offline_index(30)
