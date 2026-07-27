# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

import frappe
from frappe.auth import CookieManager, LoginManager
from frappe.tests.test_api import FrappeAPITestCase
from frappe.utils import get_test_client, set_request, today

from gameplan.gameplan.doctype.gp_discussion.gp_discussion import GPDiscussion
from gameplan.gameplan.doctype.gp_draft.gp_draft import GPDraft, find_my_draft
from gameplan.gameplan.doctype.gp_project.gp_project import GPProject
from gameplan.gameplan.doctype.gp_task.gp_task import GPTask
from gameplan.gameplan.doctype.gp_team.gp_team import GPTeam
from gameplan.mixins.archivable import Archivable
from gameplan.mixins.manage_members import ManageMembersMixin
from gameplan.tests.utils import create_discussion, create_member, create_project, create_team

MUTATING_ENDPOINT_FUNCTIONS = {
	"GP Discussion.track_visit": GPDiscussion.track_visit,
	"GP Discussion.mark_as_unread": GPDiscussion.mark_as_unread,
	"GP Discussion.move_to_project": GPDiscussion.move_to_project,
	"GP Discussion.close_discussion": GPDiscussion.close_discussion,
	"GP Discussion.reopen_discussion": GPDiscussion.reopen_discussion,
	"GP Discussion.pin_discussion": GPDiscussion.pin_discussion,
	"GP Discussion.unpin_discussion": GPDiscussion.unpin_discussion,
	"GP Discussion.add_bookmark": GPDiscussion.add_bookmark,
	"GP Discussion.remove_bookmark": GPDiscussion.remove_bookmark,
	"GP Draft.publish": GPDraft.publish,
	"gp_draft.find_my_draft": find_my_draft,
	"GP Project.move_to_team": GPProject.move_to_team,
	"GP Project.merge_with_project": GPProject.merge_with_project,
	"GP Project.invite_guest": GPProject.invite_guest,
	"GP Project.remove_guest": GPProject.remove_guest,
	"GP Project.add_member": GPProject.add_member,
	"GP Project.remove_member": GPProject.remove_member,
	"GP Project.archive": GPProject.archive,
	"GP Task.track_visit": GPTask.track_visit,
	"GP Team.add_members": GPTeam.add_members,
	"GP Team.remove_member": GPTeam.remove_member,
	"GP Team.remove_guest_access": GPTeam.remove_guest_access,
	"GP Team.remove_guest_invitation": GPTeam.remove_guest_invitation,
	"GP Team.merge_into_team": GPTeam.merge_into_team,
	"GP Team.set_member_admin": GPTeam.set_member_admin,
	"Archivable.archive": Archivable.archive,
	"Archivable.unarchive": Archivable.unarchive,
	"ManageMembersMixin.remove_member": ManageMembersMixin.remove_member,
}


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

	def document_method(self, doctype: str, name: str, method: str):
		return self.method("run_doc_method"), {
			"dt": doctype,
			"dn": str(name),
			"method": method,
		}

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

	def test_mutating_endpoint_functions_are_post_only(self):
		for endpoint, function in MUTATING_ENDPOINT_FUNCTIONS.items():
			with self.subTest(endpoint=endpoint):
				self.assertEqual(
					frappe.allowed_http_methods_for_whitelisted_func.get(function),
					["POST"],
				)

	def test_discussion_close_rejects_get_and_post_persists(self):
		team = create_team(f"POST Discussion {frappe.generate_hash(length=8)}")
		self.teams.append(team.name)
		project = create_project("POST Discussion Space", team.name)
		discussion = create_discussion("POST Discussion", project.name)
		frappe.db.commit()
		self.login_as("Administrator")
		endpoint, payload = self.document_method(
			"GP Discussion",
			discussion.name,
			"close_discussion",
		)

		get_response = self.get(endpoint, payload)

		self.assertFalse(frappe.db.get_value("GP Discussion", discussion.name, "closed_at"))
		self.assertEqual(get_response.status_code, 403, get_response.text)

		post_response = self.post(endpoint, payload)

		self.assertEqual(post_response.status_code, 200, post_response.text)
		frappe.db.rollback()
		self.assertTrue(frappe.db.get_value("GP Discussion", discussion.name, "closed_at"))

	def test_inherited_community_archive_rejects_get_and_post_persists(self):
		team = create_team(f"POST Community {frappe.generate_hash(length=8)}")
		self.teams.append(team.name)
		frappe.db.commit()
		self.login_as("Administrator")
		endpoint, payload = self.document_method("GP Team", team.name, "archive")

		get_response = self.get(endpoint, payload)

		self.assertFalse(frappe.db.get_value("GP Team", team.name, "archived_at"))
		self.assertEqual(get_response.status_code, 403, get_response.text)

		post_response = self.post(endpoint, payload)

		self.assertEqual(post_response.status_code, 200, post_response.text)
		frappe.db.rollback()
		self.assertTrue(frappe.db.get_value("GP Team", team.name, "archived_at"))

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
			role="Gameplan Admin",
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
		self.assertTrue(
			frappe.db.exists(
				"Has Role",
				{"parent": user.name, "parenttype": "User", "role": "Gameplan Admin"},
			)
		)

	def test_new_user_invitation_acceptance_persists_after_get(self):
		suffix = frappe.generate_hash(length=8)
		email = f"get_new_invitation_{suffix}@example.com"
		self.users.append(email)
		key = frappe.generate_hash(length=24)
		invitation = frappe.get_doc(
			doctype="GP Invitation",
			email=email,
			role="Gameplan Member",
			key=key,
			status="Pending",
			invited_by="Administrator",
		)
		invitation.db_insert()
		self.invitations.append(invitation.name)
		frappe.db.commit()

		response = self.get(f"{self.method('gameplan.api.accept_invitation')}?key={key}")

		self.assertEqual(response.status_code, 302, response.text)
		self.assertTrue(response.headers["Location"].startswith("/update-password?key="))
		frappe.db.rollback()
		self.assertEqual(frappe.db.get_value("GP Invitation", invitation.name, "status"), "Accepted")
		self.assertTrue(frappe.db.get_value("GP Invitation", invitation.name, "accepted_at"))
		self.assertTrue(frappe.db.exists("User", email))
		self.assertTrue(
			frappe.db.exists(
				"Has Role",
				{"parent": email, "parenttype": "User", "role": "Gameplan Member"},
			)
		)
		self.assertTrue(frappe.db.get_value("User", email, "reset_password_key"))

	def test_get_my_drafts_post_persists_duplicate_cleanup(self):
		"""The POST returns the newest reply draft and permanently removes stale duplicates."""
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

		response = self.post(self.method("gameplan.gameplan.doctype.gp_draft.gp_draft.get_my_drafts"), {})

		self.assertEqual(response.status_code, 200, response.text)
		self.assertEqual([draft["name"] for draft in response.json["message"]], [newer.name])
		frappe.db.rollback()
		stored = frappe.get_all(
			"GP Draft", filters={"owner": user.name, **fields}, order_by="modified desc", pluck="name"
		)
		self.assertEqual(stored, [newer.name])
