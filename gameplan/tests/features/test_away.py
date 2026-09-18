# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""Being away, and the card that recaps it.

A user is away when Receive notifications is off, or when the clock is outside their
active hours on a selected day. Away is read from the profile every time; a
`GP Away Period` row is written only so the rows that arrive meanwhile can point at
it, and only when something does arrive. Every notification is still written — away
holds back push and email (later phases), never the record.
"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import frappe
from frappe.utils import add_to_date, now_datetime

from gameplan.api import away_summary, dismiss_away_card, mark_away_card_read
from gameplan.notifications import away
from gameplan.tests.base import GameplanTestCase
from gameplan.tests.features.test_notifications import mention_html
from gameplan.tests.fixtures import _name, create_comment, create_community, create_discussion, create_space


def prefs(**fields):
	base = frappe._dict(
		receive_notifications=1,
		active_hours_enabled=0,
		active_hours_start=None,
		active_hours_end=None,
		active_hours_days=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
	)
	base.update(fields)
	return base


class AwayTestCase(GameplanTestCase):
	def setUp(self):
		super().setUp()
		self.community = create_community("Acme", members=[self.member, self.second_member])
		self.space = create_space("Engineering", self.community)
		with self.as_user(self.member):
			self.discussion = create_discussion("Roadmap", self.space)

	def set_prefs(self, user, **fields):
		profile = frappe.db.get_value("GP User Profile", {"user": _name(user)}, "name")
		doc = frappe.get_doc("GP User Profile", profile)
		doc.update(fields)
		doc.save(ignore_permissions=True)
		return doc

	def periods_for(self, user, **filters):
		return frappe.get_all(
			"GP Away Period",
			filters={"user": _name(user), **filters},
			fields=["name", "kind", "starts_at", "ends_at", "card_dismissed"],
			order_by="creation asc",
		)

	def mention_second_member(self, content_user=None):
		with self.as_user(content_user or self.member):
			return create_comment(self.discussion, content=mention_html(self.second_member, "Second Member"))

	def rows_for(self, user):
		return frappe.get_all(
			"GP Notification",
			filters={"to_user": _name(user), "discussion": self.discussion.name},
			fields=["name", "type", "away_period", "read"],
		)


class TestReceiveToggle(AwayTestCase):
	def test_turning_it_off_opens_a_toggle_stretch(self):
		self.set_prefs(self.second_member, receive_notifications=0)

		rows = self.periods_for(self.second_member)
		self.assertEqual([(r.kind, r.ends_at) for r in rows], [("Toggle", None)])

	def test_rows_written_meanwhile_point_at_the_stretch(self):
		self.set_prefs(self.second_member, receive_notifications=0)
		period = self.periods_for(self.second_member)[0].name

		self.mention_second_member()

		self.assertEqual([r.away_period for r in self.rows_for(self.second_member)], [period])

	def test_turning_it_back_on_closes_the_stretch_and_later_rows_are_unstamped(self):
		self.set_prefs(self.second_member, receive_notifications=0)
		self.set_prefs(self.second_member, receive_notifications=1)

		self.assertIsNotNone(self.periods_for(self.second_member)[0].ends_at)
		self.mention_second_member()
		self.assertEqual([r.away_period for r in self.rows_for(self.second_member)], [None])

	def test_flipping_off_twice_does_not_open_two_stretches(self):
		self.set_prefs(self.second_member, receive_notifications=0)
		self.set_prefs(self.second_member, receive_notifications=0)

		self.assertEqual(len(self.periods_for(self.second_member)), 1)

	def test_a_reaction_row_points_at_the_stretch_too(self):
		"""Reactions write their own row (mixins/reactions.py), not through records."""
		self.set_prefs(self.member, receive_notifications=0)
		period = self.periods_for(self.member)[0].name

		with self.as_user(self.second_member):
			frappe.get_doc("GP Discussion", self.discussion.name).react(
				operations=[{"emoji": "👍", "operation": "add"}]
			)

		rows = frappe.get_all(
			"GP Notification", filters={"to_user": self.member.name, "type": "Reaction"}, pluck="away_period"
		)
		self.assertEqual(rows, [period])

	def test_a_reachable_user_gets_no_stretch(self):
		self.mention_second_member()

		self.assertEqual(self.periods_for(self.second_member), [])
		self.assertEqual([r.away_period for r in self.rows_for(self.second_member)], [None])


class TestActiveHours(AwayTestCase):
	"""`is_away` and `scheduled_off_window` are pure over (prefs, now, tz), so the clock
	is passed in. Times are in the user's own zone; the returned window is system time."""

	IST = ZoneInfo("Asia/Kolkata")

	def local(self, text):
		"""'2026-09-16 10:00' in IST (a Wednesday), as the system-time naive the code expects."""
		aware = datetime.strptime(text, "%Y-%m-%d %H:%M").replace(tzinfo=self.IST)
		return away._system(aware)

	def test_inside_the_hours_on_a_selected_day_is_not_away(self):
		p = prefs(active_hours_enabled=1, active_hours_start="09:00:00", active_hours_end="18:00:00")
		self.assertIsNone(away.is_away(p, self.local("2026-09-16 10:00"), self.IST))

	def test_outside_the_hours_is_away_until_the_next_start(self):
		p = prefs(active_hours_enabled=1, active_hours_start="09:00:00", active_hours_end="18:00:00")
		window = away.scheduled_off_window(p, self.local("2026-09-16 20:00"), self.IST)
		self.assertEqual(window, (self.local("2026-09-16 18:00"), self.local("2026-09-17 09:00")))
		self.assertEqual(away.is_away(p, self.local("2026-09-16 20:00"), self.IST), "Active hours")

	def test_an_overnight_window_belongs_to_the_day_it_starts_on(self):
		p = prefs(active_hours_enabled=1, active_hours_start="20:00:00", active_hours_end="09:00:00")
		# 02:00 Thursday is inside Wednesday's 20:00–09:00 stretch.
		self.assertIsNone(away.is_away(p, self.local("2026-09-17 02:00"), self.IST))
		window = away.scheduled_off_window(p, self.local("2026-09-17 12:00"), self.IST)
		self.assertEqual(window, (self.local("2026-09-17 09:00"), self.local("2026-09-17 20:00")))

	def test_an_unselected_day_is_away_all_day(self):
		p = prefs(
			active_hours_enabled=1,
			active_hours_start="09:00:00",
			active_hours_end="18:00:00",
			active_hours_days=["Mon", "Tue", "Wed", "Thu", "Fri"],
		)
		# Saturday noon: off since Friday 18:00, until Monday 09:00.
		window = away.scheduled_off_window(p, self.local("2026-09-19 12:00"), self.IST)
		self.assertEqual(window, (self.local("2026-09-18 18:00"), self.local("2026-09-21 09:00")))

	def test_hours_ending_at_midnight_still_count(self):
		p = prefs(active_hours_enabled=1, active_hours_start="09:00:00", active_hours_end="00:00:00")
		self.assertIsNone(away.is_away(p, self.local("2026-09-16 23:30"), self.IST))
		self.assertEqual(away.is_away(p, self.local("2026-09-17 01:00"), self.IST), "Active hours")

	def test_a_day_ending_at_23_59_has_no_hole_before_midnight(self):
		"""The settings page offers minutes, so all day is entered as 00:00–23:59."""
		p = prefs(active_hours_enabled=1, active_hours_start="00:00:00", active_hours_end="23:59:00")
		self.assertIsNone(away.is_away(p, self.local("2026-09-16 23:59"), self.IST))
		self.assertIsNone(away.is_away(p, self.local("2026-09-17 00:00"), self.IST))
		p = prefs(active_hours_enabled=1, active_hours_start="09:00:00", active_hours_end="23:59:00")
		window = away.scheduled_off_window(p, self.local("2026-09-17 03:00"), self.IST)
		self.assertEqual(window, (self.local("2026-09-17 00:00"), self.local("2026-09-17 09:00")))

	def test_the_toggle_wins_over_the_schedule(self):
		p = prefs(
			receive_notifications=0,
			active_hours_enabled=1,
			active_hours_start="09:00:00",
			active_hours_end="18:00:00",
		)
		self.assertEqual(away.is_away(p, self.local("2026-09-16 10:00"), self.IST), "Toggle")

	def test_disabled_hours_never_make_anyone_away(self):
		p = prefs(active_hours_start="09:00:00", active_hours_end="18:00:00")
		self.assertIsNone(away.is_away(p, self.local("2026-09-16 03:00"), self.IST))

	def test_a_user_without_a_timezone_is_evaluated_in_system_time(self):
		frappe.db.set_value("User", self.second_member.name, "time_zone", None)
		self.assertEqual(str(away.user_timezone(self.second_member.name)), frappe.utils.get_system_timezone())

	def test_the_first_row_in_a_quiet_window_creates_the_stretch_and_the_second_reuses_it(self):
		frappe.db.set_value("User", self.second_member.name, "time_zone", "Asia/Kolkata")
		now_local = away._local(now_datetime(), self.IST)
		# Hours that put "now" outside them: a one-hour window that ended two hours ago.
		start = (now_local.replace(minute=0, second=0, microsecond=0) - timedelta(hours=3)).time()
		end = (now_local.replace(minute=0, second=0, microsecond=0) - timedelta(hours=2)).time()
		self.set_prefs(
			self.second_member,
			active_hours_enabled=1,
			active_hours_start=start.strftime("%H:%M:%S"),
			active_hours_end=end.strftime("%H:%M:%S"),
		)

		self.mention_second_member()
		self.mention_second_member()

		periods = self.periods_for(self.second_member, kind="Active hours")
		self.assertEqual(len(periods), 1)
		self.assertIsNotNone(periods[0].ends_at)
		self.assertEqual({r.away_period for r in self.rows_for(self.second_member)}, {periods[0].name})

	def test_editing_the_hours_closes_the_running_stretch(self):
		self.set_prefs(self.second_member, receive_notifications=1)
		frappe.get_doc(
			doctype="GP Away Period",
			user=self.second_member.name,
			kind="Active hours",
			starts_at=add_to_date(now_datetime(), hours=-1),
			ends_at=add_to_date(now_datetime(), hours=5),
		).insert(ignore_permissions=True)

		self.set_prefs(self.second_member, active_hours_days=frappe.as_json(["Mon"]))

		ends_at = self.periods_for(self.second_member)[0].ends_at
		self.assertLessEqual(ends_at, now_datetime())


class TestActiveHoursValidation(AwayTestCase):
	def test_needs_at_least_one_day(self):
		with self.assertRaises(frappe.ValidationError):
			self.set_prefs(
				self.member,
				active_hours_enabled=1,
				active_hours_start="09:00:00",
				active_hours_end="18:00:00",
				active_hours_days="[]",
			)

	def test_needs_both_times(self):
		with self.assertRaises(frappe.ValidationError):
			self.set_prefs(self.member, active_hours_enabled=1, active_hours_start="09:00:00")

	def test_needs_different_times(self):
		with self.assertRaises(frappe.ValidationError):
			self.set_prefs(
				self.member,
				active_hours_enabled=1,
				active_hours_start="09:00:00",
				active_hours_end="09:00:00",
			)

	def test_a_disabled_schedule_is_not_validated(self):
		self.set_prefs(self.member, active_hours_enabled=0, active_hours_days="[]")


class TestAwayCard(AwayTestCase):
	def setUp(self):
		super().setUp()
		self.set_prefs(self.second_member, receive_notifications=0)
		self.period = self.periods_for(self.second_member)[0].name
		# The card is for a real absence: back-date the stretch past the minimum.
		self.backdate(days=away.CARD_MIN_DAYS + 1)

	def backdate(self, days):
		frappe.db.set_value(
			"GP Away Period", self.period, "starts_at", add_to_date(now_datetime(), days=-days)
		)

	def summary(self):
		with self.as_user(self.second_member):
			return away_summary()

	def test_no_card_while_the_stretch_is_still_open(self):
		self.mention_second_member()

		self.assertIsNone(self.summary())

	def test_no_card_for_a_short_stretch(self):
		"""An evening off is not an absence: the rows simply sit in the inbox."""
		self.backdate(days=1)
		self.mention_second_member()
		self.set_prefs(self.second_member, receive_notifications=1)

		self.assertIsNone(self.summary())

	def test_no_card_for_a_quiet_stretch(self):
		self.set_prefs(self.second_member, receive_notifications=1)

		self.assertIsNone(self.summary())

	def test_the_card_lists_mentions_and_groups_comments(self):
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
		self.set_prefs(self.second_member, receive_notifications=1)

		card = self.summary()

		self.assertEqual(card["period"], self.period)
		self.assertEqual(card["kind"], "Toggle")
		self.assertEqual(card["mentions"]["total"], 1)
		mention = card["mentions"]["items"][0]
		self.assertEqual(mention["from_user"], self.member.name)
		self.assertEqual(mention["title"], "Roadmap")
		self.assertIn("@Second Member", mention["snippet"])
		(group,) = card["comments"]
		self.assertEqual(str(group["discussion"]), str(self.discussion.name))
		self.assertEqual((group["title"], group["event_count"]), ("Roadmap", 2))
		self.assertEqual((str(group["project"]), group["team"]), (str(self.space.name), self.community.name))
		self.assertEqual(card["other"], [])
		self.assertEqual(card["unread"], 2)

	def test_every_mention_is_listed(self):
		for _ in range(12):
			self.mention_second_member()
		self.set_prefs(self.second_member, receive_notifications=1)

		card = self.summary()

		self.assertEqual(card["mentions"]["total"], 12)
		self.assertEqual(len(card["mentions"]["items"]), 12)

	def test_mark_read_clears_the_rows_and_the_card(self):
		self.mention_second_member()
		self.set_prefs(self.second_member, receive_notifications=1)

		with self.as_user(self.second_member):
			mark_away_card_read(self.period)

		self.assertEqual([r.read for r in self.rows_for(self.second_member)], [1])
		self.assertIsNone(self.summary())

	def test_dismiss_hides_the_card_but_leaves_the_rows_unread(self):
		self.mention_second_member()
		self.set_prefs(self.second_member, receive_notifications=1)

		with self.as_user(self.second_member):
			dismiss_away_card(self.period)

		self.assertEqual([r.read for r in self.rows_for(self.second_member)], [0])
		self.assertIsNone(self.summary())

	def test_reading_the_rows_elsewhere_also_retires_the_card(self):
		self.mention_second_member()
		self.set_prefs(self.second_member, receive_notifications=1)

		with self.as_user(self.second_member):
			frappe.get_doc("GP Discussion", self.discussion.name).track_visit()

		self.assertIsNone(self.summary())

	def test_only_the_owner_can_act_on_a_period(self):
		self.mention_second_member()
		self.set_prefs(self.second_member, receive_notifications=1)

		with self.as_user(self.member):
			with self.assertRaises(frappe.PermissionError):
				mark_away_card_read(self.period)
			with self.assertRaises(frappe.PermissionError):
				dismiss_away_card(self.period)
			visible = frappe.qb.get_query("GP Away Period", fields=["name"], ignore_permissions=False)
			self.assertNotIn(self.period, visible.run(pluck="name"))
