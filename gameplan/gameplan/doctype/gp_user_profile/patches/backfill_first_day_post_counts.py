# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from collections import Counter

import frappe
from frappe.utils import cint, now_datetime

from gameplan.new_user_limits import FIRST_DAY, POST_COUNTER_FIELDS


def execute():
	"""Keep the remaining allowance of existing first-day accounts after migration."""
	users = frappe.get_all("User", filters={"creation": (">", now_datetime() - FIRST_DAY)}, pluck="name")
	if not users:
		return
	profiles = frappe.get_all(
		"GP User Profile",
		filters={"user": ("in", users)},
		fields=["name", "user", *set(POST_COUNTER_FIELDS.values())],
	)
	totals = {field: Counter() for field in POST_COUNTER_FIELDS.values()}
	for doctype, field in POST_COUNTER_FIELDS.items():
		rows = frappe.qb.get_query(
			doctype,
			filters={"owner": ("in", users)},
			fields=["owner", {"COUNT": "name", "as": "count"}],
			group_by="owner",
		).run(as_dict=True)
		totals[field].update({row.owner: row.count for row in rows})
	for profile in profiles:
		values = {
			field: max(cint(profile.get(field)), counts[profile.user]) for field, counts in totals.items()
		}
		frappe.db.set_value("GP User Profile", profile.name, values, update_modified=False)
