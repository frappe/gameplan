import json

import frappe

from gameplan.reporting import detail, queue, resolve, submit
from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import (
	create_comment,
	create_community,
	create_discussion,
	create_space,
	create_task,
)


class TestReviewIntegrity(GameplanTestCase):
	def setUp(self):
		super().setUp()
		self.community = create_community(
			"Review integrity", members=[self.member, self.second_member, self.outsider]
		)
		self.community.set_member_moderator(self.outsider.name, 1)
		self.space = create_space("Reported content", self.community)
		self.discussion = create_discussion("Reported discussion", self.space, owner=self.member)
		self.reply = create_comment(self.discussion, content="Reported reply", owner=self.member)

	def report(self, doc):
		with self.as_user(self.second_member):
			name = submit(doc.doctype, str(doc.name), "Spam")["name"]
		return frappe.db.get_value("GP Report", name, "review")

	def details(self, review):
		with self.as_user(self.outsider):
			return detail(self.community.name, review)

	def decide(self, review, expected, decision="Dismiss"):
		with self.as_user(self.outsider):
			return resolve(self.community.name, review, decision, "Reviewed", expected)

	def poll(self):
		draft = json.dumps({"title": "Original question", "options": [{"title": "Yes"}, {"title": "No"}]})
		with self.as_user(self.member):
			self.reply.content = f"<div data-type=\"poll\" data-poll-draft='{draft}'></div>"
			self.reply.save()
		return frappe.get_doc("GP Poll", {"comment": self.reply.name})

	def test_reported_discussion_cannot_be_permanently_deleted_until_review_is_resolved(self):
		review = self.report(self.discussion)
		with self.as_user(self.member), self.assertRaises(frappe.ValidationError):
			self.discussion.delete()
		data = self.details(review)
		self.assertEqual(data["evidence"].reported_content, self.discussion.content)
		with self.as_user(self.outsider):
			self.assertIn(review, [row.name for row in queue(self.community.name)["items"]])
		self.decide(review, data["current"]["version"])
		with self.as_user(self.member):
			self.discussion.delete()
		self.assertEqual(frappe.db.get_value("GP Review", review, "status"), "Resolved")
		self.assertTrue(frappe.db.exists("GP Report", {"review": review}))

	def test_pending_reply_reports_prevent_direct_and_cascaded_permanent_deletion(self):
		review = self.report(self.reply)
		for doc in (self.reply, self.discussion):
			with self.as_user(self.member), self.assertRaises(frappe.ValidationError):
				doc.delete()
		self.assertEqual(self.details(review)["evidence"].reported_content, "Reported reply")
		self.decide(review, self.details(review)["current"]["version"])
		with self.as_user(self.member):
			self.discussion.delete()

	def test_question_and_option_edits_invalidate_all_decisions(self):
		poll = self.poll()
		review = self.report(self.reply)
		for field in ("title", "options"):
			previous = self.details(review)["current"]["version"]
			with self.as_user(self.member):
				poll.reload()
				if field == "title":
					poll.title = "Edited question"
				else:
					poll.options[0].title = "Edited choice"
				poll.save()
			for decision in ("Dismiss", "Uphold", "Hide", "Delete Spam"):
				with self.assertRaises(frappe.TimestampMismatchError):
					self.decide(review, previous, decision)
			self.assertEqual(frappe.db.get_value("GP Review", review, "status"), "Pending")
			self.assertNotEqual(self.details(review)["current"]["version"], previous)
		self.decide(review, self.details(review)["current"]["version"])

	def test_normal_voting_does_not_invalidate_a_content_review(self):
		poll = self.poll()
		review = self.report(self.reply)
		previous = self.details(review)["current"]["version"]
		with self.as_user(self.second_member):
			poll.submit_vote("Yes")
		self.assertEqual(self.details(review)["current"]["version"], previous)
		self.decide(review, previous)

	def test_pending_reports_block_moving_reply_to_an_unreportable_target(self):
		task = create_task("Task target", self.space)
		review = self.report(self.reply)
		with self.as_user(self.member), self.assertRaises(frappe.ValidationError):
			self.reply.reference_doctype = "GP Task"
			self.reply.reference_name = str(task.name)
			self.reply.save()
		self.assertEqual(self.details(review)["evidence"].reported_content, "Reported reply")
		self.decide(review, self.details(review)["current"]["version"])
		with self.as_user(self.member):
			self.reply.reload()
			self.reply.reference_doctype = "GP Task"
			self.reply.reference_name = str(task.name)
			self.reply.save()
