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

Some notification behaviour lives here rather than in the notifications spec, because it
belongs to this mixin's write path rather than to the notification itself: the unread flag
resets on every reaction (`TestReactionNotificationUnreadState`), only an ADDED reaction
notifies at all (`TestWhichReactionChangesNotify`), and one row is reused per post, which
makes the row's link fields both its routing and its identity
(`TestReactionNotificationRouting`). The notifications spec covers what the message says.
"""

import threading

import frappe
from frappe.tests.utils import FrappeTestCase

from gameplan.api import mark_all_notifications_as_read, unread_notifications
from gameplan.mixins.reactions import HasReactions
from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import (
	create_comment,
	create_community,
	create_discussion,
	create_member,
	create_poll,
	create_space,
	create_task,
	declared_http_methods,
)
from gameplan.tests.search_isolation import guard_real_index

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
				filters={"reference_doctype": doc.doctype, "reference_name": doc.name},
				fields=["user", "emoji"],
				order_by="name asc",
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

	def test_reactions_from_several_people_at_once_all_land(self):
		"""Each request loads the post before it reacts. A reaction that lands in between
		must neither fail the later one nor be lost by it."""
		with self.as_user(self.second_member):
			loaded_before = frappe.get_doc("GP Discussion", self.discussion.name)

		self.react(self.discussion, self.admin, [add(HEART)])
		with self.as_user(self.second_member):
			loaded_before.react(operations=[add(THUMBS_UP)])

		self.assertEqual(
			self.stored_reactions(self.discussion),
			[(self.admin.name, HEART), (self.second_member.name, THUMBS_UP)],
		)

	def test_reacting_leaves_the_posts_modified_timestamp_alone(self):
		"""Someone editing the post must not hit a timestamp conflict because of a reaction."""
		modified = frappe.db.get_value("GP Discussion", self.discussion.name, "modified")

		self.react(self.discussion, self.second_member, [add(THUMBS_UP)])

		self.assertEqual(frappe.db.get_value("GP Discussion", self.discussion.name, "modified"), modified)

	def test_reacting_does_not_mark_a_comment_as_edited(self):
		self.assertFalse(frappe.db.get_value("GP Comment", self.comment.name, "edited_at"))

		self.react(self.comment, self.second_member, [add(THUMBS_UP)])

		self.assertFalse(frappe.db.get_value("GP Comment", self.comment.name, "edited_at"))


class TestReactionsAtTheSameMoment(FrappeTestCase):
	"""Many people reacting to one post at the same moment, each from their own connection.

	Every other test here reacts one call after another in a single transaction, so none
	of them fails if the locks in `react` go away. Here each person reacts from their own
	database connection, and every connection reads the post before any of them reacts.
	So each one holds a snapshot that is out of date by the time it writes, as concurrent
	requests do.

	The other connections can only see committed data, so this test commits its fixtures
	and deletes them afterwards. SQLite has no row locks to test, so it runs on MariaDB only.
	"""

	PEOPLE = 6

	def setUp(self):
		if frappe.db.db_type != "mariadb":
			self.skipTest("Tests MariaDB row locks")
		frappe.set_user("Administrator")
		guard_real_index(self)
		self.users = []
		self.community = None
		self.addCleanup(self.delete_committed_fixtures)

		suffix = frappe.generate_hash(length=8)
		self.owner = create_member(f"reaction_owner_{suffix}@example.com", "Owner")
		self.people = [
			create_member(f"reactor_{i}_{suffix}@example.com", f"Reactor {i}") for i in range(self.PEOPLE)
		]
		self.users = [self.owner.name, *(person.name for person in self.people)]
		self.community = create_community(f"Reactions {suffix}", members=[self.owner, *self.people])
		space = create_space("Reactions", self.community)
		self.discussion = create_discussion("Popular post", space, owner=self.owner)
		frappe.db.commit()

	def delete_committed_fixtures(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()
		if self.users:
			frappe.db.delete("GP Notification", {"to_user": ["in", self.users]})
		if self.community and frappe.db.exists("GP Team", self.community.name):
			frappe.delete_doc("GP Team", self.community.name, ignore_permissions=True, force=True)
		for user in self.users:
			if frappe.db.exists("User", user):
				frappe.delete_doc("User", user, ignore_permissions=True, force=True)
		frappe.db.commit()

	def react_at_once(self, users):
		"""Each of `users` reacts 👍 from their own connection, after all of them have read
		the post. Returns the errors they hit."""
		errors = []
		everyone_has_read = threading.Barrier(len(users))
		site, sites_path = frappe.local.site, frappe.local.sites_path

		def react_from_own_connection(user):
			frappe.init(site, sites_path=sites_path)
			try:
				frappe.connect()
				frappe.set_user(user)
				post = frappe.get_doc("GP Discussion", self.discussion.name)
				everyone_has_read.wait(timeout=30)
				post.react(operations=[add(THUMBS_UP)])
				frappe.db.commit()
			except Exception as error:
				errors.append(f"{user}: {error!r}")
				frappe.db.rollback()
			finally:
				frappe.destroy()

		threads = [threading.Thread(target=react_from_own_connection, args=(user,)) for user in users]
		for thread in threads:
			thread.start()
		for thread in threads:
			thread.join(timeout=60)
		self.assertFalse(any(thread.is_alive() for thread in threads), "a reaction never finished")
		# Read what the other connections committed, not this connection's snapshot.
		frappe.db.rollback()
		return errors

	def stored_reactions(self):
		return frappe.get_all(
			"GP Reaction",
			filters={"reference_doctype": "GP Discussion", "reference_name": str(self.discussion.name)},
			fields=["user", "emoji"],
		)

	def test_everyone_reacting_at_once_succeeds_and_the_owner_gets_one_notification(self):
		# The first reaction creates the owner's notification, so the others all update
		# one shared row. That is where people used to see TimestampMismatchError.
		first, *rest = self.people
		frappe.set_user(first.name)
		frappe.get_doc("GP Discussion", self.discussion.name).react(operations=[add(THUMBS_UP)])
		frappe.set_user("Administrator")
		frappe.db.commit()

		self.assertEqual(self.react_at_once([person.name for person in rest]), [])

		self.assertCountEqual(
			self.stored_reactions(), [{"user": person.name, "emoji": THUMBS_UP} for person in self.people]
		)
		notifications = frappe.get_all(
			"GP Notification",
			filters={"to_user": self.owner.name, "type": "Reaction"},
			pluck="message",
		)
		self.assertEqual(notifications, [f"{self.PEOPLE} people reacted to your post"])

	def test_one_person_adding_the_same_emoji_from_two_tabs_at_once_stores_one_row(self):
		person = self.people[0].name

		self.assertEqual(self.react_at_once([person, person]), [])

		self.assertEqual(self.stored_reactions(), [{"user": person, "emoji": THUMBS_UP}])


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


class TestReactionsAuthorizeTheStoredPost(ReactionTestCase):
	"""The v2 document-method route builds the post from fields the caller sends. A caller
	who names a post they cannot see, but sends a project they can see, must still be
	refused: the check reads the stored post, not the one sent."""

	def setUp(self):
		super().setUp()
		private_space = create_space("Leadership", self.community, is_private=1, members=[self.member])
		self.private_discussion = create_discussion("Plans", private_space, owner=self.member)
		self.react(self.private_discussion, self.member, [add(THUMBS_UP)])

	def forged(self, doc):
		"""`doc` as a caller could send it: in a space the caller can see, owned by them."""
		return frappe.get_doc(
			{
				"doctype": doc.doctype,
				"name": doc.name,
				"project": self.space.name,
				"title": "Forged",
				"owner": self.second_member.name,
				"__islocal": 1,
			}
		)

	def test_react_refuses_a_post_the_user_cannot_see(self):
		with self.as_user(self.second_member):
			forged = self.forged(self.private_discussion)
			with self.assertRaises(frappe.PermissionError):
				forged.react(operations=[add(HEART)])
			with self.assertRaises(frappe.PermissionError):
				forged.react(operations=[])

		self.assertEqual(self.stored_reactions(self.private_discussion), [(self.member.name, THUMBS_UP)])

	def test_thread_reactions_refuses_a_thread_the_user_cannot_see(self):
		with self.as_user(self.second_member):
			with self.assertRaises(frappe.PermissionError):
				self.forged(self.private_discussion).thread_reactions()

	def test_task_thread_reactions_refuses_a_task_the_user_cannot_see(self):
		task = create_task("Hire", self.private_discussion.project, owner=self.member)
		with self.as_user(self.second_member):
			with self.assertRaises(frappe.PermissionError):
				self.forged(task).thread_reactions()


class TestPollReactions(ReactionTestCase):
	"""A poll is a post like any other: the UI hangs the same Reactions component off it.
	The (user, emoji) identity rule and the participation gate must therefore behave
	exactly as they do on a discussion."""

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

	def test_reacting_leaves_the_poll_and_its_votes_untouched(self):
		with self.as_user(self.member):
			frappe.get_doc("GP Poll", self.poll.name).submit_vote("Yes")

		self.react(self.poll, self.second_member, [add(THUMBS_UP)])

		poll = frappe.get_doc("GP Poll", self.poll.name)
		self.assertEqual(poll.title, "Lunch?")
		self.assertEqual([(v.user, v.option) for v in poll.votes], [(self.member.name, "Yes")])
		self.assertEqual(poll.total_votes, 1)
		self.assertEqual([o.title for o in poll.options], ["Yes", "No"])


class TestReactionNotificationUnreadState(ReactionTestCase):
	"""A reaction has to leave the post owner's bell unread, every time.

	`notify_reactions` reuses one notification row per post, so `read = 0` is not a
	default that happens to hold — it is the only thing that raises the badge again for
	the second, third and tenth reactor after the owner has cleared it once. Drop it and
	reactions become a channel that lights up exactly once and then goes silent.
	"""

	def bell_count(self, user):
		"""What the bell badge shows for `user` (gameplan.api.unread_notifications)."""
		with self.as_user(user):
			return unread_notifications()

	def clear_bell(self, user):
		with self.as_user(user):
			mark_all_notifications_as_read()

	def reaction_notifications(self, user, discussion):
		return frappe.get_all(
			"GP Notification",
			filters={"to_user": user.name, "type": "Reaction", "discussion": discussion.name},
			pluck="name",
		)

	def test_a_reaction_lights_the_post_owners_bell(self):
		self.clear_bell(self.member)

		self.react(self.discussion, self.second_member, [add(THUMBS_UP)])

		self.assertEqual(self.bell_count(self.member), 1)

	def test_a_later_reaction_re_lights_a_bell_the_owner_already_cleared(self):
		self.react(self.discussion, self.second_member, [add(THUMBS_UP)])
		self.clear_bell(self.member)
		self.assertEqual(self.bell_count(self.member), 0)

		self.react(self.discussion, self.admin, [add(HEART)])

		# One row, re-flagged rather than a second row appearing: on this path the reset
		# is the only thing that can raise the badge.
		self.assertEqual(len(self.reaction_notifications(self.member, self.discussion)), 1)
		self.assertEqual(self.bell_count(self.member), 1)


class TestWhichReactionChangesNotify(ReactionTestCase):
	"""Only a reaction someone *added* is news to the post owner.

	`notify_reactions` runs on every save of the post, so it has to work out what
	actually changed in the reactions table. A withdrawal is not news — the owner
	already saw that reaction and cleared the bell, and re-raising it says "1 person
	reacted to your post" about a reaction that no longer exists. Swapping one emoji
	for another in a single batch (the debounced tap-tap the frontend sends) leaves
	the table the same size but *is* a new reaction, and has to notify.
	"""

	def bell_count(self, user):
		with self.as_user(user):
			return unread_notifications()

	def clear_bell(self, user):
		with self.as_user(user):
			mark_all_notifications_as_read()

	def notification(self, user, discussion):
		return frappe.db.get_value(
			"GP Notification",
			{"to_user": user.name, "type": "Reaction", "discussion": discussion.name},
			["read", "message"],
			as_dict=True,
		)

	def test_withdrawing_a_reaction_does_not_re_light_a_cleared_bell(self):
		self.react(self.discussion, self.second_member, [add(THUMBS_UP)])
		self.react(self.discussion, self.admin, [add(HEART)])
		self.clear_bell(self.member)

		self.react(self.discussion, self.admin, [remove(HEART)])

		self.assertEqual(self.bell_count(self.member), 0)
		self.assertEqual(self.notification(self.member, self.discussion).read, 1)

	def test_swapping_one_emoji_for_another_notifies(self):
		"""Remove + add in one batch keeps the table the same size, but the heart is a
		reaction the owner has never been told about."""
		self.react(self.discussion, self.second_member, [add(THUMBS_UP)])
		self.clear_bell(self.member)

		self.react(self.discussion, self.second_member, [remove(THUMBS_UP), add(HEART)])

		self.assertEqual(self.bell_count(self.member), 1)

	def test_a_save_that_leaves_the_reactions_alone_does_not_notify(self):
		self.react(self.discussion, self.second_member, [add(THUMBS_UP)])
		self.clear_bell(self.member)

		with self.as_user(self.member):
			discussion = frappe.get_doc("GP Discussion", self.discussion.name)
			discussion.title = "Welcome thread (edited)"
			discussion.save()

		self.assertEqual(self.bell_count(self.member), 0)

	def test_the_owner_reacting_to_their_own_post_never_lights_their_own_bell(self):
		"""Own reactions are excluded from the count, so adding one is not news either —
		even once someone else's reaction has put a notification row on the post."""
		self.react(self.discussion, self.second_member, [add(THUMBS_UP)])
		self.clear_bell(self.member)

		self.react(self.discussion, self.member, [add(HEART)])

		self.assertEqual(self.bell_count(self.member), 0)

	def test_the_message_counts_everyone_holding_a_reaction_after_the_change(self):
		self.react(self.discussion, self.second_member, [add(THUMBS_UP)])
		self.react(self.discussion, self.admin, [add(THUMBS_UP)])

		self.assertEqual(
			self.notification(self.member, self.discussion).message, "2 people reacted to your post"
		)


class TestReactionNotificationRouting(ReactionTestCase):
	"""A reaction notification has to name the post that was reacted to.

	The bell renders each row as a link, so the row carries the post in its own link field
	— `comment`, `poll` or `discussion` — and a reply additionally carries the thread it
	lives in, which is what lets the client open the thread and scroll to the reply.

	`notify_reactions` reuses one row per post rather than inserting one per reaction, so
	the same fields double as the lookup key. That makes them load-bearing twice over: a
	key that is not specific enough makes a reaction on a thread and a reaction on a reply
	inside it land on one row, and the second one silently overwrites the first.
	"""

	def notifications(self, user):
		rows = frappe.get_all(
			"GP Notification",
			filters={"to_user": user.name, "type": "Reaction"},
			fields=["name", "discussion", "comment", "poll"],
			order_by="creation asc",
		)
		# Link fields come back as "" or None depending on the backend; normalise so the
		# assertions below read as "points nowhere" rather than at one storage detail.
		return [
			frappe._dict(
				name=row.name,
				discussion=str(row.discussion) if row.discussion else None,
				comment=str(row.comment) if row.comment else None,
				poll=str(row.poll) if row.poll else None,
			)
			for row in rows
		]

	def test_a_comment_reaction_points_at_the_comment_and_its_thread(self):
		self.react(self.comment, self.second_member, [add(THUMBS_UP)])

		rows = self.notifications(self.member)
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0].comment, str(self.comment.name))
		self.assertEqual(rows[0].discussion, str(self.discussion.name))
		self.assertIsNone(rows[0].poll)

	def test_a_poll_reaction_points_at_the_poll_and_its_thread(self):
		self.react(self.poll, self.second_member, [add(THUMBS_UP)])

		rows = self.notifications(self.member)
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0].poll, str(self.poll.name))
		self.assertEqual(rows[0].discussion, str(self.discussion.name))
		self.assertIsNone(rows[0].comment)

	def test_a_discussion_reaction_points_at_the_discussion_alone(self):
		self.react(self.discussion, self.second_member, [add(THUMBS_UP)])

		rows = self.notifications(self.member)
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0].discussion, str(self.discussion.name))
		self.assertIsNone(rows[0].comment)
		self.assertIsNone(rows[0].poll)

	def test_a_thread_and_a_reply_inside_it_get_their_own_notifications(self):
		"""Both rows carry the same discussion, so only the emptiness of `comment` tells
		the thread's row apart from the reply's — the lookup has to say so."""
		self.react(self.comment, self.second_member, [add(THUMBS_UP)])
		self.react(self.discussion, self.second_member, [add(THUMBS_UP)])

		rows = self.notifications(self.member)
		self.assertEqual(len(rows), 2)
		self.assertEqual(len({row.name for row in rows}), 2)
		self.assertEqual({row.comment for row in rows}, {str(self.comment.name), None})

	def test_a_thread_and_a_poll_inside_it_get_their_own_notifications(self):
		self.react(self.poll, self.second_member, [add(THUMBS_UP)])
		self.react(self.discussion, self.second_member, [add(THUMBS_UP)])

		rows = self.notifications(self.member)
		self.assertEqual(len(rows), 2)
		self.assertEqual(len({row.name for row in rows}), 2)
		self.assertEqual({row.poll for row in rows}, {str(self.poll.name), None})

	def test_the_order_the_reactions_arrive_in_does_not_merge_them(self):
		"""The reverse of the two tests above: the thread's row exists first, and the
		reply's reaction must still get a row of its own rather than claiming that one."""
		self.react(self.discussion, self.second_member, [add(THUMBS_UP)])
		self.react(self.comment, self.second_member, [add(THUMBS_UP)])
		self.react(self.poll, self.second_member, [add(THUMBS_UP)])

		rows = self.notifications(self.member)
		self.assertEqual(len(rows), 3)
		self.assertEqual(
			{(row.comment, row.poll) for row in rows},
			{(None, None), (str(self.comment.name), None), (None, str(self.poll.name))},
		)

	def test_two_replies_in_one_thread_get_their_own_notifications(self):
		other_comment = create_comment(self.discussion, content="Second reply", owner=self.member)

		self.react(self.comment, self.second_member, [add(THUMBS_UP)])
		self.react(other_comment, self.second_member, [add(THUMBS_UP)])

		rows = self.notifications(self.member)
		self.assertEqual(len(rows), 2)
		self.assertEqual({row.comment for row in rows}, {str(self.comment.name), str(other_comment.name)})


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

	def test_saving_a_copy_of_the_post_loaded_before_a_reaction_keeps_the_reaction(self):
		with self.as_user(self.member):
			loaded_before = frappe.get_doc("GP Discussion", self.discussion.name)

		self.react(self.discussion, self.second_member, [add(THUMBS_UP)])
		with self.as_user(self.member):
			loaded_before.title = "Welcome thread (edited)"
			loaded_before.save()

		self.assertEqual(self.stored_reactions(self.discussion), [(self.second_member.name, THUMBS_UP)])


class TestReactionsGoWithTheirPost(ReactionTestCase):
	"""Only System Manager may delete GP Reaction rows, so these delete as the post's owner,
	an ordinary member, to show someone else's reaction does not block the delete."""

	def test_deleting_a_comment_deletes_its_reactions(self):
		self.react(self.comment, self.second_member, [add(THUMBS_UP)])

		with self.as_user(self.member):
			frappe.delete_doc("GP Comment", self.comment.name)

		self.assertEqual(self.stored_reactions(self.comment), [])

	def test_deleting_a_poll_deletes_its_reactions(self):
		self.react(self.poll, self.second_member, [add(THUMBS_UP)])

		with self.as_user(self.member):
			frappe.delete_doc("GP Poll", self.poll.name)

		self.assertEqual(self.stored_reactions(self.poll), [])

	def test_deleting_a_discussion_deletes_the_reactions_in_its_thread(self):
		for post in (self.discussion, self.comment, self.poll):
			self.react(post, self.second_member, [add(THUMBS_UP)])

		with self.as_user(self.member):
			frappe.delete_doc("GP Discussion", self.discussion.name)

		for post in (self.discussion, self.comment, self.poll):
			self.assertEqual(self.stored_reactions(post), [])


class TestThreadReactions(ReactionTestCase):
	"""A thread page loads the reactions of everything in it with one request."""

	def thread_reactions(self, doc, user):
		with self.as_user(user):
			return [
				(row.reference_doctype, str(row.reference_name), row.user, row.emoji)
				for row in frappe.get_doc(doc.doctype, doc.name).thread_reactions()
			]

	def test_a_discussion_thread_has_the_reactions_of_the_post_its_comments_and_polls(self):
		self.react(self.discussion, self.second_member, [add(THUMBS_UP)])
		self.react(self.comment, self.second_member, [add(HEART)])
		self.react(self.poll, self.member, [add(THUMBS_UP)])

		self.assertEqual(
			self.thread_reactions(self.discussion, self.member),
			[
				("GP Discussion", str(self.discussion.name), self.second_member.name, THUMBS_UP),
				("GP Comment", str(self.comment.name), self.second_member.name, HEART),
				("GP Poll", str(self.poll.name), self.member.name, THUMBS_UP),
			],
		)

	def test_a_thread_leaves_out_reactions_from_other_threads(self):
		other = create_discussion("Other thread", self.space, owner=self.member)
		other_comment = create_comment(other, owner=self.member)
		self.react(other, self.second_member, [add(THUMBS_UP)])
		self.react(other_comment, self.second_member, [add(THUMBS_UP)])

		self.assertEqual(self.thread_reactions(self.discussion, self.member), [])

	def test_a_task_thread_has_the_reactions_of_its_comments(self):
		task = create_task("Ship it", self.space, owner=self.member)
		comment = frappe.get_doc(
			doctype="GP Comment", reference_doctype="GP Task", reference_name=task.name, content="Done"
		).insert(ignore_permissions=True)
		self.react(comment, self.second_member, [add(HEART)])

		self.assertEqual(
			self.thread_reactions(task, self.member),
			[("GP Comment", str(comment.name), self.second_member.name, HEART)],
		)
