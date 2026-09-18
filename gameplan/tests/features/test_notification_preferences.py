# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""Who a notification reaches once the user has a say.

Two things decide it. The global level on `GP User Profile` (`notification_level`:
Mentions only or Mute) is the default for every discussion the user has not touched. A
`GP Discussion Subscription` row is a deliberate choice on one discussion — Mute,
Mentions only or Watch — and it wins over the global level whenever it exists. Nothing
the user *does* (commenting, reading, being mentioned) ever writes a row for them; only
the bell, or the "Watch discussions I start" checkbox at creation, does.

Reactions and poll votes are about the user's own content and follow only their own
toggles; the discussion's state never enters into it.

`features/test_notifications.py` owns what a mention or reaction *says* and how rows are
cleared; this file owns whether the row is written at all.
"""

import frappe

from gameplan.notifications.resolver import effective_discussion_state
from gameplan.tests.base import GameplanTestCase
from gameplan.tests.features.test_notifications import mention_html, quote_html
from gameplan.tests.fixtures import (
	_name,
	create_comment,
	create_community,
	create_discussion,
	create_space,
)

THUMBS_UP = "\U0001f44d"


class PreferenceTestCase(GameplanTestCase):
	def setUp(self):
		super().setUp()
		self.notifications_before = set(frappe.get_all("GP Notification", pluck="name"))
		self.community = create_community("Acme", members=[self.member, self.second_member, self.admin])
		self.space = create_space("Engineering", self.community)
		with self.as_user(self.member):
			self.discussion = create_discussion("Welcome thread", self.space)

	def set_prefs(self, user, **fields):
		profile = frappe.db.get_value("GP User Profile", {"user": _name(user)}, "name")
		frappe.db.set_value("GP User Profile", profile, fields)

	def subscribe(self, user, discussion, state):
		return frappe.get_doc(
			doctype="GP Discussion Subscription",
			user=_name(user),
			discussion=_name(discussion),
			state=state,
		).insert(ignore_permissions=True)

	def subscription_rows(self, user, discussion):
		return frappe.get_all(
			"GP Discussion Subscription",
			filters={"user": _name(user), "discussion": _name(discussion)},
			fields=["name", "state"],
		)

	def notifications_for(self, user, **filters):
		rows = frappe.get_all(
			"GP Notification",
			filters={"to_user": _name(user), **filters},
			fields=["name", "type", "message", "from_user", "discussion", "read", "event_count"],
		)
		return [row for row in rows if row.name not in self.notifications_before]

	def mention_second_member(self, author=None, discussion=None):
		with self.as_user(author or self.member):
			return create_comment(
				discussion or self.discussion,
				content=mention_html(self.second_member, "Second Member"),
			)

	def comment_as(self, user, discussion=None, content="A reply"):
		with self.as_user(user):
			return create_comment(discussion or self.discussion, content=content)

	def react_as(self, user, doc):
		with self.as_user(user):
			frappe.get_doc(doc.doctype, doc.name).react(operations=[{"emoji": THUMBS_UP, "operation": "add"}])

	def set_state(self, user, discussion, state):
		with self.as_user(user):
			return frappe.get_doc("GP Discussion", _name(discussion)).set_notification_state(state)


class TestGlobalLevel(PreferenceTestCase):
	def test_a_fresh_profile_is_on_mentions_only(self):
		state = effective_discussion_state(self.second_member.name, self.discussion.name)
		self.assertEqual(state, "Mentions only")

	def test_mentions_only_lets_a_mention_through(self):
		self.mention_second_member()

		self.assertEqual([r.type for r in self.notifications_for(self.second_member)], ["Mention"])

	def test_mentions_only_lets_a_rich_quote_through(self):
		with self.as_user(self.member):
			create_comment(self.discussion, content=quote_html(self.second_member))

		self.assertEqual([r.type for r in self.notifications_for(self.second_member)], ["Rich Quote"])

	def test_mentions_only_does_not_notify_a_plain_comment(self):
		"""Nobody watches by default: a reply lands in unread counts, not the bell."""
		self.comment_as(self.second_member)

		self.assertEqual(self.notifications_for(self.member), [])

	def test_global_mute_silences_a_mention_in_an_untouched_discussion(self):
		self.set_prefs(self.second_member, notification_level="Mute")

		self.mention_second_member()

		self.assertEqual(self.notifications_for(self.second_member), [])

	def test_global_mute_silences_a_rich_quote_in_an_untouched_discussion(self):
		self.set_prefs(self.second_member, notification_level="Mute")

		with self.as_user(self.member):
			create_comment(self.discussion, content=quote_html(self.second_member))

		self.assertEqual(self.notifications_for(self.second_member), [])

	def test_global_mute_silences_everyone_in_an_untouched_discussion(self):
		self.set_prefs(self.second_member, notification_level="Mute")

		with self.as_user(self.member):
			create_comment(self.discussion, content=mention_html("_everyone_", "Everyone"))

		self.assertEqual(self.notifications_for(self.second_member), [])
		# Someone who is not muted still hears the @everyone.
		self.assertEqual([r.type for r in self.notifications_for(self.admin)], ["Mention"])

	def test_global_mute_does_not_touch_task_mentions(self):
		"""Tasks have no discussion to mute; a mention there behaves as it always has."""
		from gameplan.tests.fixtures import create_task

		self.set_prefs(self.second_member, notification_level="Mute")

		with self.as_user(self.member):
			task = create_task("A task", self.space)
			task.description = mention_html(self.second_member, "Second Member")
			task.save()

		self.assertEqual([r.type for r in self.notifications_for(self.second_member)], ["Mention"])


class TestDiscussionState(PreferenceTestCase):
	def test_watch_notifies_every_comment(self):
		self.subscribe(self.second_member, self.discussion, "Watch")

		self.comment_as(self.member)

		rows = self.notifications_for(self.second_member)
		self.assertEqual([r.type for r in rows], ["Comment"])
		self.assertEqual(rows[0].from_user, self.member.name)
		self.assertEqual(str(rows[0].discussion), str(self.discussion.name))
		self.assertIn("commented on Welcome thread", rows[0].message)

	def test_watch_beats_a_global_mute(self):
		"""Explicit beats default: the one thing a global Mute never overrides."""
		self.set_prefs(self.second_member, notification_level="Mute")
		self.subscribe(self.second_member, self.discussion, "Watch")

		self.comment_as(self.member)
		self.mention_second_member()

		self.assertEqual(
			sorted(r.type for r in self.notifications_for(self.second_member)), ["Comment", "Mention"]
		)

	def test_an_explicit_mentions_only_survives_a_global_change(self):
		self.subscribe(self.second_member, self.discussion, "Mentions only")
		self.set_prefs(self.second_member, notification_level="Mute")

		self.mention_second_member()

		self.assertEqual([r.type for r in self.notifications_for(self.second_member)], ["Mention"])
		[row] = self.subscription_rows(self.second_member, self.discussion)
		self.assertEqual(row.state, "Mentions only")

	def test_a_muted_discussion_blocks_a_direct_mention(self):
		self.subscribe(self.second_member, self.discussion, "Mute")

		self.mention_second_member()

		self.assertEqual(self.notifications_for(self.second_member), [])

	def test_a_muted_discussion_blocks_everyone(self):
		self.subscribe(self.second_member, self.discussion, "Mute")

		with self.as_user(self.member):
			create_comment(self.discussion, content=mention_html("_everyone_", "Everyone"))

		self.assertEqual(self.notifications_for(self.second_member), [])
		self.assertEqual([r.type for r in self.notifications_for(self.admin)], ["Mention"])

	def test_a_muted_discussion_blocks_a_rich_quote(self):
		self.subscribe(self.second_member, self.discussion, "Mute")

		with self.as_user(self.member):
			create_comment(self.discussion, content=quote_html(self.second_member))

		self.assertEqual(self.notifications_for(self.second_member), [])

	def test_a_mute_on_one_discussion_leaves_another_alone(self):
		self.subscribe(self.second_member, self.discussion, "Mute")
		with self.as_user(self.member):
			other = create_discussion("Other thread", self.space)

		self.mention_second_member(discussion=other)

		self.assertEqual([r.type for r in self.notifications_for(self.second_member)], ["Mention"])

	def test_the_author_is_never_told_about_their_own_comment(self):
		self.subscribe(self.member, self.discussion, "Watch")

		self.comment_as(self.member)

		self.assertEqual(self.notifications_for(self.member), [])

	def test_a_watcher_who_cannot_see_the_space_is_not_told(self):
		private = create_space("Secret", self.community, is_private=1, members=[self.member])
		with self.as_user(self.member):
			hidden = create_discussion("Hidden", private)
		self.subscribe(self.second_member, hidden, "Watch")

		self.comment_as(self.member, discussion=hidden)

		self.assertEqual(self.notifications_for(self.second_member), [])


class TestWatchAndMentionTogether(PreferenceTestCase):
	def test_a_mentioned_watcher_gets_the_mention_and_nothing_else(self):
		"""One comment, one notification: the mention pass runs first and the watcher
		fan-out leaves out everyone it reached."""
		self.subscribe(self.second_member, self.discussion, "Watch")

		self.mention_second_member()

		self.assertEqual([r.type for r in self.notifications_for(self.second_member)], ["Mention"])

	def test_a_watcher_who_was_not_mentioned_still_gets_the_comment(self):
		self.subscribe(self.second_member, self.discussion, "Watch")
		self.subscribe(self.admin, self.discussion, "Watch")

		self.mention_second_member()

		self.assertEqual([r.type for r in self.notifications_for(self.admin)], ["Comment"])


class TestCommentMerging(PreferenceTestCase):
	def setUp(self):
		super().setUp()
		self.subscribe(self.second_member, self.discussion, "Watch")

	def test_a_second_comment_folds_into_the_unread_row(self):
		self.comment_as(self.member)
		self.comment_as(self.admin)

		rows = self.notifications_for(self.second_member)
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0].event_count, 2)
		self.assertEqual(rows[0].read, 0)
		self.assertEqual(rows[0].message, "2 new comments in Welcome thread")
		self.assertIsNone(rows[0].from_user)

	def test_a_comment_after_the_row_was_read_starts_a_fresh_row(self):
		self.comment_as(self.member)
		with self.as_user(self.second_member):
			frappe.get_doc("GP Discussion", self.discussion.name).track_visit()

		self.comment_as(self.admin)

		rows = sorted(self.notifications_for(self.second_member), key=lambda r: r.read)
		self.assertEqual([(r.read, r.event_count) for r in rows], [(0, 1), (1, 1)])

	def test_editing_a_comment_does_not_notify_again(self):
		comment = self.comment_as(self.member)

		with self.as_user(self.member):
			comment.reload()
			comment.content = "<p>Fixed a typo</p>"
			comment.save()

		rows = self.notifications_for(self.second_member)
		self.assertEqual([r.event_count for r in rows], [1])

	def test_a_merged_row_moves_its_event_time_forward(self):
		self.comment_as(self.member)
		[row] = self.notifications_for(self.second_member)
		frappe.db.set_value("GP Notification", row.name, "last_event_at", "2020-01-01 00:00:00")

		self.comment_as(self.admin)

		self.assertGreater(
			str(frappe.db.get_value("GP Notification", row.name, "last_event_at")), "2020-01-02"
		)


class TestSetNotificationState(PreferenceTestCase):
	def test_setting_a_state_writes_the_row(self):
		result = self.set_state(self.second_member, self.discussion, "Watch")

		self.assertEqual(result, {"notification_state": "Watch", "notification_state_is_explicit": True})
		self.assertEqual(self.subscription_rows(self.second_member, self.discussion)[0].state, "Watch")

	def test_setting_again_updates_the_same_row(self):
		self.set_state(self.second_member, self.discussion, "Watch")
		self.set_state(self.second_member, self.discussion, "Mute")

		rows = self.subscription_rows(self.second_member, self.discussion)
		self.assertEqual([r.state for r in rows], ["Mute"])

	def test_default_deletes_the_row_and_follows_global_again(self):
		self.set_state(self.second_member, self.discussion, "Watch")
		self.set_prefs(self.second_member, notification_level="Mute")

		result = self.set_state(self.second_member, self.discussion, "Default")

		self.assertEqual(self.subscription_rows(self.second_member, self.discussion), [])
		self.assertEqual(result, {"notification_state": "Mute", "notification_state_is_explicit": False})

	def test_default_with_no_row_is_a_no_op(self):
		result = self.set_state(self.second_member, self.discussion, "Default")

		self.assertEqual(result["notification_state"], "Mentions only")

	def test_an_unknown_state_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			self.set_state(self.second_member, self.discussion, "Loud")

	def test_the_discussion_reports_the_callers_state(self):
		self.set_state(self.second_member, self.discussion, "Watch")

		with self.as_user(self.second_member):
			d = frappe.get_doc("GP Discussion", self.discussion.name).as_dict()
		self.assertEqual(d.notification_state, "Watch")
		self.assertTrue(d.notification_state_is_explicit)

		with self.as_user(self.member):
			d = frappe.get_doc("GP Discussion", self.discussion.name).as_dict()
		self.assertEqual(d.notification_state, "Mentions only")
		self.assertFalse(d.notification_state_is_explicit)

	def test_a_row_is_private_to_its_user(self):
		row = self.subscribe(self.second_member, self.discussion, "Watch")

		self.assert_permission(row, "read", self.second_member, True)
		self.assert_permission(row, "write", self.second_member, True)
		self.assert_permission(row, "delete", self.second_member, True)
		self.assert_permission(row, "read", self.member, False)
		self.assert_permission(row, "write", self.member, False)
		self.assert_permission(row, "delete", self.member, False)

	def test_the_list_shows_only_your_own_rows(self):
		self.subscribe(self.second_member, self.discussion, "Watch")
		self.subscribe(self.member, self.discussion, "Mute")

		with self.as_user(self.member):
			rows = frappe.get_list("GP Discussion Subscription", fields=["user", "state"])
		self.assertEqual([(r.user, r.state) for r in rows], [(self.member.name, "Mute")])

	def test_deleting_the_discussion_takes_the_rows_with_it(self):
		self.subscribe(self.second_member, self.discussion, "Watch")

		frappe.delete_doc("GP Discussion", self.discussion.name, force=True)

		self.assertEqual(self.subscription_rows(self.second_member, self.discussion), [])


class TestWatchDiscussionsIStart(PreferenceTestCase):
	def test_on_writes_a_watch_row_at_creation(self):
		self.set_prefs(self.member, watch_own_discussions=1)

		with self.as_user(self.member):
			discussion = create_discussion("Mine", self.space)

		self.assertEqual(self.subscription_rows(self.member, discussion)[0].state, "Watch")

	def test_off_writes_nothing(self):
		with self.as_user(self.member):
			discussion = create_discussion("Mine", self.space)

		self.assertEqual(self.subscription_rows(self.member, discussion), [])

	def test_the_author_then_hears_every_reply(self):
		self.set_prefs(self.member, watch_own_discussions=1)
		with self.as_user(self.member):
			discussion = create_discussion("Mine", self.space)

		self.comment_as(self.second_member, discussion=discussion)

		self.assertEqual([r.type for r in self.notifications_for(self.member)], ["Comment"])

	def test_turning_the_checkbox_off_later_leaves_earlier_rows_alone(self):
		self.set_prefs(self.member, watch_own_discussions=1)
		with self.as_user(self.member):
			discussion = create_discussion("Mine", self.space)
		self.set_prefs(self.member, watch_own_discussions=0)

		self.assertEqual(self.subscription_rows(self.member, discussion)[0].state, "Watch")


class TestOwnContentToggles(PreferenceTestCase):
	def test_reactions_follow_the_toggle_not_the_discussion_state(self):
		"""A reaction is feedback on the owner's own content: a muted discussion does not
		stop it, and neither does a global Mute."""
		self.subscribe(self.member, self.discussion, "Mute")
		self.set_prefs(self.member, notification_level="Mute")

		self.react_as(self.second_member, self.discussion)

		self.assertEqual([r.type for r in self.notifications_for(self.member)], ["Reaction"])

	def test_the_reactions_toggle_off_writes_no_row(self):
		self.set_prefs(self.member, notify_reactions=0)

		self.react_as(self.second_member, self.discussion)

		self.assertEqual(self.notifications_for(self.member), [])

	def test_the_reactions_toggle_off_stops_re_lighting_an_old_row_too(self):
		self.react_as(self.second_member, self.discussion)
		[row] = self.notifications_for(self.member)
		frappe.db.set_value("GP Notification", row.name, "read", 1)
		self.set_prefs(self.member, notify_reactions=0)

		self.react_as(self.admin, self.discussion)

		self.assertEqual(frappe.db.get_value("GP Notification", row.name, "read"), 1)
