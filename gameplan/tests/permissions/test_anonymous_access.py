# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""Anonymous visitors: requests from someone who is not signed in at all.

Not Gameplan Guests. A Gameplan Guest is a signed-in outside collaborator, and
`gameplan.is_guest()` returns False for a request with nobody signed in. The permission
predicates in gameplan/permissions.py test is_guest() and then fall through to the member
rules, so before the Anonymous tier existed they would have treated an anonymous visitor
like a signed-in member: a space that is not private would read as visible.

The role layer grants the `Guest` role read access to exactly the doctypes a public thread
needs, and nothing else. TestRoleLayer pins that list and what it may grant.
TestDefaultsStayInvisible pins the outcome that matters most: content created with today's
defaults stays out of reach of anonymous visitors on every read path, whether or not public
access is switched on. TestGuestReachableEndpoints pins every endpoint a request with nobody
signed in can reach.
"""

from unittest.mock import patch

import frappe

import gameplan
from gameplan import api, command_palette
from gameplan.extends.client import get_list as get_client_list
from gameplan.gameplan.doctype.gp_discussion.api import get_discussions
from gameplan.public_access import PUBLIC_ACCESS_CONFIG_KEY, public_access_enabled
from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import (
	create_comment,
	create_community,
	create_discussion,
	create_poll,
	create_space,
)
from gameplan.tests.test_get_request_transactions import discover_whitelisted_endpoints

ANONYMOUS = "Guest"

# Doctypes that may grant the `Guest` role read access, and the only rights they may grant.
# The minimum a public thread needs. Anything here must also be scoped for anonymous
# visitors in both `permission_query_conditions` and `has_permission` in hooks.py: a
# has_permission hook alone gates opening one row, not listing all of them.
ANONYMOUS_READABLE_DOCTYPES = frozenset({"GP Team", "GP Project", "GP Discussion", "GP Comment", "GP Poll"})
ANONYMOUS_RIGHTS = frozenset({"read", "select"})

# Every whitelisted endpoint a request with nobody signed in can reach, and why.
GUEST_REACHABLE_ENDPOINTS = {
	"gameplan.api.get_user_info": "throws AuthenticationError for an anonymous caller first",
	"gameplan.api.accept_invitation": "invitation email link, opened by a plain browser navigation",
	"gameplan.email_digest.open_digest_preferences": "digest email link; signs the user in",
	"gameplan.www.g.get_context_for_dev": "throws unless developer_mode",
	"gameplan.extends.client.get_list": "the SPA's list endpoint; rows scoped by permission_query_conditions",
	"gameplan.gameplan.doctype.gp_discussion.api.get_discussions": "the feed; filtered to readable spaces",
	"gameplan.api.get_public_user_info": "name and avatar of authors of public content only",
	"gameplan.public_access.realtime_has_permission": "frappe's socket permission check, minus doctype rooms",
}

# Every right a DocPerm row can carry.
DOCPERM_RIGHTS = (
	"select",
	"read",
	"write",
	"create",
	"delete",
	"submit",
	"cancel",
	"amend",
	"report",
	"export",
	"import",
	"share",
	"print",
	"email",
)


class TestIsAnonymous(GameplanTestCase):
	def test_only_a_request_with_nobody_signed_in_is_anonymous(self):
		self.assertTrue(gameplan.is_anonymous(ANONYMOUS))

		for user in (self.admin.name, self.member.name, self.guest.name, "Administrator"):
			self.assertFalse(gameplan.is_anonymous(user), user)

	def test_is_guest_does_not_cover_anonymous_visitors(self):
		# The gap is_anonymous() exists for: is_guest() is about a role, and a request with
		# nobody signed in holds no Gameplan role.
		self.assertFalse(gameplan.is_guest(ANONYMOUS))
		self.assertTrue(gameplan.is_guest(self.guest.name))
		self.assertFalse(gameplan.is_anonymous(self.guest.name))

	def test_it_reads_the_session_user_by_default(self):
		with self.as_user(ANONYMOUS):
			self.assertTrue(gameplan.is_anonymous())

		with self.as_user(self.member):
			self.assertFalse(gameplan.is_anonymous())


class TestPublicAccessSwitch(GameplanTestCase):
	def test_it_is_off_by_default(self):
		with patch.dict(frappe.conf):
			frappe.conf.pop(PUBLIC_ACCESS_CONFIG_KEY, None)
			self.assertFalse(public_access_enabled())

	def test_site_config_turns_it_on_and_off(self):
		with patch.dict(frappe.conf, {PUBLIC_ACCESS_CONFIG_KEY: 1}):
			self.assertTrue(public_access_enabled())

		with patch.dict(frappe.conf, {PUBLIC_ACCESS_CONFIG_KEY: 0}):
			self.assertFalse(public_access_enabled())

	def test_demo_mode_keeps_it_off(self):
		# `?demo` on a demo site signs the visitor in as a real demo user, so a public reader
		# would become a member partway through a visit.
		with patch.dict(frappe.conf, {PUBLIC_ACCESS_CONFIG_KEY: 1, "gameplan_demo_enabled": 1}):
			self.assertFalse(public_access_enabled())


class TestRoleLayer(GameplanTestCase):
	def test_no_gameplan_doctype_grants_more_to_anonymous_visitors_than_allowed(self):
		doctypes = frappe.get_all("DocType", filters={"module": "Gameplan"}, pluck="name")
		self.assertTrue(doctypes)

		for doctype in doctypes:
			for perm in frappe.get_meta(doctype).permissions:
				if perm.role != ANONYMOUS:
					continue
				self.assertIn(
					doctype,
					ANONYMOUS_READABLE_DOCTYPES,
					f"{doctype} grants the Guest role access, which reaches people who are not signed in",
				)
				granted = {right for right in DOCPERM_RIGHTS if perm.get(right)}
				self.assertLessEqual(
					granted, ANONYMOUS_RIGHTS, f"{doctype} grants the Guest role {sorted(granted)}"
				)

	def test_every_anonymously_readable_doctype_is_scoped_for_lists_and_documents(self):
		query_conditions = frappe.get_hooks("permission_query_conditions", {})
		has_permission = frappe.get_hooks("has_permission", {})
		for doctype in ANONYMOUS_READABLE_DOCTYPES:
			with self.subTest(doctype=doctype):
				self.assertIn(doctype, query_conditions)
				self.assertIn(doctype, has_permission)
				self.assertTrue(
					any(perm.role == ANONYMOUS and perm.read for perm in frappe.get_meta(doctype).permissions)
				)


class TestGuestReachableEndpoints(GameplanTestCase):
	def test_only_the_listed_endpoints_answer_a_request_with_nobody_signed_in(self):
		reachable = {
			path
			for path, endpoint in discover_whitelisted_endpoints().items()
			if endpoint in frappe.guest_methods
		}

		self.assertEqual(reachable, set(GUEST_REACHABLE_ENDPOINTS))


class TestDefaultsStayInvisible(GameplanTestCase):
	"""Content created with today's defaults is unreachable for anonymous visitors.

	The community and space are neither private nor anything else: exactly what
	GPTeam.create_general_space and onboarding produce, and so what most content on a
	deployed site lives in.
	"""

	def setUp(self):
		super().setUp()
		self.community = create_community("Default Community", members=[self.member])
		self.space = create_space("Default Space", self.community, members=[self.member])
		self.discussion = create_discussion("Default Discussion", self.space, owner=self.member)
		self.comment = create_comment(self.discussion, owner=self.member)
		self.poll = create_poll("Default Poll", self.discussion, owner=self.member)
		self.content = (self.community, self.space, self.discussion, self.comment, self.poll)

	def test_no_single_document_can_be_read(self):
		for switch_on in (0, 1):
			with patch.dict(frappe.conf, {PUBLIC_ACCESS_CONFIG_KEY: switch_on}):
				for doc in self.content:
					with self.subTest(switch=switch_on, doctype=doc.doctype):
						self.assert_not_allowed(doc, "read", ANONYMOUS)

	def test_no_list_shows_them(self):
		for switch_on in (0, 1):
			with patch.dict(frappe.conf, {PUBLIC_ACCESS_CONFIG_KEY: switch_on}), self.as_user(ANONYMOUS):
				for doc in self.content:
					with self.subTest(switch=switch_on, doctype=doc.doctype):
						self.assertNotIn(
							doc.name, frappe.get_list(doc.doctype, pluck="name", limit_page_length=0)
						)
						listed = get_client_list(doctype=doc.doctype, fields=["name"], limit=0)
						self.assertNotIn(str(doc.name), {str(row.name) for row in listed})
				with self.subTest(switch=switch_on, endpoint="get_discussions"):
					self.assertNotIn(self.discussion.name, [row.name for row in get_discussions(limit=50)])

	def test_search_still_requires_a_signed_in_user(self):
		# Search reads its own index and never asks the role layer, and its index holds
		# tasks and pages too, so the whitelist decorator is what refuses an anonymous request.
		with self.as_user(ANONYMOUS):
			for endpoint in (api.search_sqlite, command_palette.search_sqlite):
				with self.assertRaises(frappe.PermissionError, msg=endpoint.__qualname__):
					frappe.is_whitelisted(endpoint)
