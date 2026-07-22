# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

import frappe
from frappe.auth import CookieManager, LoginManager
from frappe.tests.test_api import FrappeAPITestCase
from frappe.utils import get_test_client, set_request

from gameplan.tests.utils import create_member, create_team


class TestV16APICompatibility(FrappeAPITestCase):
	"""Exercise browser routes that Frappe v16 checks before controller methods run."""

	version = "v2"

	def setUp(self):
		frappe.set_user("Administrator")
		self.TEST_CLIENT = get_test_client()
		self.teams = []
		self.drafts = []
		self.users = []
		self.addCleanup(self.cleanup_committed_fixtures)
		suffix = frappe.generate_hash(length=8)
		self.member = create_member(f"api_boundary_member_{suffix}@example.com", "API Boundary Member")
		self.other_member = create_member(
			f"api_boundary_other_{suffix}@example.com", "API Boundary Other Member"
		)
		self.users.extend([self.member.name, self.other_member.name])

	def login_as(self, user: str):
		set_request(path="/")
		frappe.local.cookie_manager = CookieManager()
		frappe.local.login_manager = LoginManager()
		frappe.local.login_manager.login_as(user)
		self.TEST_CLIENT.set_cookie(key="sid", value=frappe.session.sid)
		frappe.set_user("Administrator")
		frappe.db.commit()

	def create_space(self):
		team = create_team(f"API Boundary {frappe.generate_hash(length=8)}")
		self.teams.append(team.name)
		return frappe.get_doc("GP Project", {"team": team.name})

	def create_draft(self, owner: str, content: str):
		frappe.set_user(owner)
		draft = frappe.get_doc(doctype="GP Draft", type="Discussion", mode="New", content=content).insert()
		self.drafts.append(draft.name)
		frappe.set_user("Administrator")
		return draft

	def cleanup_committed_fixtures(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()
		for draft in self.drafts:
			if frappe.db.exists("GP Draft", draft):
				frappe.delete_doc("GP Draft", draft, ignore_permissions=True, force=True)
		for team in self.teams:
			if frappe.db.exists("GP Team", team):
				frappe.delete_doc("GP Team", team, ignore_permissions=True, force=True)
		for user in self.users:
			if frappe.db.exists("User", user):
				frappe.delete_doc("User", user, ignore_permissions=True, force=True)
		frappe.db.commit()

	def test_member_space_actions_cross_the_http_permission_boundary(self):
		space = self.create_space()
		space_id = str(space.name)
		frappe.set_user(self.member.name)
		self.assertTrue(space.has_permission("read"))
		self.assertFalse(space.has_permission("write"))
		frappe.set_user("Administrator")
		frappe.db.commit()
		self.login_as(self.member.name)

		join = self.post(self.method("GP Project", "join_spaces"), {"spaces": [space_id]})
		self.assertEqual(join.status_code, 200, join.text)
		frappe.db.rollback()
		self.assertTrue(frappe.db.exists("GP Member", {"parent": space_id, "user": self.member.name}))

		visit = self.post(self.method("GP Project", "track_visit"), {"space": space_id})
		self.assertEqual(visit.status_code, 200, visit.text)
		frappe.db.rollback()
		self.assertTrue(frappe.db.exists("GP Project Visit", {"project": space_id, "user": self.member.name}))

		mark_read = self.post(self.method("GP Project", "mark_all_as_read"), {"spaces": [space_id]})
		self.assertEqual(mark_read.status_code, 200, mark_read.text)
		frappe.db.rollback()
		self.assertTrue(
			frappe.db.get_value(
				"GP Project Visit",
				{"project": space_id, "user": self.member.name},
				"mark_all_read_at",
			)
		)

		leave = self.post(self.method("GP Project", "leave_spaces"), {"spaces": [space_id]})
		self.assertEqual(leave.status_code, 200, leave.text)
		frappe.db.rollback()
		self.assertFalse(frappe.db.exists("GP Member", {"parent": space_id, "user": self.member.name}))

	def test_member_is_included_by_add_to_apps_screen_hook_over_http(self):
		"""Frappe boot calls the configured hook with no arguments for each app."""
		frappe.db.commit()
		self.login_as(self.member.name)

		response = self.get(self.method("frappe.apps.get_apps"))

		self.assertEqual(response.status_code, 200, response.text)
		apps = response.json["data"]
		self.assertIn("gameplan", [app["name"] for app in apps])

	def test_bulk_delete_drafts_checks_each_document_permission_over_http(self):
		own_drafts = [
			self.create_draft(self.member.name, "First draft"),
			self.create_draft(self.member.name, "Second draft"),
		]
		other_draft = self.create_draft(self.other_member.name, "Another member's draft")
		frappe.db.commit()
		self.login_as(self.member.name)

		response = self.post(
			self.method("GP Draft", "bulk_delete"),
			{"names": [own_drafts[0].name, other_draft.name, own_drafts[1].name]},
		)

		self.assertEqual(response.status_code, 200, response.text)
		result = response.json["data"]
		self.assertCountEqual(result["deleted"], [draft.name for draft in own_drafts])
		self.assertEqual(result["success_count"], 2)
		self.assertEqual(result["failure_count"], 1)
		self.assertEqual(result["failed"][0]["name"], other_draft.name)
		frappe.db.rollback()
		self.assertFalse(frappe.db.exists("GP Draft", own_drafts[0].name))
		self.assertFalse(frappe.db.exists("GP Draft", own_drafts[1].name))
		self.assertTrue(frappe.db.exists("GP Draft", other_draft.name))
