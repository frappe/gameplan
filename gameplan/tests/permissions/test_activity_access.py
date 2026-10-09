# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""Activity reads follow the parent document. Only Gameplan Admins write activity directly."""

import frappe

from gameplan.extends.client import get_list as get_client_list
from gameplan.public_access import VISIBILITY_MEMBER_ACCESS
from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import (
	create_community,
	create_discussion,
	create_space,
	create_task,
	grant_guest_access,
)


class ActivityTestCase(GameplanTestCase):
	def setUp(self):
		super().setUp()
		self.community = create_community("Activity Community", members=[self.member, self.second_member])
		self.private_space = create_space(
			"Activity Private Space",
			self.community,
			visibility=VISIBILITY_MEMBER_ACCESS,
			members=[self.member],
		)
		self.discussion = create_discussion("Activity Secret Plans", self.private_space, owner=self.member)
		self.task = create_task("Activity Secret Task", self.private_space, owner=self.member)

		self.retitled = self.discussion.log_activity(
			"Discussion Title Changed", data={"old_title": "Layoffs", "new_title": "Activity Secret Plans"}
		)
		self.moved = self.discussion.log_activity(
			"Discussion Moved", data={"old_project": "1", "new_project": "2"}
		)
		self.task_change = self.task.log_activity("Task Value Changed", data={"field": "status"})
		self.private_rows = {str(row.name) for row in (self.retitled, self.moved, self.task_change)}

	def listed(self, user, lister):
		with self.as_user(user):
			return {str(name) for name in lister()} & self.private_rows


def list_through_get_list():
	return frappe.get_list("GP Activity", pluck="name", limit_page_length=0)


def list_through_client():
	return [row.name for row in get_client_list(doctype="GP Activity", fields=["name"], limit=500)]


class TestReadingActivity(ActivityTestCase):
	def test_someone_outside_a_private_space_cannot_list_its_activity(self):
		for lister in (list_through_get_list, list_through_client):
			with self.subTest(lister=lister.__name__):
				self.assertEqual(self.listed(self.second_member, lister), set())
				self.assertEqual(self.listed(self.guest, lister), set())

	def test_someone_outside_a_private_space_cannot_open_its_activity(self):
		for row in (self.retitled, self.moved, self.task_change):
			self.assert_not_allowed(row, "read", self.second_member)
			self.assert_not_allowed(row, "read", self.guest)

	def test_a_member_of_the_space_still_sees_its_activity(self):
		for lister in (list_through_get_list, list_through_client):
			with self.subTest(lister=lister.__name__):
				self.assertEqual(self.listed(self.member, lister), self.private_rows)
		self.assert_allowed(self.retitled, "read", self.member)

	def test_a_guest_granted_the_space_sees_its_activity(self):
		grant_guest_access(self.guest, self.private_space)

		self.assertEqual(self.listed(self.guest, list_through_get_list), self.private_rows)
		self.assert_allowed(self.moved, "read", self.guest)

	def test_a_global_admin_sees_everything(self):
		self.assertEqual(self.listed(self.admin, list_through_get_list), self.private_rows)

	def test_activity_on_a_personal_task_is_its_owners_alone(self):
		personal = create_task("Activity Personal Task", owner=self.member)
		row = personal.log_activity("Task Value Changed", data={"field": "status"})

		self.assert_allowed(row, "read", self.member)
		self.assert_not_allowed(row, "read", self.second_member)
		with self.as_user(self.member):
			self.assertIn(row.name, frappe.get_list("GP Activity", pluck="name", limit_page_length=0))
		with self.as_user(self.second_member):
			self.assertNotIn(row.name, frappe.get_list("GP Activity", pluck="name", limit_page_length=0))


class TestWritingActivity(ActivityTestCase):
	def test_nobody_but_an_admin_creates_or_edits_activity_directly(self):
		# Even someone who can read the discussion: activity is a record of what happened.
		for user in (self.member, self.second_member, self.guest):
			with self.subTest(user=user.name):
				with self.as_user(user), self.assertRaises(frappe.PermissionError):
					frappe.get_doc(
						doctype="GP Activity",
						reference_doctype="GP Discussion",
						reference_name=self.discussion.name,
						action="Discussion Closed",
						user=user.name,
					).insert()
				with self.as_user(user), self.assertRaises(frappe.PermissionError):
					row = frappe.get_doc("GP Activity", self.retitled.name)
					row.action = "Discussion Reopened"
					row.save()

	def test_nobody_but_an_admin_deletes_activity_directly(self):
		for user in (self.member, self.second_member):
			with self.subTest(user=user.name):
				with self.as_user(user), self.assertRaises(frappe.PermissionError):
					frappe.delete_doc("GP Activity", self.retitled.name)
		self.assertTrue(frappe.db.exists("GP Activity", self.retitled.name))

	def test_the_server_still_logs_activity_for_the_people_who_act(self):
		with self.as_user(self.member):
			discussion = frappe.get_doc("GP Discussion", self.discussion.name)
			discussion.close_discussion()

		self.assertTrue(
			frappe.db.exists(
				"GP Activity",
				{
					"reference_name": str(self.discussion.name),
					"action": "Discussion Closed",
					"user": self.member.name,
				},
			)
		)

	def test_deleting_a_discussion_still_takes_its_activity_with_it(self):
		with self.as_user(self.member):
			frappe.delete_doc("GP Discussion", self.discussion.name)

		self.assertFalse(frappe.db.exists("GP Activity", self.retitled.name))
		self.assertFalse(frappe.db.exists("GP Activity", self.moved.name))
