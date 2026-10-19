# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

from types import SimpleNamespace
from unittest.mock import patch

import frappe
from frappe.api.v2 import execute_doc_method
from frappe.api.v2 import run_doc_method as run_v2_doc_method
from frappe.handler import run_doc_method
from frappe.utils import add_days, now_datetime

from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import create_comment, create_community, create_discussion, create_space


class TestStoredDocumentMethods(GameplanTestCase):
	def setUp(self):
		super().setUp()
		self.community = create_community("Stored methods", members=[self.member])
		self.other_community = create_community("Other stored methods", members=[self.member])
		self.space = create_space("Stored public space", self.community, members=[self.member])
		self.private_space = create_space(
			"Stored private space", self.community, is_private=1, members=[self.member]
		)

	def call_method(self, doc, method, *, route="docs", **kwargs):
		with (
			patch.object(
				frappe.local,
				"request",
				SimpleNamespace(method="GET" if method == "get_revisions" else "POST"),
				create=True,
			),
			patch.object(frappe.local, "response", frappe._dict(docs=[])),
			patch.object(frappe.local, "form_dict", frappe._dict(kwargs)),
		):
			if route == "docs":
				run_doc_method(method, docs=frappe.as_json(doc.as_dict()), args=frappe.as_json(kwargs))
			elif route == "dt_dn":
				run_doc_method(method, dt=doc.doctype, dn=doc.name, args=frappe.as_json(kwargs))
			elif route == "v2_document":
				result = run_v2_doc_method(method, document=doc.as_dict(), kwargs=kwargs)
			else:
				result = execute_doc_method(doc.doctype, str(doc.name), method)
			if route in {"docs", "dt_dn"}:
				result = frappe.response.get("message")
			return result, frappe.response.docs

	def test_membership_preserves_stored_space_fields(self):
		with self.as_user(self.second_member):
			for method in ("join", "leave"):
				space = frappe.get_doc("GP Project", self.space.name)
				space.title = "Local title"
				space.team = self.other_community.name
				space.set("members", [])
				_, returned = self.call_method(space, method)
				stored = frappe.get_doc("GP Project", space.name)
				self.assertEqual(stored.title, self.space.title)
				self.assertEqual(stored.team, self.community.name)
				self.assertIn(self.member.name, [row.user for row in stored.members])
				self.assertEqual(
					self.second_member.name in [row.user for row in stored.members], method == "join"
				)
				self.assertEqual(returned[0].title, stored.title)

	def test_private_space_actions_check_stored_access(self):
		with self.as_user(self.outsider):
			for method in ("join", "leave", "track_visit", "mark_all_as_read"):
				with self.subTest(method=method):
					space = frappe.get_doc("GP Project", self.private_space.name)
					space.is_private = 0
					with self.assertRaises(frappe.PermissionError):
						self.call_method(space, method)

		with self.as_user(self.member):
			space = frappe.get_doc("GP Project", self.private_space.name)
			space.is_private = 0
			self.call_method(space, "join")
		self.assertEqual(frappe.db.get_value("GP Project", space.name, "is_private"), 1)

	def test_revisions_check_stored_content_access(self):
		public_discussion = create_discussion("Public stored thread", self.space, owner=self.member)
		discussion = create_discussion("Private stored thread", self.private_space, owner=self.member)
		comment = create_comment(discussion, owner=self.member)
		for doc in (discussion, comment):
			frappe.get_doc(
				doctype="Version",
				ref_doctype=doc.doctype,
				docname=str(doc.name),
				data=frappe.as_json(
					{"changed": [["content", "Earlier content", "Stored content"]]}, indent=None
				),
			).insert(ignore_permissions=True)

			with self.as_user(self.outsider):
				local_doc = frappe.get_doc(doc.doctype, doc.name)
				if doc.doctype == "GP Discussion":
					local_doc.project = self.space.name
				else:
					local_doc.reference_name = public_discussion.name
				for route in ("docs", "dt_dn", "v2_document", "v2_named"):
					with self.subTest(doctype=doc.doctype, route=route):
						with self.assertRaises(frappe.PermissionError):
							self.call_method(local_doc, "get_revisions", route=route)

			with self.as_user(self.member):
				for route in ("docs", "dt_dn", "v2_document", "v2_named"):
					with self.subTest(doctype=doc.doctype, route=route):
						revisions, _ = self.call_method(doc, "get_revisions", route=route)
						self.assertEqual(revisions[0]["old_value"], "Earlier content")

	def test_archive_preserves_stored_space_fields(self):
		with self.as_user(self.admin):
			space = frappe.get_doc("GP Project", self.space.name)
			space.title = "Local archive title"
			space.team = self.other_community.name
			space.archive()
			space.reload()
			self.assertEqual(space.title, self.space.title)
			self.assertEqual(space.team, self.community.name)
			self.assertTrue(space.archived_at)
			space.unarchive()
			self.assertFalse(space.archived_at)

	def test_draft_actions_use_saved_content(self):
		with self.as_user(self.member):
			draft = frappe.get_doc(
				doctype="GP Draft",
				type="Discussion",
				title="Saved draft title",
				project=self.space.name,
				content="Saved draft content",
			).insert()
			draft.title = "Local draft title"
			draft.schedule(add_days(now_datetime(), 1))
			self.assertEqual(draft.title, "Saved draft title")
			self.assertTrue(draft.scheduled_at)
			draft.unschedule()
			self.assertFalse(draft.scheduled_at)
			name, _ = self.call_method(draft, "publish", route="v2_named")
			discussion = frappe.get_doc("GP Discussion", name)
			self.assertEqual(discussion.title, "Saved draft title")
			self.assertEqual(discussion.project, self.space.name)
			self.assertFalse(frappe.db.exists("GP Draft", draft.name))
