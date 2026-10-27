import json
from datetime import timedelta
from unittest.mock import patch

import frappe
from frappe.utils import now_datetime

from gameplan.approval_policy import set_policy
from gameplan.approvals import decide, submit
from gameplan.moderation_history import history
from gameplan.slow_mode import set_mode, state_name, status
from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import create_community, create_discussion, create_space, grant_guest_access
from gameplan.visibility import VISIBILITY_MEMBER_ACCESS


class TestSlowMode(GameplanTestCase):
	def setUp(self):
		super().setUp()
		self.community = create_community(
			"Slow mode", members=[self.member, self.second_member, self.outsider]
		)
		self.community.set_member_moderator(self.outsider.name, 1)
		self.space = create_space("Slow mode", self.community)
		self.discussion = create_discussion("Take your time", self.space)
		self.now = now_datetime()
		self.enterContext(patch("gameplan.slow_mode.now_datetime", side_effect=lambda: self.now))

	def setting(self, seconds):
		with self.as_user(self.outsider):
			current = status(str(self.discussion.name))["seconds"]
			return set_mode(str(self.discussion.name), seconds, "Keep discussion thoughtful", current)

	def reply(self, user=None, discussion=None, content="A considered reply"):
		with self.as_user(user or self.member):
			return frappe.get_doc(
				doctype="GP Comment",
				reference_doctype="GP Discussion",
				reference_name=str((discussion or self.discussion).name),
				content=content,
			).insert()

	def wait(self):
		with self.as_user(self.member):
			return status(str(self.discussion.name))["retry_after"]

	def test_controls_require_scope_reason_and_current_version(self):
		with self.as_user(self.member), self.assertRaises(frappe.PermissionError):
			set_mode(str(self.discussion.name), 30, "Not staff", 0)
		for seconds, reason in [(12, "Invalid interval"), (30, ""), (30, "x" * 501)]:
			with self.as_user(self.outsider), self.assertRaises(frappe.ValidationError):
				set_mode(str(self.discussion.name), seconds, reason, 0)
		self.setting(30)
		with self.as_user(self.outsider), self.assertRaises(frappe.TimestampMismatchError):
			set_mode(str(self.discussion.name), 60, "Stale setting", 0)
		with self.as_user(self.member), self.assertRaises(frappe.PermissionError):
			doc = frappe.get_doc("GP Discussion", self.discussion.name)
			doc.slow_mode_seconds = 0
			doc.save()
		private = create_space("Restricted", self.community, visibility=VISIBILITY_MEMBER_ACCESS)
		self.discussion.move_to_project(private.name)
		with self.as_user(self.outsider), self.assertRaises(frappe.PermissionError):
			set_mode(str(self.discussion.name), 60, "No access", 30)

	def test_cooldown_is_per_person_and_discussion_and_staff_are_exempt(self):
		self.setting(30)
		self.reply()
		self.assertEqual(self.wait(), 30)
		with self.assertRaises(frappe.RateLimitExceededError):
			self.reply()
		self.reply(self.second_member)
		self.reply(self.outsider)
		self.reply(self.outsider)
		other = create_discussion("Another discussion", self.space)
		self.reply(discussion=other)
		self.now += timedelta(seconds=29)
		self.assertEqual(self.wait(), 1)
		self.now += timedelta(seconds=1)
		self.reply()

	def test_deleting_editing_and_policy_changes_do_not_reset_the_clock(self):
		self.setting(30)
		reply = self.reply()
		with self.as_user(self.member):
			reply.content = "An edit during the cooldown"
			reply.save()
			reply.delete()
		self.assertEqual(self.wait(), 30)
		self.setting(0)
		self.assertEqual(self.wait(), 0)
		self.now += timedelta(seconds=10)
		self.reply()
		self.setting(60)
		self.assertEqual(self.wait(), 60)
		self.now += timedelta(seconds=20)
		self.setting(30)
		self.assertEqual(self.wait(), 10)

	def test_pending_submissions_count_once_and_approval_never_charges_again(self):
		set_policy(self.community.name, 100)
		self.setting(30)
		with self.as_user(self.member):
			first = submit("GP Comment", "first", "Pending reply", discussion=str(self.discussion.name))
			self.now += timedelta(seconds=10)
			self.assertEqual(
				submit("GP Comment", "first", "Pending reply", discussion=str(self.discussion.name)), first
			)
			with self.assertRaises(frappe.RateLimitExceededError):
				submit("GP Comment", "second", "Another pending reply", discussion=str(self.discussion.name))
		doc = frappe.get_doc("GP Submission", first["name"])
		with self.as_user(self.outsider):
			decide(doc.name, "Approve", str(doc.modified))
		self.assertEqual(self.wait(), 20)
		self.now += timedelta(seconds=20)
		with self.as_user(self.member):
			second = submit(
				"GP Comment", "second", "Another pending reply", discussion=str(self.discussion.name)
			)
			doc = frappe.get_doc("GP Submission", second["name"])
			decide(doc.name, "Withdraw", str(doc.modified))
		self.assertEqual(self.wait(), 30)

	def test_existing_submissions_and_replies_are_used_without_writing_during_status(self):
		reply = self.reply()
		frappe.db.delete("GP Slow Mode State", {"discussion": str(self.discussion.name)})
		frappe.db.set_value("GP Comment", reply.name, "creation", self.now - timedelta(seconds=10))
		self.setting(30)
		self.assertEqual(self.wait(), 20)
		self.assertFalse(
			frappe.db.exists("GP Slow Mode State", state_name(str(self.discussion.name), self.member.name))
		)

	def test_history_records_intervals_and_private_state_cannot_be_forged(self):
		self.setting(30)
		self.setting(60)
		with self.as_user(self.outsider):
			rows = history(self.community.name, "discussion", str(self.discussion.name))["items"]
		self.assertEqual(rows[0].action, "Slow Mode Changed")
		self.assertEqual((rows[0].previous_slow_mode_seconds, rows[0].slow_mode_seconds), (30, 60))
		self.reply()
		with self.as_user(self.member), self.assertRaises(frappe.PermissionError):
			frappe.get_doc(
				"GP Slow Mode State", state_name(str(self.discussion.name), self.member.name)
			).delete()
		self.discussion.delete()
		self.assertFalse(frappe.db.exists("GP Slow Mode State", {"discussion": str(self.discussion.name)}))

	def test_invited_guests_and_poll_replies_use_one_reply_cooldown(self):
		grant_guest_access(self.guest, self.space)
		self.setting(30)
		draft = json.dumps({"title": "Choose one", "options": [{"title": "Yes"}, {"title": "No"}]})
		self.reply(self.guest, content=f"<div data-type=\"poll\" data-poll-draft='{draft}'></div>")
		with self.assertRaises(frappe.RateLimitExceededError):
			self.reply(self.guest)
		self.assertEqual(frappe.db.count("GP Poll", {"discussion": self.discussion.name}), 1)

	def test_rejection_and_delayed_publication_preserve_original_submission_time(self):
		set_policy(self.community.name, 100)
		with self.as_user(self.member):
			result = submit("GP Comment", "legacy", "Held", discussion=str(self.discussion.name))
		doc = frappe.get_doc("GP Submission", result["name"])
		frappe.db.set_value("GP Submission", doc.name, "creation", self.now, update_modified=False)
		self.now += timedelta(seconds=60)
		with self.as_user(self.outsider):
			decide(doc.name, "Approve", str(doc.modified))
		frappe.db.delete("GP Slow Mode State", {"discussion": str(self.discussion.name)})
		self.setting(30)
		self.assertEqual(self.wait(), 0)
		with self.as_user(self.member):
			result = submit("GP Comment", "reject", "Held again", discussion=str(self.discussion.name))
		doc = frappe.get_doc("GP Submission", result["name"])
		with self.as_user(self.outsider):
			decide(doc.name, "Reject", str(doc.modified), "Not appropriate")
		self.assertEqual(self.wait(), 30)

	def test_deleting_legacy_replies_preserves_the_latest_accepted_time(self):
		older = self.reply()
		newer = self.reply()
		frappe.db.set_value("GP Comment", older.name, "creation", self.now - timedelta(seconds=10))
		frappe.db.set_value("GP Comment", newer.name, "creation", self.now - timedelta(seconds=5))
		frappe.db.delete("GP Slow Mode State", {"discussion": str(self.discussion.name)})
		self.setting(30)
		self.assertEqual(self.wait(), 25)
		with self.as_user(self.member):
			older.delete()
			newer.delete()
		self.assertEqual(self.wait(), 25)
