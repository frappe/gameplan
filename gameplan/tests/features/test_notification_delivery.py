# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt


from datetime import datetime
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

import frappe
from frappe.utils import add_to_date, format_datetime, get_datetime, get_system_timezone, now_datetime
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
		return self.run_tick(now_datetime().replace(minute=0, second=0, microsecond=0))

	def run_tick(self, now):
		with patch("frappe.sendmail") as sendmail:
			delivery.send_batches(now)
		return self.mails_to(sendmail, self.second_member)

	def mails_to(self, sendmail, user):
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
		mention = email["args"]["mentions"][0]
		self.assertIn("mentioned you", mention["title"])
		self.assertEqual(mention["description"], "Roadmap")
		self.assertEqual(len(email["args"]["others"]), 1)
		self.assertIn("2 new comments", email["args"]["others"][0]["title"])

		message, text = get_email_from_template(email["template"], email["args"])
		self.assertIn("Mentions", message)
		self.assertIn("Roadmap", text)

	def test_an_event_merging_into_an_already_emailed_row_is_still_delivered(self):
		"""Comments merge into one unread row rather than multiplying. `pending_rows`
		skips anything carrying `email_sent_at`, so a merge that leaves the stamp in place
		means every later comment on that discussion is silently never sent.
		"""
		frappe.get_doc(
			doctype="GP Discussion Subscription",
			user=self.second_member.name,
			discussion=self.discussion.name,
			state="Watch",
		).insert(ignore_permissions=True)
		with self.as_user(self.member):
			create_comment(self.discussion, content="<p>One</p>")
		self.run_hourly().assert_called_once()
		self.assertTrue(self.rows_for(self.second_member)[0].email_sent_at)

		with self.as_user(self.member):
			create_comment(self.discussion, content="<p>Two</p>")

		sendmail = self.run_hourly()

		sendmail.assert_called_once()
		self.assertIn("2 new comments", sendmail.call_args.kwargs["args"]["others"][0]["title"])

	def test_an_item_never_prints_its_discussion_title_twice(self):
		self.mention_second_member()
		frappe.get_doc(
			doctype="GP Discussion Subscription",
			user=self.second_member.name,
			discussion=self.discussion.name,
			state="Watch",
		).insert(ignore_permissions=True)
		with self.as_user(self.member):
			create_comment(self.discussion, content="<p>One</p>")

		email = self.run_hourly().call_args.kwargs

		comment = email["args"]["others"][0]
		self.assertIn("Roadmap", comment["title"])
		self.assertEqual(comment["description"], "")

		mention = email["args"]["mentions"][0]
		self.assertNotIn("Roadmap", mention["title"])
		self.assertEqual(mention["description"], "Roadmap")

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
	def setUp(self):
		super().setUp()
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
		frappe.db.set_value("User", self.second_member.name, "time_zone", "Asia/Gaza")
		self.run_tick(self.at("2026-09-16 18:30")).assert_not_called()
		self.run_tick(self.at("2026-09-16 20:30")).assert_called_once()


class TestAwayRecap(DeliveryTestCase):
	def away_and_back(self):
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

	def test_a_merge_during_a_later_stretch_reaches_that_stretchs_catch_up(self):
		"""The row is reused across stretches, so its away period has to move to the one
		the new event fell in. Keeping the first leaves the later recap querying a period
		the row no longer belongs to, and the activity is never reported at all.
		"""
		frappe.get_doc(
			doctype="GP Discussion Subscription",
			user=self.second_member.name,
			discussion=self.discussion.name,
			state="Watch",
		).insert(ignore_permissions=True)

		self.set_prefs(self.second_member, receive_notifications=0)
		with self.as_user(self.member):
			create_comment(self.discussion, content="<p>One</p>")
		self.set_prefs(self.second_member, receive_notifications=1)
		self.run_hourly().assert_called_once()

		self.set_prefs(self.second_member, receive_notifications=0)
		with self.as_user(self.member):
			create_comment(self.discussion, content="<p>Two</p>")
		self.set_prefs(self.second_member, receive_notifications=1)

		sendmail = self.run_hourly()

		sendmail.assert_called_once()
		self.assertEqual(
			sendmail.call_args.kwargs["subject"], "While you were away: 1 notification in Gameplan"
		)

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

	def test_the_window_is_written_in_the_readers_timezone(self):
		period = frappe.get_doc(
			doctype="GP Away Period",
			user=self.second_member.name,
			kind="Toggle",
			starts_at="2026-09-20 22:00:00",
			ends_at="2026-09-21 08:00:00",
		).insert(ignore_permissions=True)
		periods = frappe.get_all(
			"GP Away Period", filters={"name": period.name}, fields=["name", "starts_at", "ends_at"]
		)

		frappe.db.set_value("User", self.second_member.name, "time_zone", "Asia/Kolkata")
		kolkata = delivery.recap_context(self.second_member.name, [], periods)["window"]
		frappe.db.set_value("User", self.second_member.name, "time_zone", "Asia/Gaza")
		gaza = delivery.recap_context(self.second_member.name, [], periods)["window"]

		self.assertNotEqual(kolkata, gaza)
		for zone, window in (("Asia/Kolkata", kolkata), ("Asia/Gaza", gaza)):
			local = (
				get_datetime("2026-09-20 22:00:00")
				.replace(tzinfo=ZoneInfo(get_system_timezone()))
				.astimezone(ZoneInfo(zone))
			)
			self.assertIn(format_datetime(local.replace(tzinfo=None), "h:mm a"), window)
