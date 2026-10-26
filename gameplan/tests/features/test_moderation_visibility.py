from unittest.mock import patch

import frappe

from gameplan.moderated_file import moderation_allows_file
from gameplan.permissions import can_view_content
from gameplan.public_lists import polls
from gameplan.public_seo import discussion_page
from gameplan.realtime import NOTIFICATION_COUNT_CHANGED, UNREAD_COUNTS_CHANGED, unread_notification_count
from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import create_comment, create_community, create_discussion, create_space
from gameplan.visibility import VISIBILITY_ANONYMOUS


class TestModerationVisibility(GameplanTestCase):
	def setUp(self):
		super().setUp()
		self.enterContext(patch.dict(frappe.conf, gameplan_public_access_enabled=1, gameplan_demo_enabled=0))
		self.community = create_community(
			"Visibility", visibility=VISIBILITY_ANONYMOUS, members=[self.member, self.second_member]
		)
		self.community.set_member_moderator(self.second_member.name, 1)
		self.space = create_space("Public moderation", self.community, visibility=VISIBILITY_ANONYMOUS)
		self.discussion = create_discussion("Visible discussion", self.space, owner=self.member)
		self.reply = create_comment(self.discussion, content="Reported reply", owner=self.member)
		with self.as_user(self.member):
			self.poll = frappe.get_doc(
				doctype="GP Poll",
				discussion=self.discussion.name,
				comment=self.reply.name,
				title="Restricted poll question",
				options=[{"title": "Private option"}, {"title": "Other"}],
			).insert()

	def test_hidden_and_spam_removed_reply_polls_follow_all_read_paths(self):
		for action in ("hide", "delete_spam"):
			with self.as_user(self.second_member):
				getattr(self.reply, action)("Reviewed")
			for user in (self.member.name, "Guest"):
				with self.as_request("/g/discussion", user=user):
					self.assertFalse(can_view_content(user, self.poll))
					self.assertEqual(frappe.get_list("GP Poll", filters={"name": self.poll.name}), [])
					self.assertEqual(
						frappe.qb.get_query(
							"GP Poll",
							fields=["name"],
							filters={"name": self.poll.name},
							ignore_permissions=False,
						).run(),
						[],
					)
					self.assertEqual(polls(fields=["name", "title"], filters={"name": self.poll.name}), [])
			with self.as_request("/g/discussion", user="Guest"):
				self.assertNotIn(
					self.poll.name, [row.name for row in discussion_page(self.discussion.name, 1).polls]
				)
			with self.as_user(self.member), self.assertRaises(frappe.PermissionError):
				self.poll.submit_vote("Private option")
			with self.as_user(self.second_member):
				self.assertTrue(can_view_content(self.second_member.name, self.poll))
				self.reply.restore()
			with self.as_user(self.member):
				self.assertTrue(can_view_content(self.member.name, self.poll))
				self.assertEqual(len(frappe.get_list("GP Poll", filters={"name": self.poll.name})), 1)

	def test_soft_deleted_reply_polls_are_unavailable(self):
		self.reply.db_set("deleted_at", frappe.utils.now())
		with self.as_user(self.member):
			self.assertFalse(can_view_content(self.member.name, self.poll))
			self.assertEqual(frappe.get_list("GP Poll", filters={"name": self.poll.name}), [])

	def test_poll_shares_must_be_removed_before_moderation(self):
		frappe.share.add("GP Poll", self.poll.name, self.outsider.name, read=1, notify=0)
		for doc in (self.reply, self.discussion):
			with self.assertRaises(frappe.ValidationError):
				doc.hide("Reviewed")
		frappe.share.remove("GP Poll", self.poll.name, self.outsider.name)
		self.reply.hide("Reviewed")
		with self.as_user(self.outsider), self.assertRaises(frappe.PermissionError):
			frappe.get_doc("GP Poll", self.poll.name).check_permission("read")

	def test_removed_content_cannot_be_shared_and_restore_reenables_sharing(self):
		for doc in (self.reply, self.discussion):
			doc.hide("Reviewed")
			with self.assertRaises(frappe.PermissionError):
				frappe.share.add("GP Poll", self.poll.name, self.outsider.name, read=1, notify=0)
			doc.restore()
			frappe.share.add("GP Poll", self.poll.name, self.outsider.name, read=1, notify=0)
			frappe.share.remove("GP Poll", self.poll.name, self.outsider.name)

	def test_private_poll_files_follow_the_removed_reply(self):
		with self.as_user(self.member):
			file = frappe.get_doc(
				doctype="File",
				file_name="poll-proof.txt",
				content=b"Poll evidence",
				is_private=1,
				attached_to_doctype="GP Poll",
				attached_to_name=self.poll.name,
			).insert(ignore_permissions=True)
		with self.as_user(self.second_member):
			self.reply.hide("Reviewed")
		self.assertFalse(moderation_allows_file(file, self.member.name))
		self.assertTrue(moderation_allows_file(file, self.second_member.name))
		self.reply.restore()
		self.assertTrue(moderation_allows_file(file, self.member.name))

	def test_public_poll_files_must_be_private_before_reply_removal(self):
		frappe.get_doc(
			doctype="File",
			file_name="public-poll.txt",
			content=b"Public poll evidence",
			is_private=0,
			attached_to_doctype="GP Poll",
			attached_to_name=self.poll.name,
		).insert(ignore_permissions=True)
		with self.as_user(self.second_member), self.assertRaises(frappe.ValidationError):
			self.reply.hide("Reviewed")

	def test_discussion_moderation_refreshes_other_tabs_after_commit(self):
		for user, read in ((self.member.name, 0), (self.second_member.name, 1)):
			frappe.get_doc(
				doctype="GP Notification",
				to_user=user,
				discussion=self.discussion.name,
				type="Mention",
				message="Discussion notification",
				read=read,
			).insert(ignore_permissions=True)
		frappe.get_doc(
			doctype="GP Unread Record",
			user=self.member.name,
			discussion=self.discussion.name,
			project=self.space.name,
			is_unread=1,
		).insert(ignore_permissions=True)
		counts = {
			user.name: unread_notification_count(user.name) for user in (self.member, self.second_member)
		}
		for action in ("hide", "restore"):
			with patch("frappe.realtime.publish_realtime") as publish:
				if action == "hide":
					self.discussion.hide("Reviewed")
				else:
					self.discussion.restore()
			unreads = [call for call in publish.call_args_list if call.args[0] == UNREAD_COUNTS_CHANGED]
			self.assertIn(self.member.name, [call.kwargs["user"] for call in unreads])
			notifications = [
				call for call in publish.call_args_list if call.args[0] == NOTIFICATION_COUNT_CHANGED
			]
			by_user = {call.kwargs["user"]: call.kwargs["message"] for call in notifications}
			count = counts[self.member.name] - (1 if action == "hide" else 0)
			self.assertEqual(by_user[self.member.name], {"count": count, "force_refresh": True})
			self.assertEqual(
				by_user[self.second_member.name],
				{"count": counts[self.second_member.name], "force_refresh": True},
			)
			self.assertTrue(all(call.kwargs["after_commit"] for call in unreads + notifications))
