# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

import frappe
from frappe.utils import cstr

from gameplan.tests.features.test_discussions import DiscussionLifecycleTestCase
from gameplan.tests.fixtures import create_community, create_discussion, create_space


class TestHighlightedComments(DiscussionLifecycleTestCase):
	def setUp(self):
		super().setUp()
		self.reply = self.comment_as(self.second_member, "<p>Restart the worker to fix it</p>")

	def highlight(self, user, comment):
		with self.as_user(user):
			frappe.get_doc("GP Discussion", self.discussion.name).highlight_comment(cstr(comment.name))

	def unhighlight(self, user, comment):
		with self.as_user(user):
			frappe.get_doc("GP Discussion", self.discussion.name).unhighlight_comment(cstr(comment.name))

	def highlighted(self):
		return [
			cstr(name)
			for name in frappe.get_all(
				"GP Comment",
				filters={
					"reference_doctype": "GP Discussion",
					"reference_name": self.discussion.name,
					"highlighted_at": ("is", "set"),
				},
				order_by="creation asc",
				pluck="name",
			)
		]

	def test_author_can_highlight_a_reply(self):
		self.highlight(self.member, self.reply)

		self.assertEqual(self.highlighted(), [cstr(self.reply.name)])

	def test_highlighting_records_who_and_when(self):
		self.highlight(self.member, self.reply)

		stored = frappe.db.get_value(
			"GP Comment", self.reply.name, ["highlighted_by", "highlighted_at"], as_dict=True
		)
		self.assertEqual(stored.highlighted_by, self.member.name)
		self.assertIsNotNone(stored.highlighted_at)

	def test_highlighting_logs_an_activity(self):
		self.highlight(self.member, self.reply)

		self.assertEqual(self.activities(), [{"action": "Comment Highlighted", "user": self.member.name}])

	def test_highlighting_another_reply_replaces_the_first(self):
		other = self.comment_as(self.member, "Another answer")
		self.highlight(self.member, self.reply)

		self.highlight(self.member, other)

		self.assertEqual(self.highlighted(), [cstr(other.name)])
		self.assertEqual(
			[activity.action for activity in self.activities()],
			["Comment Highlighted", "Comment Unhighlighted", "Comment Highlighted"],
		)

	def test_highlighting_the_same_reply_again_changes_nothing(self):
		self.highlight(self.member, self.reply)

		self.highlight(self.member, self.reply)

		self.assertEqual(len(self.activities("Comment Highlighted")), 1)

	def test_unhighlighting_clears_the_reply_and_logs_it(self):
		self.highlight(self.member, self.reply)

		self.unhighlight(self.member, self.reply)

		self.assertEqual(self.highlighted(), [])
		self.assertEqual(len(self.activities("Comment Unhighlighted")), 1)

	def test_unhighlighting_a_reply_that_is_not_highlighted_does_nothing(self):
		self.unhighlight(self.member, self.reply)

		self.assertEqual(self.activities(), [])

	def test_works_on_a_closed_discussion(self):
		with self.as_user(self.member):
			frappe.get_doc("GP Discussion", self.discussion.name).close_discussion()

		self.highlight(self.member, self.reply)

		self.assertEqual(self.highlighted(), [cstr(self.reply.name)])

	def test_another_member_cannot_highlight(self):
		with self.assertRaises(frappe.PermissionError):
			self.highlight(self.second_member, self.reply)

		self.assertEqual(self.highlighted(), [])

	def test_another_member_cannot_unhighlight(self):
		self.highlight(self.member, self.reply)

		with self.assertRaises(frappe.PermissionError):
			self.unhighlight(self.second_member, self.reply)

		self.assertEqual(self.highlighted(), [cstr(self.reply.name)])

	def test_a_global_admin_cannot_highlight(self):
		with self.assertRaises(frappe.PermissionError):
			self.highlight(self.admin, self.reply)

		self.assertEqual(self.highlighted(), [])

	def test_a_community_admin_cannot_highlight(self):
		community = create_community("Moderated Co", members=[self.member], admins=[self.second_member])
		space = create_space("Moderated Space", community)
		self.discussion = create_discussion("Moderated thread", space, owner=self.member)
		reply = self.comment_as(self.member, "An answer")

		with self.assertRaises(frappe.PermissionError):
			self.highlight(self.second_member, reply)

		self.assertEqual(self.highlighted(), [])

	def test_the_reply_author_cannot_highlight_through_a_plain_save(self):
		with self.as_user(self.second_member):
			doc = frappe.get_doc("GP Comment", self.reply.name)
			doc.highlighted_by = self.second_member.name
			doc.highlighted_at = frappe.utils.now()
			with self.assertRaises(frappe.PermissionError):
				doc.save()

		self.assertEqual(self.highlighted(), [])

	def test_a_new_reply_cannot_arrive_highlighted(self):
		for user in (self.second_member, self.member):
			with self.as_user(user):
				reply = frappe.get_doc(
					doctype="GP Comment",
					reference_doctype="GP Discussion",
					reference_name=self.discussion.name,
					content="Forged answer",
					highlighted_by=self.member.name,
					highlighted_at=frappe.utils.now(),
				).insert()

			stored = frappe.db.get_value(
				"GP Comment", reply.name, ["highlighted_by", "highlighted_at"], as_dict=True
			)
			self.assertIsNone(stored.highlighted_by)
			self.assertIsNone(stored.highlighted_at)

	def test_moving_a_highlighted_reply_clears_its_highlight(self):
		other_discussion = create_discussion("Other thread", self.space, owner=self.member)
		self.highlight(self.member, self.reply)

		with self.as_user(self.second_member):
			doc = frappe.get_doc("GP Comment", self.reply.name)
			doc.reference_name = other_discussion.name
			doc.save()

		stored = frappe.db.get_value(
			"GP Comment", self.reply.name, ["highlighted_by", "highlighted_at"], as_dict=True
		)
		self.assertIsNone(stored.highlighted_by)
		self.assertIsNone(stored.highlighted_at)

	def test_the_reply_author_can_still_edit_a_highlighted_reply(self):
		self.highlight(self.member, self.reply)

		with self.as_user(self.second_member):
			doc = frappe.get_doc("GP Comment", self.reply.name)
			doc.content = "<p>Restart the worker, then clear the cache</p>"
			doc.save()

		self.assertEqual(self.highlighted(), [cstr(self.reply.name)])

	def test_a_reply_from_another_discussion_is_rejected(self):
		other_discussion = create_discussion("Other thread", self.space, owner=self.member)
		with self.as_user(self.member):
			foreign = frappe.get_doc(
				doctype="GP Comment",
				reference_doctype="GP Discussion",
				reference_name=other_discussion.name,
				content="Elsewhere",
			).insert()

		with self.assertRaises(frappe.ValidationError):
			self.highlight(self.member, foreign)

		self.assertIsNone(frappe.db.get_value("GP Comment", foreign.name, "highlighted_at"))

	def test_a_filter_in_place_of_a_reply_is_rejected(self):
		with self.as_user(self.member):
			with self.assertRaises(frappe.FrappeTypeError):
				frappe.get_doc("GP Discussion", self.discussion.name).highlight_comment(["like", "%"])

		self.assertEqual(self.activities(), [])

	def test_deleting_the_reply_drops_the_highlighted_reply(self):
		self.highlight(self.member, self.reply)

		self.delete_as(self.reply, self.second_member)

		self.assertIsNone(self.stored().as_dict().highlighted_reply)

	def test_highlighted_reply_carries_the_reply_author_text_and_highlighter(self):
		self.highlight(self.member, self.reply)

		with self.as_user(self.second_member):
			reply = self.stored().as_dict().highlighted_reply

		self.assertEqual(reply["name"], cstr(self.reply.name))
		self.assertEqual(reply["owner"], self.second_member.name)
		self.assertEqual(reply["highlighted_by"], self.member.name)
		self.assertIn("Restart the worker", reply["content"])

	def test_highlighted_reply_follows_the_replacement(self):
		other = self.comment_as(self.member, "Another answer")
		self.highlight(self.member, self.reply)

		self.highlight(self.member, other)

		self.assertEqual(self.stored().as_dict().highlighted_reply["name"], cstr(other.name))

	def test_highlight_text_is_long_enough_for_a_few_lines(self):
		long_reply = self.comment_as(self.second_member, "<p>" + "word " * 100 + "</p>")

		self.highlight(self.member, long_reply)

		content = self.stored().as_dict().highlighted_reply["content"]
		self.assertGreater(len(content), 200)

	def test_highlighted_reply_is_empty_without_one(self):
		self.assertIsNone(self.stored().as_dict().highlighted_reply)
