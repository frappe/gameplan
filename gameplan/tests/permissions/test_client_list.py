# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

import frappe

from gameplan.extends.client import get_list
from gameplan.gameplan.doctype.gp_discussion.api import get_discussions
from gameplan.gameplan.doctype.gp_task.gp_task import get_list as get_task_list
from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import (
	create_comment,
	create_community,
	create_discussion,
	create_page,
	create_poll,
	create_space,
	create_task,
	grant_guest_access,
	set_owner,
)


class TestClientList(GameplanTestCase):
	def setUp(self):
		super().setUp()
		self.community = create_community("Client List Community", members=[self.member, self.outsider])
		self.space = create_space("Client List Space", self.community, is_private=1, members=[self.member])
		self.discussion = create_discussion("Client List Discussion", self.space, owner=self.member)
		self.task = create_task("Client List Task", self.space, owner=self.member)

	def test_content_lists_follow_space_access(self):
		comment = create_comment(self.discussion, owner=self.member)
		task_comment = create_comment(self.task, owner=self.member)
		page = create_page("Client List Page", self.space, owner=self.member)
		poll = create_poll("Client List Poll", self.discussion, owner=self.member)
		rows = [self.space, self.discussion, self.task, comment, task_comment, page, poll]

		for doc in rows:
			for user, visible in ((self.member, True), (self.outsider, False), (self.guest, False)):
				with self.subTest(doctype=doc.doctype, user=user.name), self.as_user(user):
					listed = get_list(doctype=doc.doctype, fields=["name"], filters={"name": doc.name})
					self.assertEqual([str(row.name) for row in listed], [str(doc.name)] if visible else [])

		grant_guest_access(self.guest, self.space)
		with self.as_user(self.guest):
			for doc in rows:
				with self.subTest(doctype=doc.doctype, user=self.guest.name):
					listed = get_list(doctype=doc.doctype, fields=["name"], filters={"name": doc.name})
					self.assertEqual([str(row.name) for row in listed], [str(doc.name)])

	def test_a_space_less_task_and_its_comments_are_listed_only_for_its_owner(self):
		task = create_task("Client List Space-less Task", owner=self.member)
		comment = create_comment(task, owner=self.member)

		for user, visible in ((self.member, True), (self.second_member, False)):
			with self.subTest(user=user.name), self.as_user(user):
				tasks = get_task_list(
					fields=frappe.as_json(["name"]), filters=frappe.as_json({"name": task.name})
				)
				self.assertEqual([str(row.name) for row in tasks], [str(task.name)] if visible else [])
				comments = get_list(doctype="GP Comment", fields=["name"], filters={"name": comment.name})
				self.assertEqual([str(row.name) for row in comments], [str(comment.name)] if visible else [])

	def test_child_rows_are_listed_through_their_parent(self):
		filters = {"parenttype": "GP Project", "parent": self.space.name}
		with self.as_user(self.member):
			rows = get_list(doctype="GP Member", fields=["user"], filters=filters, parent="GP Project")
			self.assertIn(self.member.name, [row.user for row in rows])
		with self.as_user(self.outsider):
			rows = get_list(doctype="GP Member", fields=["user"], filters=filters, parent="GP Project")
			self.assertEqual(rows, [])

	def test_personal_lists_follow_their_user(self):
		draft = set_owner(
			frappe.get_doc(
				doctype="GP Draft", title="Client List Draft", content="Draft", project=self.space.name
			).insert(ignore_permissions=True),
			self.member,
		)
		rows = [draft]
		for doctype, values in (
			("GP Bookmark", {"user": self.member.name, "discussion": self.discussion.name}),
			(
				"GP Notification",
				{"to_user": self.member.name, "type": "Mention", "discussion": self.discussion.name},
			),
			("GP Project Visit", {"user": self.member.name, "project": self.space.name}),
			("GP Discussion Visit", {"user": self.member.name, "discussion": self.discussion.name}),
			("GP Followed Project", {"user": self.member.name, "project": self.space.name}),
		):
			rows.append(frappe.get_doc(doctype=doctype, **values).insert(ignore_permissions=True))
		with self.as_user(self.member):
			rows.append(frappe.get_doc(doctype="GP Pinned Project", project=self.space.name).insert())

		for doc in rows:
			for user, visible in ((self.member, True), (self.outsider, False), (self.guest, False)):
				with self.subTest(doctype=doc.doctype, user=user.name), self.as_user(user):
					listed = get_list(doctype=doc.doctype, fields=["name"], filters={"name": doc.name})
					self.assertEqual([str(row.name) for row in listed], [str(doc.name)] if visible else [])

	def test_frontend_fields_remain_readable_for_members_and_guests(self):
		grant_guest_access(self.guest, self.space)
		poll = create_poll("Client List Poll Fields", self.discussion, owner=self.member)
		for user in (self.member, self.guest):
			with self.subTest(user=user.name), self.as_user(user):
				spaces = get_list(
					doctype="GP Project",
					fields=["name", "team.title as team_title", {"members": ["user"]}],
					filters={"name": self.space.name},
				)
				self.assertEqual(len(spaces), 1)
				self.assertEqual(spaces[0].team_title, self.community.title)
				self.assertIn(self.member.name, [row.user for row in spaces[0].members])
				communities = get_list(
					doctype="GP Team",
					fields=["name", "title", {"members": ["user", "is_admin"]}],
					filters={"name": self.community.name},
				)
				self.assertEqual(len(communities), 1)
				self.assertIn(self.member.name, [row.user for row in communities[0].members])
				tasks = get_task_list(
					fields=frappe.as_json(["*", "project.title as project_title"]),
					filters=frappe.as_json({"name": self.task.name}),
				)
				self.assertEqual(len(tasks), 1)
				self.assertEqual(tasks[0].project_title, self.space.title)
				self.assertEqual(tasks[0].title, self.task.title)
				discussions = get_discussions(filters={"name": self.discussion.name}, limit=20)
				self.assertEqual(len(discussions), 1)
				self.assertEqual(discussions[0].project_title, self.space.title)
				polls = get_list(
					doctype="GP Poll",
					fields=[
						"name",
						"title",
						{"options": ["name", "title", "idx", "percentage"]},
						{"votes": ["user", "option"]},
					],
					filters={"name": poll.name},
				)
				self.assertEqual(len(polls), 1)
				self.assertEqual([row.title for row in polls[0].options], ["Yes", "No"])
				self.assertEqual(polls[0].votes, [])

	def test_linked_user_fields_follow_field_permissions(self):
		frappe.db.set_value("GP Task", self.task.name, "assigned_to", self.second_member.name)
		profile = frappe.db.get_value("GP User Profile", {"user": self.second_member.name}, "name")
		grant_guest_access(self.guest, self.space)
		for user in (self.member, self.guest):
			with self.subTest(user=user.name), self.as_user(user):
				for doctype, name, link in (
					("GP User Profile", profile, "user"),
					("GP Task", self.task.name, "assigned_to"),
				):
					with self.subTest(doctype=doctype):
						rows = get_list(
							doctype=doctype,
							fields=["name", f"{link}.api_key as api_key"],
							filters={"name": name},
						)
						self.assertEqual(len(rows), 1)
						self.assertNotIn("api_key", rows[0])
				rows = get_task_list(
					fields=frappe.as_json(["name", "assigned_to.api_key as api_key"]),
					filters=frappe.as_json({"name": self.task.name}),
				)
				self.assertEqual(len(rows), 1)
				self.assertNotIn("api_key", rows[0])
				with self.assertRaises(frappe.PermissionError):
					get_list(doctype="GP User Profile", filters={"user.api_key": ["is", "set"]})
				with self.assertRaises(frappe.PermissionError):
					get_task_list(filters=frappe.as_json({"assigned_to.api_key": ["is", "set"]}))
				with self.assertRaises(frappe.PermissionError):
					get_discussions(filters={"last_post_by.api_key": ["is", "set"]}, limit=20)
