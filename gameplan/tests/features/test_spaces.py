# Copyright (c) 2022, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from gameplan.gameplan.doctype.gp_project.gp_project import get_activity
from gameplan.search_sqlite import GameplanSearch
from gameplan.tests.fixtures import create_community, create_discussion, create_member, create_space


class TestGPProject(FrappeTestCase):
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
