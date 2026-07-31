# Copyright (c) 2023, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

import unittest
from datetime import timedelta

import frappe
from frappe.utils import get_datetime

from gameplan.gameplan.doctype.gp_discussion.api import (
	clause_discussions_commented_by_user,
	get_discussions,
	parse_offset,
)
from gameplan.gameplan.doctype.gp_discussion.gp_discussion import has_permission
from gameplan.gameplan.doctype.gp_unread_record.gp_unread_record import GPUnreadRecord
from gameplan.tests.base import GameplanTestCase

# The poll boundary belongs to the poll suite; the feed is its second reader, so it
# borrows the same frozen instant rather than inventing one that could drift.
from gameplan.tests.features.test_polls import STOP_INSTANT, frozen_clock
from gameplan.tests.fixtures import (
	create_community,
	create_discussion,
	create_poll,
	create_space,
	grant_guest_access,
)


class TestDiscussions(GameplanTestCase):
	def test_get_discussions_excludes_archived_spaces(self):
		team = create_community("Archived Discussion Filter Team")
		active_project = create_space("Active Discussion Filter Space", team.name)
		archived_project = create_space("Archived Discussion Filter Space", team.name)
		active_discussion = create_discussion("Visible discussion", active_project.name)
		archived_discussion = create_discussion("Hidden discussion", archived_project.name)

		# Creating a discussion bumps the parent Space's `modified` timestamp via
		# discussion hooks, so reload before archiving to avoid a TimestampMismatchError.
		archived_project.reload()
		archived_project.archive()

		discussions = get_discussions(filters={"team": team.name}, limit=50)
		discussion_names = [discussion.name for discussion in discussions]

		self.assertIn(active_discussion.name, discussion_names)
		self.assertNotIn(archived_discussion.name, discussion_names)

	def test_clause_discussions_commented_by_user_with_no_comments(self):
		"""Test that clause_discussions_commented_by_user handles users with no comments gracefully"""
		# Create a test user who has no comments
		test_user = "test_no_comments@example.com"
		if not frappe.db.exists("User", test_user):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": test_user,
					"first_name": "Test",
					"last_name": "NoComments",
					"send_welcome_email": 0,
				}
			).insert(ignore_permissions=True)

		# Ensure the user has no comments
		frappe.db.delete("GP Comment", {"owner": test_user})

		# This should not raise an SQL error (MariaDB error 1064)
		clause = clause_discussions_commented_by_user(test_user)

		# The clause should be valid and can be used in a query
		Discussion = frappe.qb.DocType("GP Discussion")
		query = frappe.qb.from_(Discussion).select(Discussion.name).where(clause).limit(1)

		# This should execute without error
		result = query.run()
		self.assertIsInstance(result, (list, tuple))


class TestDiscussionPermissions(GameplanTestCase):
	def setUp(self):
		super().setUp()
		self.community = create_community("Discussion Perm Community")
		self.space = create_space("Discussion Perm Space", self.community)

	def _discussion(self):
		doc = frappe.new_doc("GP Discussion")
		doc.title = "Sample discussion"
		doc.project = self.space.name
		return doc

	def test_member_can_access(self):
		self.assertTrue(has_permission(self._discussion(), "read", self.member.name))
		self.assertTrue(has_permission(self._discussion(), "write", self.member.name))

	def test_guest_without_access_denied(self):
		self.assertFalse(has_permission(self._discussion(), "read", self.guest.name))

	def test_guest_with_access_allowed(self):
		grant_guest_access(self.guest, self.space)
		self.assertTrue(has_permission(self._discussion(), "read", self.guest.name))


class DiscussionLifecycleTestCase(GameplanTestCase):
	"""World: a public space in a community both members belong to, holding one
	discussion written by `member`. `guest` is granted the space, so every "a guest
	cannot do this" assertion is about the lifecycle rule, not about access."""

	def setUp(self):
		super().setUp()
		self.community = create_community("Acme", members=[self.member, self.second_member])
		self.space = create_space("Engineering", self.community)
		self.discussion = create_discussion("Welcome thread", self.space, owner=self.member)
		grant_guest_access(self.guest, self.space)

	def stored(self):
		"""The discussion as it is in the database, not the in-memory copy under test."""
		return frappe.get_doc("GP Discussion", self.discussion.name)

	def comment_as(self, user, content="A reply"):
		"""Insert a comment as `user`.

		All the bookkeeping under test (participants, last post) keys off the comment's
		`owner`, and only an insert running as that user sets it — hence this rather than
		`create_comment(..., owner=...)`, which rewrites the owner after the side effects
		have already run.
		"""
		with self.as_user(user):
			return frappe.get_doc(
				doctype="GP Comment",
				reference_doctype="GP Discussion",
				reference_name=self.discussion.name,
				content=content,
			).insert()

	def poll_as(self, user, title="Ship on Friday?"):
		with self.as_user(user):
			return create_poll(title, self.discussion)

	def delete_as(self, doc, user):
		with self.as_user(user):
			frappe.delete_doc(doc.doctype, doc.name)

	def activities(self, action=None):
		filters = {"reference_doctype": "GP Discussion", "reference_name": self.discussion.name}
		if action:
			filters["action"] = action
		return frappe.get_all(
			"GP Activity", filters=filters, fields=["action", "user"], order_by="creation asc"
		)


class TestPinning(DiscussionLifecycleTestCase):
	"""Pinning keeps a discussion at the top of a list. Its scope decides which list:
	"Category" (the schema's name for the community) or "Space"."""

	def pin(self, user, **kwargs):
		with self.as_user(user):
			frappe.get_doc("GP Discussion", self.discussion.name).pin_discussion(**kwargs)

	def unpin(self, user):
		with self.as_user(user):
			frappe.get_doc("GP Discussion", self.discussion.name).unpin_discussion()

	def test_pinning_records_who_pinned_it_and_when(self):
		self.pin(self.member)

		discussion = self.stored()
		self.assertTrue(discussion.pinned_at)
		self.assertEqual(discussion.pinned_by, self.member.name)

	def test_pin_defaults_to_the_whole_community(self):
		self.pin(self.member)

		self.assertEqual(self.stored().pin_scope, "Category")

	def test_pin_can_be_scoped_to_the_space(self):
		self.pin(self.member, pin_scope="Space")

		self.assertEqual(self.stored().pin_scope, "Space")

	def test_pinning_logs_an_activity(self):
		self.pin(self.member)

		self.assertEqual(self.activities(), [{"action": "Discussion Pinned", "user": self.member.name}])

	def test_pinning_an_already_pinned_discussion_changes_nothing(self):
		self.pin(self.member)
		pinned_at = self.stored().pinned_at

		self.pin(self.second_member, pin_scope="Space")

		discussion = self.stored()
		self.assertEqual(discussion.pinned_by, self.member.name)
		self.assertEqual(discussion.pinned_at, pinned_at)
		self.assertEqual(discussion.pin_scope, "Category")
		self.assertEqual(len(self.activities("Discussion Pinned")), 1)

	def test_unpinning_clears_the_pin_and_logs_it(self):
		self.pin(self.member, pin_scope="Space")

		self.unpin(self.second_member)

		discussion = self.stored()
		self.assertIsNone(discussion.pinned_at)
		self.assertIsNone(discussion.pinned_by)
		self.assertIsNone(discussion.pin_scope)
		self.assertEqual([a.action for a in self.activities()], ["Discussion Pinned", "Discussion Unpinned"])

	def test_unpinning_a_discussion_that_is_not_pinned_does_nothing(self):
		self.unpin(self.member)

		self.assertEqual(self.activities(), [])

	def test_any_member_of_the_space_can_pin_someone_elses_discussion(self):
		self.pin(self.second_member)

		self.assertEqual(self.stored().pinned_by, self.second_member.name)

	def test_a_guest_cannot_pin(self):
		with self.as_user(self.guest):
			with self.assertRaises(frappe.PermissionError):
				frappe.get_doc("GP Discussion", self.discussion.name).pin_discussion()

		self.assertIsNone(self.stored().pinned_at)

	def test_pinning_is_not_a_post(self):
		"""Pinning must not bump the thread in the feed — that order is about posts."""
		before = self.stored().last_post_at

		self.pin(self.member)

		self.assertEqual(self.stored().last_post_at, before)


class TestClosingAndReopening(DiscussionLifecycleTestCase):
	"""Closing a discussion stops new posts; anyone who can edit it can reopen it."""

	def close(self, user):
		with self.as_user(user):
			frappe.get_doc("GP Discussion", self.discussion.name).close_discussion()

	def reopen(self, user):
		with self.as_user(user):
			frappe.get_doc("GP Discussion", self.discussion.name).reopen_discussion()

	def test_closing_records_who_closed_it_and_when(self):
		self.close(self.member)

		discussion = self.stored()
		self.assertTrue(discussion.closed_at)
		self.assertEqual(discussion.closed_by, self.member.name)

	def test_closing_logs_an_activity(self):
		self.close(self.second_member)

		self.assertEqual(
			self.activities(), [{"action": "Discussion Closed", "user": self.second_member.name}]
		)

	def test_a_closed_discussion_rejects_new_comments(self):
		self.close(self.member)

		with self.assertRaises(frappe.ValidationError):
			self.comment_as(self.second_member)

	def test_a_closed_discussion_rejects_new_polls(self):
		"""A poll is a post in the thread like a comment is, so the same rule applies.
		The UI hides the whole composer when a discussion is closed, which left this
		unenforced on the server."""
		self.close(self.member)

		with self.assertRaises(frappe.ValidationError):
			self.poll_as(self.second_member)

	def test_closing_twice_keeps_the_first_close(self):
		self.close(self.member)
		closed_at = self.stored().closed_at

		self.close(self.second_member)

		discussion = self.stored()
		self.assertEqual(discussion.closed_by, self.member.name)
		self.assertEqual(discussion.closed_at, closed_at)
		self.assertEqual(len(self.activities("Discussion Closed")), 1)

	def test_reopening_clears_the_close_and_logs_it(self):
		self.close(self.member)

		self.reopen(self.second_member)

		discussion = self.stored()
		self.assertIsNone(discussion.closed_at)
		self.assertIsNone(discussion.closed_by)
		self.assertEqual([a.action for a in self.activities()], ["Discussion Closed", "Discussion Reopened"])

	def test_reopening_lets_members_comment_again(self):
		self.close(self.member)
		self.reopen(self.member)

		comment = self.comment_as(self.second_member)

		self.assertEqual(str(self.stored().last_post), str(comment.name))

	def test_reopening_an_open_discussion_does_nothing(self):
		self.reopen(self.member)

		self.assertEqual(self.activities(), [])

	def test_a_guest_cannot_close(self):
		with self.as_user(self.guest):
			with self.assertRaises(frappe.PermissionError):
				frappe.get_doc("GP Discussion", self.discussion.name).close_discussion()

		self.assertIsNone(self.stored().closed_at)

	def test_closing_keeps_the_comments_that_are_already_there(self):
		comment = self.comment_as(self.second_member)

		self.close(self.member)

		self.assertEqual(self.stored().comments_count, 1)
		self.assertTrue(frappe.db.exists("GP Comment", comment.name))


class TestCommentsCount(DiscussionLifecycleTestCase):
	"""`comments_count` is the number of posts in the thread — comments and polls both."""

	def test_a_new_discussion_has_no_comments(self):
		self.assertEqual(self.stored().comments_count, 0)

	def test_adding_comments_increments_the_count(self):
		self.comment_as(self.second_member)
		self.assertEqual(self.stored().comments_count, 1)

		self.comment_as(self.member)
		self.assertEqual(self.stored().comments_count, 2)

	def test_deleting_a_comment_decrements_the_count(self):
		first = self.comment_as(self.second_member)
		self.comment_as(self.member)

		self.delete_as(first, self.second_member)

		self.assertEqual(self.stored().comments_count, 1)

	def test_deleting_the_only_comment_returns_the_count_to_zero(self):
		comment = self.comment_as(self.second_member)

		self.delete_as(comment, self.second_member)

		self.assertEqual(self.stored().comments_count, 0)

	def test_a_poll_counts_as_a_post(self):
		self.comment_as(self.second_member)
		self.poll_as(self.member)

		self.assertEqual(self.stored().comments_count, 2)

	def test_editing_a_comment_does_not_change_the_count(self):
		comment = self.comment_as(self.second_member)

		with self.as_user(self.second_member):
			comment.content = "<p>Edited reply</p>"
			comment.save()

		self.assertEqual(self.stored().comments_count, 1)


class TestLastPost(DiscussionLifecycleTestCase):
	"""`last_post_*` is what the feed sorts and previews by: the newest post in the
	thread, or the discussion itself while nobody has replied."""

	def assert_last_post_is(self, post, post_type, by):
		discussion = self.stored()
		self.assertEqual(discussion.last_post_type, post_type)
		self.assertEqual(str(discussion.last_post), str(post.name))
		self.assertEqual(discussion.last_post_by, by.name)
		self.assertEqual(get_datetime(discussion.last_post_at), get_datetime(post.creation))

	def test_a_new_discussion_is_its_own_last_post(self):
		discussion = self.stored()

		# "no last post" is falsy either way: an unset Select stores "", clearing one
		# stores NULL. What reads these (get_discussions) checks `if not last_post`.
		self.assertFalse(discussion.last_post)
		self.assertFalse(discussion.last_post_type)
		self.assertTrue(discussion.last_post_at)

	def test_a_comment_becomes_the_last_post(self):
		comment = self.comment_as(self.second_member)

		self.assert_last_post_is(comment, "GP Comment", self.second_member)

	def test_a_poll_becomes_the_last_post(self):
		poll = self.poll_as(self.second_member)

		self.assert_last_post_is(poll, "GP Poll", self.second_member)

	def test_the_newest_post_wins(self):
		self.comment_as(self.second_member)
		latest = self.comment_as(self.member, "The last word")

		self.assert_last_post_is(latest, "GP Comment", self.member)

	def test_deleting_the_newest_comment_falls_back_to_the_previous_one(self):
		first = self.comment_as(self.second_member)
		latest = self.comment_as(self.member, "The last word")

		self.delete_as(latest, self.member)

		self.assert_last_post_is(first, "GP Comment", self.second_member)

	def test_deleting_the_only_comment_returns_the_discussion_to_being_its_own_last_post(self):
		"""Otherwise the feed keeps sorting and attributing the thread by a reply that
		no longer exists."""
		comment = self.comment_as(self.second_member)

		self.delete_as(comment, self.second_member)

		discussion = self.stored()
		self.assertFalse(discussion.last_post)
		self.assertFalse(discussion.last_post_type)
		self.assertEqual(discussion.last_post_by, self.member.name)
		self.assertEqual(get_datetime(discussion.last_post_at), get_datetime(discussion.creation))

	def test_deleting_the_only_poll_returns_the_discussion_to_being_its_own_last_post(self):
		poll = self.poll_as(self.second_member)

		self.delete_as(poll, self.second_member)

		discussion = self.stored()
		self.assertFalse(discussion.last_post)
		self.assertFalse(discussion.last_post_type)
		self.assertEqual(discussion.last_post_by, self.member.name)
		self.assertEqual(get_datetime(discussion.last_post_at), get_datetime(discussion.creation))

	def test_the_feed_shows_the_author_while_nobody_has_replied(self):
		with self.as_user(self.member):
			[row] = [d for d in get_discussions(filters={"project": self.space.name}, limit=20)]

		self.assertEqual(row.last_post_by, self.member.name)


class TestParticipants(DiscussionLifecycleTestCase):
	"""`participants_count` is how many distinct people have posted in the thread,
	counting the author of the discussion itself."""

	def test_the_author_is_the_only_participant_at_first(self):
		self.assertEqual(self.stored().participants_count, 1)

	def test_a_commenter_becomes_a_participant(self):
		self.comment_as(self.second_member)

		self.assertEqual(self.stored().participants_count, 2)

	def test_commenting_twice_counts_once(self):
		self.comment_as(self.second_member)
		self.comment_as(self.second_member, "Once more")

		self.assertEqual(self.stored().participants_count, 2)

	def test_the_author_replying_to_themselves_adds_nobody(self):
		self.comment_as(self.member)

		self.assertEqual(self.stored().participants_count, 1)

	def test_a_poll_author_is_a_participant(self):
		self.poll_as(self.second_member)

		self.assertEqual(self.stored().participants_count, 2)

	def test_a_guest_who_comments_is_a_participant(self):
		self.comment_as(self.guest)

		self.assertEqual(self.stored().participants_count, 2)

	def test_deleting_someones_only_comment_drops_them(self):
		comment = self.comment_as(self.second_member)
		self.assertEqual(self.stored().participants_count, 2)

		self.delete_as(comment, self.second_member)

		self.assertEqual(self.stored().participants_count, 1)

	def test_deleting_one_of_two_comments_keeps_the_participant(self):
		first = self.comment_as(self.second_member)
		self.comment_as(self.second_member, "Once more")

		self.delete_as(first, self.second_member)

		self.assertEqual(self.stored().participants_count, 2)


class DiscussionFeedTestCase(GameplanTestCase):
	"""World for `get_discussions`, the query behind every discussion feed.

	One community with two public spaces. `member` joined the first, `second_member`
	joined the second — so every space has a member, and exactly one of them is the
	reader. That asymmetry is deliberate: a feed scoped "by membership" and a feed
	scoped "by *anyone's* membership" only differ when someone else has joined
	somewhere the reader has not.
	"""

	def setUp(self):
		super().setUp()
		self.community = create_community("Feed Co", members=[self.member, self.second_member])
		self.space = create_space("Joined", self.community, members=[self.member])
		self.other_space = create_space("Not joined", self.community, members=[self.second_member])

	def feed(self, user, limit=20, **kwargs):
		"""`get_discussions` as `user`, scoped to this community unless told otherwise."""
		filters = dict(kwargs.pop("filters", None) or {})
		filters.setdefault("team", self.community.name)
		with self.as_user(user):
			return get_discussions(filters=filters, limit=limit, **kwargs)

	def feed_names(self, user, **kwargs):
		return [str(d.name) for d in self.feed(user, **kwargs)]

	def post(self, user, title, space=None, content="<p>Body</p>"):
		"""Start a discussion as `user`.

		Inserted through the session rather than `create_discussion(owner=...)`: both the
		owner and the unread records that get built on insert key off the acting user, and
		rewriting the owner afterwards happens too late for the unread fan-out.
		"""
		return self._insert_as(
			user,
			doctype="GP Discussion",
			title=title,
			project=(space or self.space).name,
			content=content,
		)

	def comment(self, discussion, user, content="<p>A reply</p>"):
		return self._insert_as(
			user,
			doctype="GP Comment",
			reference_doctype="GP Discussion",
			reference_name=discussion.name,
			content=content,
		)

	def _insert_as(self, user, **fields):
		with self.as_user(user):
			return frappe.get_doc(**fields).insert()

	def rows_by_name(self, user):
		return {str(row.name): row for row in self.feed(user)}


class TestFeedPaging(DiscussionFeedTestCase):
	"""`limit` and `start` page the feed; `has_next_page` tells the client whether to
	ask for another page. All three come out of one deliberately over-fetched row."""

	def setUp(self):
		super().setUp()
		self.threads = [self.post(self.member, f"Thread {index}") for index in range(3)]

	def test_a_full_page_reports_that_more_are_waiting(self):
		rows = self.feed(self.member, limit=2)

		self.assertEqual(len(rows), 2)
		self.assertIs(frappe.response["has_next_page"], True)

	def test_the_last_page_reports_that_nothing_is_waiting(self):
		"""Exactly `limit` rows left is the case that decides the over-fetch: the extra
		row is what separates "a full page" from "a full page and then some"."""
		rows = self.feed(self.member, limit=3)

		self.assertEqual(len(rows), 3)
		self.assertIs(frappe.response["has_next_page"], False)

	def test_start_skips_the_rows_already_shown(self):
		names = [str(thread.name) for thread in self.threads]

		first_page = self.feed_names(self.member, limit=2, order_by="name asc")
		second_page = self.feed_names(self.member, limit=2, start=2, order_by="name asc")

		self.assertEqual(first_page, names[:2])
		self.assertEqual(second_page, names[2:])

	def test_a_start_that_is_not_a_number_pages_from_the_beginning(self):
		"""`start` is spliced into OFFSET. It used to go there as whatever string the
		client sent — `start="1); DROP TABLE ..."` landed in the statement verbatim and
		the database refused the whole query — so anything that is not a number now
		means "no offset" rather than a 500.
		"""
		names = [str(thread.name) for thread in self.threads]

		page = self.feed_names(
			self.member, limit=2, order_by="name asc", start="1); DROP TABLE `tabGP Discussion`; --"
		)

		self.assertEqual(page, names[:2])

	def test_a_negative_start_pages_from_the_beginning(self):
		names = [str(thread.name) for thread in self.threads]

		page = self.feed_names(self.member, limit=2, order_by="name asc", start=-5)

		self.assertEqual(page, names[:2])


class TestOffsetParsing(unittest.TestCase):
	"""`parse_offset` is tested apart from the feed because the case that matters most —
	a negative offset — is a syntax error on MariaDB but silently equals zero on the
	SQLite bench, so a query-level test cannot tell the clamp from its absence.
	"""

	def test_a_number_is_kept(self):
		self.assertEqual(parse_offset("2"), 2)

	def test_sql_dressed_up_as_a_number_becomes_no_offset(self):
		self.assertEqual(parse_offset("1); DROP TABLE `tabGP Discussion`; --"), 0)
		self.assertEqual(parse_offset("0 UNION SELECT 1"), 0)

	def test_a_negative_offset_is_clamped(self):
		self.assertEqual(parse_offset(-5), 0)

	def test_no_offset_at_all_is_the_first_page(self):
		self.assertEqual(parse_offset(None), 0)


class TestFeedFilterInput(DiscussionFeedTestCase):
	"""`filters` reaches the query builder as the client sent it, so the endpoint has to
	answer for the shapes a client can send."""

	def test_a_filter_value_carrying_sql_is_matched_as_text(self):
		"""Filter values are escaped by the query builder, so a value with a quote and a
		tautology in it is a title nobody has, not a clause that widens the feed.
		"""
		self.post(self.member, "Ordinary thread")

		self.assertEqual(self.feed_names(self.member, filters={"title": "x' OR 1=1 -- "}), [])

	def test_a_filters_argument_that_is_not_a_mapping_is_refused(self):
		"""`feed_type` and `participator` are lifted out of `filters` by key, so a JSON
		list used to blow up on `.pop()` — an unhandled 500 on a whitelisted endpoint.
		"""
		with self.as_user(self.member), self.assertRaises(frappe.ValidationError):
			# Straight to the endpoint: `feed()` normalises filters into a dict, which is
			# exactly the shape this test needs to get past.
			get_discussions(filters='["name", "asc"]', limit=20)


class TestEmptyFeed(DiscussionFeedTestCase):
	def test_a_feed_with_nothing_in_it_is_an_empty_list(self):
		"""The enrichment steps run in sequence and hand their result to the next one, so
		an empty feed is the case where a dropped return value blows up the whole endpoint."""
		self.assertEqual(self.feed(self.member), [])


class TestFeedUnreadCounts(DiscussionFeedTestCase):
	"""Every row carries `unread`: how many posts in that thread this reader has not
	seen. It is per-reader, so it must never be assembled from anyone else's records."""

	def test_the_author_has_nothing_to_catch_up_on_but_everyone_else_does(self):
		self.post(self.second_member, "Fresh thread")

		[author_row] = self.feed(self.second_member)
		[reader_row] = self.feed(self.member)

		self.assertEqual(author_row.unread, 0)
		self.assertEqual(reader_row.unread, 1)

	def test_each_new_post_adds_to_the_count(self):
		discussion = self.post(self.second_member, "Fresh thread")
		self.comment(discussion, self.second_member)

		[row] = self.feed(self.member)

		self.assertEqual(row.unread, 2)

	def test_reading_a_thread_returns_its_count_to_zero(self):
		discussion = self.post(self.second_member, "Fresh thread")

		GPUnreadRecord.mark_discussion_as_read_for_user(str(discussion.name), self.member.name)

		[row] = self.feed(self.member)
		self.assertEqual(row.unread, 0)


class TestFollowingFeed(DiscussionFeedTestCase):
	""" "Following" is scoped by space membership — the spaces *this* reader joined."""

	def test_it_shows_only_threads_in_spaces_the_reader_joined(self):
		joined = self.post(self.member, "In the space I joined", self.space)
		elsewhere = self.post(self.member, "In a space someone else joined", self.other_space)

		names = self.feed_names(self.member, filters={"feed_type": "following"})

		self.assertIn(str(joined.name), names)
		self.assertNotIn(str(elsewhere.name), names)


class TestUnreadFeed(DiscussionFeedTestCase):
	""" "Unread" is scoped by this reader's own outstanding unread records."""

	def setUp(self):
		super().setUp()
		self.theirs = self.post(self.second_member, "New to me")
		self.mine = self.post(self.member, "Written by me")

	def unread_feed(self):
		return self.feed_names(self.member, filters={"feed_type": "unread"})

	def test_it_shows_a_thread_the_reader_has_not_seen(self):
		self.assertIn(str(self.theirs.name), self.unread_feed())

	def test_it_hides_a_thread_the_reader_has_nothing_outstanding_in(self):
		"""The reader wrote this one, so only *other* people have unread records for it."""
		self.assertNotIn(str(self.mine.name), self.unread_feed())

	def test_reading_a_thread_drops_it_from_the_feed(self):
		GPUnreadRecord.mark_discussion_as_read_for_user(str(self.theirs.name), self.member.name)

		self.assertNotIn(str(self.theirs.name), self.unread_feed())


class TestParticipatingFeed(DiscussionFeedTestCase):
	""" "Participating" is the threads the reader started or replied to."""

	def setUp(self):
		super().setUp()
		self.started = self.post(self.member, "I started this")
		self.replied_to = self.post(self.second_member, "Someone else started this")
		self.comment(self.replied_to, self.member)
		self.untouched = self.post(self.second_member, "Nothing to do with me")
		self.comment(self.untouched, self.second_member)

	def participating(self):
		return self.feed_names(self.member, filters={"feed_type": "participating"})

	def test_it_shows_threads_the_reader_started(self):
		self.assertIn(str(self.started.name), self.participating())

	def test_it_shows_threads_the_reader_replied_to(self):
		self.assertIn(str(self.replied_to.name), self.participating())

	def test_it_hides_threads_only_other_people_touched(self):
		self.assertNotIn(str(self.untouched.name), self.participating())

	def test_the_default_feed_is_not_filtered_by_participation(self):
		self.assertIn(str(self.untouched.name), self.feed_names(self.member))


class TestFeedOngoingPolls(DiscussionFeedTestCase):
	"""Each row carries the polls still open in that thread, so the feed can render a
	vote prompt without a second request."""

	def test_a_thread_carries_its_own_polls_and_nobody_elses(self):
		with_poll = self.post(self.member, "Has a poll")
		without_poll = self.post(self.member, "Has no poll")
		poll = create_poll("Ship on Friday?", with_poll)

		rows = self.rows_by_name(self.member)

		self.assertEqual([str(p.name) for p in rows[str(with_poll.name)].ongoing_polls], [str(poll.name)])
		self.assertEqual(rows[str(without_poll.name)].ongoing_polls, [])

	def test_a_poll_that_has_stopped_is_no_longer_ongoing(self):
		discussion = self.post(self.member, "Has a stopped poll")
		poll = create_poll("Ship on Friday?", discussion)
		frappe.db.set_value("GP Poll", poll.name, "stopped_at", "2020-01-01 00:00:00", update_modified=False)

		[row] = self.feed(self.member)

		self.assertEqual(row.ongoing_polls, [])

	def test_the_feed_and_the_ballot_close_at_the_same_instant(self):
		"""The feed and the poll doctype are two readers of one rule, so they have to
		agree microsecond for microsecond: while the feed still offers a poll the ballot
		must still take a vote, and the instant it stops offering it the ballot must
		refuse. They used to disagree at exactly `stopped_at` — the feed hid a poll the
		doctype would happily have recorded a vote on.
		"""
		discussion = self.post(self.member, "Has a poll about to stop")
		poll = create_poll("Ship on Friday?", discussion)
		frappe.db.set_value("GP Poll", poll.name, "stopped_at", STOP_INSTANT, update_modified=False)
		poll.reload()

		with frozen_clock(STOP_INSTANT - timedelta(microseconds=1)):
			[still_open] = self.feed(self.member)
			with self.as_user(self.member):
				poll.submit_vote("Yes")

		with frozen_clock(STOP_INSTANT):
			[now_closed] = self.feed(self.member)
			with self.as_user(self.member), self.assertRaises(frappe.ValidationError):
				poll.submit_vote("No")

		self.assertEqual([str(p.name) for p in still_open.ongoing_polls], [str(poll.name)])
		self.assertEqual(now_closed.ongoing_polls, [])


class TestFeedSorting(DiscussionFeedTestCase):
	"""`order_by` comes straight off the query string and is spliced into the query, so
	it is checked against the sorts the feed actually offers before it gets there."""

	def setUp(self):
		super().setUp()
		self.older = self.post(self.member, "Older")
		self.newer = self.post(self.member, "Newer")
		# Two posts a few microseconds apart would sort correctly by luck; fixed stamps
		# make "newest first" mean something.
		self.stamp(self.older, "2024-01-01 00:00:00")
		self.stamp(self.newer, "2024-06-01 00:00:00")

	def stamp(self, discussion, last_post_at):
		frappe.db.set_value(
			"GP Discussion", discussion.name, "last_post_at", last_post_at, update_modified=False
		)

	def test_newest_first_is_the_default(self):
		self.assertEqual(self.feed_names(self.member), [str(self.newer.name), str(self.older.name)])

	def test_oldest_first_reverses_the_feed(self):
		names = self.feed_names(self.member, order_by="last_post_at asc")

		self.assertEqual(names, [str(self.older.name), str(self.newer.name)])

	def test_every_sort_the_app_asks_for_is_accepted(self):
		"""The three sorts the feed's Select offers, the pinned strip's own sort, and the
		upper-case spelling frappe-ui's OrderBy type also allows."""
		for order_by in (
			"last_post_at desc",
			"last_post_at asc",
			"creation desc",
			"pinned_at desc",
			"last_post_at DESC",
		):
			with self.subTest(order_by=order_by):
				self.assertEqual(len(self.feed(self.member, order_by=order_by)), 2)

	def test_a_bare_field_sorts_newest_first(self):
		"""A directionless `order_by` is what raised the original 500. It is a shape
		Frappe's own query engine accepts and reads as descending
		(`frappe.database.query.Engine._validate_order_by`), so it keeps that meaning
		here instead of being rejected.
		"""
		names = self.feed_names(self.member, order_by="last_post_at")

		self.assertEqual(names, [str(self.newer.name), str(self.older.name)])

	def test_a_field_the_feed_does_not_sort_by_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			self.feed(self.member, order_by="content desc")

	def test_a_direction_that_is_not_asc_or_desc_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			self.feed(self.member, order_by="last_post_at sideways")

	def test_a_multi_token_sort_is_refused_rather_than_being_spliced_in(self):
		"""Three tokens never burst the old `split(" ", 1)` — maxsplit swept everything
		after the field into the direction half, so this reached the database as
		`ORDER BY "last_post_at" desc, name asc`: arbitrary trailing SQL, quietly executed.
		"""
		with self.assertRaises(frappe.ValidationError):
			self.feed(self.member, order_by="last_post_at desc, name asc")


class TestFeedLastPostPreview(DiscussionFeedTestCase):
	"""Each row carries a one-line preview of the newest post: a comment's text, a
	poll's title, or the discussion's own body while nobody has replied."""

	def test_it_previews_the_last_comment(self):
		discussion = self.post(self.member, "Thread")
		self.comment(discussion, self.second_member, "<p>The latest reply</p>")

		[row] = self.feed(self.member)

		self.assertEqual(row.last_comment_content, "The latest reply")

	def test_it_names_the_last_poll(self):
		discussion = self.post(self.member, "Thread")
		with self.as_user(self.second_member):
			create_poll("Ship on Friday?", discussion)

		[row] = self.feed(self.member)

		self.assertEqual(row.last_poll_title, "Ship on Friday?")

	def test_a_thread_with_no_replies_previews_its_own_body(self):
		self.post(self.member, "Thread", content="<p>The opening post</p>")

		[row] = self.feed(self.member)

		self.assertEqual(row.last_comment_content, "The opening post")
