from unittest.mock import patch

import frappe
from frappe.core.doctype.file.file import has_permission as file_has_permission

from gameplan.api import public_file
from gameplan.gameplan.doctype.gp_comment.gp_comment import GPComment
from gameplan.permissions import can_view_content
from gameplan.public_search import PublicGameplanSearch
from gameplan.search_sqlite import GameplanSearch
from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import create_comment, create_community, create_discussion, create_space
from gameplan.tests.search_isolation import IsolatedSearchIndex
from gameplan.visibility import VISIBILITY_ANONYMOUS, VISIBILITY_MEMBER_ACCESS


class TestReplyModeration(IsolatedSearchIndex, GameplanTestCase):
	INDEX_NAME = "test_reply_moderation.db"

	def setUp(self):
		super().setUp()
		self.isolate_search_index()
		self.enterContext(patch.dict(frappe.conf, gameplan_public_access_enabled=1, gameplan_demo_enabled=0))
		self.community = create_community(
			"Reply Moderation",
			visibility=VISIBILITY_ANONYMOUS,
			members=[self.second_member],
			admins=[self.member],
		)
		self.community.set_member_moderator(self.second_member.name, 1)
		self.space = create_space("Reply Space", self.community, visibility=VISIBILITY_ANONYMOUS)
		self.discussion = create_discussion("Moderation thread", self.space, owner=self.outsider)
		self.comment = create_comment(
			self.discussion, content="<p>hiddensentinel reply</p>", owner=self.outsider
		)
		self.body = self.comment.content

	def hide(self):
		with self.as_user(self.second_member):
			self.comment.hide(" Spam ")
		self.comment.reload()

	def test_hide_and_restore_are_reversible_audited_and_idempotent(self):
		with patch.object(GPComment, "notify_mentions") as notify:
			self.hide()
			self.hide()
			self.assertTrue(self.comment.hidden_at)
			self.assertNotIn("hiddensentinel", self.comment.content)
			log = frappe.get_last_doc("GP Moderation Log", filters={"comment": self.comment.name})
			self.assertEqual(
				(log.owner, log.action, log.reason, log.content),
				(self.second_member.name, "Hide", "Spam", self.body),
			)
			with self.as_user(self.second_member):
				self.assertEqual(self.comment.get_hidden_content(), self.body)
				self.comment.restore()
				self.comment.restore()
			notify.assert_not_called()
		self.comment.reload()
		self.assertFalse(self.comment.hidden_at)
		self.assertEqual(self.comment.content, self.body)
		self.assertEqual(frappe.db.count("GP Moderation Log", {"comment": self.comment.name}), 2)

	def test_author_members_guests_and_other_community_admins_cannot_hide(self):
		create_community("Unrelated Admin", admins=[self.outsider])
		for user in [self.outsider.name, self.guest.name, "Guest"]:
			with self.subTest(user=user), self.as_user(user), self.assertRaises(frappe.PermissionError):
				self.comment.hide("Spam")
		for user in [self.member.name, self.admin.name]:
			with self.as_user(user):
				self.comment.hide("Spam")
				self.comment.restore()

	def test_private_space_access_is_required(self):
		private = create_space("Private replies", self.community, visibility=VISIBILITY_MEMBER_ACCESS)
		discussion = create_discussion("Private thread", private)
		comment = create_comment(discussion, content="Private reply")
		with self.as_user(self.second_member), self.assertRaises(frappe.PermissionError):
			comment.hide("Spam")

	def test_hidden_body_is_not_in_generic_lists_or_feed_previews(self):
		self.hide()
		for user in [self.outsider.name, self.guest.name, "Guest"]:
			with self.subTest(user=user), self.as_user(user):
				self.assertFalse(can_view_content(user, self.comment))
				rows = frappe.get_list("GP Comment", filters={"name": self.comment.name}, fields=["content"])
				self.assertNotIn("hiddensentinel", frappe.as_json(rows))
				with self.assertRaises(frappe.PermissionError):
					self.comment.get_hidden_content()
				with self.assertRaises(frappe.PermissionError):
					self.comment.restore()
				with self.assertRaises(frappe.PermissionError):
					self.comment.get_revisions()

	def test_normal_saves_cannot_hide_restore_edit_or_move_a_hidden_reply(self):
		doc = frappe.get_doc("GP Comment", self.comment.name)
		doc.hidden_at = frappe.utils.now()
		with self.assertRaises(frappe.PermissionError):
			doc.save()
		self.hide()
		other = create_discussion("Another thread", self.space)
		for values in [{"hidden_at": None}, {"content": "Bypass"}, {"reference_name": other.name}]:
			doc = frappe.get_doc("GP Comment", self.comment.name)
			doc.update(values)
			with self.subTest(values=values), self.assertRaises(frappe.PermissionError):
				doc.save()

	def test_preview_and_restore_ignore_forged_client_body(self):
		self.hide()
		self.comment.content = "Forged content"
		self.comment.hidden_at = None
		with self.as_user(self.second_member):
			self.assertEqual(self.comment.get_hidden_content(), self.body)
			self.comment.restore()
		self.assertEqual(frappe.db.get_value("GP Comment", self.comment.name, "content"), self.body)

	def test_hidden_revisions_check_stored_state(self):
		self.hide()
		self.comment.hidden_at = None
		with self.as_user(self.outsider), self.assertRaises(frappe.PermissionError):
			self.comment.get_revisions()

	def test_history_cannot_be_read_by_author_or_changed_or_deleted(self):
		self.hide()
		log = frappe.get_last_doc("GP Moderation Log", filters={"comment": self.comment.name})
		with self.as_user(self.outsider):
			self.assertFalse(log.has_permission("read"))
			self.assertFalse(log.has_permission("create"))
		log.reason = "Rewrite history"
		with self.assertRaises(frappe.PermissionError):
			log.save()
		with self.assertRaises(frappe.PermissionError):
			log.delete()

	def test_hiding_requires_a_short_reason_and_only_supports_discussion_replies(self):
		for reason in ["", " ", "x" * 501, []]:
			with (
				self.subTest(reason=reason),
				self.as_user(self.second_member),
				self.assertRaises((frappe.ValidationError, frappe.FrappeTypeError)),
			):
				self.comment.hide(reason)
		task = frappe.get_doc(doctype="GP Task", title="Task", project=self.space.name).insert(
			ignore_permissions=True
		)
		comment = frappe.get_doc(
			doctype="GP Comment", reference_doctype="GP Task", reference_name=task.name, content="Task reply"
		).insert(ignore_permissions=True)
		with self.as_user(self.admin), self.assertRaises(frappe.PermissionError):
			comment.hide("Spam")

	def test_copied_quotes_are_independent_content(self):
		quoted = create_comment(
			self.discussion,
			content=f'<blockquote data-rich-quote-id="comment:{self.comment.name}">{self.body}</blockquote>',
		)
		self.hide()
		self.assertIn("hiddensentinel", frappe.db.get_value("GP Comment", quoted.name, "content"))

	def test_attachments_follow_hidden_reply_access(self):
		file = frappe.get_doc(
			doctype="File",
			file_name="hidden-reply.txt",
			content=b"Private attachment",
			is_private=1,
			attached_to_doctype="GP Comment",
			attached_to_name=self.comment.name,
		).insert(ignore_permissions=True)
		self.addCleanup(lambda: frappe.delete_doc("File", file.name, ignore_permissions=True))
		self.hide()
		for user in [self.outsider.name, "Guest"]:
			with self.as_user(user):
				self.assertFalse(file_has_permission(file, "read", user=user))
				with self.assertRaises(frappe.PermissionError):
					public_file(file.name)
		self.assertTrue(file_has_permission(file, "read", user=self.second_member.name))

	def test_public_attachments_must_be_protected_before_hiding(self):
		file = frappe.get_doc(
			doctype="File",
			file_name="public-reply.txt",
			content=b"Public attachment",
			is_private=0,
			attached_to_doctype="GP Comment",
			attached_to_name=self.comment.name,
		).insert(ignore_permissions=True)
		self.addCleanup(lambda: frappe.delete_doc("File", file.name, ignore_permissions=True))
		with self.as_user(self.second_member), self.assertRaises(frappe.ValidationError):
			self.comment.hide("Spam")
		self.assertFalse(frappe.db.get_value("GP Comment", self.comment.name, "hidden_at"))

	def test_search_rechecks_hidden_state_even_with_a_stale_index(self):
		search = GameplanSearch()
		search._ensure_fts_table()
		search._index_documents([search.prepare_document(self.comment)])
		with patch.object(GameplanSearch, "remove_doc"):
			self.hide()
		for user, engine in [(self.outsider.name, search), ("Guest", PublicGameplanSearch())]:
			with self.as_user(user):
				self.assertEqual(engine.search("hiddensentinel")["results"], [])
		self.assertIsNone(search.prepare_document(self.comment))

	def test_hiding_removes_index_row_and_thread_refresh_contains_no_body(self):
		search = GameplanSearch()
		search._ensure_fts_table()
		search._index_documents([search.prepare_document(self.comment)])
		with patch("frappe.publish_realtime") as publish:
			self.hide()
		self.assertEqual(len(search.sql("SELECT * FROM search_fts", read_only=True)), 0)
		calls = [call for call in publish.call_args_list if call.args[0] == "new_activity"]
		self.assertEqual(len(calls), 1)
		self.assertNotIn("hiddensentinel", str(calls[0]))
		self.assertTrue(calls[0].kwargs["after_commit"])

	def test_shared_spelling_vocabulary_cannot_suggest_hidden_words(self):
		self.hide()
		search = GameplanSearch()
		with patch.object(search, "_find_similar_words", return_value=["hiddensentinel"]) as suggest:
			self.assertEqual(search._expand_query_with_corrections("hiddensentinl"), ("hiddensentinl", None))
		suggest.assert_not_called()
