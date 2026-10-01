# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""Hardening around public access: rate limits, robots.txt and the pre-flight audit."""

import itertools
from unittest.mock import patch

import frappe
from werkzeug.test import EnvironBuilder
from werkzeug.wrappers import Request

from gameplan.public_access import (
	ANONYMOUS_RATE_LIMITS,
	PUBLIC_ACCESS_CONFIG_KEY,
	VISIBILITY_ANONYMOUS,
	VISIBILITY_MEMBER_ACCESS,
	audit_public_access,
	gameplan_robots_rules,
	limit_anonymous_request_rate,
	public_access_audit,
)
from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import create_community, create_discussion, create_space
from gameplan.tests.permissions.test_anonymous_access import GUEST_REACHABLE_ENDPOINTS

ANONYMOUS = "Guest"
# Guest-reachable endpoints that are not public reads, so are not rate limited here.
NOT_RATE_LIMITED = {
	"gameplan.api.get_user_info": "refuses anonymous callers outright",
	"gameplan.api.accept_invitation": "an invitation link; frappe's login limits cover it",
	"gameplan.email_digest.open_digest_preferences": "a signed link from a digest email",
	"gameplan.www.g.get_context_for_dev": "refuses unless developer_mode",
	"gameplan.public_access.realtime_has_permission": (
		"called by the socket server, from its own address, for every socket at once"
	),
}
_ips = (f"203.0.113.{n}" for n in itertools.count(1))


def switched(on=True):
	return patch.dict(frappe.conf, {PUBLIC_ACCESS_CONFIG_KEY: 1 if on else 0})


class TestRateLimits(GameplanTestCase):
	def setUp(self):
		super().setUp()
		# A fresh address per test, so no bucket carries over between tests.
		self.ip = next(_ips)

	def request(self, path, *, user=ANONYMOUS, ip=None, method="GET"):
		request = Request(EnvironBuilder(path=path, method=method).get_environ())
		with (
			patch.object(frappe.local, "request", request, create=True),
			patch.object(frappe.local, "request_ip", ip or self.ip, create=True),
			self.as_user(user),
		):
			limit_anonymous_request_rate()

	def limited_to(self, limit, key="gameplan.api.public_file"):
		return patch.dict(ANONYMOUS_RATE_LIMITS, {key: limit})

	def test_the_limiter_is_registered(self):
		self.assertIn(
			"gameplan.public_access.limit_anonymous_request_rate", frappe.get_hooks("before_request")
		)

	def test_an_address_is_stopped_after_its_limit(self):
		with self.limited_to(3):
			for _ in range(3):
				self.request("/api/method/gameplan.api.public_file")
			with self.assertRaises(frappe.RateLimitExceededError):
				self.request("/api/v2/method/gameplan.api.public_file")

	def test_each_address_and_endpoint_has_its_own_count(self):
		with self.limited_to(2), self.limited_to(2, "gameplan.public_lists.comments"):
			for _ in range(2):
				self.request("/api/method/gameplan.api.public_file")
			self.request("/api/method/gameplan.api.public_file", ip=next(_ips))
			self.request("/api/v2/method/gameplan.public_lists.comments")

	def test_reading_a_document_counts_too(self):
		with self.limited_to(1, "document"):
			self.request("/api/v2/document/GP Discussion/1")
			with self.assertRaises(frappe.RateLimitExceededError):
				self.request("/api/v2/document/GP Comment/1")

	def test_signed_in_users_are_never_limited(self):
		with self.limited_to(1):
			for _ in range(5):
				self.request("/api/method/gameplan.api.public_file", user=self.member.name)

	def test_unlisted_endpoints_are_left_to_frappe(self):
		with self.limited_to(0):
			for _ in range(5):
				self.request("/api/method/login", method="POST")
				self.request("/g/community/x/space/1/discussions")

	def test_every_public_read_endpoint_is_limited(self):
		reads = set(GUEST_REACHABLE_ENDPOINTS) - set(NOT_RATE_LIMITED)
		self.assertLessEqual(reads, set(ANONYMOUS_RATE_LIMITS), "add a rate limit for each new public read")
		self.assertLessEqual(set(ANONYMOUS_RATE_LIMITS) - {"document"}, set(GUEST_REACHABLE_ENDPOINTS))


class TestRobots(GameplanTestCase):
	def setUp(self):
		super().setUp()
		community = create_community("Robots Community", visibility=VISIBILITY_ANONYMOUS)
		self.public_space = create_space("Robots Public", community, visibility=VISIBILITY_ANONYMOUS)
		self.general_space = create_space("Robots General", community)
		self.allow = f"Allow: /g/community/{community.name}/space/{self.public_space.name}/"

	def test_public_spaces_are_allowed_and_the_rest_of_the_app_is_not(self):
		with switched():
			lines = gameplan_robots_rules().splitlines()
		self.assertIn(self.allow, lines)
		self.assertFalse(any(f"/space/{self.general_space.name}/" in line for line in lines))
		self.assertEqual(lines[-1], "Disallow: /g/")
		self.assertLess(lines.index(self.allow), lines.index("Disallow: /g/"))

	def test_switched_off_nothing_is_allowed(self):
		with switched(False):
			self.assertNotIn("Allow:", gameplan_robots_rules())

	def test_a_space_leaving_anonymous_leaves_robots_txt(self):
		self.public_space.set_visibility(VISIBILITY_MEMBER_ACCESS)
		with switched():
			self.assertNotIn(self.allow, gameplan_robots_rules())

	def test_the_site_own_rules_are_kept(self):
		from gameplan.www.robots import get_context

		with patch.object(frappe.db, "get_single_value", return_value="User-agent: *\nDisallow: /private/"):
			robots_txt = get_context(frappe._dict())["robots_txt"]
		self.assertTrue(robots_txt.startswith("User-agent: *\nDisallow: /private/"))
		self.assertIn("Disallow: /g/", robots_txt)


class TestAudit(GameplanTestCase):
	def setUp(self):
		super().setUp()
		community = create_community("Audit Community", visibility=VISIBILITY_ANONYMOUS)
		self.public_space = create_space("Audit Public", community, visibility=VISIBILITY_ANONYMOUS)
		self.general_space = create_space("Audit General", community)
		create_discussion("Audit Discussion", self.public_space)

	def signup_role(self, role):
		frappe.db.set_single_value("Portal Settings", "default_role", role)

	def test_it_lists_what_is_public_and_who_set_it(self):
		with switched():
			report = public_access_audit()
		spaces = {space.name: space for space in report.spaces}
		self.assertEqual(spaces[self.public_space.name].public_discussions, 1)
		self.assertEqual(spaces[self.general_space.name].public_discussions, 0)
		self.assertEqual(spaces[self.public_space.name].visibility_set_by, "Administrator")
		self.assertTrue(report.public_access_enabled)

	def test_a_signup_role_that_reads_general_spaces_is_a_problem(self):
		for role in ("Gameplan Member", "Gameplan Admin", "System Manager"):
			with self.subTest(role=role):
				self.signup_role(role)
				self.assertTrue(any(role in problem for problem in public_access_audit().problems))
		self.signup_role("Gameplan Guest")
		self.assertEqual(public_access_audit().problems, [])

	def test_a_stale_public_flag_is_a_problem(self):
		frappe.db.set_value("GP Project", self.general_space.name, "is_anonymous_readable", 1)
		problems = public_access_audit().problems
		self.assertTrue(any(str(self.general_space.name) in problem for problem in problems))

	def test_the_command_fails_on_a_problem(self):
		self.signup_role("Gameplan Member")
		with patch("builtins.print"), self.assertRaises(frappe.ValidationError):
			audit_public_access()
		self.signup_role("")
		with patch("builtins.print") as printed:
			audit_public_access()
		self.assertIn("No problems found", str(printed.call_args_list[-1]))
