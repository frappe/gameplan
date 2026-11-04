# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""Row rules for the doctypes that support spaces and discussions.

GP Guest Access, GP Activity, GP Search Feedback, GP Followed Project and GP Tag are
written by server code (invitations, activity logging, tag parsing) or belong to one
user. These tests pin who can list and change them through the generic document API.
"""

import frappe

from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import (
	create_community,
	create_discussion,
	create_space,
	create_task,
	grant_guest_access,
)
from gameplan.visibility import VISIBILITY_MEMBER_ACCESS


def list_as_client(doctype, **filters):
	"""Enumerate `doctype` the way `/api/v2/document/<doctype>` does."""
	return frappe.qb.get_query(doctype, fields=["name"], filters=filters, ignore_permissions=False).run(
		pluck="name"
	)


class SupportingDoctypesTestCase(GameplanTestCase):
	def setUp(self):
		super().setUp()
		self.community = create_community("Acme", members=[self.member, self.second_member, self.outsider])
		self.private_space = create_space(
			"Board", self.community, visibility=VISIBILITY_MEMBER_ACCESS, members=[self.member]
		)
		self.discussion = create_discussion("Plans", self.private_space, owner=self.member)


class TestGuestAccess(SupportingDoctypesTestCase):
	def setUp(self):
		super().setUp()
		self.access = grant_guest_access(self.guest, self.private_space)

	def test_guest_access_is_listed_to_the_guest_and_space_managers_only(self):
		for user, visible in [
			(self.member, True),
			(self.guest, True),
			(self.admin, True),
			(self.second_member, False),
		]:
			with self.subTest(user=user.name), self.as_user(user):
				self.assertEqual(self.access.name in list_as_client("GP Guest Access"), visible)
			self.assert_permission(self.access, "read", user, visible)

	def test_guest_access_is_only_added_through_invitations(self):
		with self.as_user(self.member), self.assertRaises(frappe.PermissionError):
			frappe.get_doc(
				doctype="GP Guest Access", user=self.guest.name, project=self.private_space.name
			).insert()

	def test_only_space_managers_remove_a_guest(self):
		with self.as_user(self.second_member), self.assertRaises(frappe.PermissionError):
			frappe.delete_doc("GP Guest Access", self.access.name)

		with self.as_user(self.member):
			frappe.get_doc("GP Project", self.private_space.name).remove_guest(self.guest.name)

		self.assertFalse(frappe.db.exists("GP Guest Access", self.access.name))


class TestActivity(SupportingDoctypesTestCase):
	def setUp(self):
		super().setUp()
		with self.as_user(self.member):
			frappe.get_doc("GP Discussion", self.discussion.name).close_discussion()
		self.activity = frappe.get_last_doc(
			"GP Activity",
			filters={"reference_doctype": "GP Discussion", "reference_name": self.discussion.name},
		)

	def test_activity_follows_the_discussion_it_belongs_to(self):
		filters = {"reference_doctype": "GP Discussion", "reference_name": self.discussion.name}
		for user, visible in [(self.member, True), (self.admin, True), (self.second_member, False)]:
			with self.subTest(user=user.name), self.as_user(user):
				self.assertEqual(self.activity.name in list_as_client("GP Activity", **filters), visible)
			self.assert_permission(self.activity, "read", user, visible)

	def test_activity_on_a_personal_task_follows_the_task_owner(self):
		task = create_task("Personal", owner=self.member)
		# Edited by the admin, so the activity row's own owner is not the task owner.
		with self.as_user(self.admin):
			task = frappe.get_doc("GP Task", task.name)
			task.title = "Personal, renamed"
			task.save()
		filters = {"reference_doctype": "GP Task", "reference_name": task.name}
		activity = frappe.get_last_doc("GP Activity", filters=filters)

		for user, visible in [(self.member, True), (self.second_member, False)]:
			with self.subTest(user=user.name), self.as_user(user):
				self.assertEqual(activity.name in list_as_client("GP Activity", **filters), visible)
			self.assert_permission(activity, "read", user, visible)

	def test_activity_is_only_written_by_the_server(self):
		with self.as_user(self.member), self.assertRaises(frappe.PermissionError):
			frappe.get_doc(
				doctype="GP Activity",
				reference_doctype="GP Discussion",
				reference_name=self.discussion.name,
				action="Discussion Closed",
				user=self.second_member.name,
			).insert()

		self.assert_not_allowed(self.activity, "write", self.member)
		self.assert_not_allowed(self.activity, "delete", self.member)

	def test_deleting_a_discussion_still_removes_its_activity(self):
		with self.as_user(self.member):
			frappe.delete_doc("GP Discussion", self.discussion.name)

		self.assertFalse(frappe.db.exists("GP Activity", self.activity.name))


class TestPersonalRows(SupportingDoctypesTestCase):
	def test_search_feedback_belongs_to_whoever_sent_it(self):
		with self.as_user(self.member):
			feedback = frappe.get_doc(
				doctype="GP Search Feedback", helpful="No", query="roadmap", user=self.second_member.name
			).insert()

		self.assertEqual(feedback.user, self.member.name)
		with self.as_user(self.member):
			self.assertIn(feedback.name, list_as_client("GP Search Feedback"))
		with self.as_user(self.second_member):
			self.assertNotIn(feedback.name, list_as_client("GP Search Feedback"))
		self.assert_not_allowed(feedback, "read", self.second_member)
		self.assert_not_allowed(feedback, "write", self.member)

	def test_followed_space_belongs_to_its_user(self):
		with self.as_user(self.member):
			follow = frappe.get_doc(
				doctype="GP Followed Project",
				project=self.private_space.name,
				user=self.second_member.name,
			).insert()

		self.assertEqual(follow.user, self.member.name)
		with self.as_user(self.second_member):
			self.assertNotIn(follow.name, list_as_client("GP Followed Project"))
		self.assert_not_allowed(follow, "delete", self.second_member)
		self.assert_allowed(follow, "delete", self.member)

	def test_tags_come_from_content_not_from_the_api(self):
		tag = frappe.get_doc(doctype="GP Tag", label="supporting-doctypes-tag").insert(
			ignore_permissions=True
		)

		for user in (self.member, self.guest):
			self.assert_allowed(tag, "read", user)
			self.assert_not_allowed(tag, "write", user)
			self.assert_not_allowed(tag, "delete", user)
		with self.as_user(self.member), self.assertRaises(frappe.PermissionError):
			frappe.get_doc(doctype="GP Tag", label="supporting-doctypes-new-tag").insert()
