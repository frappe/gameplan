# Copyright (c) 2023, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import get_datetime

from gameplan.gameplan.doctype.gp_discussion.api import (
	clause_discussions_commented_by_user,
	get_discussions,
)
from gameplan.gameplan.doctype.gp_discussion.gp_discussion import has_permission
from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import (
	create_community,
	create_discussion,
	create_guest,
	create_member,
	create_poll,
	create_space,
	grant_guest_access,
)


class TestDiscussions(FrappeTestCase):
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

		# Cleanup
		frappe.db.rollback()


class TestDiscussionPermissions(FrappeTestCase):
	def setUp(self):
		self.member = create_member("test_disc_member@example.com")
		self.guest = create_guest("test_disc_guest@example.com")
		self.team = create_community("Discussion Perm Team")
		self.project = create_space("Discussion Perm Project", self.team.name)

	def tearDown(self):
		frappe.set_user("Administrator")

	def _discussion(self):
		doc = frappe.new_doc("GP Discussion")
		doc.title = "Sample discussion"
		doc.project = self.project.name
		return doc

	def test_member_can_access(self):
		self.assertTrue(has_permission(self._discussion(), "read", self.member.name))
		self.assertTrue(has_permission(self._discussion(), "write", self.member.name))

	def test_guest_without_access_denied(self):
		self.assertFalse(has_permission(self._discussion(), "read", self.guest.name))

	def test_guest_with_access_allowed(self):
		grant_guest_access(self.guest.name, self.project.name)
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
