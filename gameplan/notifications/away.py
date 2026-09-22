# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

"""When a user is not to be reached, and which stretch a notification fell in.

Two things make a user away: Receive notifications switched off (a "Toggle" stretch,
open until they switch it back on), or the clock being outside their active hours on a
selected day (an "Active hours" stretch, bounded by the schedule). Away-or-not is read
from the profile every time; `GP Away Period` rows are written only so a notification
can say which stretch it fell in and the catch-up mail (notifications/delivery.py) has
something to cover. Nothing here decides whether a row is *written* — an away user still
gets every row, with its real time; only email holds back.

Datetimes are stored the Frappe way: naive, in the site's system timezone. The schedule
is evaluated in the user's own timezone (`User.time_zone`, else the system's).
"""

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

import frappe
from frappe.utils import cint, get_datetime, get_system_timezone, get_time, now_datetime

from gameplan.notifications.preferences import profile_prefs

DAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
END_OF_DAY = time(23, 59)


def user_timezone(user: str) -> ZoneInfo:
	return ZoneInfo(frappe.db.get_value("User", user, "time_zone") or get_system_timezone())


def is_away(prefs, now: datetime | None = None, tz: ZoneInfo | None = None) -> str | None:
	""" "Toggle", "Active hours" or None — the toggle wins, being the deliberate one."""
	if not cint(prefs.receive_notifications):
		return "Toggle"
	if cint(prefs.active_hours_enabled) and scheduled_off_window(prefs, now, tz):
		return "Active hours"
	return None


def scheduled_off_window(prefs, now: datetime | None = None, tz: ZoneInfo | None = None):
	"""The off stretch `now` falls in, as system-time `(start, end)`, or None while inside
	active hours on a selected day.

	An active stretch runs from `active_hours_start` to `active_hours_end` on each selected
	day; when the end is not after the start it finishes the next day, and the stretch
	belongs to the day it started on. The off stretch is what lies between two active
	ones, so it can span days the user does not work at all.
	"""
	days = _selected_days(prefs)
	start, end = prefs.get("active_hours_start"), prefs.get("active_hours_end")
	# `is None`, not truthiness: a Time read from the database is a timedelta, and
	# midnight is timedelta(0).
	if not days or start is None or end is None or start == "" or end == "":
		return None

	tz = tz or ZoneInfo(get_system_timezone())
	now_local = _local(now or now_datetime(), tz)
	start, end = get_time(start), get_time(end)
	# The settings page offers minutes, so "until the end of the day" is entered as 23:59;
	# read literally it would leave a one-minute hole before midnight every day.
	if end >= END_OF_DAY:
		end = time(0, 0)
	overnight = end <= start

	# Every active stretch starting within a week either side is enough to bracket now,
	# even for someone who works one day a week.
	stretches = []
	for offset in range(-8, 9):
		day = now_local.date() + timedelta(days=offset)
		if day.strftime("%a") not in days:
			continue
		starts = datetime.combine(day, start, tzinfo=tz)
		ends = datetime.combine(day + timedelta(days=1 if overnight else 0), end, tzinfo=tz)
		stretches.append((starts, ends))

	for starts, ends in stretches:
		if starts <= now_local < ends:
			return None
	previous_end = max((ends for _, ends in stretches if ends <= now_local), default=None)
	next_start = min((starts for starts, _ in stretches if starts > now_local), default=None)
	if not previous_end or not next_start:
		return None
	return _system(previous_end), _system(next_start)


def get_active_away_period(user: str, now: datetime | None = None) -> str | None:
	"""The `GP Away Period` row covering `now` for `user`, created on demand, or None."""
	prefs = profile_prefs(user)
	now = now or now_datetime()
	tz = user_timezone(user)
	kind = is_away(prefs, now, tz)
	if not kind:
		return None
	if kind == "Toggle":
		return _open_toggle_period(user) or _insert_period(user, "Toggle", now, None)

	starts_at, ends_at = scheduled_off_window(prefs, now, tz)
	existing = frappe.db.get_value("GP Away Period", {"user": user, "starts_at": starts_at}, "name")
	return existing or _insert_period(user, "Active hours", starts_at, ends_at)


def set_receive_notifications(user: str, enabled) -> None:
	"""Off opens a Toggle stretch (unless one is open); on closes it at now."""
	if cint(enabled):
		for name in _open_toggle_periods(user):
			frappe.db.set_value("GP Away Period", name, "ends_at", now_datetime())
	elif not _open_toggle_period(user):
		_insert_period(user, "Toggle", now_datetime(), None)


def close_open_scheduled_period(user: str) -> None:
	"""A schedule edit ends the current scheduled stretch: whatever the new hours say, the
	stretch that was computed from the old ones no longer describes anything."""
	now = now_datetime()
	rows = frappe.get_all(
		"GP Away Period",
		filters={"user": user, "kind": "Active hours", "ends_at": [">", now]},
		pluck="name",
	)
	for name in rows:
		frappe.db.set_value("GP Away Period", name, "ends_at", now)


def pending_recap_periods(user: str) -> list:
	"""Ended stretches whose catch-up email has not gone out yet, oldest first."""
	return frappe.get_all(
		"GP Away Period",
		filters=[
			["user", "=", user],
			["ends_at", "is", "set"],
			["ends_at", "<=", now_datetime()],
			["recap_sent_at", "is", "not set"],
		],
		fields=["name", "starts_at", "ends_at"],
		order_by="ends_at asc",
	)


def mark_recap_sent(periods: list[str]) -> None:
	if not periods:
		return
	Period = frappe.qb.DocType("GP Away Period")
	(
		frappe.qb.update(Period).set(Period.recap_sent_at, now_datetime()).where(Period.name.isin(periods))
	).run()


# --- helpers ---


def _selected_days(prefs) -> set[str]:
	days = prefs.get("active_hours_days")
	if isinstance(days, str):
		days = frappe.parse_json(days or "[]")
	return {day for day in (days or []) if day in DAYS}


def _local(system_naive: datetime, tz: ZoneInfo) -> datetime:
	return get_datetime(system_naive).replace(tzinfo=ZoneInfo(get_system_timezone())).astimezone(tz)


def _system(aware: datetime) -> datetime:
	return aware.astimezone(ZoneInfo(get_system_timezone())).replace(tzinfo=None)


def _open_toggle_periods(user: str) -> list[str]:
	return frappe.get_all(
		"GP Away Period",
		filters={"user": user, "kind": "Toggle", "ends_at": ["is", "not set"]},
		pluck="name",
	)


def _open_toggle_period(user: str) -> str | None:
	rows = _open_toggle_periods(user)
	return rows[0] if rows else None


def _insert_period(user: str, kind: str, starts_at: datetime, ends_at: datetime | None) -> str:
	doc = frappe.get_doc(
		doctype="GP Away Period", user=user, kind=kind, starts_at=starts_at, ends_at=ends_at
	).insert(ignore_permissions=True)
	return doc.name
