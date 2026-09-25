# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""Offline downloads: the index and bundle endpoints behind Settings > Preferences.

A device asks for the discussions in the communities the user has joined with activity
inside a window, then fetches them a page at a time with their comments, activity, polls and
the rows the feeds render.
"""

from unittest.mock import patch

import frappe
from frappe.utils import add_days, add_to_date, now_datetime

from gameplan import offline_downloads
from gameplan.offline_downloads import get_offline_bundle, get_offline_index
from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import (
	create_comment,
	create_community,
	create_discussion,
	create_poll,
	create_space,
	declared_http_methods,
)

FIELDS = {
	"comments": ["name", "content", "owner", "creation", {"reactions": ["name", "user", "emoji"]}],
	"activities": ["name", "user", "action", "data", "creation"],
	"polls": ["name", "title", "creation", {"options": ["name", "title", "idx"]}],
}


def set_last_post_at(discussion, when):
	frappe.db.set_value("GP Discussion", discussion.name, "last_post_at", when, update_modified=False)


def set_modified(doctype, name, when):
	frappe.db.set_value(doctype, name, "modified", when, update_modified=False)


def names(docs):
	return {str(doc.name) for doc in docs}


def row_names(rows):
	return {str(row["name"]) for row in rows}


class OfflineDownloadsTestCase(GameplanTestCase):
	def setUp(self):
		super().setUp()
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

	def index(self, window, **kwargs):
		with self.as_user(self.member):
			return get_offline_index(window, **kwargs)

	def discussions(self, window, among=None):
		"""The window's discussions, among `among` (default: those setUp made), so data the
		site already holds does not count."""
		among = names(among or [self.recent, self.old, self.elsewhere, self.outside, self.secret])
		return set(self.index(window)["discussions"]) & among

	def changed(self, since):
		return self.index(30, since=str(since))["changed"]

	def revoked(self, cached):
		return sorted(self.index(30, cached=[str(name) for name in cached])["revoked"])

	def bundle(self, window, wanted=None):
		"""What a device asks for: everything in the window unless a test names its own."""
		with self.as_user(self.member):
			wanted = wanted if wanted is not None else self.index(window)["discussions"]
			return get_offline_bundle(window, FIELDS, wanted)

	def settle_before(self, when):
		"""Backdate every discussion in the window, so only what a test touches is a change."""
		for name in self.index(90)["discussions"]:
			set_modified("GP Discussion", name, when)
			frappe.db.set_value("GP Discussion", name, "last_post_at", when, update_modified=False)


class TestOfflineIndex(OfflineDownloadsTestCase):
	def test_scope_is_every_space_the_user_can_open_in_joined_communities(self):
		"""Joining the community is the scope, not joining the Space; the window narrows it."""
		self.assertEqual(self.discussions(90), names([self.recent, self.old, self.elsewhere]))
		self.assertEqual(self.discussions(30), names([self.recent, self.elsewhere]))

	def test_a_discussion_leaves_the_scope_with_its_space(self):
		private = create_space("Secret", self.community, is_private=1, members=[self.member])
		secret = create_discussion("Secret thread", private, owner=self.member)
		moved = create_discussion("Moved thread", self.joined, owner=self.member)
		deleted = create_discussion("Deleted thread", self.not_joined, owner=self.member)
		ours = [self.recent, self.old, self.elsewhere, secret, moved, deleted]
		self.assertEqual(self.discussions(90, ours), names(ours))

		private.reload()
		private.members = [m for m in private.members if m.user != self.member.name]
		private.save(ignore_permissions=True)
		frappe.db.set_value("GP Discussion", moved.name, "project", self.other_space.name)
		frappe.delete_doc("GP Discussion", deleted.name, ignore_permissions=True)
		frappe.db.set_value("GP Project", self.joined.name, "archived_at", now_datetime())

		self.assertEqual(self.discussions(90, ours), names([self.elsewhere]))

	def test_a_device_is_capped_at_the_newest_discussions(self):
		newest_first = self.index(90)["discussions"]
		with patch.object(offline_downloads, "MAX_DISCUSSIONS", 2):
			self.assertEqual(self.index(90)["discussions"], newest_first[:2])

	def test_a_space_moved_to_another_community_is_reported_by_place(self):
		"""The move rewrites `team` in one statement, so no timestamp reports it."""
		since = add_to_date(now_datetime(), minutes=-5)
		self.settle_before(add_to_date(since, minutes=-10))
		before = self.index(90)["places"][str(self.recent.name)]

		labs = create_community("Acme Labs", members=[self.member])
		frappe.get_doc("GP Project", str(self.joined.name)).move_to_team(labs.name)

		self.assertEqual(self.changed(since), [])
		self.assertNotEqual(self.index(90)["places"][str(self.recent.name)], before)

	def test_revoked_follows_read_access_not_download_scope(self):
		"""A visited discussion is revoked only when the user can no longer read it."""
		private = create_space("Secret", self.community, is_private=1, members=[self.member])
		secret = create_discussion("Secret thread", private, owner=self.member)
		gone = create_discussion("Gone thread", self.joined, owner=self.member)
		locked = create_community("Locked", is_private=1, members=[self.member])
		war_room = create_space("War Room", locked, members=[self.member])
		locked_thread = create_discussion("Locked thread", war_room, owner=self.member)
		# Readable but never downloaded: a public community they never joined.
		kept = [self.elsewhere, self.recent, self.outside]
		cached = names([secret, gone, locked_thread, *kept])
		self.assertEqual(self.revoked(cached), [])

		private.reload()
		private.members = []
		private.save(ignore_permissions=True)
		frappe.delete_doc("GP Discussion", gone.name, ignore_permissions=True)
		for doc in (locked, war_room):
			doc.reload()
			doc.members = [m for m in doc.members if m.user != self.member.name]
			doc.save(ignore_permissions=True)
		# Archiving stops a Space being downloaded; it does not stop the user reading it.
		frappe.db.set_value("GP Project", self.joined.name, "archived_at", now_datetime())

		self.assertEqual(self.revoked(cached), sorted(names([secret, gone, locked_thread])))

	def test_every_kind_of_activity_counts_as_a_change(self):
		"""A sync must not miss a change, nor fetch again what did not change."""
		comment = create_comment(self.recent, content="Hello", owner=self.member)
		poll = create_poll("Lunch?", self.recent)
		deleted = create_comment(self.recent, content="Temporary", owner=self.member)
		unchanged = create_discussion("Quiet thread", self.joined, owner=self.member)

		def changed_after(action):
			since = add_to_date(now_datetime(), seconds=-1)
			earlier = add_to_date(since, minutes=-10)
			self.settle_before(earlier)
			# Including what the previous case added.
			for doctype, parent in (("GP Comment", "reference_name"), ("GP Poll", "discussion")):
				frappe.db.set_value(
					doctype, {parent: self.recent.name}, "modified", earlier, update_modified=False
				)
			self.assertEqual(self.changed(since), [], "nothing changed yet")
			action()
			changed = self.changed(since)
			self.assertNotIn(str(unchanged.name), changed, "an untouched discussion was fetched again")
			return changed

		with self.as_user(self.member):
			cases = {
				"an edited discussion": lambda: frappe.get_doc("GP Discussion", self.recent.name).save(
					ignore_permissions=True
				),
				"a new comment": lambda: create_comment(self.recent, content="Another"),
				"an edited comment": lambda: frappe.get_doc("GP Comment", comment.name).save(
					ignore_permissions=True
				),
				"a reaction on the discussion": lambda: frappe.get_doc(
					"GP Discussion", self.recent.name
				).react(operations=[{"emoji": "👍", "operation": "add"}]),
				"a reaction on a comment": lambda: frappe.get_doc("GP Comment", comment.name).react(
					operations=[{"emoji": "🎉", "operation": "add"}]
				),
				"a poll vote": lambda: frappe.get_doc("GP Poll", poll.name).submit_vote("Yes"),
				# No row is left to compare, so the discussion's own save carries it.
				"a deleted comment": lambda: frappe.delete_doc(
					"GP Comment", deleted.name, ignore_permissions=True
				),
			}
			for label, action in cases.items():
				with self.subTest(label):
					self.assertIn(str(self.recent.name), changed_after(action), label)


class TestOfflineBundle(OfflineDownloadsTestCase):
	def test_carries_what_the_app_reads_for_each_discussion(self):
		comment = create_comment(self.recent, content="Hello", owner=self.member)
		poll = create_poll("Lunch?", self.recent)
		create_comment(self.elsewhere, content="Not this one")

		bundle = self.bundle(30)
		key = str(self.recent.name)
		doc = next(d for d in bundle["discussions"] if str(d["name"]) == key)
		# Fields added by GP Discussion.as_dict, which /api/v2/document returns too.
		for field in ("last_unread_comment", "is_bookmarked", "views"):
			self.assertIn(field, doc)
		# A Space the device never opened still needs its feed rows, not just the documents.
		row = next(r for r in bundle["rows"] if str(r["name"]) == key)
		self.assertEqual(row["project_title"], "Engineering")
		self.assertEqual(row_names(bundle["rows"]), row_names(bundle["discussions"]))
		self.assertEqual([r["name"] for r in bundle["comments"][key]], [comment.name])
		self.assertEqual(bundle["comments"][key][0]["reactions"], [])
		self.assertNotIn("_offline_parent", bundle["comments"][key][0])
		self.assertEqual([r["name"] for r in bundle["polls"][key]], [poll.name])
		self.assertEqual(len(bundle["polls"][key][0]["options"]), 2)

	def test_carries_only_a_page_of_what_the_index_would_list(self):
		"""Named discussions outside the window or the user's reach are skipped."""
		for i in range(offline_downloads.PAGE_SIZE):
			create_discussion(f"Thread {i}", self.joined)
		in_window = self.index(30)["discussions"]
		self.assertEqual(len(self.bundle(30, in_window)["discussions"]), offline_downloads.PAGE_SIZE)

		wanted = [str(self.recent.name), str(self.old.name), str(self.outside.name), str(self.secret.name)]
		self.assertEqual(row_names(self.bundle(30, wanted)["discussions"]), names([self.recent]))
		# The cap is how much a device keeps, not a boundary the bundle enforces.
		with patch.object(offline_downloads, "MAX_DISCUSSIONS", 1):
			self.assertEqual(len(self.bundle(90, [str(self.old.name)])["discussions"]), 1)

	def test_names_the_user_it_answered_for(self):
		"""A device checks this before filing an answer, whatever its cookie says by then."""
		self.assertEqual(self.index(30)["user"], self.member.name)
		self.assertEqual(self.bundle(30)["user"], self.member.name)

	def test_a_runaway_client_is_stopped_per_address(self):
		"""frappe's limiter only runs inside a request, so this test stands one up."""
		method = "gameplan.offline_downloads.get_offline_index"

		def request_from(ip):
			frappe.local.request = frappe._dict(method="POST")
			frappe.local.request_ip = ip
			frappe.form_dict.cmd = method
			frappe.cache.delete_value(f"rl:{method}:{ip}:3600")
			self.addCleanup(frappe.cache.delete_value, f"rl:{method}:{ip}:3600")

		self.addCleanup(setattr, frappe.local, "request", None)
		with patch.object(offline_downloads, "REQUESTS_PER_HOUR", 2):
			request_from("10.0.0.1")
			self.index(30)
			self.index(30)
			with self.assertRaises(frappe.RateLimitExceededError):
				self.index(30)
			# Another address has its own count.
			request_from("10.0.0.2")
			self.index(30)

	def test_is_post_only(self):
		for endpoint in (get_offline_index, get_offline_bundle):
			self.assertEqual(declared_http_methods(endpoint), {"POST"})
