# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""Archived spaces freeze page and task mutations while remaining readable."""

import frappe

from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import (
	create_community,
	create_discussion,
	create_page,
	create_space,
	create_task,
)


class ArchivedSpaceTestCase(GameplanTestCase):
	def setUp(self):
		super().setUp()
		self.community = create_community(
			"Archived Content Community",
			members=[self.member, self.second_member],
		)
		self.space = create_space("Archived Content Space", self.community)
		self.page = create_page("Existing Page", self.space, owner=self.member)
		self.task = create_task("Existing Task", self.space, owner=self.member)
		self.space.reload()
		self.space.archive()


class TestArchivedPageMutations(ArchivedSpaceTestCase):
	def test_cannot_create_a_page_in_an_archived_space(self):
		with self.as_user(self.member):
			with self.assertRaisesRegex(frappe.ValidationError, "archived"):
				frappe.get_doc(
					doctype="GP Page",
					title="Blocked Page",
					project=self.space.name,
					content="<p>Should not be saved</p>",
				).insert()

	def test_cannot_edit_a_page_in_an_archived_space(self):
		with self.as_user(self.member):
			page = frappe.get_doc("GP Page", self.page.name)
			page.content = "<p>Blocked edit</p>"
			with self.assertRaisesRegex(frappe.ValidationError, "archived"):
				page.save()

		self.page.reload()
		self.assertEqual(self.page.content, "Test content")

	def test_cannot_delete_a_page_in_an_archived_space(self):
		with self.as_user(self.member):
			with self.assertRaisesRegex(frappe.ValidationError, "archived"):
				frappe.delete_doc("GP Page", self.page.name)

		self.assertTrue(frappe.db.exists("GP Page", self.page.name))


class TestArchivedTaskMutations(ArchivedSpaceTestCase):
	def test_cannot_create_a_task_in_an_archived_space(self):
		with self.as_user(self.member):
			with self.assertRaisesRegex(frappe.ValidationError, "archived"):
				frappe.get_doc(
					doctype="GP Task",
					title="Blocked Task",
					project=self.space.name,
				).insert()

	def test_cannot_edit_a_task_in_an_archived_space(self):
		with self.as_user(self.member):
			task = frappe.get_doc("GP Task", self.task.name)
			task.title = "Blocked edit"
			with self.assertRaisesRegex(frappe.ValidationError, "archived"):
				task.save()

		self.task.reload()
		self.assertEqual(self.task.title, "Existing Task")

	def test_cannot_delete_a_task_in_an_archived_space(self):
		with self.as_user(self.member):
			with self.assertRaisesRegex(frappe.ValidationError, "archived"):
				frappe.delete_doc("GP Task", self.task.name)

		self.assertTrue(frappe.db.exists("GP Task", self.task.name))


class TestArchivedContentReadsAndRecovery(ArchivedSpaceTestCase):
	def test_page_in_an_archived_space_remains_readable(self):
		with self.as_user(self.second_member):
			page = frappe.get_doc("GP Page", self.page.name)
			page.check_permission("read")

		self.assertEqual(page.content, "Test content")

	def test_unarchiving_restores_page_creation_and_editing(self):
		self.space.unarchive()

		with self.as_user(self.member):
			created = frappe.get_doc(
				doctype="GP Page",
				title="Page After Unarchive",
				project=self.space.name,
				content="<p>New page</p>",
			).insert()
			page = frappe.get_doc("GP Page", self.page.name)
			page.content = "<p>Edited after unarchive</p>"
			page.save()

		self.assertTrue(created.name)
		self.assertEqual(page.content, "<p>Edited after unarchive</p>")

	def test_unarchiving_restores_task_creation_and_editing(self):
		self.space.unarchive()

		with self.as_user(self.member):
			created = frappe.get_doc(
				doctype="GP Task",
				title="Task After Unarchive",
				project=self.space.name,
			).insert()
			task = frappe.get_doc("GP Task", self.task.name)
			task.title = "Edited after unarchive"
			task.save()

		self.assertTrue(created.name)
		self.assertEqual(task.title, "Edited after unarchive")

	def test_pages_in_an_archived_private_space_are_also_read_only(self):
		private_space = create_space(
			"Archived Private Space",
			self.community,
			is_private=1,
			members=[self.member],
		)
		private_page = create_page("Private Space Page", private_space, owner=self.member)
		private_space.reload()
		private_space.archive()

		with self.as_user(self.member):
			with self.assertRaisesRegex(frappe.ValidationError, "archived"):
				frappe.get_doc(
					doctype="GP Page",
					title="Blocked Private Space Page",
					project=private_space.name,
				).insert()

			page = frappe.get_doc("GP Page", private_page.name)
			page.content = "<p>Blocked private-space edit</p>"
			with self.assertRaisesRegex(frappe.ValidationError, "archived"):
				page.save()

			with self.assertRaisesRegex(frappe.ValidationError, "archived"):
				frappe.delete_doc("GP Page", private_page.name)

	def test_personal_pages_remain_editable(self):
		personal_page = create_page("Personal Page", owner=self.member)

		with self.as_user(self.member):
			page = frappe.get_doc("GP Page", personal_page.name)
			page.content = "<p>Personal edit</p>"
			page.save()

		self.assertEqual(page.content, "<p>Personal edit</p>")

	def test_personal_tasks_remain_editable(self):
		personal_task = create_task("Personal Task", owner=self.member)

		with self.as_user(self.member):
			task = frappe.get_doc("GP Task", personal_task.name)
			task.title = "Personal edit"
			task.save()

		self.assertEqual(task.title, "Personal edit")

	def test_deleting_an_archived_space_cascades_to_its_page_and_task(self):
		frappe.delete_doc("GP Project", self.space.name)

		self.assertFalse(frappe.db.exists("GP Project", self.space.name))
		self.assertFalse(frappe.db.exists("GP Page", self.page.name))
		self.assertFalse(frappe.db.exists("GP Task", self.task.name))

	def test_discussion_creation_in_an_archived_space_remains_blocked(self):
		with self.assertRaisesRegex(frappe.ValidationError, "archived"):
			create_discussion("Blocked Discussion", self.space)
