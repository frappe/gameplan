# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from gameplan.extends.client import get_list as get_client_list
from gameplan.gameplan.doctype.gp_discussion.api import get_discussions
from gameplan.gameplan.doctype.gp_member.patches.backfill_team_admins import (
	execute as backfill_team_admins,
)
from gameplan.search_sqlite import GameplanSearch
from gameplan.tests.utils import create_guest, create_member, create_project, create_user, grant_guest_access


class PermissionBackendTestCase(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self._public_web_enabled = frappe.conf.get("gameplan_public_web_enabled")
		self.admin = create_user("perm_global_admin@example.com", "Global Admin", "Gameplan Admin")
		self.alice = create_member("perm_alice@example.com", "Alice")
		self.bob = create_member("perm_bob@example.com", "Bob")
		self.carol = create_member("perm_carol@example.com", "Carol")
		self.guest = create_guest("perm_guest@example.com", "Guest")

	def tearDown(self):
		frappe.set_user("Administrator")
		if self._public_web_enabled is None:
			frappe.conf.pop("gameplan_public_web_enabled", None)
		else:
			frappe.conf.gameplan_public_web_enabled = self._public_web_enabled
		frappe.db.rollback()

	def create_community(self, title, *, is_private=0, members=None, admins=None):
		team = frappe.get_doc(doctype="GP Team", title=title, is_private=is_private)
		for user in members or []:
			team.append("members", {"user": user})
		for user in admins or []:
			team.append("members", {"user": user, "is_admin": 1})
		return team.insert(ignore_permissions=True)

	def create_space(self, title, team, *, is_private=0, visibility=None, members=None):
		project = create_project(title, team, is_private=is_private)
		if visibility:
			project.visibility = visibility
		for user in members or []:
			project.append("members", {"user": user})
		project.save(ignore_permissions=True)
		return project

	def add_community_member(self, team, user, *, is_admin=0):
		team.append("members", {"user": user, "is_admin": is_admin})
		team.save(ignore_permissions=True)
		team.reload()

	def assert_can_read_doc(self, doctype, name, user):
		self.assertTrue(frappe.has_permission(doctype, "read", doc=name, user=user))

	def assert_cannot_read_doc(self, doctype, name, user):
		self.assertFalse(frappe.has_permission(doctype, "read", doc=name, user=user))

	def create_discussion(self, title, project, *, owner=None):
		doc = frappe.get_doc(doctype="GP Discussion", title=title, project=project, content="Test")
		with patch("frappe.model.document.run_server_script_for_doc_event"):
			doc.insert(ignore_permissions=True)
		if owner:
			frappe.db.set_value("GP Discussion", doc.name, "owner", owner, update_modified=False)
			doc.reload()
		return doc

	def create_comment(self, discussion, *, owner=None):
		doc = frappe.get_doc(
			doctype="GP Comment",
			reference_doctype="GP Discussion",
			reference_name=discussion.name,
			content="Test",
		)
		with patch("frappe.model.document.run_server_script_for_doc_event"):
			doc.insert(ignore_permissions=True)
		if owner:
			frappe.db.set_value("GP Comment", doc.name, "owner", owner, update_modified=False)
			doc.reload()
		return doc

	def create_poll(self, discussion, *, owner=None):
		doc = frappe.get_doc(
			doctype="GP Poll",
			discussion=discussion.name,
			title="Test Poll",
			options=[{"title": "Yes"}, {"title": "No"}],
		)
		doc.insert(ignore_permissions=True)
		if owner:
			frappe.db.set_value("GP Poll", doc.name, "owner", owner, update_modified=False)
			doc.reload()
		return doc

	def set_public_web_enabled(self, enabled):
		frappe.conf.gameplan_public_web_enabled = 1 if enabled else 0


class TestCommunityVisibility(PermissionBackendTestCase):
	def test_community_creator_becomes_community_admin(self):
		frappe.set_user(self.alice.name)
		team = frappe.get_doc(doctype="GP Team", title="Creator Admin Community").insert()

		team.reload()
		self.assertTrue(any(row.user == self.alice.name and row.is_admin for row in team.members))

	def test_private_community_is_visible_only_to_members_and_global_admins(self):
		public_team = self.create_community("Visible Public Community")
		private_team = self.create_community(
			"Hidden Private Community", is_private=1, members=[self.alice.name]
		)

		self.assert_can_read_doc("GP Team", public_team.name, self.bob.name)
		self.assert_can_read_doc("GP Team", private_team.name, self.alice.name)
		self.assert_can_read_doc("GP Team", private_team.name, self.admin.name)
		self.assert_cannot_read_doc("GP Team", private_team.name, self.bob.name)

	def test_private_community_is_filtered_from_lists_for_non_members(self):
		public_team = self.create_community("Listed Public Community")
		private_team = self.create_community(
			"Unlisted Private Community", is_private=1, members=[self.alice.name]
		)

		frappe.set_user(self.bob.name)
		teams = frappe.get_list("GP Team", fields=["name"], pluck="name")

		self.assertIn(public_team.name, teams)
		self.assertNotIn(private_team.name, teams)


class TestSpaceVisibility(PermissionBackendTestCase):
	def test_private_space_is_visible_only_to_space_members_and_global_admins(self):
		team = self.create_community("Private Space Community", members=[self.alice.name, self.bob.name])
		private_space = self.create_space(
			"Hidden Private Space", team.name, is_private=1, members=[self.alice.name]
		)

		self.assert_can_read_doc("GP Project", private_space.name, self.alice.name)
		self.assert_can_read_doc("GP Project", private_space.name, self.admin.name)
		self.assert_cannot_read_doc("GP Project", private_space.name, self.bob.name)

	def test_guest_sees_only_explicitly_granted_spaces(self):
		team = self.create_community("Guest Space Community", members=[self.alice.name])
		public_space = self.create_space("Guest Public Space", team.name)
		granted_space = self.create_space("Guest Granted Space", team.name, is_private=1)
		grant_guest_access(self.guest.name, granted_space.name)

		self.assert_cannot_read_doc("GP Project", public_space.name, self.guest.name)
		self.assert_can_read_doc("GP Project", granted_space.name, self.guest.name)

	def test_private_spaces_are_filtered_from_lists_for_non_members(self):
		team = self.create_community("List Space Community", members=[self.alice.name, self.bob.name])
		public_space = self.create_space("Listed Public Space", team.name)
		private_space = self.create_space(
			"Unlisted Private Space", team.name, is_private=1, members=[self.alice.name]
		)

		frappe.set_user(self.bob.name)
		spaces = frappe.get_list("GP Project", fields=["name"], pluck="name")

		self.assertIn(public_space.name, spaces)
		self.assertNotIn(private_space.name, spaces)

	def test_public_space_in_private_community_is_visible_only_to_community_members(self):
		team = self.create_community("Private Parent Community", is_private=1, members=[self.alice.name])
		space = self.create_space("Public Child Space", team.name)

		self.assert_can_read_doc("GP Project", space.name, self.alice.name)
		self.assert_cannot_read_doc("GP Project", space.name, self.bob.name)

		frappe.set_user(self.bob.name)
		spaces = frappe.get_list("GP Project", fields=["name"], pluck="name")

		self.assertNotIn(space.name, spaces)

	def test_client_list_filters_public_space_in_private_community_for_non_members(self):
		team = self.create_community(
			"Private Parent Client Community", is_private=1, members=[self.alice.name]
		)
		space = self.create_space("Public Client Child Space", team.name)

		frappe.set_user(self.bob.name)
		spaces = get_client_list(doctype="GP Project", fields=["name"], limit=50)

		self.assertNotIn(space.name, [space.name for space in spaces])

	def test_client_list_can_fetch_space_visibility_with_team_title(self):
		team = self.create_community("Joined Field Community", members=[self.alice.name, self.bob.name])
		space = self.create_space("Joined Field Space", team.name)

		frappe.set_user(self.bob.name)
		spaces = get_client_list(
			doctype="GP Project",
			fields=["name", "is_private", "team.title as team_title"],
			limit=50,
		)

		self.assertIn(space.name, [space.name for space in spaces])


class TestContentPermissions(PermissionBackendTestCase):
	def test_content_inherits_private_space_visibility(self):
		team = self.create_community("Private Content Community", members=[self.alice.name, self.bob.name])
		private_space = self.create_space(
			"Private Content Space", team.name, is_private=1, members=[self.alice.name]
		)
		discussion = self.create_discussion("Private Discussion", private_space.name, owner=self.alice.name)

		self.assert_can_read_doc("GP Discussion", discussion.name, self.alice.name)
		self.assert_cannot_read_doc("GP Discussion", discussion.name, self.bob.name)

	def test_members_can_edit_each_others_content_but_not_delete_it(self):
		team = self.create_community("Content Ownership Community", members=[self.alice.name, self.bob.name])
		space = self.create_space("Content Ownership Space", team.name)
		discussion = self.create_discussion("Owned Discussion", space.name, owner=self.alice.name)

		# Community-driven: any space member can edit content (incl. lifecycle
		# actions like pin/close), not just the author.
		self.assertTrue(
			frappe.has_permission("GP Discussion", "write", doc=discussion.name, user=self.alice.name)
		)
		self.assertTrue(
			frappe.has_permission("GP Discussion", "write", doc=discussion.name, user=self.bob.name)
		)
		# Deleting another member's content stays gated (destructive action).
		self.assertFalse(
			frappe.has_permission("GP Discussion", "delete", doc=discussion.name, user=self.bob.name)
		)

	def test_non_space_member_cannot_edit_private_space_content(self):
		team = self.create_community("Private Edit Community", members=[self.alice.name, self.bob.name])
		private_space = self.create_space(
			"Private Edit Space", team.name, is_private=1, members=[self.alice.name]
		)
		discussion = self.create_discussion("Private Discussion", private_space.name, owner=self.alice.name)

		# Bob can't see the private space, so he can't edit its content either.
		self.assertFalse(
			frappe.has_permission("GP Discussion", "write", doc=discussion.name, user=self.bob.name)
		)

	def test_community_admin_can_edit_and_delete_other_members_content(self):
		team = self.create_community(
			"Content Moderator Community", members=[self.alice.name, self.bob.name], admins=[self.bob.name]
		)
		space = self.create_space("Content Moderator Space", team.name)
		discussion = self.create_discussion("Moderated Discussion", space.name, owner=self.alice.name)

		self.assertTrue(
			frappe.has_permission("GP Discussion", "write", doc=discussion.name, user=self.bob.name)
		)
		self.assertTrue(
			frappe.has_permission("GP Discussion", "delete", doc=discussion.name, user=self.bob.name)
		)

	def test_guest_with_space_access_can_read_but_not_edit_discussion(self):
		team = self.create_community("Guest Content Community", members=[self.alice.name])
		space = self.create_space("Guest Content Space", team.name)
		discussion = self.create_discussion("Guest Readable Discussion", space.name, owner=self.alice.name)
		grant_guest_access(self.guest.name, space.name)

		self.assertTrue(
			frappe.has_permission("GP Discussion", "read", doc=discussion.name, user=self.guest.name)
		)
		self.assertFalse(
			frappe.has_permission("GP Discussion", "write", doc=discussion.name, user=self.guest.name)
		)
		self.assertFalse(
			frappe.has_permission("GP Discussion", "delete", doc=discussion.name, user=self.guest.name)
		)

	def test_private_page_is_owner_only_and_project_page_inherits_space(self):
		team = self.create_community("Page Permission Community", members=[self.alice.name, self.bob.name])
		private_space = self.create_space(
			"Page Private Space", team.name, is_private=1, members=[self.alice.name]
		)
		private_page = self.create_page("Private Page", owner=self.alice.name)
		space_page = self.create_page("Space Page", project=private_space.name, owner=self.alice.name)

		self.assert_can_read_doc("GP Page", private_page.name, self.alice.name)
		self.assert_cannot_read_doc("GP Page", private_page.name, self.bob.name)
		self.assert_can_read_doc("GP Page", space_page.name, self.alice.name)
		self.assert_cannot_read_doc("GP Page", space_page.name, self.bob.name)

	def create_page(self, title, *, owner, project=None):
		doc = frappe.get_doc(doctype="GP Page", title=title, content="Test", project=project)
		doc.insert(ignore_permissions=True)
		frappe.db.set_value("GP Page", doc.name, "owner", owner, update_modified=False)
		doc.reload()
		return doc


class TestPublicWebPermissions(PermissionBackendTestCase):
	def test_switch_off_blocks_anonymous_public_web_space(self):
		self.set_public_web_enabled(False)
		team = self.create_community("Public Web Off Community", members=[self.alice.name])
		space = self.create_space("Public Web Off Space", team.name, visibility="Public Web")
		discussion = self.create_discussion("Public Web Off Discussion", space.name, owner=self.alice.name)

		self.assert_cannot_read_doc("GP Team", team.name, "Guest")
		self.assert_cannot_read_doc("GP Project", space.name, "Guest")
		self.assert_cannot_read_doc("GP Discussion", discussion.name, "Guest")

	def test_anonymous_can_read_public_web_discussion_comments_and_polls(self):
		self.set_public_web_enabled(True)
		team = self.create_community("Public Web Community", members=[self.alice.name])
		space = self.create_space("Public Web Space", team.name, visibility="Public Web")
		discussion = self.create_discussion("Public Web Discussion", space.name, owner=self.alice.name)
		comment = self.create_comment(discussion, owner=self.alice.name)
		poll = self.create_poll(discussion, owner=self.alice.name)

		self.assert_can_read_doc("GP Team", team.name, "Guest")
		self.assert_can_read_doc("GP Project", space.name, "Guest")
		self.assert_can_read_doc("GP Discussion", discussion.name, "Guest")
		self.assert_can_read_doc("GP Comment", comment.name, "Guest")
		self.assert_can_read_doc("GP Poll", poll.name, "Guest")

	def test_anonymous_cannot_read_members_or_private_space_content(self):
		self.set_public_web_enabled(True)
		team = self.create_community("Members Web Community", members=[self.alice.name])
		members_space = self.create_space("Members Only Space", team.name)
		private_space = self.create_space("Private Only Space", team.name, is_private=1)
		members_discussion = self.create_discussion(
			"Members Discussion", members_space.name, owner=self.alice.name
		)
		private_discussion = self.create_discussion(
			"Private Discussion", private_space.name, owner=self.alice.name
		)

		self.assert_cannot_read_doc("GP Project", members_space.name, "Guest")
		self.assert_cannot_read_doc("GP Project", private_space.name, "Guest")
		self.assert_cannot_read_doc("GP Discussion", members_discussion.name, "Guest")
		self.assert_cannot_read_doc("GP Discussion", private_discussion.name, "Guest")

	def test_anonymous_public_web_access_is_read_only(self):
		self.set_public_web_enabled(True)
		team = self.create_community("Read Only Web Community", members=[self.alice.name])
		space = self.create_space("Read Only Web Space", team.name, visibility="Public Web")
		discussion = self.create_discussion("Read Only Web Discussion", space.name, owner=self.alice.name)
		poll = self.create_poll(discussion, owner=self.alice.name)

		self.assertFalse(frappe.has_permission("GP Discussion", "write", doc=discussion.name, user="Guest"))
		self.assertFalse(frappe.has_permission("GP Poll", "write", doc=poll.name, user="Guest"))

		frappe.set_user("Guest")
		comment = frappe.get_doc(
			doctype="GP Comment",
			reference_doctype="GP Discussion",
			reference_name=discussion.name,
			content="Anonymous write",
		)
		with self.assertRaises(frappe.PermissionError):
			comment.insert()
		with self.assertRaises(frappe.PermissionError):
			poll.submit_vote("Yes")


class TestPermissionAwareQueries(PermissionBackendTestCase):
	def test_discussion_feed_filters_public_space_in_private_community(self):
		team = self.create_community("Private Feed Community", is_private=1, members=[self.alice.name])
		space = self.create_space("Public Feed Space", team.name)
		discussion = self.create_discussion("Hidden Feed Discussion", space.name, owner=self.alice.name)

		frappe.set_user(self.bob.name)
		discussions = get_discussions(limit=20)

		self.assertNotIn(discussion.name, [discussion.name for discussion in discussions])

	def test_search_accessible_projects_filters_public_space_in_private_community(self):
		team = self.create_community("Private Search Community", is_private=1, members=[self.alice.name])
		space = self.create_space("Public Search Space", team.name)

		frappe.set_user(self.bob.name)
		accessible_projects = GameplanSearch()._get_accessible_projects()

		self.assertNotIn(str(space.name), accessible_projects)


class TestCommunityManagement(PermissionBackendTestCase):
	def test_backfill_promotes_team_owner_instead_of_first_member(self):
		team = self.create_community("Owner Backfill Community", members=[self.bob.name, self.alice.name])
		frappe.db.set_value("GP Team", team.name, "owner", self.alice.name, update_modified=False)
		team.reload()
		for member in team.members:
			member.is_admin = 0
		team.save(ignore_permissions=True)

		backfill_team_admins()

		team.reload()
		self.assertTrue(any(row.user == self.alice.name and row.is_admin for row in team.members))
		self.assertFalse(any(row.user == self.bob.name and row.is_admin for row in team.members))

	def test_backfill_adds_team_owner_when_owner_is_not_a_member(self):
		team = self.create_community("Owner Missing Backfill Community", members=[self.bob.name])
		frappe.db.set_value("GP Team", team.name, "owner", self.alice.name, update_modified=False)
		team.reload()
		for member in team.members:
			member.is_admin = 0
		team.save(ignore_permissions=True)

		backfill_team_admins()

		team.reload()
		self.assertTrue(any(row.user == self.alice.name and row.is_admin for row in team.members))

	def test_community_admin_can_add_members_to_own_community(self):
		team = self.create_community("Managed Community", members=[self.alice.name], admins=[self.alice.name])

		frappe.set_user(self.alice.name)
		team.add_members([self.bob.name])

		team.reload()
		self.assertTrue(any(row.user == self.bob.name for row in team.members))

	def test_remove_community_member_removes_private_space_membership(self):
		team = self.create_community(
			"Cascade Removed Community",
			members=[self.alice.name, self.bob.name],
			admins=[self.alice.name],
		)
		private_space = self.create_space(
			"Cascade Removed Space", team.name, is_private=1, members=[self.bob.name]
		)
		other_team = self.create_community("Cascade Other Community", members=[self.alice.name])
		other_private_space = self.create_space(
			"Cascade Other Space", other_team.name, is_private=1, members=[self.bob.name]
		)

		frappe.set_user(self.alice.name)
		team.remove_member(self.bob.name)

		team.reload()
		private_space.reload()
		other_private_space.reload()
		self.assertFalse(any(row.user == self.bob.name for row in team.members))
		self.assertFalse(any(row.user == self.bob.name for row in private_space.members))
		self.assertTrue(any(row.user == self.bob.name for row in other_private_space.members))

	def test_cannot_remove_last_community_admin(self):
		frappe.set_user(self.alice.name)
		team = frappe.get_doc(doctype="GP Team", title="Last Admin Removal Community").insert()

		with self.assertRaises(frappe.ValidationError):
			team.remove_member(self.alice.name)

		team.reload()
		self.assertTrue(any(row.user == self.alice.name and row.is_admin for row in team.members))

	def test_community_admin_can_promote_and_demote_members_in_own_community(self):
		team = self.create_community(
			"Managed Admin Community",
			members=[self.alice.name, self.bob.name],
			admins=[self.alice.name],
		)

		frappe.set_user(self.alice.name)
		team.set_member_admin(self.bob.name, 1)

		team.reload()
		self.assertTrue(any(row.user == self.bob.name and row.is_admin for row in team.members))

		team.set_member_admin(self.bob.name, 0)

		team.reload()
		self.assertFalse(any(row.user == self.bob.name and row.is_admin for row in team.members))

	def test_cannot_demote_last_community_admin(self):
		frappe.set_user(self.alice.name)
		team = frappe.get_doc(doctype="GP Team", title="Last Admin Demotion Community").insert()

		with self.assertRaises(frappe.ValidationError):
			team.set_member_admin(self.alice.name, 0)

		team.reload()
		self.assertTrue(any(row.user == self.alice.name and row.is_admin for row in team.members))

	def test_member_cannot_add_members_to_community(self):
		team = self.create_community("Unmanaged Community", members=[self.alice.name])

		frappe.set_user(self.alice.name)
		with self.assertRaises(frappe.PermissionError):
			team.add_members([self.bob.name])

	def test_member_cannot_promote_members_in_community(self):
		team = self.create_community("Unmanaged Admin Community", members=[self.alice.name, self.bob.name])

		frappe.set_user(self.alice.name)
		with self.assertRaises(frappe.PermissionError):
			team.set_member_admin(self.bob.name, 1)

	def test_community_admin_can_remove_guest_access_from_own_community(self):
		team = self.create_community(
			"Managed Guest Community",
			members=[self.alice.name],
			admins=[self.alice.name],
		)
		space = self.create_space("Managed Guest Space", team.name, is_private=1)
		other_team = self.create_community("Other Guest Community", members=[self.alice.name])
		other_space = self.create_space("Other Guest Space", other_team.name, is_private=1)
		grant_guest_access(self.guest.name, space.name)
		grant_guest_access(self.guest.name, other_space.name)

		frappe.set_user(self.alice.name)
		team.remove_guest_access(self.guest.name)

		self.assertFalse(
			frappe.db.exists("GP Guest Access", {"user": self.guest.name, "project": space.name})
		)
		self.assertTrue(
			frappe.db.exists("GP Guest Access", {"user": self.guest.name, "project": other_space.name})
		)

	def test_community_admin_removes_only_own_projects_from_guest_invitation(self):
		team = self.create_community(
			"Managed Guest Invitation Community",
			members=[self.alice.name],
			admins=[self.alice.name],
		)
		space = self.create_space("Managed Guest Invitation Space", team.name, is_private=1)
		other_team = self.create_community("Other Guest Invitation Community", members=[self.alice.name])
		other_space = self.create_space("Other Guest Invitation Space", other_team.name, is_private=1)
		with patch("frappe.sendmail"):
			invitation = frappe.get_doc(
				doctype="GP Invitation",
				email="pending-community-guest@example.com",
				role="Gameplan Guest",
				projects=frappe.as_json([space.name, other_space.name]),
			).insert(ignore_permissions=True)

		frappe.set_user(self.alice.name)
		team.remove_guest_invitation(invitation.name)

		invitation.reload()
		self.assertEqual(frappe.parse_json(invitation.projects), [other_space.name])

	def test_member_cannot_remove_guest_access_from_community(self):
		team = self.create_community("Unmanaged Guest Community", members=[self.alice.name])
		space = self.create_space("Unmanaged Guest Space", team.name, is_private=1)
		grant_guest_access(self.guest.name, space.name)

		frappe.set_user(self.alice.name)
		with self.assertRaises(frappe.PermissionError):
			team.remove_guest_access(self.guest.name)

	def test_community_admin_cannot_manage_another_community(self):
		own_team = self.create_community(
			"Own Managed Community", members=[self.alice.name], admins=[self.alice.name]
		)
		other_team = self.create_community("Other Managed Community", members=[self.carol.name])
		self.assertTrue(any(row.user == self.alice.name and row.is_admin for row in own_team.members))

		frappe.set_user(self.alice.name)
		with self.assertRaises(frappe.PermissionError):
			other_team.add_members([self.bob.name])

	def test_global_admin_can_manage_any_community(self):
		team = self.create_community("Globally Managed Community", members=[self.alice.name])

		frappe.set_user(self.admin.name)
		team.add_members([self.bob.name])

		team.reload()
		self.assertTrue(any(row.user == self.bob.name for row in team.members))


class TestSpaceManagement(PermissionBackendTestCase):
	def test_member_can_join_visible_public_space_without_manage_access(self):
		team = self.create_community("Joinable Public Community", members=[self.alice.name, self.bob.name])
		space = self.create_space("Joinable Public Space", team.name)

		frappe.set_user(self.bob.name)
		space = frappe.get_doc("GP Project", space.name)
		space.join()

		space.reload()
		self.assertTrue(any(row.user == self.bob.name for row in space.members))

	def test_member_can_leave_public_space_without_manage_access(self):
		team = self.create_community("Leaveable Public Community", members=[self.alice.name, self.bob.name])
		space = self.create_space("Leaveable Public Space", team.name, members=[self.bob.name])

		frappe.set_user(self.bob.name)
		space = frappe.get_doc("GP Project", space.name)
		space.leave()

		space.reload()
		self.assertFalse(any(row.user == self.bob.name for row in space.members))

	def test_member_cannot_join_public_space_in_inaccessible_private_community(self):
		team = self.create_community("Blocked Join Community", is_private=1, members=[self.alice.name])
		space = self.create_space("Blocked Join Space", team.name)

		frappe.set_user(self.bob.name)
		with self.assertRaises(frappe.PermissionError):
			space.join()

	def test_private_space_member_can_add_community_member_to_private_space(self):
		team = self.create_community(
			"Private Space Management Community", members=[self.alice.name, self.bob.name]
		)
		space = self.create_space("Managed Private Space", team.name, is_private=1, members=[self.alice.name])

		frappe.set_user(self.alice.name)
		space.add_member(self.bob.name)

		space.reload()
		self.assertTrue(any(row.user == self.bob.name for row in space.members))

	def test_non_space_member_cannot_manage_private_space_members(self):
		team = self.create_community(
			"Blocked Private Space Community", members=[self.alice.name, self.bob.name]
		)
		space = self.create_space("Blocked Private Space", team.name, is_private=1, members=[self.alice.name])

		frappe.set_user(self.bob.name)
		with self.assertRaises(frappe.PermissionError):
			space.add_member(self.carol.name)

	def test_private_space_member_can_invite_guest_to_space(self):
		team = self.create_community("Guest Invite Community", members=[self.alice.name])
		space = self.create_space("Guest Invite Space", team.name, is_private=1, members=[self.alice.name])

		frappe.set_user(self.alice.name)
		space.invite_guest("new_perm_guest@example.com")

		self.assertTrue(frappe.db.exists("GP Invitation", {"email": "new_perm_guest@example.com"}))

	def test_regular_member_cannot_invite_guest_to_public_space(self):
		team = self.create_community("Blocked Public Guest Invite Community", members=[self.alice.name])
		space = self.create_space("Blocked Public Guest Invite Space", team.name)

		frappe.set_user(self.alice.name)
		with self.assertRaises(frappe.PermissionError):
			space.invite_guest("blocked_public_guest@example.com")

		self.assertFalse(frappe.db.exists("GP Invitation", {"email": "blocked_public_guest@example.com"}))

	def test_non_space_member_cannot_invite_guest_to_private_space(self):
		team = self.create_community(
			"Blocked Guest Invite Community", members=[self.alice.name, self.bob.name]
		)
		space = self.create_space(
			"Blocked Guest Invite Space", team.name, is_private=1, members=[self.alice.name]
		)

		frappe.set_user(self.bob.name)
		with self.assertRaises(frappe.PermissionError):
			space.invite_guest("blocked_perm_guest@example.com")
