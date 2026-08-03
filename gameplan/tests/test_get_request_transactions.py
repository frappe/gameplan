# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""Frappe rolls the database transaction back at the end of every GET request
(`frappe/app.py::sync_database`), whatever the handler did. A mutation left reachable by
GET therefore runs, calls `save()` without error, and is then silently discarded.

This module guards that from both ends:

- `TestWhitelistedEndpointHttpMethods` enumerates *every* `@frappe.whitelist()` under
  `gameplan/` and requires it to declare an unsafe HTTP method, unless it is on an
  explicit allowlist below. Enumerating rather than listing the mutating endpoints is
  the whole point: a newly added mutating endpoint is caught by default.
- `TestGetRequestTransactions` drives the real HTTP stack for the interesting cases —
  mutations refused over GET, and the invitation link, which is deliberately GET-reachable
  and has to survive that rollback.
"""

import ast
import importlib
import pathlib

import frappe
from frappe.auth import CookieManager, LoginManager
from frappe.tests.test_api import FrappeAPITestCase
from frappe.tests.utils import FrappeTestCase
from frappe.utils import get_test_client, set_request, today

import gameplan
from gameplan.tests.fixtures import declared_http_methods
from gameplan.tests.utils import create_discussion, create_member, create_project, create_team

# Names that register a function with frappe's whitelist. `whitelist_for_tests` wraps
# `frappe.whitelist`, and `gameplan.ui_test_helpers` defines a module-local `whitelist`
# decorator that does the same — all three must be discovered.
WHITELIST_DECORATOR_NAMES = {"whitelist", "whitelist_for_tests"}

# The methods whose handlers Frappe lets commit. Anything else (GET, HEAD, OPTIONS) is
# rolled back, so a mutation must declare at least one of these and none of the others.
UNSAFE_HTTP_METHODS = frozenset({"POST", "PUT", "DELETE", "PATCH"})

# Endpoints that only read. Being rolled back at the end of the request costs them
# nothing, so they may stay GET-reachable. Every whitelisted endpoint that is NOT listed
# here (or in DELIBERATE_GET_MUTATIONS) must declare an unsafe method.
READ_ONLY_ENDPOINTS = frozenset(
	{
		# Directory and notification reads.
		"gameplan.api.get_user_info",
		"gameplan.api.unread_notifications",
		"gameplan.api.get_unsplash_photos",
		# Unsplash proxy. Talks to a third party with our key and writes nothing of ours.
		"gameplan.unsplash.search_photos",
		# Search. The SQLite index lives outside the transaction, but these only query it.
		"gameplan.api.search_sqlite",
		"gameplan.api.get_search_filter_options",
		"gameplan.command_palette.search_sqlite",
		# Permission-checked list/report queries.
		"gameplan.extends.client.get_list",
		"gameplan.gameplan.doctype.gp_discussion.api.get_discussions",
		"gameplan.gameplan.doctype.gp_task.gp_task.get_list",
		"gameplan.gameplan.doctype.gp_user_profile.gp_user_profile.get_list",
		# Revision history.
		"gameplan.gameplan.doctype.gp_comment.gp_comment.GPComment.get_revisions",
		"gameplan.gameplan.doctype.gp_discussion.gp_discussion.GPDiscussion.get_revisions",
		# Space membership, activity and unread counters.
		"gameplan.gameplan.doctype.gp_project.gp_project.get_joined_spaces",
		"gameplan.gameplan.doctype.gp_project.gp_project.get_activity",
		"gameplan.gameplan.doctype.gp_project.gp_project.get_unread_count",
		"gameplan.gameplan.doctype.gp_unread_record.api.get_unread_count",
		"gameplan.gameplan.doctype.gp_unread_record.api.get_participating_unread_count",
		# Profile reads.
		"gameplan.gameplan.doctype.gp_user_profile.gp_user_profile.get_last_post",
		"gameplan.gameplan.doctype.gp_user_profile.gp_user_profile.get_my_bento_cards",
		"gameplan.gameplan.doctype.gp_user_profile.gp_user_profile.get_bento_cards",
	}
)

# The only mutations allowed to stay GET-reachable. Both are the target of a link in an
# outbound email, so the browser arrives with a plain navigation and cannot POST, and
# both commit explicitly (via session creation) rather than relying on the request's
# transaction. The two `..._invitation_acceptance_persists_after_get` tests below prove
# that the commit really happens.
DELIBERATE_GET_MUTATIONS = {
	"gameplan.api.accept_invitation": "invitation email link; the login it performs commits",
	"gameplan.email_digest.open_digest_preferences": "digest email link; logs the user in, then redirects",
}

GET_REACHABLE_ENDPOINTS = READ_ONLY_ENDPOINTS | frozenset(DELIBERATE_GET_MUTATIONS)

# A floor on what the AST walk must find, so a walker that silently stops matching
# decorators fails loudly instead of vacuously passing every assertion below.
MINIMUM_DISCOVERED_ENDPOINTS = 70


def _whitelisted_qualnames(tree: ast.Module) -> list[list[str]]:
	"""Dotted name parts of every whitelisted function in a parsed module.

	A walk rather than a regex so a decorator inside a class body is attributed to that
	class (`GPDiscussion.close_discussion`), and so a `# @frappe.whitelist()` in a
	comment or docstring cannot be mistaken for one.
	"""
	found: list[list[str]] = []
	scope: list[str] = []

	def visit(node):
		for child in ast.iter_child_nodes(node):
			if isinstance(child, ast.ClassDef):
				scope.append(child.name)
				visit(child)
				scope.pop()
			elif isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef):
				for decorator in child.decorator_list:
					call = decorator.func if isinstance(decorator, ast.Call) else decorator
					if ast.unparse(call).split(".")[-1] in WHITELIST_DECORATOR_NAMES:
						found.append([*scope, child.name])
						break
				scope.append(child.name)
				visit(child)
				scope.pop()
			else:
				visit(child)

	visit(tree)
	return found


def discover_whitelisted_endpoints() -> dict[str, object]:
	"""Every whitelisted function under `gameplan/`, as dotted path -> function object.

	Discovery is static (so nothing can be forgotten) but the returned value is the live
	object, because what Frappe actually enforces is
	`frappe.allowed_http_methods_for_whitelisted_func`, which is keyed by function.
	"""
	package = pathlib.Path(gameplan.__file__).parent
	endpoints = {}
	for path in sorted(package.rglob("*.py")):
		module_name = ".".join(path.relative_to(package.parent).with_suffix("").parts)
		module_name = module_name.removesuffix(".__init__")
		source = path.read_text(encoding="utf-8")
		qualnames = _whitelisted_qualnames(ast.parse(source, str(path)))
		if not qualnames:
			continue
		module = importlib.import_module(module_name)
		for parts in qualnames:
			function = module
			for part in parts:
				function = getattr(function, part)
			endpoints[".".join([module_name, *parts])] = function
	return endpoints


class TestWhitelistedEndpointHttpMethods(FrappeTestCase):
	"""Every whitelisted endpoint must be POST-only unless it is an allowlisted read."""

	def setUp(self):
		super().setUp()
		self.endpoints = discover_whitelisted_endpoints()

	def test_the_endpoint_walk_finds_the_whole_app(self):
		self.assertGreaterEqual(
			len(self.endpoints),
			MINIMUM_DISCOVERED_ENDPOINTS,
			f"Only {len(self.endpoints)} whitelisted endpoints were discovered under "
			f"{pathlib.Path(gameplan.__file__).parent}. The guard below is vacuous if the "
			"walk stops matching decorators — check WHITELIST_DECORATOR_NAMES.",
		)

	def test_every_whitelisted_endpoint_is_post_only(self):
		for endpoint, function in sorted(self.endpoints.items()):
			if endpoint in GET_REACHABLE_ENDPOINTS:
				continue
			with self.subTest(endpoint=endpoint):
				declared = declared_http_methods(function)
				self.assertTrue(
					declared and declared <= UNSAFE_HTTP_METHODS,
					f"{endpoint} declares {sorted(declared)}. Frappe rolls the transaction back at "
					"the end of every GET request, so a mutation reachable by GET runs, saves "
					'without error and is then discarded. Add methods=["POST"] to its '
					"@frappe.whitelist(), or — if it only reads — add it to READ_ONLY_ENDPOINTS.",
				)

	def test_the_get_reachable_allowlists_have_no_stale_entries(self):
		"""A renamed or deleted endpoint must not leave a silent hole in the allowlist."""
		for endpoint in sorted(GET_REACHABLE_ENDPOINTS):
			with self.subTest(endpoint=endpoint):
				self.assertIn(
					endpoint,
					self.endpoints,
					f"{endpoint} is allowlisted as GET-reachable but no longer exists. "
					"Remove the stale entry.",
				)

	def test_the_two_deliberate_get_mutations_are_the_only_ones(self):
		"""Locked down by name: adding a third needs a deliberate edit here, with a reason."""
		self.assertEqual(
			sorted(DELIBERATE_GET_MUTATIONS),
			[
				"gameplan.api.accept_invitation",
				"gameplan.email_digest.open_digest_preferences",
			],
		)


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
