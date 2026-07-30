# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""Polls: casting and retracting votes, stopping a poll, and who may do either.

A poll is content that lives inside a discussion, so it takes that discussion's space
for access: everyone who can reach the space may vote, and nobody else can even see it.
Voting itself is participation (like reacting), which is why the vote methods are the
gate rather than the `write` permission — see GPPoll.save_after_voting. That save skips
permissions, so the methods first restore all poll state from storage
(GPPoll.discard_client_state); TestTamperedVotePayload locks that invariant.

The other half of that rule is that a poll's ballot and lifecycle belong to its author:
`write` alone must not let another member stop a poll or rewrite its votes, whether they
go through `stop_poll` or straight at the document — TestPollFieldProtection locks that.
"""

from contextlib import contextmanager
from datetime import timedelta
from unittest.mock import patch

import frappe
import frappe.utils.data
from frappe.utils import add_days, get_datetime, now_datetime

from gameplan.gameplan.doctype.gp_poll.gp_poll import GPPoll
from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import (
	create_community,
	create_discussion,
	create_poll,
	create_space,
	declared_http_methods,
	grant_guest_access,
)

# A fixed instant to stop a poll at. Far enough ahead that the real clock never reaches
# it, so a test that forgets to freeze the clock fails instead of passing by accident.
STOP_INSTANT = get_datetime("2099-01-01 09:00:00.500000")


@contextmanager
def frozen_clock(instant):
	"""Hold the whole request at `instant`.

	A poll closes on a microsecond boundary, and a test that waited for real time to
	pass could only ever observe one side of it. `frappe.utils` re-exports
	`now_datetime` under its own name, so both that binding and the definition in
	`frappe.utils.data` (which `frappe.utils.now` calls) have to be replaced before
	every reader of the clock agrees on where the boundary is.
	"""
	with (
		patch.object(frappe.utils, "now_datetime", return_value=instant),
		patch.object(frappe.utils.data, "now_datetime", return_value=instant),
	):
		yield


class PollTestCase(GameplanTestCase):
	"""One public space with a discussion, and a poll in it owned by `member`."""

	def setUp(self):
		super().setUp()
		self.community = create_community("Poll Community", members=[self.member, self.second_member])
		self.space = create_space("Poll Space", self.community)
		self.discussion = create_discussion("Poll thread", self.space, owner=self.member)

	def poll(self, **kwargs):
		kwargs.setdefault("owner", self.member)
		return create_poll("Ship on Friday?", self.discussion, **kwargs)

	def option(self, poll, title):
		return next(option for option in poll.options if option.title == title)

	def vote(self, poll, user, option):
		with self.as_user(user):
			poll.submit_vote(option)
		poll.reload()
		return poll


class TestPollVoting(PollTestCase):
	def test_vote_is_recorded_against_the_voter_and_updates_the_tally(self):
		poll = self.poll()

		self.vote(poll, self.second_member, "Yes")

		self.assertEqual(poll.total_votes, 1)
		self.assertEqual([(v.user, v.option) for v in poll.votes], [(self.second_member.name, "Yes")])
		self.assertEqual(self.option(poll, "Yes").votes, 1)
		self.assertEqual(self.option(poll, "Yes").percentage, 100)
		self.assertEqual(self.option(poll, "No").votes, 0)
		self.assertEqual(self.option(poll, "No").percentage, 0)

	def test_tally_splits_across_voters(self):
		poll = self.poll()

		self.vote(poll, self.member, "Yes")
		self.vote(poll, self.second_member, "No")

		self.assertEqual(poll.total_votes, 2)
		self.assertEqual(self.option(poll, "Yes").percentage, 50)
		self.assertEqual(self.option(poll, "No").percentage, 50)

	def test_voting_again_replaces_the_previous_answer(self):
		"""A voter may change their mind: one answer per voter, and it is the latest one."""
		poll = self.poll()
		self.vote(poll, self.member, "Yes")

		self.vote(poll, self.member, "No")

		self.assertEqual(poll.total_votes, 1)
		self.assertEqual([(v.user, v.option) for v in poll.votes], [(self.member.name, "No")])
		self.assertEqual(self.option(poll, "Yes").votes, 0)
		self.assertEqual(self.option(poll, "Yes").percentage, 0)
		self.assertEqual(self.option(poll, "No").votes, 1)
		self.assertEqual(self.option(poll, "No").percentage, 100)

	def test_repeating_the_same_answer_changes_nothing(self):
		poll = self.poll()
		self.vote(poll, self.member, "Yes")

		self.vote(poll, self.member, "Yes")

		self.assertEqual(poll.total_votes, 1)
		self.assertEqual([(v.user, v.option) for v in poll.votes], [(self.member.name, "Yes")])

	def test_changing_a_vote_leaves_the_other_voters_alone(self):
		poll = self.poll()
		self.vote(poll, self.member, "Yes")
		self.vote(poll, self.second_member, "Yes")

		self.vote(poll, self.member, "No")

		self.assertEqual(poll.total_votes, 2)
		self.assertEqual(
			sorted((v.user, v.option) for v in poll.votes),
			sorted([(self.member.name, "No"), (self.second_member.name, "Yes")]),
		)
		self.assertEqual(self.option(poll, "Yes").votes, 1)
		self.assertEqual(self.option(poll, "No").votes, 1)
		self.assertEqual(self.option(poll, "Yes").percentage, 50)
		self.assertEqual(self.option(poll, "No").percentage, 50)

	def test_vote_for_an_option_that_does_not_exist_is_rejected(self):
		poll = self.poll()

		with self.as_user(self.member), self.assertRaises(frappe.ValidationError):
			poll.submit_vote("Maybe")

		poll.reload()
		self.assertEqual(poll.total_votes, 0)
		self.assertEqual(poll.votes, [])

	def test_duplicate_options_are_rejected_at_insert(self):
		with self.assertRaises(frappe.ValidationError):
			create_poll("Dupes", self.discussion, options=("Yes", "Yes"))

	def test_retract_vote_removes_only_the_callers_vote(self):
		poll = self.poll()
		self.vote(poll, self.member, "Yes")
		self.vote(poll, self.second_member, "No")

		with self.as_user(self.second_member):
			poll.retract_vote()
		poll.reload()

		self.assertEqual(poll.total_votes, 1)
		self.assertEqual([(v.user, v.option) for v in poll.votes], [(self.member.name, "Yes")])
		self.assertEqual(self.option(poll, "Yes").percentage, 100)
		self.assertEqual(self.option(poll, "No").votes, 0)

	def test_retracting_the_last_vote_clears_the_tally(self):
		poll = self.poll()
		self.vote(poll, self.member, "Yes")

		with self.as_user(self.member):
			poll.retract_vote()
		poll.reload()

		self.assertEqual(poll.total_votes, 0)
		self.assertEqual(poll.votes, [])
		self.assertEqual(self.option(poll, "Yes").votes, 0)
		self.assertEqual(self.option(poll, "Yes").percentage, 0)

	def test_retract_without_a_vote_is_a_no_op(self):
		poll = self.poll()
		self.vote(poll, self.member, "Yes")

		with self.as_user(self.second_member):
			poll.retract_vote()
		poll.reload()

		self.assertEqual(poll.total_votes, 1)


class TestAnonymousPoll(PollTestCase):
	def test_anonymous_vote_records_the_voter_but_not_their_choice(self):
		poll = self.poll(anonymous=1)

		self.vote(poll, self.second_member, "Yes")

		self.assertEqual(poll.total_votes, 1)
		self.assertEqual([(v.user, v.option) for v in poll.votes], [(self.second_member.name, None)])
		self.assertEqual(self.option(poll, "Yes").votes, 1)
		self.assertEqual(self.option(poll, "Yes").percentage, 100)

	def test_anonymous_poll_keeps_the_one_vote_per_user_guard(self):
		poll = self.poll(anonymous=1)
		self.vote(poll, self.member, "Yes")

		self.vote(poll, self.member, "No")

		self.assertEqual(poll.total_votes, 1)
		self.assertEqual(self.option(poll, "Yes").votes, 1)
		self.assertEqual(self.option(poll, "No").votes, 0)

	def test_anonymous_vote_cannot_be_retracted(self):
		poll = self.poll(anonymous=1)
		self.vote(poll, self.member, "Yes")

		with self.as_user(self.member), self.assertRaises(frappe.ValidationError):
			poll.retract_vote()

		poll.reload()
		self.assertEqual(poll.total_votes, 1)


class TestMultipleAnswerPoll(PollTestCase):
	"""`multiple_answers` lifts the one-vote guard to one vote per user *per option*.

	A percentage answers "how many of the people who voted picked this?", so it is a
	share of the voters, not of the answer rows. On a multiple-answer poll the shares can
	therefore add up to more than 100% — the standard for "select all that apply" — and
	they read against the UI's own label, "N answers from M people".
	"""

	def test_a_voter_can_pick_several_options(self):
		poll = self.poll(multiple_answers=1, options=("Yes", "No", "Later"))

		self.vote(poll, self.member, "Yes")
		self.vote(poll, self.member, "Later")

		self.assertEqual(poll.total_votes, 2)
		self.assertEqual(sorted(v.option for v in poll.votes if v.user == self.member.name), ["Later", "Yes"])
		self.assertEqual(self.option(poll, "Yes").votes, 1)
		self.assertEqual(self.option(poll, "Later").votes, 1)
		self.assertEqual(self.option(poll, "No").votes, 0)
		# The only voter picked both, so both are at 100% of the people who voted.
		self.assertEqual(self.option(poll, "Yes").percentage, 100)
		self.assertEqual(self.option(poll, "Later").percentage, 100)

	def test_percentages_are_a_share_of_the_voters_not_of_the_answers(self):
		poll = self.poll(multiple_answers=1, options=("Yes", "No", "Later"))

		self.vote(poll, self.member, "Yes")
		self.vote(poll, self.member, "Later")
		self.vote(poll, self.second_member, "Yes")

		# Three answers from two people: everyone picked "Yes", half also picked "Later".
		self.assertEqual(poll.total_votes, 3)
		self.assertEqual(self.option(poll, "Yes").percentage, 100)
		self.assertEqual(self.option(poll, "Later").percentage, 50)
		self.assertEqual(self.option(poll, "No").percentage, 0)

	def test_repeat_vote_for_the_same_option_is_ignored(self):
		poll = self.poll(multiple_answers=1)

		self.vote(poll, self.member, "Yes")
		self.vote(poll, self.member, "Yes")

		self.assertEqual(poll.total_votes, 1)
		self.assertEqual(self.option(poll, "Yes").votes, 1)

	def test_a_single_answer_can_be_retracted(self):
		poll = self.poll(multiple_answers=1)
		self.vote(poll, self.member, "Yes")
		self.vote(poll, self.member, "No")

		with self.as_user(self.member):
			poll.retract_vote(option="Yes")
		poll.reload()

		self.assertEqual([(v.user, v.option) for v in poll.votes], [(self.member.name, "No")])
		self.assertEqual(self.option(poll, "Yes").votes, 0)
		self.assertEqual(self.option(poll, "No").percentage, 100)

	def test_retract_without_an_option_drops_every_answer(self):
		poll = self.poll(multiple_answers=1)
		self.vote(poll, self.member, "Yes")
		self.vote(poll, self.member, "No")

		with self.as_user(self.member):
			poll.retract_vote()
		poll.reload()

		self.assertEqual(poll.votes, [])
		self.assertEqual(poll.total_votes, 0)

	def test_anonymous_multiple_answer_poll_is_rejected(self):
		with self.assertRaisesRegex(
			frappe.ValidationError,
			"Anonymous polls cannot allow multiple answers",
		):
			self.poll(anonymous=1, multiple_answers=1)


class TestStoppingAPoll(PollTestCase):
	def test_owner_can_stop_the_poll(self):
		poll = self.poll()

		with self.as_user(self.member):
			poll.stop_poll()
		poll.reload()

		self.assertIsNotNone(poll.stopped_at)

	def test_global_admin_can_stop_another_members_poll(self):
		poll = self.poll()

		with self.as_user(self.admin):
			poll.stop_poll()
		poll.reload()

		self.assertIsNotNone(poll.stopped_at)

	def test_community_admin_can_stop_another_members_poll(self):
		poll = self.poll()
		community = frappe.get_doc("GP Team", self.community.name)
		community.get_member(self.second_member.name).is_admin = 1
		community.save(ignore_permissions=True)

		with self.as_user(self.second_member):
			poll.stop_poll()
		poll.reload()

		self.assertIsNotNone(poll.stopped_at)

	def test_another_member_cannot_stop_the_poll(self):
		poll = self.poll()

		with self.as_user(self.second_member), self.assertRaises(frappe.PermissionError):
			poll.stop_poll()

		poll.reload()
		self.assertIsNone(poll.stopped_at)

	def test_outsider_cannot_stop_the_poll(self):
		poll = self.poll()

		with self.as_user(self.outsider), self.assertRaises(frappe.PermissionError):
			poll.stop_poll()

	def test_voting_on_a_stopped_poll_is_rejected(self):
		poll = self.poll()
		with self.as_user(self.member):
			poll.stop_poll()

		with self.as_user(self.second_member), self.assertRaises(frappe.ValidationError):
			poll.submit_vote("Yes")

		poll.reload()
		self.assertEqual(poll.total_votes, 0)

	def test_retracting_on_a_stopped_poll_is_rejected(self):
		poll = self.poll()
		self.vote(poll, self.member, "Yes")
		with self.as_user(self.member):
			poll.stop_poll()

		with self.as_user(self.member), self.assertRaises(frappe.ValidationError):
			poll.retract_vote()

		poll.reload()
		self.assertEqual(poll.total_votes, 1)

	def test_a_poll_set_to_end_later_still_accepts_votes(self):
		poll = self.poll()
		frappe.db.set_value("GP Poll", poll.name, "stopped_at", add_days(now_datetime(), 1))
		poll.reload()

		self.vote(poll, self.second_member, "Yes")

		self.assertEqual(poll.total_votes, 1)


class TestTheStopInstant(PollTestCase):
	"""`stopped_at` names the moment the poll stops, not the last moment it runs.

	`stop_poll` stamps it with the current time, so if that exact microsecond still
	counted as open a vote could land after the stop was recorded. The boundary is
	therefore inclusive, and the discussion feed reads the same rule — see
	TestFeedOngoingPolls.test_the_feed_and_the_ballot_close_at_the_same_instant.
	"""

	def stopping_poll(self):
		poll = self.poll()
		frappe.db.set_value("GP Poll", poll.name, "stopped_at", STOP_INSTANT, update_modified=False)
		poll.reload()
		return poll

	def test_a_vote_at_the_stop_instant_is_refused(self):
		poll = self.stopping_poll()

		with frozen_clock(STOP_INSTANT), self.as_user(self.second_member):
			with self.assertRaises(frappe.ValidationError):
				poll.submit_vote("Yes")

		poll.reload()
		self.assertEqual(poll.total_votes, 0)

	def test_a_vote_a_microsecond_earlier_is_accepted(self):
		"""The other side of the same boundary: closing it one tick early would end
		every poll before the instant it advertises."""
		poll = self.stopping_poll()

		with frozen_clock(STOP_INSTANT - timedelta(microseconds=1)), self.as_user(self.second_member):
			poll.submit_vote("Yes")

		poll.reload()
		self.assertEqual(poll.total_votes, 1)

	def test_a_retraction_at_the_stop_instant_is_refused(self):
		poll = self.stopping_poll()
		self.vote(poll, self.second_member, "Yes")

		with frozen_clock(STOP_INSTANT), self.as_user(self.second_member):
			with self.assertRaises(frappe.ValidationError):
				poll.retract_vote()

		poll.reload()
		self.assertEqual(poll.total_votes, 1)


class TestArchivedPoll(PollTestCase):
	def setUp(self):
		super().setUp()
		self.poll_doc = self.poll()

	def archive_space(self):
		self.space.reload()
		self.space.archive()

	def test_poll_in_an_archived_space_remains_readable(self):
		self.archive_space()

		with self.as_user(self.second_member):
			poll = frappe.get_doc("GP Poll", self.poll_doc.name)
			# frappe.get_doc runs no permission check of its own, so ask for one.
			poll.check_permission("read")

		self.assertEqual(poll.title, "Ship on Friday?")

	def test_cannot_vote_in_an_archived_space(self):
		self.archive_space()

		with (
			self.as_user(self.second_member),
			self.assertRaisesRegex(
				frappe.ValidationError,
				r"Space Poll Space is archived\. Cannot vote in polls\.",
			),
		):
			self.poll_doc.submit_vote("Yes")

		self.poll_doc.reload()
		self.assertEqual(self.poll_doc.total_votes, 0)

	def test_cannot_retract_a_vote_in_an_archived_space(self):
		self.vote(self.poll_doc, self.second_member, "Yes")
		self.archive_space()

		with (
			self.as_user(self.second_member),
			self.assertRaisesRegex(
				frappe.ValidationError,
				r"Space Poll Space is archived\. Cannot retract votes from polls\.",
			),
		):
			self.poll_doc.retract_vote()

		self.poll_doc.reload()
		self.assertEqual(
			[(vote.user, vote.option) for vote in self.poll_doc.votes],
			[(self.second_member.name, "Yes")],
		)

	def test_cannot_stop_a_poll_in_an_archived_space(self):
		self.archive_space()

		with (
			self.as_user(self.member),
			self.assertRaisesRegex(
				frappe.ValidationError,
				r"Space Poll Space is archived\. Cannot stop polls\.",
			),
		):
			self.poll_doc.stop_poll()

		self.poll_doc.reload()
		self.assertIsNone(self.poll_doc.stopped_at)


class TestTamperedVotePayload(PollTestCase):
	"""A vote may carry nothing but the vote.

	The v2 document-method route loads stored state, but participants can invoke these
	methods through Gameplan's interaction-level `write` permission and the vote save
	deliberately runs with `ignore_permissions`. These tests call the same public methods
	on a dirty document to lock the stronger invariant that only server-loaded state can
	reach the database, regardless of the whitelisted surface or in-process caller.
	"""

	def tampered(self, poll):
		copy = frappe.get_doc("GP Poll", poll.name)
		copy.title = "HIJACKED"
		copy.anonymous = 1
		copy.multiple_answers = 1
		copy.options[0].title = "Pwned option"
		return copy

	def assert_poll_intact(self, poll):
		poll.reload()
		self.assertEqual(poll.title, "Ship on Friday?")
		self.assertEqual([option.title for option in poll.options], ["Yes", "No"])
		self.assertFalse(poll.anonymous)
		self.assertFalse(poll.multiple_answers)

	def test_submit_vote_discards_the_fields_the_caller_sent(self):
		poll = self.poll()

		with self.as_user(self.second_member):
			self.tampered(poll).submit_vote("Yes")

		self.assert_poll_intact(poll)
		# ...and the vote still lands, against the poll's real option
		self.assertEqual([(v.user, v.option) for v in poll.votes], [(self.second_member.name, "Yes")])
		self.assertEqual(self.option(poll, "Yes").votes, 1)

	def test_retract_vote_discards_the_fields_the_caller_sent(self):
		poll = self.poll()
		self.vote(poll, self.second_member, "Yes")

		with self.as_user(self.second_member):
			self.tampered(poll).retract_vote()

		self.assert_poll_intact(poll)
		self.assertEqual(poll.votes, [])

	def test_stop_poll_discards_the_fields_the_caller_sent(self):
		poll = self.poll()

		with self.as_user(self.member):
			self.tampered(poll).stop_poll()

		self.assert_poll_intact(poll)
		self.assertIsNotNone(poll.stopped_at)

	def test_clearing_stopped_at_in_the_payload_does_not_reopen_the_poll(self):
		poll = self.poll()
		with self.as_user(self.member):
			poll.stop_poll()

		with self.as_user(self.second_member):
			reopened = frappe.get_doc("GP Poll", poll.name)
			reopened.stopped_at = None
			with self.assertRaises(frappe.ValidationError):
				reopened.submit_vote("Yes")

		poll.reload()
		self.assertIsNotNone(poll.stopped_at)
		self.assertEqual(poll.total_votes, 0)


class TestPollFieldProtection(PollTestCase):
	"""A poll's ballot and lifecycle belong to its author, not to the space.

	`stop_poll` says so, but the whitelisted method is not the only way in: content
	inside a space is editable by every member who can reach it, so a plain
	`PUT /api/v2/document/GP Poll/<name>` lands on `save()` and never passes through
	`stop_poll`. These tests drive that same `save()`, loading the poll inside the other
	member's session — the builder leaves `ignore_permissions` on the doc it returns, so
	reusing that object would skip the check under test.
	"""

	def test_another_member_cannot_stop_the_poll_by_saving_it(self):
		poll = self.poll()

		with self.as_user(self.second_member), self.assertRaises(frappe.PermissionError):
			tampered = frappe.get_doc("GP Poll", poll.name)
			tampered.stopped_at = frappe.utils.now()
			tampered.save()

		poll.reload()
		self.assertIsNone(poll.stopped_at)

	def test_another_member_cannot_rewrite_the_recorded_votes(self):
		poll = self.poll()
		self.vote(poll, self.member, "Yes")

		with self.as_user(self.second_member), self.assertRaises(frappe.PermissionError):
			tampered = frappe.get_doc("GP Poll", poll.name)
			tampered.votes = []
			tampered.save()

		poll.reload()
		self.assertEqual([(v.user, v.option) for v in poll.votes], [(self.member.name, "Yes")])

	def test_another_member_cannot_rewrite_the_options(self):
		poll = self.poll()

		with self.as_user(self.second_member), self.assertRaises(frappe.PermissionError):
			tampered = frappe.get_doc("GP Poll", poll.name)
			tampered.options[0].title = "Pwned option"
			tampered.save()

		poll.reload()
		self.assertEqual([option.title for option in poll.options], ["Yes", "No"])

	def test_another_member_cannot_inflate_the_vote_count(self):
		poll = self.poll()

		with self.as_user(self.second_member), self.assertRaises(frappe.PermissionError):
			tampered = frappe.get_doc("GP Poll", poll.name)
			tampered.total_votes = 99
			tampered.save()

		poll.reload()
		self.assertEqual(poll.total_votes, 0)

	def test_the_owner_may_still_save_the_poll(self):
		poll = self.poll()

		with self.as_user(self.member):
			owned = frappe.get_doc("GP Poll", poll.name)
			owned.stopped_at = frappe.utils.now()
			owned.save()

		poll.reload()
		self.assertIsNotNone(poll.stopped_at)

	def test_a_community_admin_may_still_moderate_the_poll(self):
		poll = self.poll()
		community = frappe.get_doc("GP Team", self.community.name)
		community.get_member(self.second_member.name).is_admin = 1
		community.save(ignore_permissions=True)

		with self.as_user(self.second_member):
			moderated = frappe.get_doc("GP Poll", poll.name)
			moderated.stopped_at = frappe.utils.now()
			moderated.save()

		poll.reload()
		self.assertIsNotNone(poll.stopped_at)

	def test_the_guard_does_not_block_voting(self):
		"""Voting writes the very fields the guard protects, which is why it runs through
		submit_vote and its own participation gate rather than the `write` permission."""
		poll = self.poll()

		self.vote(poll, self.second_member, "Yes")

		self.assertEqual([(v.user, v.option) for v in poll.votes], [(self.second_member.name, "Yes")])

	def test_the_guard_does_not_block_reacting(self):
		poll = self.poll()

		with self.as_user(self.second_member):
			frappe.get_doc("GP Poll", poll.name).react(operations=[{"emoji": "👍", "operation": "add"}])

		poll.reload()
		self.assertEqual([(row.user, row.emoji) for row in poll.reactions], [(self.second_member.name, "👍")])


class TestDeletingAPoll(PollTestCase):
	"""Deleting a discussion takes the polls inside it, whoever posted them.

	The delete cascade in `gameplan/mixins/on_delete.py` removes each child on behalf of
	a parent whose own delete was already authorised, so the per-poll owner rule must not
	be re-applied to it — otherwise one other member's poll vetoes the thread owner's
	delete and rolls the whole operation back.
	"""

	def test_discussion_owner_can_delete_a_thread_holding_another_members_poll(self):
		poll = create_poll("Second member's poll", self.discussion, owner=self.second_member)

		with self.as_user(self.member):
			frappe.delete_doc("GP Discussion", self.discussion.name)

		self.assertFalse(frappe.db.exists("GP Poll", poll.name))
		self.assertFalse(frappe.db.exists("GP Discussion", self.discussion.name))

	def test_the_cascade_exemption_does_not_reach_a_direct_delete(self):
		poll = create_poll("Second member's poll", self.discussion, owner=self.second_member)

		# `member` owns the discussion but not the poll, and is no kind of admin.
		with self.as_user(self.member), self.assertRaises(frappe.PermissionError):
			frappe.delete_doc("GP Poll", poll.name)

		self.assertTrue(frappe.db.exists("GP Poll", poll.name))


class TestPollMutationHTTPMethods(GameplanTestCase):
	def test_poll_mutations_are_post_only(self):
		for method in (GPPoll.submit_vote, GPPoll.retract_vote, GPPoll.stop_poll):
			self.assertEqual(declared_http_methods(method), {"POST"})


class TestWhoMayVote(PollTestCase):
	def setUp(self):
		super().setUp()
		# A poll nobody outside the space can reach: only `member` is in this space.
		self.private_space = create_space("Locked Space", self.community, is_private=1, members=[self.member])
		self.private_discussion = create_discussion("Locked thread", self.private_space, owner=self.member)

	def private_poll(self):
		return create_poll("Ship on Friday?", self.private_discussion, owner=self.member)

	def test_any_community_member_may_read_and_vote_in_a_public_space(self):
		poll = self.poll()

		self.assert_allowed(poll, "read", self.second_member)
		self.vote(poll, self.second_member, "Yes")
		self.assertEqual(poll.total_votes, 1)

	def test_member_outside_a_private_space_cannot_read_or_vote(self):
		poll = self.private_poll()

		self.assert_not_allowed(poll, "read", self.second_member)
		with self.as_user(self.second_member), self.assertRaises(frappe.PermissionError):
			frappe.get_doc("GP Poll", poll.name).submit_vote("Yes")

		poll.reload()
		self.assertEqual(poll.total_votes, 0)

	def test_stopped_poll_does_not_leak_its_state_outside_the_space(self):
		poll = self.private_poll()
		with self.as_user(self.member):
			poll.stop_poll()

		with (
			self.as_user(self.second_member),
			self.assertRaisesRegex(frappe.PermissionError, "You do not have access to this poll"),
		):
			frappe.get_doc("GP Poll", poll.name).submit_vote("Yes")

	def test_only_the_owner_and_moderators_may_delete_a_poll(self):
		poll = self.poll()

		self.assert_allowed(poll, "delete", self.member)  # its owner
		self.assert_allowed(poll, "delete", self.admin)  # global admin
		self.assert_not_allowed(poll, "delete", self.second_member)
		self.assert_not_allowed(poll, "delete", self.outsider)

	def test_poll_list_hides_polls_from_spaces_the_user_cannot_reach(self):
		poll = self.private_poll()
		filters = {"discussion": self.private_discussion.name}

		with self.as_user(self.member):
			visible = frappe.get_list("GP Poll", filters=filters, pluck="name")
		self.assertEqual([str(name) for name in visible], [str(poll.name)])

		with self.as_user(self.second_member):
			self.assertEqual(frappe.get_list("GP Poll", filters=filters, pluck="name"), [])


class TestGuestPollParticipation(GameplanTestCase):
	"""Guests are participants in the spaces they are granted: they may create, vote,
	and react to polls there."""

	def setUp(self):
		super().setUp()
		self.community = create_community("Guest Poll Community", members=[self.member])
		self.space = create_space("Granted Space", self.community, is_private=1, members=[self.member])
		self.other_space = create_space(
			"Ungranted Space", self.community, is_private=1, members=[self.member]
		)
		grant_guest_access(self.guest, self.space)
		self.discussion = create_discussion("Guest poll thread", self.space, owner=self.member)
		self.other_discussion = create_discussion("Closed thread", self.other_space, owner=self.member)

	def test_guest_can_create_a_poll_but_not_a_discussion_in_a_granted_space(self):
		with self.as_user(self.guest):
			poll = frappe.get_doc(
				doctype="GP Poll",
				title="Guest lunch poll",
				discussion=self.discussion.name,
				options=[{"title": "Yes"}, {"title": "No"}],
			).insert()

			with self.assertRaises(frappe.PermissionError):
				frappe.get_doc(
					doctype="GP Discussion",
					title="Guest-created discussion",
					content="<p>Not participation content</p>",
					project=self.space.name,
				).insert()

		self.assertEqual(poll.owner, self.guest.name)

	def test_guest_cannot_create_a_poll_outside_their_granted_spaces(self):
		with self.as_user(self.guest), self.assertRaises(frappe.PermissionError):
			frappe.get_doc(
				doctype="GP Poll",
				title="Hidden poll",
				discussion=self.other_discussion.name,
				options=[{"title": "Yes"}, {"title": "No"}],
			).insert()

	def test_guest_can_vote_in_a_granted_space(self):
		poll = create_poll("Lunch?", self.discussion, owner=self.member)

		with self.as_user(self.guest):
			poll.submit_vote("Yes")
		poll.reload()

		self.assertEqual([(v.user, v.option) for v in poll.votes], [(self.guest.name, "Yes")])

	def test_guest_can_react_to_a_poll_in_a_granted_space(self):
		poll = create_poll("Lunch?", self.discussion, owner=self.member)

		with self.as_user(self.guest):
			frappe.get_doc("GP Poll", poll.name).react(operations=[{"emoji": "👍", "operation": "add"}])

		poll.reload()
		self.assertEqual([(row.user, row.emoji) for row in poll.reactions], [(self.guest.name, "👍")])

	def test_guest_cannot_vote_outside_their_granted_spaces(self):
		poll = create_poll("Lunch?", self.other_discussion, owner=self.member)

		with self.as_user(self.guest), self.assertRaises(frappe.PermissionError):
			poll.submit_vote("Yes")

		poll.reload()
		self.assertEqual(poll.total_votes, 0)

	def test_guest_cannot_rewrite_a_poll_they_can_vote_in(self):
		"""Voting is participation, not write access: a plain save must still be refused.

		The doc is loaded inside the guest's session on purpose — the builder's insert
		leaves `ignore_permissions` on its own doc object, so reusing it would skip the
		very check under test.
		"""
		poll = create_poll("Lunch?", self.discussion, owner=self.member)

		with self.as_user(self.guest), self.assertRaises(frappe.PermissionError):
			guest_copy = frappe.get_doc("GP Poll", poll.name)
			guest_copy.title = "Hijacked"
			guest_copy.save()

		poll.reload()
		self.assertEqual(poll.title, "Lunch?")

	def test_guest_voting_cannot_rewrite_the_poll(self):
		"""The vote save bypasses permissions, so it must carry nothing the guest sent."""
		poll = create_poll("Lunch?", self.discussion, owner=self.member)

		with self.as_user(self.guest):
			tampered = frappe.get_doc("GP Poll", poll.name)
			tampered.title = "GUEST HIJACKED"
			tampered.options[0].title = "Pwned option"
			tampered.anonymous = 1
			tampered.submit_vote("Yes")

		poll.reload()
		self.assertEqual(poll.title, "Lunch?")
		self.assertEqual([option.title for option in poll.options], ["Yes", "No"])
		self.assertFalse(poll.anonymous)
		self.assertEqual([(v.user, v.option) for v in poll.votes], [(self.guest.name, "Yes")])
