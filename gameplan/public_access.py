# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

"""Public read access: letting people who are not signed in read chosen spaces.

A community or a space has one of three visibility tiers:

- Anonymous: anyone with the link can read it, signed in or not.
- General: anyone signed in to Gameplan can read it.
- Member Access: only the people on its member list can read it.

Refer to a tier through the constants below, never a bare string. "Anonymous" as a tier
means "readable by people who are not signed in". It does not mean that the content or its
author is anonymous, and `GP Poll.anonymous` (a poll with hidden voters) is unrelated.
"""

import frappe
from frappe.utils import cint

VISIBILITY_ANONYMOUS = "Anonymous"
VISIBILITY_GENERAL = "General"
VISIBILITY_MEMBER_ACCESS = "Member Access"
VISIBILITY_TIERS = (VISIBILITY_ANONYMOUS, VISIBILITY_GENERAL, VISIBILITY_MEMBER_ACCESS)

PUBLIC_ACCESS_CONFIG_KEY = "gameplan_public_access_enabled"


def public_access_enabled() -> bool:
	"""Whether this site lets people who are not signed in read the Anonymous tier.

	Off unless site config turns it on. Every anonymous read path checks it, so setting
	`gameplan_public_access_enabled` to 0 in site_config.json closes public access on that
	site without a deploy.

	Always off while demo mode is on. On a demo site, opening /g with `?demo` in the URL
	signs the visitor in as a real demo user (see `login_as_demo_user_if_enabled` in
	www/g.py), so a public reader would silently become a member partway through a visit.
	"""
	from gameplan.demo.demo import demo_data_enabled

	if demo_data_enabled():
		return False
	return bool(cint(frappe.conf.get(PUBLIC_ACCESS_CONFIG_KEY)))
