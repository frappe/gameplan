# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

"""robots.txt: frappe's own (Website Settings or site config), plus Gameplan's rules.

Overrides frappe/www/robots.py, which serves only the configured text; an app installed
after frappe wins the route.
"""

from urllib.parse import quote

import frappe

from gameplan.public_access import public_access_enabled

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


def gameplan_robots_rules() -> str:
	"""Crawler rules for the app at /g: public spaces may be crawled, nothing else may.

	A space is listed exactly when someone not signed in may read it: public access is on and
	the space is anonymous-readable (`is_anonymous_readable`, kept current with the rule the
	permission checks use). Allow lines come first, for crawlers that take the first match;
	the others take the longest, which is also the Allow. The API is not blocked: it answers
	nobody more than they may read, and a crawler that renders the page needs it.
	"""
	lines = ["# Gameplan: only spaces anyone may read without signing in.", "User-agent: *"]
	if public_access_enabled():
		Project = frappe.qb.DocType("GP Project")
		spaces = (
			frappe.qb.from_(Project)
			.select(Project.team, Project.name)
			.where(Project.is_anonymous_readable == 1)
			.orderby(Project.team)
			.orderby(Project.name)
			.run()
		)
		for team, name in spaces:
			lines.append(f"Allow: /g/community/{quote(str(team))}/space/{quote(str(name))}/")
	lines.append("Disallow: /g/")
	return "\n".join(lines)
