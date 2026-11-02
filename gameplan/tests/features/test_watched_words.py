from unittest.mock import patch

import frappe

from gameplan.approvals import decide, detail, queue, submit
from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import create_comment, create_community, create_discussion, create_space
from gameplan.watched_word_edits import original
from gameplan.watched_word_edits import submit as edit
from gameplan.watched_word_matching import censor, matches, pattern
from gameplan.watched_word_payload import clean
from gameplan.watched_words import add, remove, rules, upload


class TestWatchedWords(GameplanTestCase):
	def setUp(self):
		super().setUp()
		frappe.local.request_cache.clear()
		self.community = create_community(
			"Watched words", admins=[self.member], members=[self.second_member, self.outsider]
		)
		self.community.set_member_moderator(self.second_member.name, 1)
		self.space = create_space("Watched Space", self.community)
		self.post = create_discussion("Original title", self.space, owner=self.outsider)
		self.post.content = "<p>Original body</p>"
		self.post.save()

	def rule(self, action, word, sensitive=False):
		with self.as_user(self.member):
			return add(self.community.name, action, word, sensitive)

	def post_content(self, content, title="A discussion"):
		with self.as_user(self.outsider):
			return submit(
				"GP Discussion", frappe.generate_hash(), content, project=str(self.space.name), title=title
			)

	def approve(self, result):
		with self.as_user(self.second_member):
			row = detail(result["name"])
			return decide(row.name, "Approve", str(row.modified))

	def test_only_admins_manage_community_rules(self):
		self.rule("Block", "spam")
		for user in [self.second_member, self.outsider]:
			with self.as_user(user), self.assertRaises(frappe.PermissionError):
				rules(self.community.name, "Block")
		with self.as_user(self.member):
			row = rules(self.community.name, "Block")["items"][0]
			other = create_community("Other rules")
			with self.assertRaises(frappe.PermissionError):
				remove(other.name, row.name)
			add(self.community.name, "Block", "SPAM")
			self.assertEqual(len(rules(self.community.name, "Block")["items"]), 1)

	def test_matching_preserves_code_and_covers_inline_markup_and_links(self):
		self.rule("Block", "spam*")
		self.assertTrue(matches(self.community.name, "Block", "", "<p>sp<strong>ammer</strong></p>"))
		self.assertFalse(matches(self.community.name, "Block", "", "<p>antispam</p><code>spammer</code>"))
		self.assertTrue(matches(self.community.name, "Block", "", '<a href="https://spam.example">link</a>'))
		self.assertTrue(pattern("a*b*c").search("aabbcc"))
		self.assertFalse(pattern("SPAM", True).search("spam"))

	def test_block_covers_new_content_edits_and_staff_exemptions(self):
		self.rule("Block", "spam")
		with self.assertRaises(frappe.ValidationError):
			self.post_content("<p>spam</p>")
		with self.as_user(self.outsider), self.assertRaises(frappe.ValidationError):
			frappe.get_doc("GP Discussion", self.post.name).update({"content": "<p>spam</p>"}).save()
		with self.as_user(self.second_member):
			create_comment(self.post, content="<p>spam</p>", owner=self.second_member)

	def test_censor_is_scoped_non_destructive_and_preserves_markup_code_and_urls(self):
		self.rule("Censor", "spam")
		source = '<p>sp<strong>am</strong> <code>spam</code> <a href="https://spam.example">https://spam.example</a></p>'
		masked = censor(self.community.name, source, html=True)
		self.assertIn("■■<strong>■■</strong>", masked)
		self.assertIn("<code>spam</code>", masked)
		self.assertIn("https://spam.example", masked)
		self.assertEqual(censor("unrelated", source, html=True), source)
		self.assertEqual(
			censor(self.community.name, "<p>spam<br>spam</p>", html=True), "<p>■■■■<br/>■■■■</p>"
		)
		self.post.db_set("content", "<p>spam</p>")
		self.assertEqual(
			clean({"doctype": "GP Discussion", "name": self.post.name, "content": self.post.content}).content,
			"<p>■■■■</p>",
		)
		self.assertEqual(frappe.db.get_value("GP Discussion", self.post.name, "content"), "<p>spam</p>")
		with self.as_user(self.outsider):
			self.assertEqual(original("GP Discussion", str(self.post.name))["content"], "<p>spam</p>")

	def test_flag_uses_existing_review_queue_once_without_impersonating_a_reporter(self):
		self.rule("Flag", "suspicious")
		result = self.post_content("<p>suspicious</p>")
		self.assertEqual(result["doctype"], "GP Discussion")
		review = frappe.get_all("GP Review", filters={"reference_name": result["name"]}, pluck="name")
		self.assertEqual(len(review), 1)
		reports = frappe.get_all(
			"GP Report", filters={"review": review[0]}, fields=["automatic_rule", "reported_content"]
		)
		self.assertEqual(len(reports), 1)
		self.assertTrue(reports[0].automatic_rule)
		self.assertIn("suspicious", reports[0].reported_content)

	def test_action_priority_and_approval_do_not_generate_a_second_flag(self):
		for action in ["Flag", "Require approval"]:
			self.rule(action, "reviewme")
		result = self.post_content("<p>reviewme</p>")
		self.assertEqual(result["doctype"], "GP Submission")
		published = self.approve(result)
		self.assertEqual(frappe.db.count("GP Review", {"reference_name": published["published_name"]}), 0)
		self.rule("Block", "reviewme")
		with self.assertRaises(frappe.ValidationError):
			self.post_content("<p>reviewme</p>")

	def test_new_block_rules_recheck_pending_publication(self):
		self.rule("Require approval", "reviewme")
		result = self.post_content("<p>reviewme</p>")
		self.rule("Block", "reviewme")
		with self.assertRaises(frappe.ValidationError):
			self.approve(result)
		self.assertEqual(frappe.db.get_value("GP Submission", result["name"], "status"), "Pending")

	def test_edit_approval_keeps_old_post_visible_and_does_not_create_another_post(self):
		self.rule("Require approval", "reviewme")
		before = str(self.post.modified)
		with self.as_user(self.outsider):
			result = edit("GP Discussion", str(self.post.name), before, "<p>reviewme</p>", "Proposed title")
		self.assertEqual(frappe.db.get_value("GP Discussion", self.post.name, "title"), "Original title")
		published = self.approve(result)
		self.assertEqual(str(published["published_name"]), str(self.post.name))
		self.assertEqual(frappe.db.get_value("GP Discussion", self.post.name, "title"), "Proposed title")
		self.assertEqual(frappe.db.get_value("GP Discussion", self.post.name, "owner"), self.outsider.name)

	def test_stale_edits_require_fresh_review(self):
		self.rule("Require approval", "reviewme")
		with self.as_user(self.outsider):
			result = edit(
				"GP Discussion", str(self.post.name), str(self.post.modified), "<p>reviewme</p>", "Edit"
			)
		self.post.db_set("title", "Changed by staff")
		with self.assertRaises(frappe.TimestampMismatchError):
			self.approve(result)

	def test_csv_preview_is_additive_deduplicated_and_atomic(self):
		with self.as_user(self.member):
			file = frappe.get_doc(
				doctype="File", file_name="words.csv", content='spam\n"buy, now",,true\nSPAM\n', is_private=1
			).save(ignore_permissions=True)
			preview = upload(self.community.name, "Block", file.name)
			self.assertEqual((preview["added"], preview["duplicates"]), (2, 1))
			self.assertEqual(frappe.db.count("GP Watched Word"), 0)
			upload(self.community.name, "Block", file.name, preview["expected"])
			self.assertEqual(len(rules(self.community.name, "Block")["items"]), 2)
			bad = frappe.get_doc(
				doctype="File", file_name="bad.csv", content="valid\ninvalid,,maybe", is_private=1
			).save(ignore_permissions=True)
			with self.assertRaises(frappe.ValidationError):
				upload(self.community.name, "Block", bad.name)
			self.assertEqual(len(rules(self.community.name, "Block")["items"]), 2)

	def test_reply_edit_approval_preserves_identity(self):
		reply = create_comment(self.post, content="<p>Original reply</p>", owner=self.outsider)
		self.rule("Require approval", "reviewme")
		with self.as_user(self.outsider):
			result = edit("GP Comment", str(reply.name), str(reply.modified), "<p>reviewme</p>")
		self.assertEqual(frappe.db.get_value("GP Comment", reply.name, "content"), "<p>Original reply</p>")
		published = self.approve(result)
		self.assertEqual(str(published["published_name"]), str(reply.name))
		self.assertEqual(frappe.db.get_value("GP Comment", reply.name, "content"), "<p>reviewme</p>")

	def test_pending_edit_follows_current_private_space_access(self):
		from gameplan.approval_access import can_read_submission
		from gameplan.visibility import VISIBILITY_MEMBER_ACCESS

		self.rule("Require approval", "reviewme")
		with self.as_user(self.outsider):
			result = edit("GP Discussion", str(self.post.name), str(self.post.modified), "reviewme", "Edit")
		private = create_space(
			"Private destination",
			self.community,
			visibility=VISIBILITY_MEMBER_ACCESS,
			members=[self.outsider],
		)
		self.post.move_to_project(private.name)
		submission = frappe.get_doc("GP Submission", result["name"])
		with self.as_user(self.second_member):
			self.assertFalse(can_read_submission(submission))
			self.assertEqual(frappe.get_list("GP Submission", filters={"name": submission.name}), [])
			self.assertEqual(queue(self.community.name)["items"], [])

	def test_removed_and_archived_content_cannot_queue_edits(self):
		self.rule("Require approval", "reviewme")
		self.post.hide("Moderation test")
		self.post.reload()
		with self.as_user(self.outsider), self.assertRaises(frappe.PermissionError):
			edit("GP Discussion", str(self.post.name), str(self.post.modified), "reviewme", "Edit")
		self.post.restore()
		self.post.reload()
		self.space.archive()
		with self.as_user(self.outsider), self.assertRaises(frappe.ValidationError):
			edit("GP Discussion", str(self.post.name), str(self.post.modified), "reviewme", "Edit")

	def test_censor_leaves_metadata_intact_and_restricts_original_to_author_or_moderator(self):
		self.rule("Censor", "Pending")
		self.post.db_set("content", "<p>Pending</p>")
		row = clean({"project": self.space.name, "title": "Pending", "status": "Pending"})
		self.assertEqual(row.title, "■■■■■■■")
		self.assertEqual(row.status, "Pending")
		with self.as_user(self.member):
			self.assertEqual(original("GP Discussion", str(self.post.name))["content"], "<p>Pending</p>")
		other = create_community("Nonstaff editors", members=[self.member, self.outsider])
		other_space = create_space("Other", other)
		self.post.move_to_project(other_space.name)
		with self.as_user("Administrator"):
			add(other.name, "Censor", "Pending")
		with self.as_user(self.member), self.assertRaises(frappe.PermissionError):
			original("GP Discussion", str(self.post.name))

	def test_csv_rejects_changed_preview_and_foreign_upload(self):
		with self.as_user(self.member):
			file = frappe.get_doc(
				doctype="File", file_name="preview.csv", content="first", is_private=1
			).save(ignore_permissions=True)
			preview = upload(self.community.name, "Block", file.name)
			add(self.community.name, "Block", "second")
			with self.assertRaises(frappe.TimestampMismatchError):
				upload(self.community.name, "Block", file.name, preview["expected"])
			self.assertEqual([row.word for row in rules(self.community.name, "Block")["items"]], ["second"])
		with self.as_user("Administrator"), self.assertRaises(frappe.PermissionError):
			upload(self.community.name, "Block", file.name)

	def test_censor_handles_activity_titles_and_aliased_content(self):
		self.rule("Censor", "sensitive")
		activity = clean(
			{
				"reference_doctype": "GP Discussion",
				"reference_name": self.post.name,
				"data": frappe.as_json({"old_title": "sensitive", "new_title": "clear"}),
			}
		)
		self.assertNotIn("sensitive", activity.data)
		with self.as_request("/api/v2/document/GP Discussion"):
			frappe.form_dict.fields = '["content as body"]'
			self.assertEqual(clean({"project": self.space.name, "body": "sensitive"}).body, "■■■■■■■■■")

	def test_csv_import_supports_the_full_action_limit(self):
		with self.as_user(self.member):
			file = frappe.get_doc(
				doctype="File",
				file_name="limit.csv",
				content="\n".join(f"word{i}" for i in range(2000)),
				is_private=1,
			).save(ignore_permissions=True)
			preview = upload(self.community.name, "Block", file.name)
			self.assertEqual(preview["added"], 2000)
			upload(self.community.name, "Block", file.name, preview["expected"])
			self.assertEqual(frappe.db.count("GP Watched Word", {"community": self.community.name}), 2000)
			with self.assertRaises(frappe.ValidationError):
				add(self.community.name, "Block", "overflow")

	def test_forum_notification_messages_and_email_censor_post_text(self):
		from gameplan.email_digest import format_notification_item

		self.rule("Censor", "sensitive")
		notification = frappe._dict(
			discussion=self.post.name,
			discussion_title="A sensitive title",
			project=self.space.name,
			team=self.community.name,
			type="New Discussion",
			message="A new discussion: sensitive",
		)
		self.assertNotIn("sensitive", clean(notification).message)
		item = format_notification_item(notification, {}, self.outsider.name)
		self.assertNotIn("sensitive", item["title"] + item["description"])

	def test_response_scope_reads_are_batched_across_posts_and_communities(self):
		other = create_community("Other censor", admins=[self.member])
		other_space = create_space("Other censor Space", other)
		other_post = create_discussion("Other original", other_space)
		reply = create_comment(self.post, content="Original reply")
		with self.as_user(self.member):
			add(self.community.name, "Censor", "alpha")
			add(other.name, "Censor", "beta")
		rows = [
			{"doctype": "GP Discussion", "name": self.post.name, "content": "alpha beta"},
			{"doctype": "GP Discussion", "name": other_post.name, "content": "alpha beta"},
			{"doctype": "GP Comment", "name": reply.name, "content": "alpha beta"},
		]
		clean(rows)
		counts = []
		for payload in (rows, rows * 40):
			with patch.object(frappe.db, "sql", wraps=frappe.db.sql) as queries:
				result = clean(payload)
			counts.append(queries.call_count)
			self.assertEqual(result[0].content, "■■■■■ beta")
			self.assertEqual(result[1].content, "alpha ■■■■")
			self.assertEqual(result[2].content, "■■■■■ beta")
		self.assertEqual(counts, [3, 3])

	def test_held_edit_does_not_change_legacy_reply_cooldown(self):
		from frappe.utils import add_to_date, get_datetime

		from gameplan.slow_mode import last_submission

		reply = create_comment(self.post, content="Old reply", owner=self.outsider)
		created = add_to_date(frappe.utils.now(), hours=-2)
		frappe.db.set_value("GP Comment", reply.name, "creation", created)
		frappe.db.delete(
			"GP Slow Mode State", {"discussion": str(self.post.name), "user": self.outsider.name}
		)
		self.rule("Require approval", "reviewword")
		with self.as_user(self.outsider):
			edit("GP Comment", str(reply.name), str(reply.reload().modified), "reviewword")
		self.assertEqual(
			get_datetime(last_submission(str(self.post.name), user=self.outsider.name)), get_datetime(created)
		)
