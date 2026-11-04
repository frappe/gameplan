from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

import frappe
from frappe.tests.test_api import FrappeAPITestCase
from frappe.utils import now_datetime

from gameplan.community_bans import is_banned, set_ban
from gameplan.restriction_queries import account_history, account_suspensions, candidates, my_bans
from gameplan.restrictions import (
	active,
	expire_due,
	expiry_from_iso,
	iso_expiry,
	require_not_suspended,
	set_restriction,
	state,
	utc_now,
)
from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import create_community


class TestTimedRestrictions(GameplanTestCase):
	def setUp(self):
		super().setUp()
		self.enterContext(patch("frappe.enqueue"))
		self.community = create_community("Timed bans", admins=[self.member], members=[self.outsider])

	def ban(self, **kwargs):
		return set_restriction(self.outsider.name, 1, "Repeated spam", self.community.name, **kwargs)

	def suspend(self, **kwargs):
		return set_restriction(self.outsider.name, 1, "Account abuse", **kwargs)

	def expire(self, community=""):
		row = state(self.outsider.name, community)
		frappe.db.set_value("GP User Restriction", row.name, "expires_at", utc_now() - timedelta(seconds=1))
		frappe.local.request_cache.clear()

	def test_community_expiry_applies_without_running_cleanup(self):
		self.ban(duration_seconds=3600)
		self.assertTrue(is_banned(self.community.name, self.outsider.name))
		self.expire(self.community.name)
		self.assertFalse(is_banned(self.community.name, self.outsider.name))
		self.assertTrue(state(self.outsider.name, self.community.name).active)
		with self.as_user(self.outsider):
			self.assertEqual(my_bans(), [])

	def test_suspension_blocks_login_session_and_token_auth_guard(self):
		self.suspend(duration_seconds=86400)
		with self.assertRaises(frappe.AuthenticationError):
			require_not_suspended(SimpleNamespace(user=self.outsider.name))
		with self.as_user(self.outsider), self.assertRaises(frappe.AuthenticationError):
			require_not_suspended()
		self.assertEqual(frappe.db.get_value("User", self.outsider.name, "enabled"), 1)

	def test_expiry_does_not_enable_independently_disabled_account(self):
		self.suspend(duration_seconds=3600)
		frappe.db.set_value("User", self.outsider.name, "enabled", 0)
		self.expire()
		require_not_suspended(SimpleNamespace(user=self.outsider.name))
		self.assertEqual(frappe.db.get_value("User", self.outsider.name, "enabled"), 0)

	def test_expiry_is_recorded_once_with_original_deadline(self):
		self.ban(duration_seconds=3600)
		self.expire(self.community.name)
		deadline = state(self.outsider.name, self.community.name).expires_at
		expire_due()
		expire_due()
		logs = frappe.get_all(
			"GP Moderation Log",
			filters={
				"community": self.community.name,
				"user": self.outsider.name,
				"action": "Restriction Expired",
			},
			fields=["expires_at"],
		)
		self.assertEqual(len(logs), 1)
		self.assertEqual(str(logs[0].expires_at), str(deadline))

	def test_stale_changes_are_rejected_and_lifting_requires_a_reason(self):
		original = self.ban()
		self.ban(duration_seconds=3600, expected_modified=original["modified"])
		with self.assertRaises(frappe.TimestampMismatchError):
			self.ban(expected_modified=original["modified"])
		with self.assertRaises(frappe.ValidationError):
			set_ban(self.community.name, self.outsider.name, 0)
		set_ban(self.community.name, self.outsider.name, 0, "Appeal accepted")
		self.assertFalse(is_banned(self.community.name, self.outsider.name))

	def test_indefinite_ban_can_change_expiry_without_duplicate_action(self):
		self.ban()
		self.ban()
		self.assertEqual(
			frappe.db.count(
				"GP Moderation Log", {"community": self.community.name, "user": self.outsider.name}
			),
			1,
		)
		self.ban(duration_seconds=3600)
		self.assertEqual(
			frappe.db.count(
				"GP Moderation Log",
				{"community": self.community.name, "user": self.outsider.name, "action": "Ban Changed"},
			),
			1,
		)

	def test_scope_and_staff_protections(self):
		with self.as_user(self.member):
			self.ban()
			for operation in (
				self.suspend,
				account_suspensions,
				candidates,
				lambda: account_history(self.outsider.name),
			):
				with self.assertRaises(frappe.PermissionError):
					operation()
		for user in ("Administrator", self.admin.name):
			with self.assertRaises(frappe.ValidationError):
				set_restriction(user, 1, "Protected account")
		with self.as_user(self.outsider), self.assertRaises(frappe.PermissionError):
			self.ban()

	def test_user_feedback_does_not_include_other_users_reasons(self):
		self.ban(duration_seconds=3600)
		with self.as_user(self.outsider):
			self.assertEqual(my_bans()[0].reason, "Repeated spam")
		with self.as_user(self.member):
			self.assertEqual(my_bans(), [])

	def test_current_state_cannot_be_forged_by_generic_document_save(self):
		self.ban()
		doc = frappe.get_doc("GP User Restriction", state(self.outsider.name, self.community.name).name)
		doc.active = 0
		with self.assertRaises(frappe.PermissionError):
			doc.save(ignore_permissions=True)

	def test_timezone_offsets_represent_the_same_instant(self):
		with patch("gameplan.restrictions.utc_now", return_value=now_datetime() - timedelta(days=3650)):
			self.assertEqual(
				expiry_from_iso("2026-11-03T15:30:00+05:30"), expiry_from_iso("2026-11-03T10:00:00Z")
			)
			self.assertEqual(
				expiry_from_iso("2026-11-03T10:00:00Z"),
				expiry_from_iso(iso_expiry(expiry_from_iso("2026-11-03T10:00:00Z"))),
			)
		with self.assertRaises(frappe.ValidationError):
			expiry_from_iso("2099-01-01T10:00:00")

	def test_suspension_queries_return_current_state_without_history_scan(self):
		self.suspend()
		with patch("gameplan.moderation_logs.latest_logs", side_effect=AssertionError("History scan")):
			self.assertTrue(active(state(self.outsider.name)))
			self.assertEqual(account_suspensions()["items"][0].user, self.outsider.name)
			self.assertNotIn(self.outsider.name, [row.name for row in candidates()["items"]])
		self.assertEqual(account_history(self.outsider.name)["items"][0].action, "Suspend")

	def test_email_is_enqueued_only_after_commit(self):
		with patch("frappe.enqueue") as enqueue:
			self.ban()
			self.assertTrue(enqueue.call_args.kwargs["enqueue_after_commit"])

	def test_legacy_bans_backfill_idempotently_without_overwriting_new_state(self):
		from gameplan.patches.backfill_user_restrictions import execute

		frappe.get_doc(
			doctype="GP Moderation Log",
			user=self.outsider.name,
			community=self.community.name,
			action="Ban",
			reason="Legacy ban",
		).insert(ignore_permissions=True)
		execute()
		execute()
		self.assertTrue(is_banned(self.community.name, self.outsider.name))
		self.assertIsNone(state(self.outsider.name, self.community.name).expires_at)
		self.ban(duration_seconds=3600)
		deadline = state(self.outsider.name, self.community.name).expires_at
		execute()
		self.assertEqual(state(self.outsider.name, self.community.name).expires_at, deadline)

	def test_presets_are_elapsed_time_and_independent_of_site_timezone(self):
		from datetime import datetime

		instant = datetime(2026, 11, 1, 5, 30)
		with patch("gameplan.restrictions.utc_now", return_value=instant):
			self.ban(duration_seconds=86400)
		self.assertEqual(
			state(self.outsider.name, self.community.name).expires_at, instant + timedelta(hours=24)
		)
		with patch("gameplan.restrictions.utc_now", return_value=datetime(2026, 1, 1)):
			self.assertEqual(
				expiry_from_iso("2026-11-01T01:30:00-04:00") + timedelta(hours=1),
				expiry_from_iso("2026-11-01T01:30:00-05:00"),
			)

	def test_expiry_cleanup_is_bounded_and_continues_large_batches(self):
		from gameplan.restrictions import restriction_name

		for index in range(102):
			community = f"expiry-batch-{index}"
			frappe.get_doc(
				doctype="GP User Restriction",
				name=restriction_name(self.outsider.name, community),
				user=self.outsider.name,
				community=community,
				active=1,
				expires_at=utc_now() - timedelta(seconds=1),
				reason="Batch expiry",
			).db_insert()
		with patch("frappe.enqueue") as enqueue:
			expire_due()
			self.assertEqual(
				frappe.db.count("GP User Restriction", {"user": self.outsider.name, "active": 1}), 2
			)
			enqueue.assert_called_once_with(expire_due, queue="long", enqueue_after_commit=True)
		expire_due()
		self.assertEqual(frappe.db.count("GP User Restriction", {"user": self.outsider.name, "active": 1}), 0)


class TestRestrictionHTTP(FrappeAPITestCase):
	def setUp(self):
		from frappe.auth import CookieManager, LoginManager
		from frappe.utils import get_test_client, set_request
		from frappe.utils.password import set_encrypted_password, update_password

		from gameplan.tests.fixtures import create_member

		frappe.set_user("Administrator")
		self.TEST_CLIENT = get_test_client()
		self.user = create_member(
			f"suspension-{frappe.generate_hash(length=8)}@example.test", "Suspension HTTP"
		)
		self.addCleanup(self.cleanup_user)
		self.key = frappe.generate_hash(length=20)
		frappe.db.set_value("User", self.user.name, "api_key", self.key)
		set_encrypted_password("User", self.user.name, "suspension-test-secret", "api_secret")
		update_password(self.user.name, "TestSuspension2026!")
		set_request(path="/")
		frappe.local.cookie_manager = CookieManager()
		frappe.local.login_manager = LoginManager()
		frappe.local.login_manager.login_as(self.user.name)
		self.TEST_CLIENT.set_cookie(key="sid", value=frappe.session.sid)
		frappe.set_user("Administrator")
		frappe.db.commit()

	def cleanup_user(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()
		frappe.db.delete("GP Moderation Log", {"user": self.user.name})
		frappe.delete_doc("User", self.user.name, ignore_permissions=True, force=True)
		frappe.db.commit()

	def test_cookie_api_key_and_password_login_reject_suspension_and_resume_at_expiry(self):
		# Retain the old cookie deliberately: enforcement must work even if cleanup is delayed.
		with patch("frappe.enqueue"), patch("gameplan.restrictions.revoke_sessions"):
			set_restriction(self.user.name, 1, "HTTP boundary test", duration_seconds=3600)
			frappe.db.commit()
		endpoint = self.method("frappe.auth.get_logged_user")
		headers = {"Authorization": f"token {self.key}:suspension-test-secret"}
		self.assertEqual(self.get(endpoint).status_code, 401)
		self.assertEqual(self.get(endpoint, headers=headers).status_code, 401)
		self.TEST_CLIENT.delete_cookie("sid")
		self.assertEqual(
			self.post(
				self.method("login"), {"usr": self.user.name, "pwd": "TestSuspension2026!"}
			).status_code,
			401,
		)
		frappe.db.set_value(
			"GP User Restriction", state(self.user.name).name, "expires_at", utc_now() - timedelta(seconds=1)
		)
		frappe.db.commit()
		self.assertEqual(self.get(endpoint, headers=headers).status_code, 200)
		self.assertEqual(
			self.post(
				self.method("login"), {"usr": self.user.name, "pwd": "TestSuspension2026!"}
			).status_code,
			200,
		)
