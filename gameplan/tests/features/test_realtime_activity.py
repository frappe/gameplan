# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""The realtime half of the activity timeline.

Every logged activity is announced over the socket so that anyone with the
discussion (or task) open sees the timeline update without reloading. The event
has to land in the *document* room: `frappe.publish_realtime` falls back to the
site room when `doctype`/`docname` are missing, and only Desk (System User)
sockets join the site room — Gameplan members are Website Users, so they would
never receive it. That exact regression shipped once; these tests pin it.
"""

from unittest.mock import patch

import frappe

from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import (
	create_community,
	create_discussion,
	create_space,
	create_task,
)


class RealtimeActivityTestCase(GameplanTestCase):
	"""World: a public space in a community both members belong to, holding one
	discussion and one task written by `member`."""

	def setUp(self):
		super().setUp()
		self.community = create_community("Acme", members=[self.member, self.second_member])
		self.space = create_space("Engineering", self.community)
		self.discussion = create_discussion("Welcome thread", self.space, owner=self.member)
		self.task = create_task("Ship it", self.space, owner=self.member)

	@staticmethod
	def _new_activity_calls(publish_realtime):
		return [call for call in publish_realtime.call_args_list if call.args[0] == "new_activity"]

	def capture_broadcasts(self, action):
		"""Run `action` with `frappe.publish_realtime` mocked, and return the
		`new_activity` calls it made."""
		with patch("frappe.publish_realtime") as publish_realtime:
			action()
			return self._new_activity_calls(publish_realtime)

	def capture_one_broadcast(self, action):
		calls = self.capture_broadcasts(action)
		self.assertEqual(len(calls), 1, f"expected exactly one new_activity broadcast, got {len(calls)}")
		return calls[0]

	def close_discussion(self):
		with self.as_user(self.member):
			frappe.get_doc("GP Discussion", self.discussion.name).close_discussion()


class TestActivityBroadcastRoom(RealtimeActivityTestCase):
	"""Which room the event goes to. This is the part that broke."""

	def test_activity_is_broadcast_into_the_document_room(self):
		call = self.capture_one_broadcast(self.close_discussion)

		self.assertEqual(call.kwargs.get("doctype"), "GP Discussion")
		self.assertEqual(str(call.kwargs.get("docname")), str(self.discussion.name))

	def test_activity_is_not_broadcast_to_the_site_room(self):
		"""Without doctype/docname frappe publishes to the site room, which only Desk
		sockets join — the members who need the update are Website Users."""
		call = self.capture_one_broadcast(self.close_discussion)

		self.assertTrue(call.kwargs.get("doctype"), "doctype missing: this is a site-room broadcast")
		self.assertTrue(call.kwargs.get("docname"), "docname missing: this is a site-room broadcast")

	def test_activity_is_not_addressed_to_a_single_user(self):
		"""`user=` would narrow the event to the acting user's own room, so everyone
		else with the discussion open would still be looking at a stale timeline."""
		call = self.capture_one_broadcast(self.close_discussion)

		self.assertIsNone(call.kwargs.get("user"))

	def test_activity_is_published_after_commit(self):
		"""Publishing inline would race the transaction: a listener reloading the
		timeline could read the database before the activity row is visible."""
		call = self.capture_one_broadcast(self.close_discussion)

		self.assertTrue(call.kwargs.get("after_commit"))


class TestActivityBroadcastPayload(RealtimeActivityTestCase):
	"""What the event carries. `frontend/src/socket.ts` types this as
	`NewActivityEvent`; the listeners in CommentsArea/CommentsList filter on it."""

	def test_payload_identifies_the_document_the_activity_belongs_to(self):
		call = self.capture_one_broadcast(self.close_discussion)

		self.assertEqual(
			call.args[1],
			{"reference_doctype": "GP Discussion", "reference_name": str(self.discussion.name)},
		)

	def test_reference_name_is_a_string(self):
		"""Discussions autoname to an integer. The listeners compare against
		`String(props.name)`, so a number here would never match and the timeline
		would silently stop updating."""
		call = self.capture_one_broadcast(self.close_discussion)

		self.assertIsInstance(call.args[1]["reference_name"], str)

	def test_the_broadcast_names_the_same_document_as_the_stored_activity(self):
		with patch("frappe.publish_realtime") as publish_realtime:
			self.close_discussion()
			[call] = self._new_activity_calls(publish_realtime)

		activity = frappe.get_last_doc(
			"GP Activity",
			filters={"reference_doctype": "GP Discussion", "reference_name": self.discussion.name},
		)
		self.assertEqual(call.args[1]["reference_doctype"], activity.reference_doctype)
		self.assertEqual(call.args[1]["reference_name"], str(activity.reference_name))


class TestEveryActivityIsBroadcast(RealtimeActivityTestCase):
	"""Every action that writes to the timeline announces itself — one broadcast per
	activity row, so a watching tab never has to reload to catch up."""

	def discussion_as(self, user):
		with self.as_user(user):
			return frappe.get_doc("GP Discussion", self.discussion.name)

	def assert_broadcasts_for_document(self, action, doctype, docname):
		call = self.capture_one_broadcast(action)

		self.assertEqual(call.kwargs.get("doctype"), doctype)
		self.assertEqual(str(call.kwargs.get("docname")), str(docname))
		self.assertEqual(call.args[1]["reference_doctype"], doctype)
		self.assertEqual(call.args[1]["reference_name"], str(docname))

	def assert_discussion_broadcast(self, action):
		self.assert_broadcasts_for_document(action, "GP Discussion", self.discussion.name)

	def test_closing_broadcasts(self):
		self.assert_discussion_broadcast(self.close_discussion)

	def test_reopening_broadcasts(self):
		self.close_discussion()

		def reopen():
			self.discussion_as(self.member).reopen_discussion()

		self.assert_discussion_broadcast(reopen)

	def test_pinning_broadcasts(self):
		def pin():
			self.discussion_as(self.member).pin_discussion()

		self.assert_discussion_broadcast(pin)

	def test_unpinning_broadcasts(self):
		self.discussion_as(self.member).pin_discussion()

		def unpin():
			self.discussion_as(self.member).unpin_discussion()

		self.assert_discussion_broadcast(unpin)

	def test_renaming_broadcasts(self):
		def rename():
			with self.as_user(self.member):
				discussion = frappe.get_doc("GP Discussion", self.discussion.name)
				discussion.title = "Renamed thread"
				discussion.save()

		self.assert_discussion_broadcast(rename)

	def test_moving_to_another_space_broadcasts(self):
		other_space = create_space("Design", self.community)

		def move():
			with self.as_user(self.member):
				frappe.get_doc("GP Discussion", self.discussion.name).move_to_project(other_space.name)

		self.assert_discussion_broadcast(move)

	def test_a_task_value_change_broadcasts_into_the_task_room(self):
		"""Tasks share the activity mixin and the same timeline component, so the
		event has to be scoped to the task, not to the discussion."""

		def change_status():
			with self.as_user(self.member):
				task = frappe.get_doc("GP Task", self.task.name)
				task.status = "In Progress"
				task.save()

		self.assert_broadcasts_for_document(change_status, "GP Task", self.task.name)

	def test_each_logged_activity_gets_its_own_broadcast(self):
		"""One save can record several changes; a watching tab should be told about
		the save once per activity row, never fewer."""

		def change_two_fields():
			with self.as_user(self.member):
				task = frappe.get_doc("GP Task", self.task.name)
				task.status = "In Progress"
				task.priority = "High"
				task.save()

		calls = self.capture_broadcasts(change_two_fields)

		activities = frappe.get_all(
			"GP Activity", filters={"reference_doctype": "GP Task", "reference_name": self.task.name}
		)
		self.assertEqual(len(calls), 2)
		self.assertEqual(len(calls), len(activities))

	def test_a_save_that_changes_nothing_on_the_timeline_broadcasts_nothing(self):
		"""Otherwise every unrelated save would make every open tab refetch the
		timeline."""

		def touch():
			with self.as_user(self.member):
				discussion = frappe.get_doc("GP Discussion", self.discussion.name)
				discussion.content = "<p>Same thread, new body</p>"
				discussion.save()

		self.assertEqual(self.capture_broadcasts(touch), [])

	def test_a_rejected_action_broadcasts_nothing(self):
		"""log_activity refuses an action the doctype doesn't declare, and must not
		announce an activity it never stored."""

		def log_unknown_action():
			with self.assertRaisesRegex(Exception, "^Invalid action to log activity for this document$"):
				frappe.get_doc("GP Discussion", self.discussion.name).log_activity("Discussion Vaporised")

		self.assertEqual(self.capture_broadcasts(log_unknown_action), [])
