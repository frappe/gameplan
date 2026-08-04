# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""Password-less "become another user", for the floating dev switcher only.

Frappe already ships `frappe.core.doctype.user.user.impersonate`, and it is the
wrong tool here: it opens with a `User` "impersonate" permission check, so the
first switch to an ordinary member takes away the permission needed for the
second one. A switcher you cannot switch back out of is worse than none.

So this endpoint has no role check at all. Everything protecting it is about
*where it is running*, not *who is calling*, which is the only way it can stay
reversible.
"""

import frappe
from frappe.utils import cint

CONFIG_KEY = "enable_dev_user_switcher"


def _assert_dev_switching_allowed():
	"""Two independent gates, both of which have to hold.

	Gate 1 is `frappe._dev_server`, read from the DEV_SERVER environment variable
	when frappe is imported. `bench start` sets it; a production gunicorn worker
	does not, and no amount of `site_config.json` can turn it on afterwards. That
	is what makes this module dead on a real server whatever else is configured.
	Bench installs an app by putting its repo directory on `sys.path`, so this
	file ships to every server and the gating has to be at runtime.

	Gate 2 is the config key, read through `cint` so a *string* "0" or "false"
	reads as disabled rather than as a truthy string. A dev server should not
	hand out other people's sessions until it has been asked to.
	"""
	if not (frappe._dev_server or frappe.in_test):
		frappe.throw(
			"Switching users without a password needs a development server, started with "
			"'bench start' (or DEV_SERVER=1 bench serve)."
		)

	if not cint(frappe.conf.get(CONFIG_KEY)):
		frappe.throw(
			f"Set '{CONFIG_KEY}' to 1 in site_config.json to switch users without a password. "
			'The value is read with cint, so the quoted strings "true"/"false"/"0" all read '
			"as disabled — use a number or a JSON boolean."
		)


@frappe.whitelist(methods=["POST"])
def switch_user(user: str):
	"""Start a fresh session as `user`, with no password.

	Limited to users the switcher actually lists, which is the same filter
	`gameplan.api.get_user_info` uses: somebody holding a Gameplan role. On a site
	running other apps too, that keeps this away from accounts that have nothing
	to do with Gameplan.
	"""
	_assert_dev_switching_allowed()

	enabled = frappe.db.get_value("User", user, "enabled")
	if enabled is None:
		frappe.throw(f"No such user: {user}")
	if not enabled:
		frappe.throw(f"{user} is disabled")

	has_gameplan_role = frappe.db.exists(
		"Has Role", {"parenttype": "User", "parent": user, "role": ("like", "Gameplan %")}
	)
	if not has_gameplan_role:
		frappe.throw(f"{user} is not a Gameplan user")

	# `login_as`, not frappe's `impersonate`: an impersonated session carries the
	# original session's end time and audit user, and the point of switching here
	# is to see exactly what a normal session for this user sees.
	frappe.local.login_manager.login_as(user)
	return {"user": user}
