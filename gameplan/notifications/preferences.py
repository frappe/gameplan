# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt


import frappe

DEFAULT_PARTICIPATION = "Watch"
PARTICIPATION_LEVELS = ("Watch", "Mentions only")

DAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")

PREF_FIELDS = (
	"participation_level",
	"receive_notifications",
	"active_hours_enabled",
	"active_hours_start",
	"active_hours_end",
	"active_hours_days",
)

_DEFAULTS = frappe._dict(
	participation_level=DEFAULT_PARTICIPATION,
	receive_notifications=1,
	active_hours_enabled=0,
	active_hours_start=None,
	active_hours_end=None,
	active_hours_days=list(DAYS),
)


def profile_prefs(user: str) -> frappe._dict:
	row = frappe.db.get_value("GP User Profile", {"user": user}, list(PREF_FIELDS), as_dict=True)
	prefs = frappe._dict(_DEFAULTS)
	if row:
		for field in PREF_FIELDS:
			if row.get(field) not in (None, ""):
				prefs[field] = row[field]
	return prefs


def participation_level(user: str) -> str:
	level = profile_prefs(user).participation_level
	return level if level in PARTICIPATION_LEVELS else DEFAULT_PARTICIPATION


def wants_content_feedback(user: str) -> bool:
	return participation_level(user) == "Watch"
