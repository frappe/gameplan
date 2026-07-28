# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""Contracts and access guards for Gameplan's cross-cutting API endpoints."""

import frappe

from gameplan.api import can_access_gameplan, get_search_filter_options, onboarding
from gameplan.search_sqlite import GameplanSearch
from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import (
	create_community,
	create_discussion,
	create_space,
	create_user,
	declared_http_methods,
)
from gameplan.tests.search_isolation import IsolatedSearchIndex
from gameplan.ui_test_helpers import create_invitation, rebuild_search_index, reset

EMPTY_FILTER_OPTIONS = {
	"authors": {},
	"projects": {},
	"teams": {},
	"doctypes": {},
	"tags": {},
}


class APIEndpointTestCase(GameplanTestCase):
	def assert_anonymous_denied(self, endpoint):
		"""Assert the public Frappe boundary rejects an unauthenticated caller."""
		with self.as_user("Guest"), self.assertRaises(frappe.PermissionError):
			frappe.is_whitelisted(endpoint)


class TestUITestHelperHTTPMethods(GameplanTestCase):
	def test_ui_test_mutations_are_post_only(self):
		for endpoint in (reset, rebuild_search_index, create_invitation):
			self.assertEqual(declared_http_methods(endpoint), {"POST"})


class TestOnboardingEndpoint(APIEndpointTestCase):
	def test_returns_the_created_community_and_space_route_identifiers(self):
		with self.as_user(self.member):
			result = onboarding(
				community="API Onboarding Community",
				space="API Onboarding Space",
				icon="lucide-users",
				emails="[]",
				is_private=1,
			)

		self.assertEqual(set(result), {"team", "space"})

		community = frappe.get_doc("GP Team", result["team"])
		space = frappe.get_doc("GP Project", result["space"])
		self.assertEqual(community.title, "API Onboarding Community")
		self.assertIsNotNone(community.get_member(self.member.name))
		self.assertEqual(space.title, "API Onboarding Space")
		self.assertEqual(space.team, community.name)
		self.assertEqual(space.icon, "lucide-users")
		self.assertEqual(space.is_private, 1)

	def test_anonymous_caller_is_denied(self):
		self.assert_anonymous_denied(onboarding)

	def test_authenticated_user_without_a_gameplan_role_is_denied(self):
		roleless_user = create_user("api-onboarding-roleless@example.com", "Roleless")

		with (
			self.as_user(roleless_user),
			self.assertRaises(frappe.PermissionError),
		):
			onboarding(
				community="Forbidden API Community",
				space="Forbidden API Space",
				icon="users",
				emails="[]",
			)

		self.assertFalse(frappe.db.exists("GP Team", {"title": "Forbidden API Community"}))


class TestSearchFilterOptionsEndpoint(IsolatedSearchIndex, APIEndpointTestCase):
	INDEX_NAME = "test_gameplan_search_filter_options.db"

	def setUp(self):
		super().setUp()
		# Must happen before the first indexable document: the doc_event hook builds a
		# fresh GameplanSearch, which resolves db_path from INDEX_NAME at construction.
		self.isolate_search_index()
		self.search = GameplanSearch()
		self.search.drop_index()

	def test_filter_options_use_an_isolated_database(self):
		self.assert_uses_isolated_index(self.search)

	def test_returns_a_stable_empty_contract_without_an_index(self):
		with self.as_user(self.member):
			result = get_search_filter_options()

		self.assertEqual(result, EMPTY_FILTER_OPTIONS)

	def test_returns_only_options_from_spaces_the_user_can_access(self):
		visible_user = create_user(
			"api-filter-visible@example.com", "Visible Filter Author", "Gameplan Member"
		)
		hidden_user = create_user("api-filter-hidden@example.com", "Hidden Filter Author", "Gameplan Member")
		visible_community = create_community(
			"API Visible Filter Community", is_private=1, members=[visible_user]
		)
		hidden_community = create_community(
			"API Hidden Filter Community", is_private=1, members=[hidden_user]
		)
		visible_space = create_space(
			"API Visible Filter Space", visible_community, is_private=1, members=[visible_user]
		)
		hidden_space = create_space(
			"API Hidden Filter Space", hidden_community, is_private=1, members=[hidden_user]
		)
		visible_tag = "api-visible-filter-tag"
		hidden_tag = "api-hidden-filter-tag"
		create_discussion(
			"Visible filter result",
			visible_space,
			content=f'<p><span class="tag-item" data-tag-label="{visible_tag}">#{visible_tag}</span></p>',
			owner=visible_user,
		)
		create_discussion(
			"Hidden filter result",
			hidden_space,
			content=f'<p><span class="tag-item" data-tag-label="{hidden_tag}">#{hidden_tag}</span></p>',
			owner=hidden_user,
		)
		self.search.build_index()

		with self.as_user(visible_user):
			result = get_search_filter_options()

		self.assertEqual(set(result), set(EMPTY_FILTER_OPTIONS))
		project_counts = {str(project): count for project, count in result["projects"].items()}
		self.assertEqual(result["authors"][visible_user.name], 1)
		self.assertEqual(project_counts[str(visible_space.name)], 1)
		self.assertEqual(result["teams"][visible_community.name], 1)
		self.assertGreaterEqual(result["doctypes"]["GP Discussion"], 1)
		self.assertEqual(result["tags"][visible_tag], 1)
		self.assertNotIn(hidden_user.name, result["authors"])
		self.assertNotIn(str(hidden_space.name), project_counts)
		self.assertNotIn(hidden_community.name, result["teams"])
		self.assertNotIn(hidden_tag, result["tags"])

	def test_anonymous_caller_is_denied(self):
		self.assert_anonymous_denied(get_search_filter_options)


class TestCanAccessGameplan(APIEndpointTestCase):
	def test_administrator_can_access_without_a_gameplan_role(self):
		with self.as_user("Administrator"):
			result = can_access_gameplan()

		self.assertIs(result, True)

	def test_each_allowed_role_can_access(self):
		system_manager = create_user("api-system-manager@example.com", "System Manager", "System Manager")

		for user in (system_manager, self.admin, self.member, self.guest):
			with self.subTest(user=user.name), self.as_user(user):
				self.assertIs(can_access_gameplan(), True)

	def test_anonymous_caller_cannot_access(self):
		with self.as_user("Guest"):
			result = can_access_gameplan()

		self.assertIs(result, False)

	def test_user_without_an_allowed_role_cannot_access(self):
		roleless_user = create_user("api-roleless@example.com", "Roleless")

		with self.as_user(roleless_user):
			result = can_access_gameplan()

		self.assertIs(result, False)

	def test_user_cannot_access_when_the_gameplan_module_is_blocked(self):
		user = frappe.get_doc("User", self.member.name)
		self.addCleanup(frappe.clear_document_cache, "User", user.name)
		user.append("block_modules", {"module": "Gameplan"})
		user.save(ignore_permissions=True)
		frappe.clear_document_cache("User", user.name)

		with self.as_user(user):
			result = can_access_gameplan()

		self.assertIs(result, False)
