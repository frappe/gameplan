# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

"""robots.txt: frappe's own (Website Settings or site config), plus Gameplan's rules.

Overrides frappe/www/robots.py, which serves only the configured text; an app installed
after frappe wins the route. See gameplan.public_access.gameplan_robots_rules.
"""

import frappe

from gameplan.public_access import gameplan_robots_rules

base_template_path = "www/robots.txt"
# The Allow lines follow the spaces' tiers, which change without a deploy.
no_cache = 1


def get_context(context):
	configured = (
		frappe.db.get_single_value("Website Settings", "robots_txt")
		or (frappe.local.conf.robots_txt and frappe.read_file(frappe.local.conf.robots_txt))
		or ""
	)
	return {"robots_txt": "\n\n".join(part for part in (configured.strip(), gameplan_robots_rules()) if part)}
