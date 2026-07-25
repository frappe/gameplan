# Copyright (c) 2022, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""Notification behaviour.

What creates a GP Notification, who it reaches, and how it gets cleared.

Gameplan has two separate "something happened" channels, and this file only owns the
first one:

- **GP Notification** (the bell + its badge) — someone addressed *you*: a mention, an
  @everyone mention, a rich quote of your words, a reaction on your post.
- **GP Unread Record** (space/discussion unread counts, `features/test_unread.py`) —
  new content in a space you can see, including a plain reply on your own discussion.

So a plain reply does NOT create a notification; it lands in the reply author's
co-members' unread records instead (see
`test_plain_reply_reaches_the_owner_through_unread_records_not_the_bell`). The email
digest mirrors the same split: `get_unread_notifications` vs `get_unread_discussions`.
"""

import frappe

from gameplan.api import mark_all_notifications_as_read, unread_notifications
from gameplan.gameplan.doctype.gp_notification.gp_notification import GPNotification
from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import (
	_name,
	create_comment,
	create_community,
	create_discussion,
	create_member,
	create_space,
)


def mention_html(user, label="Someone", body="Hey"):
	"""The HTML TipTap stores for an @-mention (`_everyone_` for the everyone entry)."""
	email = user if isinstance(user, str) else user.name
	return f'<p>{body} <span data-type="mention" data-id="{email}" data-label="{label}">@{label}</span></p>'


def quote_html(author, quoted="Original words", body="Answering that"):
	"""The HTML the rich-quote extension stores when you reply to someone's selection."""
	email = author if isinstance(author, str) else author.name
	return f'<blockquote data-author="{email}"><p>{quoted}</p></blockquote><p>{body}</p>'


def _make_notification(to_user, **kwargs):
	return frappe.get_doc(doctype="GP Notification", to_user=to_user, type="Mention", **kwargs).insert(
		ignore_permissions=True
	)


class NotificationTestCase(GameplanTestCase):
	"""Personas plus a community/space both members can reach.

	The site can already hold notifications addressed to these same persona emails (the
	Cypress seed uses them too, and an E2E run leaves its mention behind). So instead of
	wiping the table — which would clear another suite's rows and hide ordering bugs —
	every assertion here is scoped: `notifications_for` ignores rows that predate the
	test, and the count tests assert a delta against the endpoint's starting value.
	"""

	def setUp(self):
		super().setUp()
		self.notifications_before = set(frappe.get_all("GP Notification", pluck="name"))
		self.community = create_community("Acme", members=[self.member, self.second_member])
		self.space = create_space("Engineering", self.community)

	def notifications_for(self, user, **filters):
		"""The GP Notification rows this test created for `user`."""
		rows = frappe.get_all(
			"GP Notification",
			filters={"to_user": _name(user), **filters},
			fields=["name", "type", "message", "from_user", "discussion", "comment", "task", "read"],
		)
		return [row for row in rows if row.name not in self.notifications_before]

	def unread_count(self, user):
		"""What `gameplan.api.unread_notifications` reports for `user` right now."""
		with self.as_user(user):
			return unread_notifications()


class TestMentionNotifications(NotificationTestCase):
	def test_mention_in_a_discussion_notifies_the_mentioned_user(self):
		with self.as_user(self.member):
			discussion = create_discussion(
				"Mention thread", self.space, content=mention_html(self.second_member, "Second Member")
			)

		rows = self.notifications_for(self.second_member)
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0].type, "Mention")
		self.assertEqual(rows[0].from_user, self.member.name)
		self.assertEqual(str(rows[0].discussion), str(discussion.name))
		self.assertEqual(rows[0].read, 0)
		self.assertIn("mentioned you", rows[0].message)

	def test_mention_in_a_comment_notifies_the_mentioned_user_and_links_the_discussion(self):
		discussion = create_discussion("Plain thread", self.space, owner=self.member)
		with self.as_user(self.member):
			comment = create_comment(discussion, content=mention_html(self.second_member, "Second Member"))

		rows = self.notifications_for(self.second_member)
		self.assertEqual(len(rows), 1)
		self.assertEqual(str(rows[0].comment), str(comment.name))
		# The discussion link is what makes the bell row navigable (Notifications.vue).
		self.assertEqual(str(rows[0].discussion), str(discussion.name))

	def test_mentioning_yourself_creates_no_notification(self):
		with self.as_user(self.member):
			create_discussion("Self mention", self.space, content=mention_html(self.member, "Member"))

		self.assertEqual(self.notifications_for(self.member), [])

	def test_editing_a_post_does_not_duplicate_an_existing_mention(self):
		with self.as_user(self.member):
			discussion = create_discussion(
				"Mention thread", self.space, content=mention_html(self.second_member, "Second Member")
			)
			discussion.content = mention_html(self.second_member, "Second Member", body="Hey, edited")
			discussion.save()

		self.assertEqual(len(self.notifications_for(self.second_member)), 1)

	def test_everyone_mention_notifies_the_other_members_but_not_the_author(self):
		with self.as_user(self.member):
			create_discussion("Everyone thread", self.space, content=mention_html("_everyone_", "Everyone"))

		rows = self.notifications_for(self.second_member)
		self.assertEqual(len(rows), 1)
		self.assertIn("mentioned everyone", rows[0].message)
		self.assertEqual(self.notifications_for(self.member), [])

	def test_everyone_mention_skips_users_who_cannot_see_the_space(self):
		"""An @everyone in a private space must not reach the whole site.

		The notification row carries the discussion, and the bell list joins its title,
		so notifying a user who cannot open the space both leaks the title and hands
		them a dead link.
		"""
		private_space = create_space(
			"Secret Plans", self.community, is_private=1, members=[self.member, self.second_member]
		)
		with self.as_user(self.member):
			create_discussion(
				"Everyone thread", private_space, content=mention_html("_everyone_", "Everyone")
			)

		self.assertEqual(len(self.notifications_for(self.second_member)), 1)
		self.assertEqual(self.notifications_for(self.outsider), [])

	def test_mentioning_a_user_who_cannot_see_the_space_creates_no_notification(self):
		"""The mention autocomplete offers every active user, not just space members."""
		private_space = create_space("Secret Plans", self.community, is_private=1, members=[self.member])
		with self.as_user(self.member):
			create_discussion("Secret thread", private_space, content=mention_html(self.outsider, "Outsider"))

		self.assertEqual(self.notifications_for(self.outsider), [])

	def test_rich_quote_notifies_the_quoted_author(self):
		discussion = create_discussion("Plain thread", self.space, owner=self.second_member)
		with self.as_user(self.member):
			create_comment(discussion, content=quote_html(self.second_member))

		rows = self.notifications_for(self.second_member)
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0].type, "Rich Quote")
		self.assertIn("quoted you", rows[0].message)

	def test_quoting_yourself_creates_no_notification(self):
		discussion = create_discussion("Plain thread", self.space, owner=self.member)
		with self.as_user(self.member):
			create_comment(discussion, content=quote_html(self.member))

		self.assertEqual(self.notifications_for(self.member), [])

	def test_a_mentioned_quoted_author_is_notified_only_once(self):
		discussion = create_discussion("Plain thread", self.space, owner=self.second_member)
		content = quote_html(self.second_member) + mention_html(self.second_member, "Second Member")
		with self.as_user(self.member):
			create_comment(discussion, content=content)

		rows = self.notifications_for(self.second_member)
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0].type, "Mention")


class TestReplyNotifications(NotificationTestCase):
	def setUp(self):
		super().setUp()
		self.discussion = create_discussion("Welcome thread", self.space, owner=self.member)

	def test_reply_mentioning_the_discussion_owner_notifies_them(self):
		with self.as_user(self.second_member):
			create_comment(self.discussion, content=mention_html(self.member, "Member"))

		rows = self.notifications_for(self.member)
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0].from_user, self.second_member.name)
		self.assertEqual(str(rows[0].discussion), str(self.discussion.name))

	def test_reply_quoting_the_discussion_owner_notifies_them(self):
		with self.as_user(self.second_member):
			create_comment(self.discussion, content=quote_html(self.member))

		rows = self.notifications_for(self.member)
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0].type, "Rich Quote")

	def test_plain_reply_reaches_the_owner_through_unread_records_not_the_bell(self):
		"""Replies are an unread-record concern, not a bell notification.

		Notifying on every reply would double up with the space/discussion unread
		counts (and the digest's "unread discussions" section) and would make the bell
		unusable on a busy thread.
		"""
		with self.as_user(self.second_member):
			comment = create_comment(self.discussion, content="<p>Just replying</p>")

		self.assertEqual(self.notifications_for(self.member), [])
		self.assertTrue(
			frappe.db.exists(
				"GP Unread Record",
				{"user": self.member.name, "comment": comment.name, "is_unread": 1},
			)
		)

	def test_owners_own_reply_notifies_nobody(self):
		with self.as_user(self.member):
			create_comment(self.discussion, content="<p>Following up on my own post</p>")

		self.assertEqual(self.notifications_for(self.member), [])
		self.assertEqual(self.notifications_for(self.second_member), [])


class TestReactionNotifications(NotificationTestCase):
	def setUp(self):
		super().setUp()
		self.discussion = create_discussion("Welcome thread", self.space, owner=self.member)

	def _react(self, doc, user, emoji="👍"):
		with self.as_user(user):
			frappe.get_doc(doc.doctype, doc.name).react(operations=[{"emoji": emoji, "operation": "add"}])

	def test_reaction_notifies_the_post_owner(self):
		self._react(self.discussion, self.second_member)

		rows = self.notifications_for(self.member)
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0].type, "Reaction")
		self.assertEqual(rows[0].message, "1 person reacted to your post")
		self.assertEqual(str(rows[0].discussion), str(self.discussion.name))

	def test_reacting_to_your_own_post_creates_no_notification(self):
		self._react(self.discussion, self.member)

		self.assertEqual(self.notifications_for(self.member), [])

	def test_your_own_reaction_is_not_counted_in_the_message(self):
		self._react(self.discussion, self.second_member)
		self._react(self.discussion, self.member, emoji="💖")

		rows = self.notifications_for(self.member)
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0].message, "1 person reacted to your post")


class TestUnreadNotificationsCount(NotificationTestCase):
	def test_counts_only_the_session_users_unread_rows(self):
		before = {
			user.name: self.unread_count(user)
			for user in (self.member, self.second_member, self.outsider)
		}
		_make_notification(self.member.name, read=0)
		_make_notification(self.member.name, read=0)
		_make_notification(self.member.name, read=1)
		_make_notification(self.second_member.name, read=0)

		# Two of member's four rows are unread and one belongs to member2; the count is
		# per session user and ignores rows already marked read.
		self.assertEqual(self.unread_count(self.member), before[self.member.name] + 2)
		self.assertEqual(self.unread_count(self.second_member), before[self.second_member.name] + 1)
		self.assertEqual(self.unread_count(self.outsider), before[self.outsider.name])

	def test_a_new_mention_increments_the_count(self):
		before = self.unread_count(self.second_member)

		space = create_space("Product", self.community)
		with self.as_user(self.member):
			create_discussion(
				"Mention thread", space, content=mention_html(self.second_member, "Second Member")
			)

		self.assertEqual(self.unread_count(self.second_member), before + 1)


class TestMarkNotificationsAsRead(NotificationTestCase):
	def test_mark_all_notifications_as_read_clears_the_count(self):
		_make_notification(self.member.name, read=0)
		_make_notification(self.member.name, read=0)

		with self.as_user(self.member):
			mark_all_notifications_as_read()

		# Nothing of member's is left unread, whatever the table held before.
		self.assertEqual(self.unread_count(self.member), 0)

	def test_mark_all_notifications_as_read_leaves_other_users_alone(self):
		mine = _make_notification(self.member.name, read=0)
		theirs = _make_notification(self.second_member.name, read=0)

		with self.as_user(self.member):
			mark_all_notifications_as_read()

		self.assertEqual(frappe.db.get_value("GP Notification", mine.name, "read"), 1)
		self.assertEqual(frappe.db.get_value("GP Notification", theirs.name, "read"), 0)

	def test_clear_notifications_marks_matching_rows_read(self):
		discussion = create_discussion("Clear D1", self.space, content="x")
		matching = _make_notification(self.member.name, discussion=discussion.name, read=0)
		unrelated = _make_notification(self.member.name, read=0)

		GPNotification.clear_notifications(discussion=discussion.name, user=self.member.name)

		# Only the discussion-scoped row is cleared; the unrelated one stays unread.
		self.assertEqual(frappe.db.get_value("GP Notification", matching.name, "read"), 1)
		self.assertEqual(frappe.db.get_value("GP Notification", unrelated.name, "read"), 0)

	def test_clear_notifications_handles_empty_link_values_for_autoincrement_names(self):
		user = create_member("test_notification_empty_link@example.com")
		discussion = create_discussion("Notification Empty Link Discussion", self.space)
		comment = create_comment(discussion, content="Unrelated notification")
		matching = _make_notification(user.name, discussion=discussion.name, read=0)
		unrelated = _make_notification(user.name, discussion="", comment=comment.name, read=0)

		GPNotification.clear_notifications(discussion=discussion.name, user=user.name)

		self.assertEqual(frappe.db.get_value("GP Notification", matching.name, "read"), 1)
		self.assertEqual(frappe.db.get_value("GP Notification", unrelated.name, "read"), 0)
