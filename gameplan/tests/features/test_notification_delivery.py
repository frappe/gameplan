# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""The email channel: one hourly mail per user who asked for it, each row sent once, and
a closing mail as the user's active hours end.

Everything is a `GP Notification` row first; delivery only decides which rows also go
out by mail. Rows already read, written during an away stretch, older than the horizon
or pointing at something the user can no longer open are stamped instead of sent, so
the next run does not see them again.
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import frappe
from frappe.utils import add_to_date, get_datetime, now_datetime
from frappe.utils.jinja import get_email_from_template

from gameplan.notifications import delivery
from gameplan.tests.base import GameplanTestCase
from gameplan.tests.features.test_notifications import mention_html
from gameplan.tests.fixtures import _name, create_comment, create_community, create_discussion, create_space


class DeliveryTestCase(GameplanTestCase):
	def setUp(self):
		super().setUp()
		self.community = create_community(
			"Acme", members=[self.member, self.second_member], admins=[self.admin]
		)
		self.space = create_space("Engineering", self.community)
		with self.as_user(self.member):
			self.discussion = create_discussion("Roadmap", self.space)
		self.set_prefs(self.second_member, notification_channel="Email")

	def set_prefs(self, user, **fields):
		profile = frappe.db.get_value("GP User Profile", {"user": _name(user)}, "name")
		doc = frappe.get_doc("GP User Profile", profile)
		doc.update(fields)
		doc.save(ignore_permissions=True)

	def mention_second_member(self, discussion=None):
		with self.as_user(self.member):
			return create_comment(
				discussion or self.discussion, content=mention_html(self.second_member, "Second Member")
			)

	def rows_for(self, user):
		return frappe.get_all(
			"GP Notification",
			filters={"to_user": _name(user), "team": self.community.name},
			fields=["name", "type", "read", "email_sent_at", "away_period"],
			order_by="creation asc",
		)

	def run_hourly(self):
		"""The tick at the top of the current hour."""
		return self.run_tick(now_datetime().replace(minute=0, second=0, microsecond=0))

	def run_tick(self, now):
		with patch("frappe.sendmail") as sendmail:
			delivery.send_batches(now)
		return self.mails_to(sendmail, self.second_member)

	def mails_to(self, sendmail, user):
		"""Only the mails addressed to `user`. The batch walks every profile on the site,
		and this one runs against a site with real ones, so another user's mail must not
		count as this test's."""
		scoped = MagicMock()
		for call in sendmail.call_args_list:
			if call.kwargs.get("recipients") == [_name(user)]:
				scoped(*call.args, **call.kwargs)
		return scoped


class TestHourlyBatch(DeliveryTestCase):
	def test_one_mail_per_user_with_mentions_first(self):
		self.mention_second_member()
		frappe.get_doc(
			doctype="GP Discussion Subscription",
			user=self.second_member.name,
			discussion=self.discussion.name,
			state="Watch",
		).insert(ignore_permissions=True)
		with self.as_user(self.member):
			create_comment(self.discussion, content="<p>One</p>")
			create_comment(self.discussion, content="<p>Two</p>")

		sendmail = self.run_hourly()

		sendmail.assert_called_once()
		email = sendmail.call_args.kwargs
		self.assertEqual(email["recipients"], [self.second_member.name])
		self.assertEqual(email["subject"], "2 new notifications in Gameplan")
		self.assertEqual(email["template"], "notification_batch")
		self.assertEqual([item["title"] for item in email["args"]["mentions"]], ["Roadmap"])
		self.assertEqual(len(email["args"]["others"]), 1)
		self.assertIn("2 new comments", email["args"]["others"][0]["description"])

		message, text = get_email_from_template(email["template"], email["args"])
		self.assertIn("Mentions", message)
		self.assertIn("Roadmap", text)

	def test_every_sent_row_is_stamped_and_the_next_run_sends_nothing(self):
		self.mention_second_member()
		self.run_hourly()

		self.assertTrue(all(row.email_sent_at for row in self.rows_for(self.second_member)))
		self.run_hourly().assert_not_called()

	def test_nothing_pending_means_no_mail(self):
		self.run_hourly().assert_not_called()

	def test_in_app_users_get_no_mail(self):
		self.set_prefs(self.second_member, notification_channel="In-app")
		self.mention_second_member()

		self.run_hourly().assert_not_called()
		self.assertIsNone(self.rows_for(self.second_member)[0].email_sent_at)

	def test_a_row_read_in_the_app_is_not_mailed(self):
		self.mention_second_member()
		with self.as_user(self.second_member):
			frappe.get_doc("GP Discussion", self.discussion.name).track_visit()

		self.run_hourly().assert_not_called()
		self.assertTrue(self.rows_for(self.second_member)[0].email_sent_at)

	def test_rows_from_an_open_away_stretch_wait_for_the_catch_up(self):
		self.set_prefs(self.second_member, receive_notifications=0)
		self.mention_second_member()

		self.run_hourly().assert_not_called()
		row = self.rows_for(self.second_member)[0]
		self.assertTrue(row.away_period)
		self.assertIsNone(row.email_sent_at)

	def test_a_row_older_than_the_horizon_is_stamped_without_a_mail(self):
		self.mention_second_member()
		stale = add_to_date(now_datetime(), hours=-(delivery.HORIZON_HOURS + 1))
		frappe.db.set_value(
			"GP Notification", self.rows_for(self.second_member)[0].name, "last_event_at", stale
		)

		self.run_hourly().assert_not_called()
		self.assertTrue(self.rows_for(self.second_member)[0].email_sent_at)

	def test_a_row_whose_space_the_user_lost_is_stamped_without_a_mail(self):
		private = create_space(
			"Secret", self.community, is_private=1, members=[self.member, self.second_member]
		)
		with self.as_user(self.member):
			secret = create_discussion("Plans", private)
		self.mention_second_member(secret)
		with self.as_user(self.admin):
			frappe.get_doc("GP Project", private.name).remove_member(self.second_member.name)

		self.run_hourly().assert_not_called()
		rows = frappe.get_all(
			"GP Notification",
			filters={"to_user": self.second_member.name, "discussion": secret.name},
			fields=["email_sent_at"],
		)
		self.assertTrue(rows[0].email_sent_at)

	def test_a_row_whose_target_is_gone_is_stamped_without_a_mail(self):
		self.mention_second_member()
		row = self.rows_for(self.second_member)[0]
		frappe.db.set_value(
			"GP Notification",
			row.name,
			{"discussion": None, "comment": None, "project": None, "team": None},
		)

		self.run_hourly().assert_not_called()
		self.assertTrue(frappe.db.get_value("GP Notification", row.name, "email_sent_at"))

	def test_the_digest_and_the_hourly_mail_are_independent(self):
		from datetime import date

		from gameplan.email_digest import send_digest_for_profile

		self.set_prefs(self.second_member, email_digest_frequency="Weekly")
		self.mention_second_member()
		profile = frappe.get_doc("GP User Profile", {"user": self.second_member.name})

		with patch("frappe.sendmail") as sendmail:
			send_digest_for_profile(profile, date(2026, 9, 18))
			delivery.send_batches(now_datetime().replace(minute=0, second=0, microsecond=0))

		self.assertEqual(
			[call.kwargs["template"] for call in self.mails_to(sendmail, self.second_member).call_args_list],
			["email_digest", "notification_batch"],
		)


class TestSendTimes(DeliveryTestCase):
	"""`should_send` reads the clock in the user's zone; the test user has none, so system
	time is that zone and the times below are literal. 2026-09-16 is a Wednesday."""

	def setUp(self):
		super().setUp()
		# The row is written while the schedule is still all-day, so it carries no away
		# stamp; the 9-to-6 schedule then governs when it is mailed.
		self.mention_second_member()
		self.set_prefs(
			self.second_member,
			active_hours_enabled=1,
			active_hours_start="09:00:00",
			active_hours_end="18:00:00",
			active_hours_days=frappe.as_json(["Mon", "Tue", "Wed", "Thu", "Fri"]),
		)

	def at(self, text):
		return get_datetime(datetime.strptime(text, "%Y-%m-%d %H:%M"))

	def test_the_top_of_an_hour_inside_the_window_sends(self):
		self.run_tick(self.at("2026-09-16 10:00")).assert_called_once()

	def test_a_tick_between_hours_sends_nothing(self):
		self.run_tick(self.at("2026-09-16 10:05")).assert_not_called()
		self.run_tick(self.at("2026-09-16 10:30")).assert_not_called()

	def test_the_window_closing_sends_the_last_mail(self):
		self.run_tick(self.at("2026-09-16 18:00")).assert_called_once()

	def test_after_the_closing_tick_nothing_more_goes_out_that_day(self):
		self.run_tick(self.at("2026-09-16 18:05")).assert_not_called()
		self.run_tick(self.at("2026-09-16 18:30")).assert_not_called()
		self.run_tick(self.at("2026-09-16 22:00")).assert_not_called()

	def test_a_day_off_sends_nothing_even_on_the_hour(self):
		self.run_tick(self.at("2026-09-19 10:00")).assert_not_called()

	def test_the_toggle_off_holds_everything(self):
		self.set_prefs(self.second_member, receive_notifications=0)
		self.run_tick(self.at("2026-09-16 10:00")).assert_not_called()
		self.run_tick(self.at("2026-09-16 18:00")).assert_not_called()

	def test_the_closing_mail_follows_the_users_timezone(self):
		# 18:00 in Gaza is 20:30 in the site's Asia/Calcutta: the closing tick moves with it,
		# and the site's 18:30 (16:00 in Gaza, mid-window, off the hour) is nothing special.
		frappe.db.set_value("User", self.second_member.name, "time_zone", "Asia/Gaza")
		self.run_tick(self.at("2026-09-16 18:30")).assert_not_called()
		self.run_tick(self.at("2026-09-16 20:30")).assert_called_once()


class TestAwayRecap(DeliveryTestCase):
	"""What arrived while the user was away goes out in its own mail once the stretch ends."""

	def away_and_back(self):
		"""Switch notifications off, take a mention, switch back on: one ended stretch."""
		self.set_prefs(self.second_member, receive_notifications=0)
		self.mention_second_member()
		self.set_prefs(self.second_member, receive_notifications=1)

	def periods(self):
		return frappe.get_all(
			"GP Away Period",
			filters={"user": self.second_member.name},
			fields=["name", "ends_at", "recap_sent_at"],
		)

	def test_the_catch_up_names_the_stretch_and_stamps_the_rows(self):
		self.away_and_back()

		sendmail = self.run_hourly()

		sendmail.assert_called_once()
		email = sendmail.call_args.kwargs
		self.assertEqual(email["recipients"], [self.second_member.name])
		self.assertEqual(email["subject"], "While you were away: 1 notification in Gameplan")
		self.assertEqual(email["args"]["title"], "While you were away")
		self.assertTrue(email["args"]["window"])
		self.assertEqual(len(email["args"]["mentions"]), 1)
		self.assertTrue(self.rows_for(self.second_member)[0].email_sent_at)

	def test_it_is_sent_once(self):
		self.away_and_back()
		self.run_hourly()

		self.run_hourly().assert_not_called()
		self.assertTrue(all(p.recap_sent_at for p in self.periods()))

	def test_a_stretch_still_open_is_not_caught_up_yet(self):
		self.set_prefs(self.second_member, receive_notifications=0)
		self.mention_second_member()

		delivery.send_away_recap(self.second_member.name)

		self.assertIsNone(self.rows_for(self.second_member)[0].email_sent_at)
		self.assertFalse(any(p.recap_sent_at for p in self.periods()))

	def test_an_empty_stretch_is_stamped_without_a_mail(self):
		self.set_prefs(self.second_member, receive_notifications=0)
		self.set_prefs(self.second_member, receive_notifications=1)

		self.run_hourly().assert_not_called()
		self.assertTrue(all(p.recap_sent_at for p in self.periods()))

	def test_a_row_read_in_the_app_is_not_caught_up(self):
		self.away_and_back()
		row = self.rows_for(self.second_member)[0]
		frappe.db.set_value("GP Notification", row.name, "read", 1)

		self.run_hourly().assert_not_called()

	def test_the_catch_up_has_no_horizon(self):
		"""Days old is the point of a catch-up, so the ordinary 24-hour cutoff is not applied."""
		self.away_and_back()
		row = self.rows_for(self.second_member)[0]
		frappe.db.set_value(
			"GP Notification", row.name, "last_event_at", add_to_date(now_datetime(), hours=-72)
		)

		self.run_hourly().assert_called_once()

	def test_an_in_app_user_gets_no_catch_up(self):
		self.set_prefs(self.second_member, notification_channel="In-app")
		self.away_and_back()

		self.run_hourly().assert_not_called()
