# Copyright (c) 2022, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""Space (GP Project) behaviour: archiving, activity, search scoping, and who may
join, leave, manage members or invite guests."""

import frappe
from frappe.tests.utils import FrappeTestCase

from gameplan.gameplan.doctype.gp_project.gp_project import get_activity
from gameplan.search_sqlite import GameplanSearch
from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import create_community, create_discussion, create_member, create_space


class TestSpaces(FrappeTestCase):
	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def test_archive_deletes_current_users_pin(self):
		frappe.set_user("Administrator")
		team = create_community("Pinned Archive Team")
		project = create_space("Pinned Archive Space", team.name)
		pin = frappe.get_doc(doctype="GP Pinned Project", project=project.name).insert(
			ignore_permissions=True
		)

		project.archive()

		self.assertTrue(project.archived_at)
		self.assertFalse(frappe.db.exists("GP Pinned Project", pin.name))

	def test_search_private_space_requires_space_membership(self):
		member = create_member("test_search_member@example.com")
		team = create_community("Search Permissions Team")
		team.add_member(member.name)
		team.save(ignore_permissions=True)

		public_project = create_space("Search Public Space", team.name)
		private_project = create_space("Search Private Space", team.name, is_private=1)

		frappe.set_user(member.name)
		accessible_projects = GameplanSearch()._get_accessible_projects()

		self.assertIn(str(public_project.name), accessible_projects)
		self.assertNotIn(str(private_project.name), accessible_projects)

		frappe.set_user("Administrator")
		private_project.add_member(member.name)

		frappe.set_user(member.name)
		accessible_projects = GameplanSearch()._get_accessible_projects()

		self.assertIn(str(private_project.name), accessible_projects)

	def test_get_activity_returns_latest_accessible_space_activity(self):
		member = create_member("test_space_activity_member@example.com")
		team = create_community("Space Activity Team")
		public_project = create_space("Public Activity Space", team.name)
		private_project = create_space("Private Activity Space", team.name, is_private=1)

		older_discussion = create_discussion("Older Activity", public_project.name)
		latest_discussion = create_discussion("Latest Activity", public_project.name)
		private_discussion = create_discussion("Private Activity", private_project.name)
		frappe.db.set_value("GP Discussion", older_discussion.name, "last_post_at", "2026-01-01 10:00:00")
		frappe.db.set_value("GP Discussion", latest_discussion.name, "last_post_at", "2026-01-02 10:00:00")
		frappe.db.set_value("GP Discussion", private_discussion.name, "last_post_at", "2026-01-03 10:00:00")

		frappe.set_user(member.name)
		activity = get_activity()

		self.assertEqual(str(activity[str(public_project.name)]), "2026-01-02 10:00:00")
		self.assertNotIn(str(private_project.name), activity)


class TestSpaceMembership(GameplanTestCase):
	"""Joining, leaving, managing members and inviting guests.

	Joining a public space needs only visibility, but every managing action
	(adding members, inviting guests) needs manage access — space membership for a
	private space, community admin for a public one.
	"""

	def test_member_can_join_visible_public_space(self):
		community = create_community("Joinable Public Community", members=[self.member, self.second_member])
		space = create_space("Joinable Public Space", community)

		with self.as_user(self.second_member):
			frappe.get_doc("GP Project", space.name).join()

		space.reload()
		self.assertTrue(any(row.user == self.second_member.name for row in space.members))

	def test_member_can_leave_public_space(self):
		community = create_community("Leaveable Public Community", members=[self.member, self.second_member])
		space = create_space("Leaveable Public Space", community, members=[self.second_member])

		with self.as_user(self.second_member):
			frappe.get_doc("GP Project", space.name).leave()

		space.reload()
		self.assertFalse(any(row.user == self.second_member.name for row in space.members))

	def test_member_cannot_join_public_space_in_inaccessible_private_community(self):
		community = create_community("Blocked Join Community", is_private=1, members=[self.member])
		space = create_space("Blocked Join Space", community)

		with self.as_user(self.second_member), self.assertRaises(frappe.PermissionError):
			space.join()

	def test_private_space_member_can_add_community_member_to_private_space(self):
		community = create_community(
			"Private Space Management Community", members=[self.member, self.second_member]
		)
		space = create_space("Managed Private Space", community, is_private=1, members=[self.member])

		with self.as_user(self.member):
			space.add_member(self.second_member.name)

		space.reload()
		self.assertTrue(any(row.user == self.second_member.name for row in space.members))

	def test_non_space_member_cannot_manage_private_space_members(self):
		community = create_community(
			"Blocked Private Space Community", members=[self.member, self.second_member]
		)
		space = create_space("Blocked Private Space", community, is_private=1, members=[self.member])

		with self.as_user(self.second_member), self.assertRaises(frappe.PermissionError):
			space.add_member(self.outsider.name)

	def test_private_space_member_can_invite_guest_to_space(self):
		community = create_community("Guest Invite Community", members=[self.member])
		space = create_space("Guest Invite Space", community, is_private=1, members=[self.member])

		with self.as_user(self.member):
			space.invite_guest("new_perm_guest@example.com")

		self.assertTrue(frappe.db.exists("GP Invitation", {"email": "new_perm_guest@example.com"}))

	def test_regular_member_cannot_invite_guest_to_public_space(self):
		community = create_community("Blocked Public Guest Invite Community", members=[self.member])
		space = create_space("Blocked Public Guest Invite Space", community)

		with self.as_user(self.member), self.assertRaises(frappe.PermissionError):
			space.invite_guest("blocked_public_guest@example.com")

		self.assertFalse(frappe.db.exists("GP Invitation", {"email": "blocked_public_guest@example.com"}))

	def test_non_space_member_cannot_invite_guest_to_private_space(self):
		community = create_community(
			"Blocked Guest Invite Community", members=[self.member, self.second_member]
		)
		space = create_space("Blocked Guest Invite Space", community, is_private=1, members=[self.member])

		with self.as_user(self.second_member), self.assertRaises(frappe.PermissionError):
			space.invite_guest("blocked_perm_guest@example.com")
