# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.auth import CookieManager, LoginManager
from frappe.tests.test_api import FrappeAPITestCase
from frappe.utils import get_test_client, set_request, today

from gameplan.tests.utils import create_discussion, create_member, create_project, create_team


class TestGetRequestTransactions(FrappeAPITestCase):
	"""Guard Gameplan endpoints whose transaction behavior differs for GET requests."""

	def setUp(self):
		frappe.set_user("Administrator")
		self.TEST_CLIENT = get_test_client()
		self.drafts = []
		self.invitations = []
		self.teams = []
		self.users = []
		self.addCleanup(self.cleanup_committed_fixtures)

	def login_as(self, user: str):
		set_request(path="/")
		frappe.local.cookie_manager = CookieManager()
		frappe.local.login_manager = LoginManager()
		frappe.local.login_manager.login_as(user)
		self.TEST_CLIENT.set_cookie(key="sid", value=frappe.session.sid)
		frappe.set_user("Administrator")
		frappe.db.commit()

	def cleanup_committed_fixtures(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()
		for invitation in self.invitations:
			if frappe.db.exists("GP Invitation", invitation):
				frappe.delete_doc("GP Invitation", invitation, ignore_permissions=True, force=True)
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

	def test_existing_user_invitation_acceptance_persists_after_get(self):
		"""The email link remains a GET because both successful branches commit explicitly.

		An established user follows the login branch, whose session creation commits the accepted
		invitation before Frappe's end-of-request GET rollback runs.
		"""
		suffix = frappe.generate_hash(length=8)
		user = create_member(f"get_invitation_{suffix}@example.com", "GET Invitation")
		self.users.append(user.name)
		frappe.db.set_value("User", user.name, "last_password_reset_date", today())

		key = frappe.generate_hash(length=24)
		invitation = frappe.get_doc(
			doctype="GP Invitation",
			email=user.name,
			role="Gameplan Member",
			key=key,
			status="Pending",
			invited_by="Administrator",
		)
		# Avoid sending email while preserving the exact document consumed by the endpoint.
		invitation.db_insert()
		self.invitations.append(invitation.name)
		frappe.db.commit()

		response = self.get(f"{self.method('gameplan.api.accept_invitation')}?key={key}")

		self.assertEqual(response.status_code, 302, response.text)
		self.assertEqual(response.headers["Location"], "/g")
		frappe.db.rollback()
		self.assertEqual(frappe.db.get_value("GP Invitation", invitation.name, "status"), "Accepted")
		self.assertTrue(frappe.db.get_value("GP Invitation", invitation.name, "accepted_at"))

	def test_get_my_drafts_deduplicates_response_without_cleanup(self):
		"""A GET returns one row per reply without attempting a rolled-back delete."""
		suffix = frappe.generate_hash(length=8)
		user = create_member(f"get_drafts_{suffix}@example.com", "GET Drafts")
		self.users.append(user.name)
		team = create_team(f"GET Drafts {suffix}")
		self.teams.append(team.name)
		project = create_project(f"GET Drafts Space {suffix}", team.name)
		discussion = create_discussion(f"GET Drafts Discussion {suffix}", project.name)

		frappe.set_user(user.name)
		fields = {
			"type": "Comment",
			"mode": "New",
			"reference_doctype": "GP Discussion",
			"reference_name": str(discussion.name),
		}
		older = frappe.get_doc(doctype="GP Draft", content="older", **fields).insert()
		newer = frappe.get_doc(doctype="GP Draft", content="newer", **fields).insert()
		self.drafts.extend([older.name, newer.name])
		frappe.set_user("Administrator")
		frappe.db.commit()
		self.login_as(user.name)

		with patch("frappe.delete_doc", side_effect=AssertionError("GET attempted draft cleanup")) as delete:
			response = self.get(
				self.method("gameplan.gameplan.doctype.gp_draft.gp_draft.get_my_drafts")
			)

		self.assertEqual(response.status_code, 200, response.text)
		delete.assert_not_called()
		self.assertEqual([draft["name"] for draft in response.json["message"]], [newer.name])
		frappe.db.rollback()
		stored = frappe.get_all(
			"GP Draft", filters={"owner": user.name, **fields}, order_by="modified desc", pluck="name"
		)
		self.assertEqual(stored, [newer.name, older.name])
