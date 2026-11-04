# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

import frappe
from frappe.client import set_value

from gameplan.gameplan.doctype.gp_team.gp_team import join_team, leave_team, update_joined_teams
from gameplan.permissions import (
	can_manage_community,
	can_moderate_space,
	can_view_space,
	is_community_moderator,
)
from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import create_community, create_space
from gameplan.visibility import VISIBILITY_MEMBER_ACCESS


class TestCommunityModerators(GameplanTestCase):
	def setUp(self):
		super().setUp()
		self.community = create_community(
			"Moderator Community", members=[self.second_member], admins=[self.member]
		)
		self.space = create_space("Moderated Space", self.community)

	def appoint_moderator(self):
		with self.as_user(self.member):
			self.community.set_member_moderator(self.second_member.name, 1)

	def test_community_admin_can_appoint_and_remove_a_moderator(self):
		self.appoint_moderator()
		self.assertTrue(is_community_moderator(self.second_member.name, self.community.name))
		self.assertTrue(can_moderate_space(self.second_member.name, self.space))

		with self.as_user(self.member):
			self.community.reload()
			self.community.set_member_moderator(self.second_member.name, 0)

		self.community.reload()
		self.assertIsNotNone(self.community.get_member(self.second_member.name))
		self.assertFalse(is_community_moderator(self.second_member.name, self.community.name))
		self.assertFalse(can_moderate_space(self.second_member.name, self.space.name))

	def test_global_admin_can_assign_without_community_membership(self):
		with self.as_user(self.admin):
			self.community.set_member_moderator(self.second_member.name, 1)
		self.assertTrue(is_community_moderator(self.second_member.name, self.community.name))

	def test_assignment_requires_an_existing_member(self):
		with self.as_user(self.member), self.assertRaises(frappe.ValidationError):
			self.community.set_member_moderator(self.outsider.name, 1)
		self.community.reload()
		self.assertIsNone(self.community.get_member(self.outsider.name))

	def test_non_admins_cannot_assign_or_remove_moderators(self):
		self.appoint_moderator()
		for actor in (self.second_member.name, self.outsider.name, self.guest.name, "Guest"):
			for value in (0, 1):
				with self.subTest(actor=actor, value=value):
					with self.as_user(actor), self.assertRaises(frappe.PermissionError):
						self.community.set_member_moderator(self.second_member.name, value)
		self.assertTrue(is_community_moderator(self.second_member.name, self.community.name))

	def test_community_admin_cannot_assign_in_another_community(self):
		other = create_community("Other Moderator Community", members=[self.second_member])
		with self.as_user(self.member), self.assertRaises(frappe.PermissionError):
			other.set_member_moderator(self.second_member.name, 1)

	def test_member_cannot_forge_appointment_through_document_save(self):
		community = frappe.get_doc("GP Team", self.community.name)
		community.get_member(self.second_member.name).is_moderator = 1
		with self.as_user(self.second_member), self.assertRaises(frappe.PermissionError):
			community.save()
		self.assertFalse(is_community_moderator(self.second_member.name, self.community.name))

	def test_member_cannot_forge_appointment_through_child_field_update(self):
		member = self.community.get_member(self.second_member.name)
		with self.as_user(self.second_member), self.assertRaises(frappe.PermissionError):
			set_value("GP Member", member.name, "is_moderator", 1)
		self.assertFalse(is_community_moderator(self.second_member.name, self.community.name))

	def test_moderation_does_not_grant_community_management(self):
		self.appoint_moderator()
		self.assertFalse(can_manage_community(self.second_member.name, self.community.name))
		with self.as_user(self.second_member), self.assertRaises(frappe.PermissionError):
			self.community.set_member_admin(self.second_member.name, 1)

	def test_moderator_can_act_only_in_their_community(self):
		self.appoint_moderator()
		other = create_community("Unmoderated Community", members=[self.second_member])
		space = create_space("Unmoderated Space", other)
		self.assertTrue(can_view_space(self.second_member.name, space))
		self.assertFalse(can_moderate_space(self.second_member.name, space))

	def test_moderator_does_not_gain_private_space_access(self):
		private_space = create_space(
			"Private Moderated Space", self.community, visibility=VISIBILITY_MEMBER_ACCESS
		)
		self.appoint_moderator()
		self.assertFalse(can_view_space(self.second_member.name, private_space))
		self.assertFalse(can_moderate_space(self.second_member.name, private_space))

		private_space.append("members", {"user": self.second_member.name})
		private_space.save(ignore_permissions=True)
		self.assertTrue(can_moderate_space(self.second_member.name, private_space))

	def test_existing_admin_authority_respects_private_access(self):
		private_space = create_space(
			"Private Admin Space", self.community, visibility=VISIBILITY_MEMBER_ACCESS
		)
		self.assertTrue(can_moderate_space(self.member.name, self.space))
		self.assertFalse(can_moderate_space(self.member.name, private_space))
		self.assertTrue(can_moderate_space(self.admin.name, private_space))

	def test_space_membership_flag_does_not_grant_community_moderation(self):
		self.space.append("members", {"user": self.second_member.name, "is_moderator": 1})
		self.space.save(ignore_permissions=True)
		self.assertFalse(is_community_moderator(self.second_member.name, self.community.name))
		self.assertFalse(can_moderate_space(self.second_member.name, self.space))

	def test_guests_and_anonymous_users_cannot_moderate(self):
		self.community.append("members", {"user": self.guest.name, "is_moderator": 1})
		self.community.save(ignore_permissions=True)
		for actor in (self.guest.name, "Guest"):
			self.assertFalse(can_moderate_space(actor, self.space))
		with self.as_user(self.member), self.assertRaises(frappe.ValidationError):
			self.community.set_member_moderator(self.guest.name, 1)

	def test_removing_membership_revokes_moderation_and_rejoin_does_not_restore_it(self):
		self.appoint_moderator()
		with self.as_user(self.member):
			self.community.reload()
			self.community.remove_member(self.second_member.name)
		self.assertFalse(can_moderate_space(self.second_member.name, self.space))
		with self.as_user(self.second_member):
			join_team(self.community.name)
		self.assertFalse(can_moderate_space(self.second_member.name, self.space))

	def test_leaving_community_revokes_moderation_even_with_private_membership(self):
		private_space = create_space(
			"Retained Private Space",
			self.community,
			visibility=VISIBILITY_MEMBER_ACCESS,
			members=[self.second_member],
		)
		self.appoint_moderator()
		with self.as_user(self.second_member):
			leave_team(self.community.name)
		self.assertTrue(can_view_space(self.second_member.name, private_space))
		self.assertFalse(can_moderate_space(self.second_member.name, private_space))

	def test_sidebar_membership_update_revokes_moderation(self):
		self.appoint_moderator()
		other = create_community("Remaining Community", members=[self.second_member])
		with self.as_user(self.second_member):
			update_joined_teams([other.name])
		self.assertFalse(can_moderate_space(self.second_member.name, self.space))

	def test_community_merge_does_not_transfer_moderator_appointments(self):
		self.appoint_moderator()
		target = create_community("Moderator Merge Target", admins=[self.member])
		with self.as_user(self.member):
			self.community.reload()
			self.community.merge_into_team(target.name)
		target.reload()
		self.assertIsNotNone(target.get_member(self.second_member.name))
		self.assertFalse(is_community_moderator(self.second_member.name, target.name))
