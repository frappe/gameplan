# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""Polls: casting and retracting votes, stopping a poll, and who may do either.

A poll is content that lives inside a discussion, so it takes that discussion's space
for access: everyone who can reach the space may vote, and nobody else can even see it.
Voting itself is participation (like reacting), which is why the vote methods are the
gate rather than the `write` permission — see GPPoll.save_after_voting. That save skips
permissions, so the methods first throw away everything the caller sent
(GPPoll.discard_client_state); TestTamperedVotePayload locks that.
"""

import frappe
from frappe.utils import add_days, now_datetime

from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import (
	create_community,
	create_discussion,
	create_poll,
	create_space,
	grant_guest_access,
)


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

	def test_one_vote_per_user(self):
		poll = self.poll()
		self.vote(poll, self.member, "Yes")

		# Voting again — even for another option — leaves the first vote standing.
		self.vote(poll, self.member, "No")

		self.assertEqual(poll.total_votes, 1)
		self.assertEqual([(v.user, v.option) for v in poll.votes], [(self.member.name, "Yes")])
		self.assertEqual(self.option(poll, "No").votes, 0)

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

	Percentages stay a share of the vote rows cast, so they still add up to 100%: on a
	multiple-answer poll `total_votes` counts answers, not voters.
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
		self.assertEqual(self.option(poll, "Yes").percentage, 50)

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

	def test_anonymous_multiple_answer_poll_still_allows_only_one_vote(self):
		# An anonymous vote row carries no option, so a second answer could never be told
		# apart from a double vote. Anonymity wins: one vote per voter.
		poll = self.poll(anonymous=1, multiple_answers=1)

		self.vote(poll, self.member, "Yes")
		self.vote(poll, self.member, "No")

		self.assertEqual(poll.total_votes, 1)


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


class TestTamperedVotePayload(PollTestCase):
	"""A vote may carry nothing but the vote.

	`submit_vote`, `retract_vote` and `stop_poll` are reachable over `run_doc_method`,
	which builds the document from the caller's own JSON and checks only `read` — so any
	reader can hand these methods a poll whose title, options, flags or `stopped_at` they
	rewrote, and the vote save deliberately runs with `ignore_permissions`. These tests
	stand in for that endpoint by mutating the doc before calling the method, and lock the
	guarantee that only server-computed state ever reaches the database.
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
	"""Guests are participants in the spaces they are granted: they may vote there."""

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

	def test_guest_can_vote_in_a_granted_space(self):
		poll = create_poll("Lunch?", self.discussion, owner=self.member)

		with self.as_user(self.guest):
			poll.submit_vote("Yes")
		poll.reload()

		self.assertEqual([(v.user, v.option) for v in poll.votes], [(self.guest.name, "Yes")])

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
