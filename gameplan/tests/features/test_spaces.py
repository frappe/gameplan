# Copyright (c) 2022, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""Space (GP Project) behaviour: archiving, activity, search scoping, and who may
join, leave, manage members or invite guests."""

import frappe
from frappe.tests.utils import FrappeTestCase

from gameplan.gameplan.doctype.gp_project import gp_project as gp_project_module
from gameplan.gameplan.doctype.gp_project.gp_project import (
	GPProject,
	get_activity,
	mark_all_as_read,
	track_visits,
)
from gameplan.search_sqlite import GameplanSearch
from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import (
	create_community,
	create_discussion,
	create_member,
	create_space,
	grant_guest_access,
)


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

	def test_joining_a_space_twice_keeps_one_membership(self):
		community = create_community("Idempotent Join Community", members=[self.member])
		space = create_space("Idempotent Join Space", community)

		with self.as_user(self.member):
			frappe.get_doc("GP Project", space.name).join()
			frappe.get_doc("GP Project", space.name).join()

		self.assertEqual(
			frappe.db.count(
				"GP Member",
				{"parenttype": "GP Project", "parent": space.name, "user": self.member.name},
			),
			1,
		)

	def test_member_can_leave_public_space(self):
		community = create_community("Leaveable Public Community", members=[self.member, self.second_member])
		space = create_space("Leaveable Public Space", community, members=[self.second_member])

		with self.as_user(self.second_member):
			frappe.get_doc("GP Project", space.name).leave()

		space.reload()
		self.assertFalse(any(row.user == self.second_member.name for row in space.members))

	def test_leaving_a_space_twice_stays_left(self):
		community = create_community("Idempotent Leave Community", members=[self.member])
		space = create_space("Idempotent Leave Space", community, members=[self.member])

		with self.as_user(self.member):
			frappe.get_doc("GP Project", space.name).leave()
			frappe.get_doc("GP Project", space.name).leave()

		self.assertFalse(
			frappe.db.exists(
				"GP Member",
				{"parenttype": "GP Project", "parent": space.name, "user": self.member.name},
			)
		)

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


class TestSpaceReadState(GameplanTestCase):
	def setUp(self):
		super().setUp()
		self.community = create_community("Read State Community", members=[self.member, self.second_member])
		self.space = create_space(
			"Read State Space", self.community, members=[self.member, self.second_member]
		)
		with self.as_user(self.second_member):
			self.discussion = create_discussion("Unread Space Discussion", self.space)

	def test_marking_a_space_read_clears_only_the_current_users_unread_state(self):
		with self.as_user(self.member):
			frappe.get_doc("GP Project", self.space.name).mark_all_as_read()

		self.assertEqual(
			frappe.db.get_value(
				"GP Unread Record",
				{"user": self.member.name, "discussion": self.discussion.name},
				"is_unread",
			),
			0,
		)
		self.assertEqual(
			frappe.db.get_value(
				"GP Unread Record",
				{"user": self.outsider.name, "discussion": self.discussion.name},
				"is_unread",
			),
			1,
		)
		visit = frappe.db.get_value(
			"GP Project Visit",
			{"user": self.member.name, "project": self.space.name},
			["last_visit", "mark_all_read_at"],
			as_dict=True,
		)
		self.assertTrue(visit.last_visit)
		self.assertTrue(visit.mark_all_read_at)

	def test_bulk_mark_read_accepts_numeric_space_names_from_the_list_api(self):
		with self.as_user(self.member):
			mark_all_as_read(spaces=[int(self.space.name)])

		self.assertEqual(
			frappe.db.get_value(
				"GP Unread Record",
				{"user": self.member.name, "discussion": self.discussion.name},
				"is_unread",
			),
			0,
		)

	def test_visiting_a_space_upserts_the_current_users_visit(self):
		old_last_visit = "2026-01-01 00:00:00"
		visit = frappe.get_doc(
			doctype="GP Project Visit",
			user=self.member.name,
			project=self.space.name,
			last_visit=old_last_visit,
		).insert(ignore_permissions=True)

		with self.as_user(self.member):
			frappe.get_doc("GP Project", self.space.name).track_visit()
			frappe.get_doc("GP Project", self.space.name).track_visit()

		self.assertEqual(
			frappe.db.count("GP Project Visit", {"user": self.member.name, "project": self.space.name}),
			1,
		)
		visit.reload()
		self.assertGreater(
			frappe.utils.get_datetime(visit.last_visit),
			frappe.utils.get_datetime(old_last_visit),
		)
		self.assertIsNone(visit.mark_all_read_at)

	def test_member_cannot_track_a_visit_to_an_inaccessible_space(self):
		private_community = create_community("Private Visit Community", is_private=1, members=[self.member])
		private_space = create_space(
			"Private Visit Space", private_community, is_private=1, members=[self.member]
		)

		with self.as_user(self.outsider), self.assertRaises(frappe.PermissionError):
			private_space.track_visit()

		self.assertFalse(
			frappe.db.exists(
				"GP Project Visit",
				{"user": self.outsider.name, "project": private_space.name},
			)
		)

	def test_marking_a_space_read_updates_the_existing_visit(self):
		old_timestamp = "2026-01-01 00:00:00"
		visit = frappe.get_doc(
			doctype="GP Project Visit",
			user=self.member.name,
			project=self.space.name,
			last_visit=old_timestamp,
			mark_all_read_at=old_timestamp,
		).insert(ignore_permissions=True)

		with self.as_user(self.member):
			frappe.get_doc("GP Project", self.space.name).mark_all_as_read()

		self.assertEqual(
			frappe.db.count("GP Project Visit", {"user": self.member.name, "project": self.space.name}),
			1,
		)
		visit.reload()
		self.assertGreater(
			frappe.utils.get_datetime(visit.mark_all_read_at),
			frappe.utils.get_datetime(old_timestamp),
		)
		self.assertGreater(
			frappe.utils.get_datetime(visit.last_visit),
			frappe.utils.get_datetime(old_timestamp),
		)

	def test_guest_with_space_access_can_record_a_visit(self):
		grant_guest_access(self.guest, self.space)

		with self.as_user(self.guest):
			frappe.get_doc("GP Project", self.space.name).track_visit()

		self.assertTrue(
			frappe.db.get_value(
				"GP Project Visit",
				{"user": self.guest.name, "project": self.space.name},
				"last_visit",
			)
		)

	def test_guest_without_space_access_cannot_record_a_visit(self):
		with self.as_user(self.guest), self.assertRaises(frappe.PermissionError):
			frappe.get_doc("GP Project", self.space.name).track_visit()

		self.assertFalse(
			frappe.db.exists(
				"GP Project Visit",
				{"user": self.guest.name, "project": self.space.name},
			)
		)

	def test_member_cannot_mark_an_inaccessible_space_read(self):
		private_community = create_community(
			"Private Read State Community", is_private=1, members=[self.member]
		)
		private_space = create_space(
			"Private Read State Space", private_community, is_private=1, members=[self.member]
		)

		with self.as_user(self.outsider), self.assertRaises(frappe.PermissionError):
			private_space.mark_all_as_read()

		self.assertFalse(
			frappe.db.exists(
				"GP Project Visit",
				{"user": self.outsider.name, "project": private_space.name},
			)
		)


class TestSpaceMutationHTTPMethods(GameplanTestCase):
	def test_following_is_not_a_space_api(self):
		for method in ("follow", "unfollow"):
			self.assertFalse(hasattr(GPProject, method))
		for endpoint in ("follow_spaces", "unfollow_spaces"):
			self.assertFalse(hasattr(gp_project_module, endpoint))

	def test_space_membership_mutations_are_post_only(self):
		for method in (
			GPProject.join,
			GPProject.leave,
			GPProject.track_visit,
			GPProject.mark_all_as_read,
			track_visits,
		):
			self.assertEqual(frappe.allowed_http_methods_for_whitelisted_func[method], ["POST"])
