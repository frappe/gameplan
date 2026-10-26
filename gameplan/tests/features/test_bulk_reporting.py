import json

import frappe

from gameplan.reporting import resolve, submit
from gameplan.reporting_bulk import preview
from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import (
	create_comment,
	create_community,
	create_discussion,
	create_space,
	declared_http_methods,
)
from gameplan.visibility import VISIBILITY_MEMBER_ACCESS


class TestBulkReporting(GameplanTestCase):
	def setUp(self):
		super().setUp()
		self.community = create_community(
			"Bulk reports", members=[self.member, self.second_member, self.outsider]
		)
		self.community.set_member_moderator(self.outsider.name, 1)
		self.space = create_space("Bulk review", self.community)
		self.discussion = create_discussion(
			"Current title", self.space, content="<p>First &amp; second</p>", owner=self.member
		)

	def review(self, doc=None, reason="Spam"):
		doc = doc or self.discussion
		with self.as_user(self.second_member):
			report = submit(doc.doctype, str(doc.name), reason, "Report note")
		return frappe.db.get_value("GP Report", report["name"], "review")

	def previews(self, reviews):
		with self.as_user(self.outsider):
			return preview(self.community.name, reviews)

	def decide(self, item, **kwargs):
		with self.as_user(self.outsider):
			resolve(
				self.community.name,
				item["review"],
				"Dismiss",
				"Reviewed together",
				item["version"],
				require_visible=True,
				**kwargs,
			)

	def test_preview_summarizes_all_reasons_without_reporter_evidence(self):
		review = self.review()
		# Summaries must include reports beyond the detail dialog's 40-report page.
		frappe.db.bulk_insert(
			"GP Report",
			fields=["name", "review", "owner", "reason"],
			values=[(frappe.generate_hash(), review, f"reporter{i}@example.com", "Other") for i in range(41)],
		)
		item = self.previews([review])[0]
		self.assertEqual(item["title"], "Current title")
		self.assertEqual(item["excerpt"], "First & second")
		self.assertEqual(item["reasons"], [{"reason": "Other", "count": 41}, {"reason": "Spam", "count": 1}])
		self.assertNotIn("owner", item)
		self.assertNotIn("reported_content", item)
		self.assertNotIn("Report note", frappe.as_json(item))
		frappe.db.set_value("GP Discussion", self.discussion.name, "content", "<p>" + "x" * 500 + "</p>")
		self.assertEqual(len(self.previews([review])[0]["excerpt"]), 300)

	def test_preview_requires_moderation_and_bounds_selection(self):
		review = self.review()
		for user in (self.member, self.second_member, self.guest, "Guest"):
			with self.subTest(user=str(user)), self.as_user(user), self.assertRaises(frappe.PermissionError):
				preview(self.community.name, [review])
		for names in ([], [review, review], list(map(str, range(51))), [1], [""]):
			with self.subTest(names=names), self.assertRaises(frappe.ValidationError):
				self.previews(names)
		self.assertEqual(declared_http_methods(preview), {"POST"})

	def test_private_missing_and_moved_targets_have_no_preview_details(self):
		private = create_space(
			"Private",
			self.community,
			visibility=VISIBILITY_MEMBER_ACCESS,
			members=[self.member, self.second_member],
		)
		doc = create_discussion("Restricted title", private, content="Restricted body", owner=self.member)
		restricted, moved = self.review(doc), self.review()
		other = create_community("Other Community")
		other_space = create_space("Other Space", other)
		self.discussion.move_to_project(other_space.name)
		for item in self.previews([restricted, moved, "missing-review"]):
			self.assertEqual(set(item), {"review", "error"})
			self.assertEqual(item["error"], "This review is no longer available.")
		private.add_member(self.outsider.name)
		self.assertEqual(self.previews([restricted])[0]["title"], "Restricted title")

	def test_changed_item_does_not_prevent_another_review_from_resolving(self):
		other = create_discussion("Other", self.space, owner=self.member)
		first, changed = self.previews([self.review(), self.review(other)])
		frappe.db.set_value("GP Discussion", other.name, "content", "Changed since preview")
		self.decide(first)
		with self.assertRaises(frappe.TimestampMismatchError):
			self.decide(changed)
		self.assertEqual(frappe.db.get_value("GP Review", first["review"], "status"), "Resolved")
		self.assertEqual(frappe.db.get_value("GP Review", changed["review"], "status"), "Pending")
		self.assertEqual(
			frappe.db.get_value("GP Review", first["review"], "decision_note"), "Reviewed together"
		)

	def test_removed_parent_and_deleted_reply_are_skipped_even_if_body_did_not_change(self):
		for removed_parent in (False, True):
			with self.subTest(parent=removed_parent):
				reply = create_comment(self.discussion, content="Unchanged reply", owner=self.member)
				review = self.review(reply)
				item = self.previews([review])[0]
				if removed_parent:
					self.discussion.hide("Removed discussion")
				else:
					frappe.db.set_value("GP Comment", reply.name, "deleted_at", frappe.utils.now())
				with self.assertRaises(frappe.TimestampMismatchError):
					self.decide(item)
				self.assertNotIn("version", self.previews([review])[0])
				self.assertEqual(frappe.db.get_value("GP Review", review, "status"), "Pending")

	def test_resolved_reviews_and_lost_moderator_authority_cannot_be_replayed(self):
		review = self.review()
		item = self.previews([review])[0]
		self.decide(item)
		self.assertNotIn("version", self.previews([review])[0])
		with self.assertRaises(frappe.TimestampMismatchError):
			self.decide(item)
		self.community.set_member_moderator(self.outsider.name, 0)
		with self.assertRaises(frappe.PermissionError):
			self.decide(item)

	def test_private_access_and_community_scope_are_rechecked_after_preview(self):
		private = create_space(
			"Private review",
			self.community,
			visibility=VISIBILITY_MEMBER_ACCESS,
			members=[self.member, self.second_member, self.outsider],
		)
		doc = create_discussion("Private target", private, owner=self.member)
		item = self.previews([self.review(doc)])[0]
		private.remove_member(self.outsider.name)
		with self.assertRaises(frappe.PermissionError):
			self.decide(item)
		private.add_member(self.outsider.name)
		other_space = create_space("Moved review", create_community("Moved Community"))
		doc.move_to_project(other_space.name)
		with self.assertRaises(frappe.PermissionError):
			self.decide(item)
		self.assertEqual(frappe.db.get_value("GP Review", item["review"], "status"), "Pending")

	def test_poll_edits_after_bulk_preview_require_a_fresh_review(self):
		draft = json.dumps({"title": "Original question", "options": [{"title": "Yes"}, {"title": "No"}]})
		with self.as_user(self.member):
			reply = create_comment(
				self.discussion,
				content=f"<div data-type=\"poll\" data-poll-draft='{draft}'></div>",
				owner=self.member,
			)
		review = self.review(reply)
		item = self.previews([review])[0]
		with self.as_user(self.member):
			poll = frappe.get_doc("GP Poll", {"comment": reply.name})
			poll.options[0].title = "Changed choice"
			poll.save()
		with self.assertRaises(frappe.TimestampMismatchError):
			self.decide(item)
		self.assertEqual(frappe.db.get_value("GP Review", review, "status"), "Pending")
		self.decide(self.previews([review])[0])
		self.assertEqual(frappe.db.get_value("GP Review", review, "status"), "Resolved")
