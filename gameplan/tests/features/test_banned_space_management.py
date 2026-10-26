import frappe

from gameplan.community_bans import set_ban
from gameplan.permissions import can_manage_space, can_view_space
from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import create_comment, create_community, create_discussion, create_space
from gameplan.visibility import VISIBILITY_MEMBER_ACCESS


class TestBannedSpaceManagement(GameplanTestCase):
	def setUp(self):
		super().setUp()
		self.community = create_community("Ban boundary", members=[self.member])
		self.destination = create_community("Other Community", members=[self.member])
		self.space = create_space(
			"Member managed", self.community, visibility=VISIBILITY_MEMBER_ACCESS, members=[self.member]
		)
		self.other_space = create_space(
			"Merge destination", self.destination, visibility=VISIBILITY_MEMBER_ACCESS, members=[self.member]
		)
		self.discussion = create_discussion("Keep this discussion", self.space, owner=self.member)
		self.reply = create_comment(self.discussion, content="Keep this reply", owner=self.second_member)
		self.assertTrue(can_manage_space(self.member.name, self.space))
		set_ban(self.community.name, self.member.name, 1, "Read only")

	def test_banned_space_member_cannot_move_through_method_or_normal_save(self):
		with self.as_user(self.member):
			with self.assertRaises(frappe.PermissionError):
				self.space.move_to_team(self.destination.name)
			self.space.reload()
			self.space.team = self.destination.name
			with self.assertRaises(frappe.PermissionError):
				self.space.save()
		self.assertEqual(frappe.db.get_value("GP Project", self.space.name, "team"), self.community.name)

	def test_banned_space_member_cannot_merge_into_another_community(self):
		with self.as_user(self.member), self.assertRaises(frappe.PermissionError):
			self.space.merge_with_project(str(self.other_space.name))

	def test_banned_space_member_cannot_delete_the_space_or_its_content(self):
		with self.as_user(self.member), self.assertRaises(frappe.PermissionError):
			frappe.delete_doc("GP Project", self.space.name)
		for doc in (self.space, self.discussion, self.reply):
			self.assertTrue(frappe.db.exists(doc.doctype, doc.name))

	def test_reading_and_other_community_management_remain_available_and_unban_restores_management(self):
		self.assertFalse(can_manage_space(self.member.name, self.space))
		self.assertTrue(can_view_space(self.member.name, self.space.name))
		self.assertTrue(can_manage_space(self.member.name, self.other_space))
		self.assertTrue(can_manage_space("Administrator", self.space))
		set_ban(self.community.name, self.member.name, 0)
		self.assertTrue(can_manage_space(self.member.name, self.space))
		with self.as_user(self.member):
			self.space.move_to_team(self.destination.name)
		self.assertEqual(frappe.db.get_value("GP Project", self.space.name, "team"), self.destination.name)
