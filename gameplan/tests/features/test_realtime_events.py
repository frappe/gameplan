# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""The events Gameplan publishes so open tabs update themselves.

These replace `refetch_resource`, which named a frappe-ui `createResource` cache key and
asked the client to reload whatever sat under it. Once the frontend moved to `useCall`,
those keys resolved to nothing and every push became a silent no-op — the notification
badge and the shared user list stopped updating live and no test noticed, because the
old tests only checked that a cache key had been published.

So these assert at `frappe.realtime.publish_realtime`: the event name and the room it
lands in, which is what determines whether a browser actually hears it.
"""

from unittest.mock import patch

import frappe

from gameplan.realtime import (
	NOTIFICATION_COUNT_CHANGED,
	UNREAD_COUNTS_CHANGED,
	USERS_CHANGED,
	notify_unread_counts_changed,
	notify_users_changed,
)
from gameplan.tests.base import GameplanTestCase


def events_named(publish_realtime, event):
	return [call for call in publish_realtime.call_args_list if call.args and call.args[0] == event]


class TestRealtimeEvents(GameplanTestCase):
	def notification_for(self, user, read):
		return frappe.get_doc(
			doctype="GP Notification",
			to_user=user.name,
			from_user=self.member.name,
			type="Reaction",
			message="1 person reacted to your post",
			read=read,
		).insert(ignore_permissions=True)

	def test_a_new_notification_tells_its_recipient(self):
		with patch("frappe.realtime.publish_realtime") as publish_realtime:
			frappe.get_doc(
				doctype="GP Notification",
				to_user=self.second_member.name,
				from_user=self.member.name,
				type="Mention",
				message="Hello",
			).insert(ignore_permissions=True)

		[call] = events_named(publish_realtime, NOTIFICATION_COUNT_CHANGED)
		self.assertEqual(call.kwargs.get("user"), self.second_member.name)

	def test_re_lighting_a_cleared_notification_tells_its_recipient_again(self):
		"""A reaction rewrites the post's existing notification row instead of adding one.

		`HasReactions.notify_reactions` resets `read` on that row, so the count moves on an
		UPDATE. An insert-only hook left the badge stale in every open tab until a reload.
		"""
		notification = self.notification_for(self.second_member, read=1)

		with patch("frappe.realtime.publish_realtime") as publish_realtime:
			notification.read = 0
			notification.flags.ignore_permissions = True
			notification.save()

		[call] = events_named(publish_realtime, NOTIFICATION_COUNT_CHANGED)
		self.assertEqual(call.kwargs.get("user"), self.second_member.name)

	def test_marking_one_notification_read_tells_that_user(self):
		"""The bell's per-row mark-as-read is a PUT, so the other tabs only hear about it
		if updates publish too."""
		notification = self.notification_for(self.second_member, read=0)

		with patch("frappe.realtime.publish_realtime") as publish_realtime:
			notification.read = 1
			notification.flags.ignore_permissions = True
			notification.save()

		[call] = events_named(publish_realtime, NOTIFICATION_COUNT_CHANGED)
		self.assertEqual(call.kwargs.get("user"), self.second_member.name)

	def test_an_edit_that_leaves_the_count_alone_announces_nothing(self):
		"""Re-lighting an already-unread row rewrites its message; the count has not moved."""
		notification = self.notification_for(self.second_member, read=0)

		with patch("frappe.realtime.publish_realtime") as publish_realtime:
			notification.message = "2 people reacted to your post"
			notification.flags.ignore_permissions = True
			notification.save()

		self.assertEqual(events_named(publish_realtime, NOTIFICATION_COUNT_CHANGED), [])

	def test_clearing_notifications_tells_that_user(self):
		from gameplan.gameplan.doctype.gp_notification.gp_notification import GPNotification

		with patch("frappe.realtime.publish_realtime") as publish_realtime:
			GPNotification.clear_notifications(user=self.member.name)

		[call] = events_named(publish_realtime, NOTIFICATION_COUNT_CHANGED)
		self.assertEqual(call.kwargs.get("user"), self.member.name)

	def test_the_user_list_change_reaches_website_users_not_just_desk_users(self):
		"""Gameplan members are Website Users, and only System Users join the site room.

		A roomless `publish_realtime` lands in the site room ("all"), so it would reach
		nobody here — the same silent-no-op shape this whole module exists to prevent.
		"""
		with patch("frappe.realtime.publish_realtime") as publish_realtime:
			notify_users_changed()

		[call] = events_named(publish_realtime, USERS_CHANGED)
		self.assertEqual(call.kwargs.get("room"), frappe.realtime.get_website_room())
		self.assertIsNone(call.kwargs.get("user"))

	def test_every_event_is_held_until_the_transaction_commits(self):
		"""A rolled-back request must not tell the browser about a change that never landed."""
		with patch("frappe.realtime.publish_realtime") as publish_realtime:
			notify_unread_counts_changed(self.member.name)
			notify_users_changed()

		for call in publish_realtime.call_args_list:
			self.assertTrue(call.kwargs.get("after_commit"), f"{call.args[0]} is not after_commit")

	def test_one_call_notifies_each_distinct_user_once(self):
		users = [self.member.name, self.second_member.name, self.member.name, None, ""]

		with patch("frappe.realtime.publish_realtime") as publish_realtime:
			notify_unread_counts_changed(users)

		notified = sorted(
			call.kwargs.get("user") for call in events_named(publish_realtime, UNREAD_COUNTS_CHANGED)
		)
		self.assertEqual(notified, sorted([self.member.name, self.second_member.name]))
