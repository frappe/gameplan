# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""Pages: creation, editing, and the personal-versus-space visibility split."""

import frappe

from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import (
	create_community,
	create_page,
	create_space,
	grant_guest_access,
)


class PageTestCase(GameplanTestCase):
	def setUp(self):
		super().setUp()
		self.community = create_community(
			"Page Community",
			members=[self.member, self.second_member],
		)
		self.space = create_space(
			"Page Space",
			self.community,
			is_private=1,
			members=[self.member, self.second_member],
		)
		grant_guest_access(self.guest, self.space)
		self.private_page = create_page(
			"Member Notes",
			content="<p>Personal notes</p>",
			owner=self.member,
		)
		self.space_page = create_page(
			"Shared Handbook",
			self.space,
			content="<p>Shared notes</p>",
			owner=self.member,
		)

	def edit_content(self, page, user, content):
		with self.as_user(user):
			doc = frappe.get_doc("GP Page", page.name)
			doc.content = content
			doc.save()
			doc.reload()
			return doc.content

	def visible_created_pages(self, user):
		with self.as_user(user):
			visible = {str(name) for name in frappe.get_list("GP Page", pluck="name")}
		return visible & {str(self.private_page.name), str(self.space_page.name)}


class TestPageCreation(PageTestCase):
	def test_member_can_create_a_private_page(self):
		with self.as_user(self.member):
			page = frappe.get_doc(
				doctype="GP Page",
				title="Private Scratchpad",
				content="<p>First draft</p>",
			).insert()

		self.assertEqual(page.owner, self.member.name)
		self.assertIsNone(page.project)
		self.assertEqual(page.content, "<p>First draft</p>")

	def test_member_can_create_a_page_in_a_visible_space(self):
		with self.as_user(self.second_member):
			page = frappe.get_doc(
				doctype="GP Page",
				title="Space Notes",
				project=self.space.name,
				content="<p>Shared draft</p>",
			).insert()

		self.assertEqual(page.owner, self.second_member.name)
		self.assertEqual(page.project, self.space.name)
		self.assertEqual(page.content, "<p>Shared draft</p>")

	def test_guest_cannot_create_a_page_in_a_granted_space(self):
		with self.as_user(self.guest):
			page = frappe.get_doc(
				doctype="GP Page",
				title="Guest Page",
				project=self.space.name,
				content="<p>Guest draft</p>",
			)
			with self.assertRaises(frappe.PermissionError):
				page.insert()


class TestPageEditing(PageTestCase):
	def test_owner_can_edit_private_page_content(self):
		content = self.edit_content(self.private_page, self.member, "<p>Updated personal notes</p>")

		self.assertEqual(content, "<p>Updated personal notes</p>")

	def test_space_member_can_edit_space_page_content(self):
		content = self.edit_content(self.space_page, self.second_member, "<p>Updated handbook</p>")

		self.assertEqual(content, "<p>Updated handbook</p>")

	def test_global_admin_can_edit_private_page_content(self):
		content = self.edit_content(self.private_page, self.admin, "<p>Admin update</p>")

		self.assertEqual(content, "<p>Admin update</p>")

	def test_other_member_cannot_edit_private_page_content(self):
		with self.assertRaises(frappe.PermissionError):
			self.edit_content(self.private_page, self.second_member, "<p>Other member update</p>")

		self.private_page.reload()
		self.assertEqual(self.private_page.content, "<p>Personal notes</p>")

	def test_guest_cannot_edit_members_space_page_content(self):
		with self.assertRaises(frappe.PermissionError):
			self.edit_content(self.space_page, self.guest, "<p>Guest update</p>")

		self.space_page.reload()
		self.assertEqual(self.space_page.content, "<p>Shared notes</p>")


class TestPageVisibility(PageTestCase):
	def test_direct_read_follows_private_page_owner_and_space_membership(self):
		expectations = {
			"admin": (True, True),
			"member": (True, True),
			"second_member": (False, True),
			"guest": (False, True),
			"outsider": (False, False),
		}

		for actor_name, (private_read, space_read) in expectations.items():
			actor = getattr(self, actor_name)
			with self.subTest(actor=actor_name, page="private"):
				self.assert_permission(self.private_page, "read", actor, private_read)
			with self.subTest(actor=actor_name, page="space"):
				self.assert_permission(self.space_page, "read", actor, space_read)

	def test_page_lists_follow_private_page_owner_and_space_membership(self):
		private_name = str(self.private_page.name)
		space_name = str(self.space_page.name)
		expectations = {
			"admin": {private_name, space_name},
			"member": {private_name, space_name},
			"second_member": {space_name},
			"guest": {space_name},
			"outsider": set(),
		}

		for actor_name, expected in expectations.items():
			with self.subTest(actor=actor_name):
				self.assertEqual(self.visible_created_pages(getattr(self, actor_name)), expected)
