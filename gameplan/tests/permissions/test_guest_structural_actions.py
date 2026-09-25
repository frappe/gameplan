# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""A guest participates in a space. A guest never moves or manages anything.

Rule (Faris, 2026-09-19): in the spaces they are granted, guests comment, reply, react,
vote, start discussions, and edit the content they wrote. They do not archive, move or manage anything.
That means no moving a space to another community, no moving a discussion, page, task,
comment or poll to another space or thread, no archive or unarchive, no space settings,
no member changes and no pinning.

Every test here sets up the guest the way production does: granted, and then joined
(GPProject.join adds a GP Member row). That row is what used to make can_manage_space
answer True for a guest on a private space.
"""

import frappe
from frappe.client import set_value

from gameplan.gameplan.doctype.gp_discussion.gp_discussion import move_discussions
from gameplan.gameplan.doctype.gp_project.gp_project import mark_all_as_read, track_visits
from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import (
	create_comment,
	create_community,
	create_discussion,
	create_guest,
	create_page,
	create_poll,
	create_space,
	create_task,
	grant_guest_access,
)

REACTION_ADD = [{"emoji": "\U0001f44d", "operation": "add"}]


class GuestInJoinedSpacesTestCase(GameplanTestCase):
	"""Two private spaces in one community, both granted to the guest and both joined."""

	def setUp(self):
		super().setUp()
		self.community = create_community("Guest Rule Community", members=[self.member])
		self.other_community = create_community("Guest Rule Other Community", members=[self.member])
		self.space = create_space("Guest Rule Space", self.community, is_private=1, members=[self.member])
		self.second_space = create_space(
			"Guest Rule Second Space", self.community, is_private=1, members=[self.member]
		)
		for space in (self.space, self.second_space):
			grant_guest_access(self.guest, space)
			with self.as_user(self.guest):
				frappe.get_doc("GP Project", space.name).join()

		self.member_discussion = create_discussion("Member thread", self.space, owner=self.member)
		self.guest_discussion = create_discussion("Guest thread", self.space, owner=self.guest)
		self.second_discussion = create_discussion("Second thread", self.second_space, owner=self.member)

	def run_doc_method(self, doc, method, **kwargs):
		"""Call a whitelisted document method the way the v2 POST route does."""
		doc.check_permission("write")
		return getattr(doc, method)(**kwargs)

	def stored(self, doc):
		return frappe.get_doc(doc.doctype, doc.name)


class TestGuestCannotManageSpaces(GuestInJoinedSpacesTestCase):
	def test_the_joined_guest_holds_a_member_row(self):
		"""Precondition for every other test in this module."""
		self.assertTrue(
			frappe.db.exists(
				"GP Member", {"parenttype": "GP Project", "parent": self.space.name, "user": self.guest.name}
			)
		)

	def test_guest_holds_no_write_or_delete_on_a_joined_space(self):
		self.assert_not_allowed(self.space, "write", self.guest)
		self.assert_not_allowed(self.space, "delete", self.guest)

	def test_guest_cannot_move_a_space_to_another_community(self):
		with self.as_user(self.guest), self.assertRaises(frappe.PermissionError):
			frappe.get_doc("GP Project", self.space.name).move_to_team(self.other_community.name)

		self.assertEqual(self.stored(self.space).team, self.community.name)

	def test_guest_cannot_archive_a_space(self):
		with self.as_user(self.guest), self.assertRaises(frappe.PermissionError):
			self.run_doc_method(frappe.get_doc("GP Project", self.space.name), "archive")

		with self.as_user(self.guest), self.assertRaises(frappe.PermissionError):
			frappe.get_doc("GP Project", self.space.name).archive()

		self.assertIsNone(self.stored(self.space).archived_at)

	def test_guest_cannot_unarchive_a_space(self):
		frappe.get_doc("GP Project", self.space.name).archive()

		with self.as_user(self.guest), self.assertRaises(frappe.PermissionError):
			frappe.get_doc("GP Project", self.space.name).unarchive()

		self.assertIsNotNone(self.stored(self.space).archived_at)

	def test_guest_cannot_edit_space_settings(self):
		for fieldname, value in (("title", "Renamed by guest"), ("icon", "lucide-star"), ("is_private", 0)):
			with self.subTest(fieldname=fieldname):
				with self.as_user(self.guest), self.assertRaises(frappe.PermissionError):
					space = frappe.get_doc("GP Project", self.space.name)
					space.set(fieldname, value)
					space.save()

				with self.as_user(self.guest), self.assertRaises(frappe.PermissionError):
					set_value("GP Project", self.space.name, fieldname, value)

		stored = self.stored(self.space)
		self.assertEqual(stored.title, "Guest Rule Space")
		self.assertEqual(stored.is_private, 1)

	def test_guest_cannot_add_or_remove_space_members(self):
		with self.as_user(self.guest), self.assertRaises(frappe.PermissionError):
			frappe.get_doc("GP Project", self.space.name).add_member(self.second_member.name)

		with self.as_user(self.guest), self.assertRaises(frappe.PermissionError):
			frappe.get_doc("GP Project", self.space.name).remove_member(self.member.name)

		members = {row.user for row in self.stored(self.space).members}
		self.assertIn(self.member.name, members)
		self.assertNotIn(self.second_member.name, members)

	def test_guest_cannot_merge_spaces(self):
		with self.as_user(self.guest), self.assertRaises(frappe.PermissionError):
			frappe.get_doc("GP Project", self.second_space.name).merge_with_project(self.space.name)

		self.assertTrue(frappe.db.exists("GP Project", self.second_space.name))

	def test_guest_cannot_delete_a_space(self):
		with self.as_user(self.guest), self.assertRaises(frappe.PermissionError):
			frappe.delete_doc("GP Project", self.space.name)

		self.assertTrue(frappe.db.exists("GP Project", self.space.name))

	def test_guest_cannot_manage_a_community_even_with_an_admin_row(self):
		community = frappe.get_doc("GP Team", self.community.name)
		community.append("members", {"user": self.guest.name, "is_admin": 1})
		community.save(ignore_permissions=True)

		other_guest = create_guest("guest2@example.com", "Second Guest")
		grant_guest_access(other_guest, self.second_space)

		self.assert_not_allowed(community, "write", self.guest)
		# The community-admin methods check can_manage_community directly, not the role
		# layer, so this is the route that an admin row alone would open.
		with self.as_user(self.guest), self.assertRaises(frappe.PermissionError):
			frappe.get_doc("GP Team", self.community.name).remove_guest_access(other_guest.name)

		self.assertTrue(
			frappe.db.exists("GP Guest Access", {"user": other_guest.name, "project": self.second_space.name})
		)

	def test_a_member_of_the_private_space_still_manages_it(self):
		"""Members are permissive by design: the guest rule must not narrow them."""
		self.assert_allowed(self.space, "write", self.member)
		with self.as_user(self.member):
			frappe.get_doc("GP Project", self.space.name).archive()
			frappe.get_doc("GP Project", self.space.name).unarchive()


class TestGuestCannotMoveContent(GuestInJoinedSpacesTestCase):
	def test_guest_cannot_move_own_discussion_with_move_to_project(self):
		with self.as_user(self.guest), self.assertRaises(frappe.PermissionError):
			self.run_doc_method(
				frappe.get_doc("GP Discussion", self.guest_discussion.name),
				"move_to_project",
				project=self.second_space.name,
			)

		self.assertEqual(str(self.stored(self.guest_discussion).project), str(self.space.name))

	def test_guest_cannot_move_own_discussion_with_move_discussions(self):
		with self.as_user(self.guest):
			result = move_discussions(
				[{"name": self.guest_discussion.name, "project": self.second_space.name}]
			)

		self.assertEqual(result["moved"], [])
		self.assertEqual([row["name"] for row in result["failed"]], [self.guest_discussion.name])
		self.assertEqual(str(self.stored(self.guest_discussion).project), str(self.space.name))

	def test_guest_cannot_move_a_members_discussion_with_move_discussions(self):
		with self.as_user(self.guest):
			result = move_discussions(
				[{"name": self.member_discussion.name, "project": self.second_space.name}]
			)

		self.assertEqual(result["moved"], [])
		self.assertEqual(str(self.stored(self.member_discussion).project), str(self.space.name))

	def test_guest_cannot_move_own_discussion_by_saving_its_project(self):
		with self.as_user(self.guest), self.assertRaises(frappe.PermissionError):
			discussion = frappe.get_doc("GP Discussion", self.guest_discussion.name)
			discussion.project = self.second_space.name
			discussion.save()

		with self.as_user(self.guest), self.assertRaises(frappe.PermissionError):
			set_value("GP Discussion", self.guest_discussion.name, "project", self.second_space.name)

		self.assertEqual(str(self.stored(self.guest_discussion).project), str(self.space.name))

	def test_guest_cannot_move_own_page_or_task(self):
		page = create_page("Guest page", self.space, owner=self.guest)
		task = create_task("Guest task", self.space, owner=self.guest)

		for doc in (page, task):
			with self.subTest(doctype=doc.doctype):
				with self.as_user(self.guest), self.assertRaises(frappe.PermissionError):
					set_value(doc.doctype, doc.name, "project", self.second_space.name)
				self.assertEqual(str(self.stored(doc).project), str(self.space.name))

	def test_guest_cannot_move_own_comment_to_another_thread(self):
		comment = create_comment(self.guest_discussion, owner=self.guest)

		with self.as_user(self.guest), self.assertRaises(frappe.PermissionError):
			set_value("GP Comment", comment.name, "reference_name", self.second_discussion.name)

		self.assertEqual(str(self.stored(comment).reference_name), str(self.guest_discussion.name))

	def test_guest_cannot_move_own_poll_to_another_thread(self):
		poll = create_poll("Guest poll", self.guest_discussion, owner=self.guest)

		with self.as_user(self.guest), self.assertRaises(frappe.PermissionError):
			set_value("GP Poll", poll.name, "discussion", self.second_discussion.name)

		self.assertEqual(str(self.stored(poll).discussion), str(self.guest_discussion.name))

	def test_guest_cannot_pin_own_discussion(self):
		with self.as_user(self.guest), self.assertRaises(frappe.PermissionError):
			self.run_doc_method(frappe.get_doc("GP Discussion", self.guest_discussion.name), "pin_discussion")

		self.assertIsNone(self.stored(self.guest_discussion).pinned_at)

	def test_guest_cannot_unpin_own_discussion(self):
		with self.as_user(self.member):
			frappe.get_doc("GP Discussion", self.guest_discussion.name).pin_discussion()

		with self.as_user(self.guest), self.assertRaises(frappe.PermissionError):
			frappe.get_doc("GP Discussion", self.guest_discussion.name).unpin_discussion()

		self.assertIsNotNone(self.stored(self.guest_discussion).pinned_at)

	def test_a_member_still_moves_and_pins_any_discussion(self):
		for space in (self.space, self.second_space):
			frappe.get_doc("GP Project", space.name).add_member_row(self.second_member.name)

		with self.as_user(self.second_member):
			discussion = frappe.get_doc("GP Discussion", self.guest_discussion.name)
			discussion.pin_discussion()
			discussion.move_to_project(self.second_space.name)

		stored = self.stored(self.guest_discussion)
		self.assertIsNotNone(stored.pinned_at)
		self.assertEqual(str(stored.project), str(self.second_space.name))


class TestGuestStillParticipates(GuestInJoinedSpacesTestCase):
	"""Participation keeps working for a guest who has joined the space."""

	def test_guest_can_comment_and_reply(self):
		with self.as_user(self.guest):
			for discussion in (self.member_discussion, self.guest_discussion):
				comment = frappe.get_doc(
					doctype="GP Comment",
					reference_doctype="GP Discussion",
					reference_name=discussion.name,
					content="<p>Guest reply</p>",
				).insert()
				self.assertEqual(comment.owner, self.guest.name)

	def test_guest_can_start_a_discussion_in_a_granted_space(self):
		with self.as_user(self.guest):
			discussion = frappe.get_doc(
				doctype="GP Discussion",
				title="Guest question",
				content="<p>Started by the guest</p>",
				project=self.space.name,
			).insert()

		self.assertEqual(discussion.owner, self.guest.name)
		self.assertEqual(str(discussion.project), str(self.space.name))

	def test_guest_can_publish_a_discussion_draft_in_a_granted_space(self):
		"""The new-discussion page posts through GPDraft.publish."""
		with self.as_user(self.guest):
			draft = frappe.get_doc(
				doctype="GP Draft",
				type="Discussion",
				title="Guest draft",
				content="<p>Drafted by the guest</p>",
				project=self.space.name,
			).insert()
			self.run_doc_method(draft, "publish")

		name = frappe.db.get_value("GP Discussion", {"title": "Guest draft"}, "name")
		self.assertEqual(frappe.db.get_value("GP Discussion", name, "owner"), self.guest.name)

	def test_guest_cannot_start_a_discussion_outside_granted_spaces(self):
		ungranted = create_space("Guest Rule Ungranted", self.community, is_private=1, members=[self.member])
		with self.as_user(self.guest), self.assertRaises(frappe.PermissionError):
			frappe.get_doc(
				doctype="GP Discussion", title="Blocked", content="<p>No</p>", project=ungranted.name
			).insert()

	def test_guest_still_cannot_create_a_page_or_task(self):
		for doctype in ("GP Page", "GP Task"):
			with self.subTest(doctype=doctype):
				with self.as_user(self.guest), self.assertRaises(frappe.PermissionError):
					frappe.get_doc(doctype=doctype, title="Blocked", project=self.space.name).insert()

	def test_guest_can_react_to_a_discussion_and_a_comment(self):
		comment = create_comment(self.member_discussion, owner=self.member)
		with self.as_user(self.guest):
			self.run_doc_method(
				frappe.get_doc("GP Discussion", self.member_discussion.name), "react", operations=REACTION_ADD
			)
			self.run_doc_method(frappe.get_doc("GP Comment", comment.name), "react", operations=REACTION_ADD)

		self.assertIn(self.guest.name, {r.user for r in self.stored(self.member_discussion).reactions})
		self.assertIn(self.guest.name, {r.user for r in self.stored(comment).reactions})

	def test_guest_can_vote_in_a_poll(self):
		poll = create_poll("Lunch?", self.member_discussion, owner=self.member)

		with self.as_user(self.guest):
			self.run_doc_method(frappe.get_doc("GP Poll", poll.name), "submit_vote", option="Yes")

		self.assertEqual([(v.user, v.option) for v in self.stored(poll).votes], [(self.guest.name, "Yes")])

	def test_guest_can_edit_own_discussion_and_comment(self):
		comment = create_comment(self.member_discussion, owner=self.guest)
		with self.as_user(self.guest):
			discussion = frappe.get_doc("GP Discussion", self.guest_discussion.name)
			discussion.title = "Guest thread, edited"
			discussion.content = "<p>Edited by the guest</p>"
			discussion.save()

			own_comment = frappe.get_doc("GP Comment", comment.name)
			own_comment.content = "<p>Edited comment</p>"
			own_comment.save()

		self.assertEqual(self.stored(self.guest_discussion).title, "Guest thread, edited")
		self.assertIn("Edited comment", self.stored(comment).content)

	def test_guest_can_delete_own_comment_and_poll(self):
		comment = create_comment(self.member_discussion, owner=self.guest)
		poll = create_poll("Guest poll", self.member_discussion, owner=self.guest)

		with self.as_user(self.guest):
			frappe.delete_doc("GP Comment", comment.name)
			frappe.delete_doc("GP Poll", poll.name)

		self.assertFalse(frappe.db.exists("GP Comment", comment.name))
		self.assertFalse(frappe.db.exists("GP Poll", poll.name))

	def test_guest_can_close_and_reopen_own_discussion(self):
		with self.as_user(self.guest):
			self.run_doc_method(
				frappe.get_doc("GP Discussion", self.guest_discussion.name), "close_discussion"
			)
			self.assertIsNotNone(self.stored(self.guest_discussion).closed_at)
			self.run_doc_method(
				frappe.get_doc("GP Discussion", self.guest_discussion.name), "reopen_discussion"
			)

		self.assertIsNone(self.stored(self.guest_discussion).closed_at)

	def test_guest_cannot_close_a_members_discussion(self):
		with self.as_user(self.guest), self.assertRaises(frappe.PermissionError):
			self.run_doc_method(
				frappe.get_doc("GP Discussion", self.member_discussion.name), "close_discussion"
			)

		self.assertIsNone(self.stored(self.member_discussion).closed_at)

	def test_guest_can_delete_own_discussion_with_its_replies(self):
		"""The delete cascades to other users' comments, polls, visits and activity."""
		comment = create_comment(self.guest_discussion, owner=self.member)
		poll = create_poll("Member poll", self.guest_discussion, owner=self.member)
		with self.as_user(self.member):
			frappe.get_doc("GP Discussion", self.guest_discussion.name).track_visit()
		with self.as_user(self.guest):
			# Closing logs a GP Activity row, which the delete has to take with it.
			frappe.get_doc("GP Discussion", self.guest_discussion.name).close_discussion()
			frappe.delete_doc("GP Discussion", self.guest_discussion.name)

		self.assertFalse(frappe.db.exists("GP Discussion", self.guest_discussion.name))
		self.assertFalse(frappe.db.exists("GP Comment", comment.name))
		self.assertFalse(frappe.db.exists("GP Poll", poll.name))
		self.assertFalse(
			frappe.db.exists(
				"GP Activity",
				{"reference_doctype": "GP Discussion", "reference_name": self.guest_discussion.name},
			)
		)

	def test_guest_cannot_delete_a_members_discussion(self):
		self.assert_not_allowed(self.member_discussion, "delete", self.guest)
		with self.as_user(self.guest), self.assertRaises(frappe.PermissionError):
			frappe.delete_doc("GP Discussion", self.member_discussion.name)

		self.assertTrue(frappe.db.exists("GP Discussion", self.member_discussion.name))

	def test_guest_still_cannot_delete_own_page_or_task(self):
		page = create_page("Guest page", self.space, owner=self.guest)
		task = create_task("Guest task", self.space, owner=self.guest)
		for doc in (page, task):
			with self.subTest(doctype=doc.doctype):
				with self.as_user(self.guest), self.assertRaises(frappe.PermissionError):
					frappe.delete_doc(doc.doctype, doc.name)
				self.assertTrue(frappe.db.exists(doc.doctype, doc.name))

	def test_guest_can_bookmark_and_mark_read_or_unread(self):
		with self.as_user(self.guest):
			discussion = frappe.get_doc("GP Discussion", self.member_discussion.name)
			self.run_doc_method(discussion, "add_bookmark")
			self.run_doc_method(discussion, "track_visit")
			self.run_doc_method(discussion, "mark_as_unread")
			self.run_doc_method(discussion, "remove_bookmark")
			track_visits([self.space.name])
			mark_all_as_read([self.space.name])

		self.assertFalse(
			frappe.db.exists(
				"GP Bookmark", {"discussion": self.member_discussion.name, "user": self.guest.name}
			)
		)
		self.assertTrue(
			frappe.db.exists(
				"GP Discussion Visit", {"discussion": self.member_discussion.name, "user": self.guest.name}
			)
		)
		self.assertTrue(
			frappe.db.get_value(
				"GP Project Visit", {"project": self.space.name, "user": self.guest.name}, "mark_all_read_at"
			)
		)
