# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""The reaction toggle itself (gameplan/mixins/reactions.py::HasReactions.react).

Who may react is the guest-participation spec's job
(`features/test_guest_participation.py`) and what a reaction notifies is the
notifications spec's (`features/test_notifications.py`). What is left — and what this
file owns — is the operation contract of `react`:

- a reaction is identified by (user, emoji), so add is idempotent and remove is scoped
  to the acting user's own row,
- a batch of operations is applied in order (that is how the debounced frontend sends
  a quick toggle),
- garbage in a batch is ignored, not stored,
- reacting never touches the post itself.
"""

import frappe

from gameplan.mixins.reactions import HasReactions
from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import (
	create_comment,
	create_community,
	create_discussion,
	create_poll,
	create_space,
	declared_http_methods,
)

THUMBS_UP = "\U0001f44d"
HEART = "\U0001f496"


def add(emoji):
	return {"emoji": emoji, "operation": "add"}


def remove(emoji):
	return {"emoji": emoji, "operation": "remove"}


class ReactionTestCase(GameplanTestCase):
	def setUp(self):
		super().setUp()
		self.community = create_community("Acme", members=[self.member, self.second_member])
		self.space = create_space("Engineering", self.community)
		self.discussion = create_discussion("Welcome thread", self.space, owner=self.member)
		self.comment = create_comment(self.discussion, owner=self.member)
		self.poll = create_poll("Lunch?", self.discussion, owner=self.member)

	def react(self, doc, user, operations):
		with self.as_user(user):
			return frappe.get_doc(doc.doctype, doc.name).react(operations=operations)

	def stored_reactions(self, doc):
		"""(user, emoji) pairs as they are stored, read back from the database."""
		return [
			(row.user, row.emoji)
			for row in frappe.get_all(
				"GP Reaction",
				filters={"parenttype": doc.doctype, "parent": doc.name},
				fields=["user", "emoji"],
				order_by="idx asc",
			)
		]


class TestReact(ReactionTestCase):
	def test_add_stores_the_acting_users_reaction(self):
		self.react(self.discussion, self.second_member, [add(THUMBS_UP)])

		self.assertEqual(self.stored_reactions(self.discussion), [(self.second_member.name, THUMBS_UP)])

	def test_react_returns_the_updated_reactions(self):
		reactions = self.react(self.discussion, self.second_member, [add(THUMBS_UP)])

		self.assertEqual([(r.user, r.emoji) for r in reactions], [(self.second_member.name, THUMBS_UP)])

	def test_adding_the_same_emoji_twice_stores_one_row(self):
		self.react(self.discussion, self.second_member, [add(THUMBS_UP)])
		self.react(self.discussion, self.second_member, [add(THUMBS_UP)])

		self.assertEqual(self.stored_reactions(self.discussion), [(self.second_member.name, THUMBS_UP)])

	def test_a_user_can_hold_several_different_emojis(self):
		self.react(self.discussion, self.second_member, [add(THUMBS_UP)])
		self.react(self.discussion, self.second_member, [add(HEART)])

		self.assertEqual(
			self.stored_reactions(self.discussion),
			[(self.second_member.name, THUMBS_UP), (self.second_member.name, HEART)],
		)

	def test_two_users_can_hold_the_same_emoji(self):
		self.react(self.discussion, self.member, [add(THUMBS_UP)])
		self.react(self.discussion, self.second_member, [add(THUMBS_UP)])

		self.assertEqual(
			self.stored_reactions(self.discussion),
			[(self.member.name, THUMBS_UP), (self.second_member.name, THUMBS_UP)],
		)

	def test_remove_takes_back_the_acting_users_reaction(self):
		self.react(self.discussion, self.second_member, [add(THUMBS_UP)])
		self.react(self.discussion, self.second_member, [remove(THUMBS_UP)])

		self.assertEqual(self.stored_reactions(self.discussion), [])

	def test_remove_only_takes_back_the_acting_users_own_row(self):
		self.react(self.discussion, self.member, [add(THUMBS_UP)])
		self.react(self.discussion, self.second_member, [add(THUMBS_UP)])

		self.react(self.discussion, self.second_member, [remove(THUMBS_UP)])

		self.assertEqual(self.stored_reactions(self.discussion), [(self.member.name, THUMBS_UP)])

	def test_remove_only_takes_back_the_named_emoji(self):
		self.react(self.discussion, self.second_member, [add(THUMBS_UP), add(HEART)])

		self.react(self.discussion, self.second_member, [remove(THUMBS_UP)])

		self.assertEqual(self.stored_reactions(self.discussion), [(self.second_member.name, HEART)])

	def test_removing_a_reaction_that_was_never_added_changes_nothing(self):
		self.react(self.discussion, self.member, [add(THUMBS_UP)])

		self.react(self.discussion, self.second_member, [remove(THUMBS_UP)])

		self.assertEqual(self.stored_reactions(self.discussion), [(self.member.name, THUMBS_UP)])

	def test_a_batch_is_applied_in_order(self):
		"""The frontend debounces a quick tap-tap into one batch, so the last operation
		on an emoji is the state the user ends up with."""
		self.react(self.discussion, self.second_member, [add(THUMBS_UP), add(HEART), remove(THUMBS_UP)])

		self.assertEqual(self.stored_reactions(self.discussion), [(self.second_member.name, HEART)])

	def test_reactions_work_the_same_way_on_a_comment(self):
		self.react(self.comment, self.second_member, [add(THUMBS_UP)])
		self.assertEqual(self.stored_reactions(self.comment), [(self.second_member.name, THUMBS_UP)])

		self.react(self.comment, self.second_member, [remove(THUMBS_UP)])
		self.assertEqual(self.stored_reactions(self.comment), [])

	def test_reactions_work_the_same_way_on_a_poll(self):
		"""Poll.vue renders the same Reactions component on a poll, so GP Poll has to
		answer `react` exactly like a discussion or a comment does."""
		self.react(self.poll, self.second_member, [add(THUMBS_UP)])
		self.assertEqual(self.stored_reactions(self.poll), [(self.second_member.name, THUMBS_UP)])

		self.react(self.poll, self.second_member, [remove(THUMBS_UP)])
		self.assertEqual(self.stored_reactions(self.poll), [])

	def test_reacting_leaves_the_post_untouched(self):
		original = frappe.get_doc("GP Discussion", self.discussion.name)

		self.react(self.discussion, self.second_member, [add(THUMBS_UP)])

		updated = frappe.get_doc("GP Discussion", self.discussion.name)
		self.assertEqual(updated.title, original.title)
		self.assertEqual(updated.content, original.content)
		self.assertEqual(updated.owner, original.owner)

	def test_reacting_does_not_mark_a_comment_as_edited(self):
		self.assertFalse(frappe.db.get_value("GP Comment", self.comment.name, "edited_at"))

		self.react(self.comment, self.second_member, [add(THUMBS_UP)])

		self.assertFalse(frappe.db.get_value("GP Comment", self.comment.name, "edited_at"))


class TestReactionMutationHTTPMethods(GameplanTestCase):
	def test_react_is_post_only(self):
		self.assertEqual(declared_http_methods(HasReactions.react), {"POST"})


class TestReactPayload(ReactionTestCase):
	def test_an_empty_batch_returns_the_current_reactions_and_changes_nothing(self):
		self.react(self.discussion, self.member, [add(THUMBS_UP)])

		reactions = self.react(self.discussion, self.second_member, [])

		self.assertEqual([(r.user, r.emoji) for r in reactions], [(self.member.name, THUMBS_UP)])
		self.assertEqual(self.stored_reactions(self.discussion), [(self.member.name, THUMBS_UP)])

	def test_a_json_encoded_batch_is_accepted(self):
		"""Over HTTP the payload arrives as a JSON string, not a list."""
		self.react(self.discussion, self.second_member, frappe.as_json([add(THUMBS_UP)]))

		self.assertEqual(self.stored_reactions(self.discussion), [(self.second_member.name, THUMBS_UP)])

	def test_a_payload_that_is_not_a_list_is_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			self.react(self.discussion, self.second_member, {"emoji": THUMBS_UP, "operation": "add"})

		self.assertEqual(self.stored_reactions(self.discussion), [])

	def test_an_operation_without_an_emoji_is_ignored(self):
		self.react(self.discussion, self.second_member, [{"operation": "add"}, add(THUMBS_UP)])

		self.assertEqual(self.stored_reactions(self.discussion), [(self.second_member.name, THUMBS_UP)])

	def test_an_unknown_operation_is_ignored(self):
		self.react(self.discussion, self.second_member, [{"emoji": HEART, "operation": "toggle"}])

		self.assertEqual(self.stored_reactions(self.discussion), [])


class TestPollReactions(ReactionTestCase):
	"""A poll is a post like any other: it carries a `reactions` table and the UI hangs
	the same Reactions component off it. The (user, emoji) identity rule and the
	participation gate must therefore behave exactly as they do on a discussion."""

	def test_a_second_member_can_react_to_someone_elses_poll(self):
		self.react(self.poll, self.second_member, [add(THUMBS_UP)])

		self.assertEqual(self.stored_reactions(self.poll), [(self.second_member.name, THUMBS_UP)])

	def test_react_returns_the_updated_reactions(self):
		reactions = self.react(self.poll, self.second_member, [add(THUMBS_UP)])

		self.assertEqual([(r.user, r.emoji) for r in reactions], [(self.second_member.name, THUMBS_UP)])

	def test_reacting_again_with_the_same_emoji_toggles_it_off(self):
		self.react(self.poll, self.second_member, [add(THUMBS_UP)])
		self.react(self.poll, self.second_member, [remove(THUMBS_UP)])

		self.assertEqual(self.stored_reactions(self.poll), [])

	def test_adding_the_same_emoji_twice_stores_one_row(self):
		self.react(self.poll, self.second_member, [add(THUMBS_UP)])
		self.react(self.poll, self.second_member, [add(THUMBS_UP)])

		self.assertEqual(self.stored_reactions(self.poll), [(self.second_member.name, THUMBS_UP)])

	def test_a_user_can_hold_several_different_emojis(self):
		self.react(self.poll, self.second_member, [add(THUMBS_UP), add(HEART)])

		self.assertEqual(
			self.stored_reactions(self.poll),
			[(self.second_member.name, THUMBS_UP), (self.second_member.name, HEART)],
		)

	def test_remove_only_takes_back_the_acting_users_own_row(self):
		self.react(self.poll, self.member, [add(THUMBS_UP)])
		self.react(self.poll, self.second_member, [add(THUMBS_UP)])

		self.react(self.poll, self.second_member, [remove(THUMBS_UP)])

		self.assertEqual(self.stored_reactions(self.poll), [(self.member.name, THUMBS_UP)])

	def test_a_duplicate_row_saved_directly_is_collapsed_on_validate(self):
		"""Same validate-time de-duplication its siblings apply, so a doubled row can
		never reach the database however the poll is saved."""
		poll = frappe.get_doc("GP Poll", self.poll.name)
		poll.append("reactions", {"user": self.member.name, "emoji": THUMBS_UP})
		poll.append("reactions", {"user": self.member.name, "emoji": THUMBS_UP})
		poll.save(ignore_permissions=True)

		self.assertEqual(self.stored_reactions(self.poll), [(self.member.name, THUMBS_UP)])

	def test_reacting_leaves_the_poll_and_its_votes_untouched(self):
		with self.as_user(self.member):
			frappe.get_doc("GP Poll", self.poll.name).submit_vote("Yes")

		self.react(self.poll, self.second_member, [add(THUMBS_UP)])

		poll = frappe.get_doc("GP Poll", self.poll.name)
		self.assertEqual(poll.title, "Lunch?")
		self.assertEqual([(v.user, v.option) for v in poll.votes], [(self.member.name, "Yes")])
		self.assertEqual(poll.total_votes, 1)
		self.assertEqual([o.title for o in poll.options], ["Yes", "No"])


class TestReactionsSurviveAnEdit(ReactionTestCase):
	def test_editing_the_post_keeps_the_reactions(self):
		"""The E2E happy path asserts a reaction survives a reload; this pins the other
		way a reaction could get lost — someone editing the post it hangs on."""
		self.react(self.discussion, self.second_member, [add(THUMBS_UP)])

		with self.as_user(self.member):
			discussion = frappe.get_doc("GP Discussion", self.discussion.name)
			discussion.title = "Welcome thread (edited)"
			discussion.save()

		self.assertEqual(self.stored_reactions(self.discussion), [(self.second_member.name, THUMBS_UP)])
