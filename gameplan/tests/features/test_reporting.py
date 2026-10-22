import frappe

from gameplan.community_bans import set_ban
from gameplan.reporting import detail, queue, resolve, submit
from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import (
	create_comment,
	create_community,
	create_discussion,
	create_space,
	grant_guest_access,
)
from gameplan.visibility import VISIBILITY_MEMBER_ACCESS


class TestReporting(GameplanTestCase):
	def setUp(self):
		super().setUp()
		self.community = create_community("Reports", members=[self.member, self.second_member, self.outsider])
		self.community.set_member_moderator(self.outsider.name, 1)
		self.space = create_space("Reports Space", self.community)
		self.discussion = create_discussion(
			"Original title", self.space, content="Original evidence", owner=self.member
		)
		self.reply = create_comment(self.discussion, content="Reply evidence", owner=self.member)

	def report(self, doc=None, user=None, **values):
		doc = doc or self.discussion
		with self.as_user(user or self.second_member):
			return submit(doc.doctype, str(doc.name), values.pop("reason", "Spam"), **values)["name"]

	def review(self, report=None):
		return frappe.db.get_value("GP Report", report or self.report(), "review")

	def decide(self, review, decision="Dismiss", **kwargs):
		with self.as_user(self.outsider):
			data = detail(self.community.name, review)
			return resolve(
				self.community.name,
				review,
				decision,
				kwargs.pop("note", "Reviewed"),
				kwargs.pop("expected_version", data["current"]["version"]),
				**kwargs,
			)

	def test_reports_group_and_duplicate_submission_preserves_original_evidence(self):
		first = self.report(note="First note")
		self.assertEqual(self.report(note="Changed note"), first)
		second = self.report(user=self.outsider)
		self.assertNotEqual(first, second)
		self.assertEqual(self.review(first), self.review(second))
		with self.as_user(self.outsider):
			data = detail(self.community.name, self.review(first))
		self.assertEqual(len(data["reports"]), 2)
		self.assertEqual(data["reports"][0].note, "First note")
		self.assertEqual(data["reports"][0].owner, self.second_member.name)

	def test_edited_content_does_not_overwrite_reported_version(self):
		review = self.review()
		self.discussion.reload()
		self.discussion.content = "Edited content"
		self.discussion.save()
		with self.as_user(self.outsider):
			data = detail(self.community.name, review)
		self.assertIn("Original evidence", data["evidence"].reported_content)
		self.assertIn("Edited content", data["current"]["content"])

	def test_each_resolution_records_actor_note_and_preserves_or_removes_content(self):
		for decision in ("Dismiss", "Uphold", "Hide", "Delete Spam"):
			with self.subTest(decision=decision):
				doc = create_discussion(decision, self.space, owner=self.member)
				review = self.review(self.report(doc))
				self.decide(review, decision)
				stored = frappe.get_doc("GP Review", review)
				self.assertEqual(
					(stored.status, stored.decision, stored.decision_note), ("Resolved", decision, "Reviewed")
				)
				self.assertEqual(stored.decided_by, self.outsider.name)
				self.assertTrue(stored.decided_at)
				doc.reload()
				self.assertEqual(bool(doc.hidden_at), decision == "Hide")
				self.assertEqual(bool(doc.spam_removed_at), decision == "Delete Spam")

	def test_resolved_review_cannot_be_overwritten_and_new_report_gets_new_review(self):
		first = self.report()
		review = self.review(first)
		self.decide(review)
		with self.assertRaises(frappe.TimestampMismatchError):
			self.decide(review, "Hide")
		self.assertNotEqual(self.review(self.report()), review)
		self.discussion.reload()
		self.assertFalse(self.discussion.hidden_at)

	def test_changed_post_blocks_a_stale_decision(self):
		review = self.review()
		with self.as_user(self.outsider):
			old = detail(self.community.name, review)["current"]["version"]
		self.discussion.reload()
		self.discussion.content = "Changed during review"
		self.discussion.save()
		with self.assertRaises(frappe.TimestampMismatchError):
			self.decide(review, "Hide", expected_version=old)
		self.assertEqual(frappe.db.get_value("GP Review", review, "status"), "Pending")

	def test_private_space_and_community_moves_change_queue_and_detail_access(self):
		review = self.review(self.report(self.reply))
		private = create_space(
			"Private reports", self.community, visibility=VISIBILITY_MEMBER_ACCESS, members=[self.member]
		)
		self.discussion.reload()
		self.discussion.project = private.name
		self.discussion.save()
		with self.as_user(self.outsider):
			self.assertEqual(queue(self.community.name)["items"], [])
			with self.assertRaises(frappe.PermissionError):
				detail(self.community.name, review)
		other = create_community("Destination", admins=[self.outsider])
		space = create_space("Moved", other)
		self.discussion.reload()
		self.discussion.project = space.name
		self.discussion.save()
		with self.as_user(self.outsider):
			self.assertEqual(queue(self.community.name)["items"], [])
			self.assertEqual(queue(other.name)["items"][0].name, review)
			detail(other.name, review)

	def test_reporters_and_authors_cannot_read_evidence_or_queue(self):
		report = self.report()
		review = self.review(report)
		for user in (self.member, self.second_member, self.guest, "Guest"):
			with self.subTest(user=str(user)), self.as_user(user):
				for call in (lambda: queue(self.community.name), lambda: detail(self.community.name, review)):
					with self.assertRaises(frappe.PermissionError):
						call()
				for doctype, name in (("GP Review", review), ("GP Report", report)):
					with self.assertRaises(frappe.PermissionError):
						frappe.get_doc(doctype, name).check_permission("read")

	def test_reporting_eligibility_and_removed_target_guards(self):
		for user in (self.member, self.guest, "Guest"):
			with self.subTest(user=str(user)), self.assertRaises(frappe.PermissionError):
				self.report(user=user)
		grant_guest_access(self.guest, self.space)
		self.report(user=self.guest)
		set_ban(self.community.name, self.second_member.name, 1, "Spam")
		with self.assertRaises(frappe.PermissionError):
			self.report()
		set_ban(self.community.name, self.second_member.name, 0)
		self.discussion.hide("Removed")
		with self.assertRaises(frappe.PermissionError):
			self.report()

	def test_quota_is_per_account_across_targets_and_does_not_count_duplicates(self):
		first = self.report()
		for index in range(9):
			self.report(create_discussion(f"Quota {index}", self.space, owner=self.member))
		self.assertEqual(self.report(), first)
		other = create_community("Quota elsewhere", members=[self.second_member])
		space = create_space("Other quota Space", other)
		with self.assertRaises(frappe.RateLimitExceededError):
			self.report(create_discussion("Elsewhere", space, owner=self.member))
		self.report(self.reply, user=self.outsider)

	def test_validation_immutable_records_and_post_type(self):
		for values in ({"reason": "Unknown"}, {"reason": "Other"}, {"note": "x" * 501}):
			with self.subTest(values=values), self.assertRaises(frappe.ValidationError):
				self.report(**values)
		report = self.report(reason="Other", note="Explanation")
		review = self.review(report)
		for doctype, name in (("GP Report", report), ("GP Review", review)):
			doc = frappe.get_doc(doctype, name)
			with self.assertRaises(frappe.PermissionError):
				doc.save(ignore_permissions=True)
			with self.assertRaises(frappe.PermissionError):
				doc.delete(ignore_permissions=True)
		with self.assertRaises(frappe.ValidationError):
			self.decide(review, note="")
		with self.assertRaises(frappe.ValidationError):
			self.decide(review, "Ban")
		with self.as_user(self.second_member), self.assertRaises(frappe.ValidationError):
			submit("User", self.member.name, "Spam")

	def test_quota_expires_and_queue_pages_omit_inaccessible_targets(self):
		for index in range(42):
			frappe.get_doc(
				doctype="GP Review",
				reference_doctype="GP Discussion",
				reference_name=f"missing-{index}",
				status="Pending",
			).insert(ignore_permissions=True)
		review = self.review()
		with self.as_user(self.outsider):
			self.assertEqual([row.name for row in queue(self.community.name)["items"]], [review])
			self.assertFalse(queue(self.community.name)["has_more"])
			self.assertEqual(queue(self.community.name, status="Resolved")["items"], [])
		Report = frappe.qb.DocType("GP Report")
		frappe.qb.update(Report).set(Report.creation, "2000-01-01 00:00:00").run()
		self.report(self.reply)

	def test_evidence_is_loaded_one_version_at_a_time_and_cannot_cross_reviews(self):
		first = self.report()
		self.discussion.reload()
		self.discussion.content = "Later reported version"
		self.discussion.save()
		second = self.report(user=self.outsider)
		other = self.report(self.reply)
		with self.as_user(self.outsider):
			data = detail(self.community.name, self.review(first), report=second)
			self.assertNotIn("reported_content", data["reports"][0])
			self.assertIn("Later reported version", data["evidence"].reported_content)
			with self.assertRaises(frappe.PermissionError):
				detail(self.community.name, self.review(first), report=other)
