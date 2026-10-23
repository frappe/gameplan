# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""Live public URLs, split into bounded sitemaps; never cache permission decisions."""

import math
from urllib.parse import urlencode

import frappe
from frappe.query_builder.functions import Count, Max
from frappe.utils import get_datetime, get_url

from gameplan.public_access import public_access_enabled
from gameplan.public_seo import community_path, discussion_path, page_number, public_viewer, space_path

SITEMAP_SIZE = 1000
SECTIONS = {"communities": "GP Team", "spaces": "GP Project", "discussions": "GP Discussion"}
SITEMAP_PATH = "/gameplan_sitemap.xml"


def get_context(context):
	frappe.local.no_cache = True
	frappe.local.response_headers.update({"Cache-Control": "private, no-store", "X-Robots-Tag": "noindex"})
	context.links = []
	context.sitemaps = []
	if not public_access_enabled():
		return context
	with public_viewer():
		section = frappe.form_dict.get("section")
		if not section:
			for name, doctype in SECTIONS.items():
				table = frappe.qb.DocType(doctype)
				count = (
					frappe.qb.get_query(
						doctype, fields=[Count(table.name).as_("total")], ignore_permissions=False
					)
					.run(as_dict=True)[0]
					.total
				)
				for page in range(1, math.ceil(count / SITEMAP_SIZE) + 1):
					context.sitemaps.append(
						get_url(SITEMAP_PATH + "?" + urlencode({"section": name, "page": page}))
					)
			return context
		if section not in SECTIONS:
			frappe.throw("Page not found", frappe.DoesNotExistError)
		page = page_number(frappe.form_dict.get("page"))
		doctype = SECTIONS[section]
		fields = ["name", "modified"]
		if section == "spaces":
			fields += ["team"]
		elif section == "discussions":
			fields += ["project", "team", "slug", "last_post_at"]
		rows = frappe.get_list(
			doctype,
			fields=fields,
			order_by="name asc",
			start=(page - 1) * SITEMAP_SIZE,
			page_length=SITEMAP_SIZE,
		)
		if not rows and page > 1:
			frappe.throw("Page not found", frappe.DoesNotExistError)
		if section == "discussions":
			teams = dict(
				frappe.get_all(
					"GP Project",
					filters={"name": ["in", [row.project for row in rows]]},
					fields=["name", "team"],
					as_list=True,
				)
			)
			teams = {str(name): team for name, team in teams.items()}
			for row in rows:
				row.team = teams[str(row.project)]
		modified = discussion_updates(rows) if section == "discussions" else {}
		path_for = {
			"communities": lambda row: community_path(row.name),
			"spaces": space_path,
			"discussions": discussion_path,
		}[section]
		context.links = [
			frappe._dict(
				loc=get_url(path_for(row)),
				lastmod=max(
					get_datetime(row.modified), modified.get(str(row.name), get_datetime(row.modified))
				)
				.date()
				.isoformat(),
			)
			for row in rows
		]
	return context


def discussion_updates(rows):
	updates = {
		str(row.name): max(get_datetime(row.modified), get_datetime(row.last_post_at or row.modified))
		for row in rows
	}
	for doctype, parent in (("GP Comment", "reference_name"), ("GP Poll", "discussion")):
		table = frappe.qb.DocType(doctype)
		query = (
			frappe.qb.from_(table)
			.select(table[parent], Max(table.modified).as_("changed"))
			.where(table[parent].isin(list(updates)))
			.groupby(table[parent])
		)
		if doctype == "GP Comment":
			query = query.where(table.reference_doctype == "GP Discussion")
		for row in query.run(as_dict=True):
			key = str(row[parent])
			updates[key] = max(updates[key], get_datetime(row.changed))
	return updates
