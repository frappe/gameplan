# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""Contracts and access guards for Gameplan's cross-cutting API endpoints."""

import json
from unittest.mock import patch

import frappe
from frappe.utils import add_days, now

from gameplan.api import (
	can_access_gameplan,
	get_search_filter_options,
	get_user_info,
	invite_by_email,
	onboarding,
	search_sqlite,
)
from gameplan.search_sqlite import GameplanSearch
from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import (
	create_comment,
	create_community,
	create_discussion,
	create_member,
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

	def test_the_first_space_is_public_unless_the_signup_asks_for_privacy(self):
		"""Signup omits is_private, and the default decides whether a brand-new
		community's first space is visible to the teammates invited alongside it."""
		with self.as_user(self.member):
			result = onboarding(
				community="API Default Privacy Community",
				space="API Default Privacy Space",
				icon="lucide-users",
				emails="[]",
			)

		self.assertEqual(frappe.db.get_value("GP Project", result["space"], "is_private"), 0)

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


class TestGetUserInfoEndpoint(APIEndpointTestCase):
	"""The member directory the SPA boots from: who exists, who "I" am, and how active.

	The email-visibility split (guests never see other members' addresses) lives in
	`test_members.py`; this class owns the shape of a row.
	"""

	def user_info(self, caller, target):
		with self.as_user(caller):
			rows = get_user_info(target.name)
		self.assertEqual([row.name for row in rows], [target.name])
		return rows[0]

	def test_an_anonymous_caller_reaches_the_endpoint_and_is_told_to_authenticate(self):
		"""Deliberately guest-reachable: the SPA needs the 401 that AuthenticationError
		produces to send the visitor to log in. Closing the whitelist to guests would
		return 403 instead, which the frontend treats as "logged in, but forbidden"."""
		with self.as_user("Guest"):
			frappe.is_whitelisted(get_user_info)

			with self.assertRaises(frappe.AuthenticationError):
				get_user_info()

	def test_reports_the_session_user_and_their_highest_gameplan_role(self):
		info = self.user_info(self.member, self.member)

		self.assertIs(info.session_user, True)
		self.assertEqual(info.role, "Gameplan Member")

	def test_another_member_is_not_reported_as_the_session_user(self):
		info = self.user_info(self.member, self.second_member)

		self.assertNotIn("session_user", info)
		self.assertEqual(info.role, "Gameplan Member")

	def test_a_user_holding_two_gameplan_roles_appears_once_at_the_higher_role(self):
		"""The role filter joins Has Role, so a member later promoted to admin matches
		twice; without deduplication the directory lists them twice."""
		promoted = create_member("api-promoted@example.com", "Promoted Member")
		promoted.add_roles("Gameplan Admin")

		with self.as_user(self.member):
			rows = get_user_info()

		matches = [row for row in rows if row.name == promoted.name]
		self.assertEqual(len(matches), 1)
		self.assertEqual(matches[0].role, "Gameplan Admin")

	def test_an_empty_profile_image_leaves_the_users_own_avatar_alone(self):
		"""Nothing copies User.user_image into GP User Profile.image, so an account that
		only ever set an avatar in Frappe has one and not the other. Overwriting
		unconditionally blanked those users in the app while email digests still drew
		them, so the two renderers disagreed about the same person."""
		framework_avatar = create_member("api-avatar-framework@example.com", "Framework Avatar")
		frappe.db.set_value("User", framework_avatar.name, "user_image", "/files/framework-avatar.png")
		profile = frappe.db.get_value("GP User Profile", {"user": framework_avatar.name})
		frappe.db.set_value("GP User Profile", profile, "image", "")

		info = self.user_info(self.member, framework_avatar)

		self.assertEqual(info.user_image, "/files/framework-avatar.png")

	def test_the_profile_image_wins_when_both_are_set(self):
		"""The profile image is the one Gameplan lets you edit, so the fallback must not
		invert into "whatever Frappe holds beats what the user just uploaded"."""
		both = create_member("api-avatar-both@example.com", "Both Avatars")
		frappe.db.set_value("User", both.name, "user_image", "/files/stale-avatar.png")
		profile = frappe.db.get_value("GP User Profile", {"user": both.name})
		frappe.db.set_value("GP User Profile", profile, "image", "/files/profile-avatar.png")

		info = self.user_info(self.member, both)

		self.assertEqual(info.user_image, "/files/profile-avatar.png")

	def test_counts_the_authors_own_discussions_and_comments(self):
		author = create_member("api-counts-author@example.com", "Counts Author")
		space = create_space("API Counts Space", create_community("API Counts Community"))
		discussion = create_discussion("Counted discussion", space, owner=author)
		create_comment(discussion, owner=author)

		info = self.user_info(self.member, author)

		self.assertEqual(info.discussions_count_3m, 1)
		self.assertEqual(info.comments_count_3m, 1)

	def test_a_user_with_no_activity_counts_zero(self):
		quiet = create_member("api-counts-quiet@example.com", "Quiet Member")

		info = self.user_info(self.member, quiet)

		self.assertEqual(info.discussions_count_3m, 0)
		self.assertEqual(info.comments_count_3m, 0)

	def test_activity_older_than_three_months_is_left_out(self):
		"""The two counts are labelled "3m" in the profile; widening the window silently
		would restate a dormant account as an active one."""
		author = create_member("api-counts-stale@example.com", "Stale Author")
		space = create_space("API Stale Space", create_community("API Stale Community"))
		discussion = create_discussion("Stale discussion", space, owner=author)
		comment = create_comment(discussion, owner=author)
		# 100 days is outside a 3-month window but inside a 4-month one, so an off-by-one
		# on the window boundary changes both counts.
		long_ago = add_days(now(), -100)
		frappe.db.set_value("GP Discussion", discussion.name, "creation", long_ago, update_modified=False)
		frappe.db.set_value("GP Comment", comment.name, "creation", long_ago, update_modified=False)

		info = self.user_info(self.member, author)

		self.assertEqual(info.discussions_count_3m, 0)
		self.assertEqual(info.comments_count_3m, 0)


class TestInviteByEmailEndpoint(APIEndpointTestCase):
	"""The admin gate and role allowlist are covered in `test_members.py`, and the
	de-duplication rules in `test_invitations.py`; what is left — and what nothing else
	asserts — is that an authorized invite actually creates the invitations."""

	def setUp(self):
		super().setUp()
		# GP Invitation.after_insert emails the invitee; a bare dev site has no outgoing
		# account and raises, so mute the send for the whole case.
		sendmail = patch("frappe.sendmail")
		sendmail.start()
		self.addCleanup(sendmail.stop)

	def test_an_admin_invite_creates_an_invitation_per_address(self):
		emails = ["api-invitee-one@example.com", "api-invitee-two@example.com"]

		with self.as_user(self.admin):
			invite_by_email(", ".join(emails), role="Gameplan Member")

		for email in emails:
			with self.subTest(email=email):
				self.assertTrue(
					frappe.db.exists("GP Invitation", {"email": email, "role": "Gameplan Member"})
				)

	def test_an_unparseable_address_is_dropped_instead_of_failing_the_whole_invite(self):
		"""Admins paste address lists; one typo must not discard the other invites."""
		with self.as_user(self.admin):
			invite_by_email("api-invitee-valid@example.com, not-an-email", role="Gameplan Member")

		self.assertTrue(frappe.db.exists("GP Invitation", {"email": "api-invitee-valid@example.com"}))
		self.assertFalse(frappe.db.exists("GP Invitation", {"email": "not-an-email"}))


class TestSearchEndpoint(IsolatedSearchIndex, APIEndpointTestCase):
	INDEX_NAME = "test_gameplan_search_api_endpoint.db"

	def setUp(self):
		super().setUp()
		# Must happen before the first indexable document: the doc_event hook builds a
		# fresh GameplanSearch, which resolves db_path from INDEX_NAME at construction.
		self.isolate_search_index()
		self.search = GameplanSearch()
		self.search.drop_index()

	def test_filters_are_accepted_as_json_and_as_an_already_parsed_object(self):
		"""Both call shapes are real: a query-string caller sends the filters as a JSON
		string, while a JSON request body arrives already parsed as a dict."""
		community = create_community("API Search Community")
		space = create_space("API Search Space", community)
		create_discussion("Search endpoint coverage", space, content="apisearchneedle", owner=self.member)
		self.search.build_index()
		filters = {"project": [str(space.name)]}

		with self.as_user(self.member):
			from_object = search_sqlite("apisearchneedle", filters=filters)
			from_json = search_sqlite("apisearchneedle", filters=json.dumps(filters))

		self.assertTrue(from_object["results"])
		self.assertEqual(
			[result["id"] for result in from_object["results"]],
			[result["id"] for result in from_json["results"]],
		)

	def test_anonymous_caller_is_denied(self):
		self.assert_anonymous_denied(search_sqlite)
