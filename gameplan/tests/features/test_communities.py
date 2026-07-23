# Copyright (c) 2022, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""Community (GP Team) behaviour: the General space, joined-community state, and
moving spaces between communities via merge or move_to_team."""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from gameplan.gameplan.doctype.gp_member.patches.backfill_team_admins import (
	execute as backfill_team_admins,
)
from gameplan.gameplan.doctype.gp_team.gp_team import update_joined_teams
from gameplan.gameplan.doctype.gp_user_profile.gp_user_profile import get_session_user_profile
from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import (
	create_community,
	create_discussion,
	create_member,
	create_space,
	grant_guest_access,
)


class TestCommunities(FrappeTestCase):
	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def test_after_insert_creates_general_space(self):
		team = frappe.get_doc(doctype="GP Team", title="General Space Team").insert(ignore_permissions=True)

		spaces = frappe.db.get_all("GP Project", filters={"team": team.name}, fields=["title", "is_private"])
		self.assertEqual(len(spaces), 1)
		self.assertEqual(spaces[0].title, "General")
		# General must be public so all community members can see it by default.
		self.assertEqual(spaces[0].is_private, 0)

	def test_after_insert_skips_general_when_space_already_exists(self):
		team = frappe.get_doc(doctype="GP Team", title="Existing Space Team").insert(ignore_permissions=True)
		# Hook already created exactly one General space.
		self.assertEqual(frappe.db.count("GP Project", {"team": team.name}), 1)

		# Re-running the hook must not duplicate it (idempotency rule).
		team.create_general_space()
		self.assertEqual(frappe.db.count("GP Project", {"team": team.name}), 1)

	def test_skip_general_space_flag_suppresses_hook(self):
		team = frappe.new_doc("GP Team")
		team.title = "Suppressed Space Team"
		team.flags.skip_general_space = True
		team.insert(ignore_permissions=True)

		self.assertEqual(frappe.db.count("GP Project", {"team": team.name}), 0)

	def test_update_joined_teams_saves_profile_community_order(self):
		user = create_member("community-order@example.com", "Community Order")
		first_team = frappe.get_doc(doctype="GP Team", title="Order First Team").insert(
			ignore_permissions=True
		)
		second_team = frappe.get_doc(doctype="GP Team", title="Order Second Team").insert(
			ignore_permissions=True
		)

		frappe.set_user(user.name)
		ordered_teams = [second_team.name, first_team.name]

		self.assertEqual(update_joined_teams(ordered_teams), ordered_teams)
		self.assertEqual(frappe.parse_json(get_session_user_profile().community_order), ordered_teams)

	def test_update_joined_teams_saves_profile_sidebar_badge_style(self):
		user = create_member("sidebar-badge-style@example.com", "Sidebar Badge Style")
		team = frappe.get_doc(doctype="GP Team", title="Badge Style Team").insert(ignore_permissions=True)

		frappe.set_user(user.name)

		self.assertEqual(update_joined_teams([team.name], "Dot"), [team.name])
		self.assertEqual(get_session_user_profile().sidebar_badge_style, "Dot")

	def test_update_joined_teams_rejects_invalid_sidebar_badge_style(self):
		user = create_member("invalid-sidebar-badge-style@example.com", "Invalid Badge Style")
		team = frappe.get_doc(doctype="GP Team", title="Invalid Badge Style Team").insert(
			ignore_permissions=True
		)

		frappe.set_user(user.name)

		self.assertRaises(frappe.ValidationError, update_joined_teams, [team.name], "Banner")

	def test_merge_into_team_moves_spaces_members_and_archives_source(self):
		source_member = create_member("merge-source-member@example.com", "Merge Source Member")
		source = frappe.get_doc(doctype="GP Team", title="Merge Source Team").insert(ignore_permissions=True)
		target = frappe.get_doc(doctype="GP Team", title="Merge Target Team").insert(ignore_permissions=True)
		source.add_member(source_member.name, is_admin=1)
		source.save(ignore_permissions=True)
		project = create_space("Merge Source Space", source.name)
		discussion = create_discussion("Merge Source Discussion", project.name)
		task = frappe.get_doc(doctype="GP Task", title="Merge Source Task", project=project.name).insert(
			ignore_permissions=True
		)
		page = frappe.get_doc(doctype="GP Page", title="Merge Source Page", project=project.name).insert(
			ignore_permissions=True
		)

		source.merge_into_team(target.name)

		source.reload()
		target.reload()
		self.assertTrue(source.archived_at)
		self.assertTrue(target.get_member(source_member.name).is_admin)
		self.assertEqual(frappe.db.get_value("GP Project", project.name, "team"), target.name)
		self.assertEqual(frappe.db.get_value("GP Discussion", discussion.name, "team"), target.name)
		self.assertEqual(frappe.db.get_value("GP Task", task.name, "team"), target.name)
		self.assertEqual(frappe.db.get_value("GP Page", page.name, "team"), target.name)

	def test_move_to_team_repoints_discussions_and_tasks(self):
		source = create_community("Bulk Source Team")
		target = create_community("Bulk Target Team")
		project = create_space("Bulk Move Space", source.name)
		discussion = create_discussion("D1", project.name, content="x")
		task = frappe.get_doc(doctype="GP Task", title="T1", project=project.name).insert(
			ignore_permissions=True
		)

		# Inserting child docs bumps the project's modified timestamp via counter
		# hooks; reload so move_to_team's save sees the latest (as a fresh API call would).
		project.reload()
		project.move_to_team(target.name)

		self.assertEqual(frappe.db.get_value("GP Project", project.name, "team"), target.name)
		self.assertEqual(frappe.db.get_value("GP Discussion", discussion.name, "team"), target.name)
		self.assertEqual(frappe.db.get_value("GP Task", task.name, "team"), target.name)


class TestCommunityMembership(GameplanTestCase):
	"""Adding, removing, promoting and demoting members, and revoking guest access.

	Every one of these is gated on community admin: a plain member may not run
	them, and an admin's reach stops at their own community.
	"""

	def test_community_admin_can_add_members(self):
		community = create_community("Managed Community", admins=[self.member])

		with self.as_user(self.member):
			community.add_members([self.second_member.name])

		community.reload()
		self.assertTrue(any(row.user == self.second_member.name for row in community.members))

	def test_member_cannot_add_members(self):
		community = create_community("Unmanaged Community", members=[self.member])

		with self.as_user(self.member), self.assertRaises(frappe.PermissionError):
			community.add_members([self.second_member.name])

	def test_global_admin_can_manage_any_community(self):
		community = create_community("Globally Managed Community", members=[self.member])

		with self.as_user(self.admin):
			community.add_members([self.second_member.name])

		community.reload()
		self.assertTrue(any(row.user == self.second_member.name for row in community.members))

	def test_community_admin_cannot_manage_another_community(self):
		create_community("Own Managed Community", admins=[self.member])
		other = create_community("Other Managed Community", members=[self.outsider])

		with self.as_user(self.member), self.assertRaises(frappe.PermissionError):
			other.add_members([self.second_member.name])

	def test_removing_a_member_cascades_to_private_spaces_of_that_community_only(self):
		community = create_community(
			"Cascade Removed Community", members=[self.second_member], admins=[self.member]
		)
		private_space = create_space(
			"Cascade Removed Space", community, is_private=1, members=[self.second_member]
		)
		other_community = create_community("Cascade Other Community", members=[self.member])
		other_private_space = create_space(
			"Cascade Other Space", other_community, is_private=1, members=[self.second_member]
		)

		with self.as_user(self.member):
			community.remove_member(self.second_member.name)

		community.reload()
		private_space.reload()
		other_private_space.reload()
		self.assertFalse(any(row.user == self.second_member.name for row in community.members))
		self.assertFalse(any(row.user == self.second_member.name for row in private_space.members))
		# The other community's private space is untouched.
		self.assertTrue(any(row.user == self.second_member.name for row in other_private_space.members))

	def test_cannot_remove_last_community_admin(self):
		with self.as_user(self.member):
			community = frappe.get_doc(doctype="GP Team", title="Last Admin Removal Community").insert()

			with self.assertRaises(frappe.ValidationError):
				community.remove_member(self.member.name)

		community.reload()
		self.assertTrue(any(row.user == self.member.name and row.is_admin for row in community.members))

	def test_community_admin_can_promote_and_demote_members(self):
		community = create_community(
			"Managed Admin Community", members=[self.second_member], admins=[self.member]
		)

		with self.as_user(self.member):
			community.set_member_admin(self.second_member.name, 1)
			community.reload()
			self.assertTrue(
				any(row.user == self.second_member.name and row.is_admin for row in community.members)
			)

			community.set_member_admin(self.second_member.name, 0)

		community.reload()
		self.assertFalse(
			any(row.user == self.second_member.name and row.is_admin for row in community.members)
		)

	def test_cannot_demote_last_community_admin(self):
		with self.as_user(self.member):
			community = frappe.get_doc(doctype="GP Team", title="Last Admin Demotion Community").insert()

			with self.assertRaises(frappe.ValidationError):
				community.set_member_admin(self.member.name, 0)

		community.reload()
		self.assertTrue(any(row.user == self.member.name and row.is_admin for row in community.members))

	def test_member_cannot_promote_members(self):
		community = create_community("Unmanaged Admin Community", members=[self.member, self.second_member])

		with self.as_user(self.member), self.assertRaises(frappe.PermissionError):
			community.set_member_admin(self.second_member.name, 1)

	def test_community_admin_revokes_guest_access_only_in_own_community(self):
		community = create_community("Managed Guest Community", admins=[self.member])
		space = create_space("Managed Guest Space", community, is_private=1)
		other_community = create_community("Other Guest Community", members=[self.member])
		other_space = create_space("Other Guest Space", other_community, is_private=1)
		grant_guest_access(self.guest, space)
		grant_guest_access(self.guest, other_space)

		with self.as_user(self.member):
			community.remove_guest_access(self.guest.name)

		self.assertFalse(
			frappe.db.exists("GP Guest Access", {"user": self.guest.name, "project": space.name})
		)
		self.assertTrue(
			frappe.db.exists("GP Guest Access", {"user": self.guest.name, "project": other_space.name})
		)

	def test_community_admin_removes_only_own_spaces_from_a_guest_invitation(self):
		community = create_community("Managed Guest Invitation Community", admins=[self.member])
		space = create_space("Managed Guest Invitation Space", community, is_private=1)
		other_community = create_community("Other Guest Invitation Community", members=[self.member])
		other_space = create_space("Other Guest Invitation Space", other_community, is_private=1)
		with patch("frappe.sendmail"):
			invitation = frappe.get_doc(
				doctype="GP Invitation",
				email="pending-community-guest@example.com",
				role="Gameplan Guest",
				projects=frappe.as_json([space.name, other_space.name]),
			).insert(ignore_permissions=True)

		with self.as_user(self.member):
			community.remove_guest_invitation(invitation.name)

		invitation.reload()
		self.assertEqual(frappe.parse_json(invitation.projects), [other_space.name])

	def test_member_cannot_revoke_guest_access(self):
		community = create_community("Unmanaged Guest Community", members=[self.member])
		space = create_space("Unmanaged Guest Space", community, is_private=1)
		grant_guest_access(self.guest, space)

		with self.as_user(self.member), self.assertRaises(frappe.PermissionError):
			community.remove_guest_access(self.guest.name)


class TestCommunityAdminBackfill(GameplanTestCase):
	"""The patch that promotes an admin on communities that ended up with none."""

	def _community_without_admins(self, title, members):
		community = create_community(title, members=members)
		frappe.db.set_value("GP Team", community.name, "owner", self.member.name, update_modified=False)
		community.reload()
		for row in community.members:
			row.is_admin = 0
		community.save(ignore_permissions=True)
		return community

	def test_backfill_promotes_the_owner_not_the_first_member(self):
		community = self._community_without_admins(
			"Owner Backfill Community", [self.second_member, self.member]
		)

		backfill_team_admins()

		community.reload()
		self.assertTrue(any(row.user == self.member.name and row.is_admin for row in community.members))
		self.assertFalse(
			any(row.user == self.second_member.name and row.is_admin for row in community.members)
		)

	def test_backfill_adds_the_owner_when_they_are_not_a_member(self):
		community = self._community_without_admins("Owner Missing Backfill Community", [self.second_member])

		backfill_team_admins()

		community.reload()
		self.assertTrue(any(row.user == self.member.name and row.is_admin for row in community.members))
