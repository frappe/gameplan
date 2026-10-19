from unittest.mock import patch

import frappe

from gameplan.community_bans import content_is_banned, is_banned, set_ban
from gameplan.mixins.moderation import is_removed
from gameplan.moderation import community_bans, removed_content
from gameplan.permissions import can_create_content, can_delete_content, can_view_content, can_write_content
from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import (
	create_comment,
	create_community,
	create_discussion,
	create_poll,
	create_space,
)
from gameplan.tests.search_isolation import IsolatedSearchIndex
from gameplan.visibility import VISIBILITY_ANONYMOUS, VISIBILITY_MEMBER_ACCESS


class TestModerationCore(IsolatedSearchIndex, GameplanTestCase):
	INDEX_NAME = "test_moderation_core.db"

	def setUp(self):
		super().setUp()
		self.isolate_search_index()
		self.enterContext(patch.dict(frappe.conf, gameplan_public_access_enabled=1, gameplan_demo_enabled=0))
		self.community = create_community(
			"Moderation core", admins=[self.member], members=[self.second_member, self.outsider]
		)
		self.community.set_member_moderator(self.second_member.name, 1)
		self.space = create_space("Moderated", self.community, visibility=VISIBILITY_ANONYMOUS)
		self.discussion = create_discussion("Original title", self.space, owner=self.outsider)
		self.discussion.content = "<p>Original body</p>"
		self.discussion.save()
		self.reply = create_comment(self.discussion, content="Original reply", owner=self.outsider)

	def ban(self):
		with self.as_user(self.second_member):
			set_ban(self.community.name, self.outsider.name, 1, "Repeated spam")

	def test_discussion_removal_and_restore_preserve_content_and_children(self):
		original = self.discussion.content
		with self.as_user(self.second_member):
			self.discussion.hide("Off topic")
			self.discussion.delete_spam("Spam")
			self.discussion.reload()
			self.assertTrue(self.discussion.spam_removed_at)
			self.assertFalse(self.discussion.hidden_at)
			self.assertEqual(self.discussion.get_hidden_content(), original)
			rows = removed_content(self.community.name)["items"]
			self.assertEqual(
				(str(rows[0].name), rows[0].title, rows[0].reason),
				(str(self.discussion.name), "Original title", "Spam"),
			)
			self.discussion.restore()
		self.discussion.reload()
		self.assertFalse(is_removed(self.discussion))
		self.assertEqual((self.discussion.title, self.discussion.content), ("Original title", original))
		self.assertTrue(frappe.db.exists("GP Comment", self.reply.name))

	def test_removed_discussion_closes_descendant_access_and_lists(self):
		self.discussion.hide("Spam")
		self.discussion.reload()
		with self.as_user(self.outsider):
			self.assertFalse(can_view_content(self.outsider.name, self.discussion))
			self.assertFalse(can_view_content(self.outsider.name, self.reply))
			for doctype in ["GP Discussion", "GP Comment"]:
				self.assertEqual(
					frappe.get_list(
						doctype,
						filters={
							"name": self.discussion.name if doctype == "GP Discussion" else self.reply.name
						},
					),
					[],
				)
			with self.assertRaises(frappe.PermissionError):
				self.discussion.get_revisions()
			with self.assertRaises(frappe.PermissionError):
				create_comment(self.discussion, content="Bypass")

	def test_private_space_is_not_revealed_in_removed_content(self):
		private = create_space("Private moderation", self.community, visibility=VISIBILITY_MEMBER_ACCESS)
		discussion = create_discussion("Private title", private)
		discussion.hide("Private spam")
		with self.as_user(self.second_member):
			self.assertEqual(removed_content(self.community.name)["items"], [])
			with self.assertRaises(frappe.PermissionError):
				discussion.restore()

	def test_reply_spam_is_reversible_without_removing_other_posts(self):
		self.reply.delete_spam("Spam")
		self.reply.reload()
		self.assertTrue(self.reply.spam_removed_at)
		self.assertNotIn("Original reply", self.reply.content)
		self.assertTrue(can_view_content(self.outsider.name, self.discussion))
		with self.as_user(self.second_member):
			self.assertEqual(len(removed_content(self.community.name, "GP Comment")["items"]), 1)
			self.reply.restore()
		self.reply.reload()
		self.assertIn("Original reply", self.reply.content)

	def test_normal_saves_cannot_set_or_clear_moderation_state(self):
		for doc in [self.discussion, self.reply]:
			copy = frappe.get_doc(doc.doctype, doc.name)
			copy.spam_removed_at = frappe.utils.now()
			with self.assertRaises(frappe.PermissionError):
				copy.save()

	def test_ban_is_scoped_read_only_and_can_be_lifted(self):
		self.ban()
		other = create_community("Elsewhere")
		other_space = create_space("Elsewhere", other)
		other_post = create_discussion("Elsewhere", other_space)
		with self.as_user(self.outsider):
			self.assertTrue(can_view_content(self.outsider.name, self.discussion))
			self.assertFalse(can_create_content(self.outsider.name, self.discussion))
			self.assertFalse(can_write_content(self.outsider.name, self.discussion))
			self.assertFalse(can_delete_content(self.outsider.name, self.discussion))
			self.assertFalse(content_is_banned(other_post))
			with self.assertRaises(frappe.PermissionError):
				create_comment(self.discussion, content="Banned reply")
			with self.assertRaises(frappe.PermissionError):
				self.reply.react([{"emoji": "👍", "operation": "add"}])
			with self.assertRaises(frappe.PermissionError):
				self.discussion.reload().update({"content": "Banned edit"}).save(ignore_permissions=True)
		with self.as_user(self.second_member):
			self.assertEqual(community_bans(self.community.name)[0].user, self.outsider.name)
			set_ban(self.community.name, self.outsider.name, 0)
		self.assertFalse(is_banned(self.community.name, self.outsider.name))

	def test_ban_survives_membership_removal_and_rejoin(self):
		self.ban()
		self.community.reload().remove_member(self.outsider.name)
		self.community.reload().add_members([self.outsider.name])
		self.assertTrue(is_banned(self.community.name, self.outsider.name))

	def test_staff_cannot_be_banned_or_banned_users_promoted(self):
		for user in [self.member.name, self.second_member.name, self.admin.name, "Administrator"]:
			with self.subTest(user=user), self.assertRaises(frappe.ValidationError):
				set_ban(self.community.name, user, 1, "Spam")
		self.ban()
		with self.assertRaises(frappe.ValidationError):
			self.community.reload().set_member_moderator(self.outsider.name, 1)

	def test_ordinary_users_cannot_manage_bans_or_removed_content(self):
		with self.as_user(self.outsider):
			for action in [
				lambda: set_ban(self.community.name, self.member.name, 1, "Spam"),
				lambda: removed_content(self.community.name),
				lambda: community_bans(self.community.name),
			]:
				with self.assertRaises(frappe.PermissionError):
					action()

	def test_removed_thread_files_deny_the_uploader_shares_zip_and_cloning(self):
		from frappe.core.api.file import zip_files

		with self.as_user(self.outsider):
			file = frappe.get_doc(
				doctype="File",
				file_name="removed-thread.txt",
				content=b"Removed file",
				is_private=1,
				attached_to_doctype="GP Comment",
				attached_to_name=self.reply.name,
			).insert(ignore_permissions=True)
		self.addCleanup(lambda: frappe.delete_doc("File", file.name, ignore_permissions=True))
		frappe.share.add("File", file.name, self.outsider.name, read=1)
		self.discussion.hide("Spam")
		file = frappe.get_doc("File", file.name)
		with self.as_user(self.outsider):
			self.assertFalse(file.is_downloadable())
			for read in [
				file.get_content,
				lambda: file.has_permission("read"),
				lambda: zip_files(frappe.as_json([file.name])),
			]:
				with self.assertRaises(frappe.PermissionError):
					read()
			file.attached_to_name = None
			with self.assertRaises(frappe.PermissionError):
				file.save(ignore_permissions=True)
			with self.assertRaises(frappe.PermissionError):
				frappe.get_doc(
					doctype="File", file_name="copy.txt", file_url=file.file_url, is_private=1
				).insert(ignore_permissions=True)
		self.discussion.restore()
		with self.as_user(self.outsider):
			self.assertTrue(file.reload().is_downloadable())

	def test_banned_user_cannot_vote_or_invite_in_a_private_space_they_belong_to(self):
		poll = create_poll("Vote", self.discussion)
		private = create_space(
			"Private", self.community, visibility=VISIBILITY_MEMBER_ACCESS, members=[self.outsider]
		)
		self.ban()
		with self.as_user(self.outsider):
			for participate in [
				lambda: poll.submit_vote("Yes"),
				lambda: poll.retract_vote(),
				lambda: private.invite_guest("new@example.com"),
			]:
				with self.assertRaises(frappe.PermissionError):
					participate()

	def test_a_ban_blocks_moving_content_out_of_its_community(self):
		other = create_community("Move destination")
		space = create_space("Destination", other)
		self.ban()
		with self.as_user(self.outsider):
			doc = frappe.get_doc("GP Discussion", self.discussion.name)
			doc.project = space.name
			with self.assertRaises(frappe.PermissionError):
				doc.save(ignore_permissions=True)

	def test_restoring_keeps_closed_and_pinned_state_and_does_not_notify(self):
		from gameplan.gameplan.doctype.gp_discussion.gp_discussion import GPDiscussion

		stamp = frappe.utils.now()
		self.discussion.db_set({"closed_at": stamp, "pinned_at": stamp})
		with patch.object(GPDiscussion, "notify_mentions") as notify:
			self.discussion.delete_spam("Spam")
			self.discussion.restore()
			notify.assert_not_called()
		self.discussion.reload()
		self.assertEqual(str(self.discussion.closed_at), stamp)
		self.assertEqual(str(self.discussion.pinned_at), stamp)

	def test_search_rechecks_a_removed_discussion_and_its_replies(self):
		from gameplan.public_search import PublicGameplanSearch
		from gameplan.search_sqlite import GameplanSearch

		search = GameplanSearch()
		search._ensure_fts_table()
		search._index_documents(
			[search.prepare_document(self.discussion), search.prepare_document(self.reply)]
		)
		with self.as_user(self.outsider):
			self.assertEqual(len(search.search("Original")["results"]), 2)
		self.discussion.hide("Spam")
		for user, engine in [(self.outsider.name, search), ("Guest", PublicGameplanSearch())]:
			with self.as_user(user):
				self.assertEqual(engine.search("Original")["results"], [])

	def test_notifications_about_removed_discussions_return_only_after_restore(self):
		notification = frappe.get_doc(
			doctype="GP Notification",
			to_user=self.outsider.name,
			discussion=self.discussion.name,
			type="Mention",
			message="Original title notification",
		).insert(ignore_permissions=True)
		self.discussion.hide("Spam")
		with self.as_user(self.outsider):
			self.assertEqual(frappe.get_list("GP Notification", filters={"name": notification.name}), [])
			self.assertFalse(frappe.get_doc("GP Notification", notification.name).has_permission("read"))
		self.discussion.restore()
		with self.as_user(self.outsider):
			self.assertEqual(len(frappe.get_list("GP Notification", filters={"name": notification.name})), 1)

	def test_banned_user_cannot_attach_a_file_to_existing_content(self):
		self.ban()
		with self.as_user(self.outsider), self.assertRaises(frappe.PermissionError):
			frappe.get_doc(
				doctype="File",
				file_name="banned-upload.txt",
				content=b"Banned upload",
				is_private=1,
				attached_to_doctype="GP Comment",
				attached_to_name=self.reply.name,
			).insert(ignore_permissions=True)
