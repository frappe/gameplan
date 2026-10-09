# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

"""Public forum search over the existing FTS index, with live permission checks."""

from html import escape

import frappe

from gameplan.public_access import anonymous_readable_criterion, public_access_enabled
from gameplan.public_payload import handles_for
from gameplan.search_sqlite import GameplanSearch, content_fingerprint

PUBLIC_SEARCH_DOCTYPES = ("GP Discussion", "GP Comment")
PUBLIC_SEARCH_FILTERS = frozenset({"project", "team", "doctype"})
SEARCH_FILTERS = PUBLIC_SEARCH_FILTERS | {"owner", "tags"}
MAX_QUERY_LENGTH = 200
MAX_QUERY_WORDS = 12
MAX_FILTER_VALUES = 20
MAX_PUBLIC_RESULTS = 50


class PublicGameplanSearch(GameplanSearch):
	"""Reuse ranking and snippets, but never expose the index as an authority."""

	def search(self, query: str, title_only=False, filters=None):
		require_public_search()
		if not isinstance(query, str) or len(query) > MAX_QUERY_LENGTH:
			frappe.throw("Search must be text of at most 200 characters.")
		query = query.strip()
		if len(query.split()) > MAX_QUERY_WORDS:
			frappe.throw("Search must contain at most 12 words.")
		filters = validate_search_filters(filters, anonymous=True)
		if len(query) < 2 or not self.index_exists():
			return self._empty_search_result(title_only, filters)

		effective_filters = {
			**filters,
			"doctype": [
				doctype
				for doctype in filters.get("doctype", PUBLIC_SEARCH_DOCTYPES)
				if doctype in PUBLIC_SEARCH_DOCTYPES
			],
		}
		response = super().search(query, title_only, effective_filters)
		results = self._public_results(response["results"])[:MAX_PUBLIC_RESULTS]
		response["results"] = results
		response["summary"]["applied_filters"] = filters
		# Candidate counts and ranking metadata may include stale, inaccessible records.
		for key in ("total_matches", "returned_matches", "filtered_matches"):
			response["summary"][key] = len(results)
		return response

	def _expand_query_with_corrections(self, query):
		# The shared vocabulary includes private posts. It is not a public suggestion source.
		return query, None

	def get_filter_options(self):
		require_public_search()
		options = {"authors": {}, "projects": {}, "teams": {}, "doctypes": {}, "tags": {}}
		if not self.is_search_enabled() or not self.index_exists():
			return options
		Project = frappe.qb.DocType("GP Project")
		spaces = (
			frappe.qb.from_(Project)
			.select(Project.name, Project.team)
			.where(Project.is_anonymous_readable == 1)
			.where(anonymous_readable_criterion(Project))
		).run(as_dict=True)
		# Public facets have no counts: counting every indexed post is too expensive here.
		options["projects"] = {str(space.name): 0 for space in spaces}
		options["teams"] = {space.team: 0 for space in spaces}
		options["doctypes"] = {doctype: 0 for doctype in PUBLIC_SEARCH_DOCTYPES}
		return options

	def _public_results(self, results):
		live_rows = self._live_rows(results)
		authors = handles_for({row.owner for row in live_rows.values()})
		public_results = []
		for result in results:
			row = live_rows.get(result["id"])
			if not row or str(result["project"]) != str(row.project) or result["team"] != row.team:
				continue
			if result.get("content_hash") != content_fingerprint(
				self._process_content(row.get("title")), self._process_content(row.content)
			):
				continue
			if result["doctype"] == "GP Comment" and (
				result["reference_doctype"] != "GP Discussion"
				or str(result["reference_name"]) != str(row.reference_name)
			):
				continue
			public_results.append(
				{
					"id": result["id"],
					"doctype": result["doctype"],
					"name": result["name"],
					"project": str(row.project),
					"team": row.team,
					"title": highlight_text(result.get("title")),
					"content": highlight_text(result.get("content")),
					"modified": result["modified"],
					"author": authors.get(row.owner, ""),
					"reference_doctype": result.get("reference_doctype"),
					"reference_name": result.get("reference_name"),
				}
			)
		return public_results

	def _live_rows(self, results):
		"""Two bounded queries check current permissions, parent metadata and text."""
		Project = frappe.qb.DocType("GP Project")
		Discussion = frappe.qb.DocType("GP Discussion")
		public_space = (Project.is_anonymous_readable == 1) & anonymous_readable_criterion(Project)
		rows = {}
		for doctype in PUBLIC_SEARCH_DOCTYPES:
			names = [result["name"] for result in results if result["doctype"] == doctype]
			if not names:
				continue
			Content = frappe.qb.DocType(doctype)
			query = frappe.qb.from_(Content)
			if doctype == "GP Discussion":
				query = query.select(Content.title)
			if doctype == "GP Comment":
				query = (
					query.join(Discussion)
					.on(Content.reference_name == Discussion.name)
					.select(Content.reference_name)
					.where((Content.reference_doctype == "GP Discussion") & Content.deleted_at.isnull())
				)
			live = (
				query.join(Project)
				.on(Discussion.project == Project.name)
				.select(
					Content.name, Content.owner, Content.content, Project.name.as_("project"), Project.team
				)
				.where(Content.name.isin(names) & public_space)
			).run(as_dict=True)
			rows.update({f"{doctype}:{row.name}": row for row in live})
		return rows


def require_public_search():
	if not public_access_enabled():
		frappe.throw("Not permitted", frappe.PermissionError)


def validate_search_filters(filters, *, anonymous=False):
	"""Only plain, bounded values may reach the FTS engine's SQL filter builder."""
	if filters is None or filters == "":
		return {}
	if isinstance(filters, str):
		if anonymous and len(filters) > 8000:
			frappe.throw("Search filters are too long.")
		try:
			filters = frappe.parse_json(filters)
		except ValueError:
			frappe.throw("Search filters must be a JSON object.")
	if not isinstance(filters, dict):
		frappe.throw("Search filters must be an object.")
	allowed = PUBLIC_SEARCH_FILTERS if anonymous else SEARCH_FILTERS
	if set(filters) - allowed:
		frappe.throw("Search contains an unsupported filter.", frappe.PermissionError)
	validated = {}
	for field, values in filters.items():
		values = values if isinstance(values, list) else [values]
		if field == "project":
			values = [str(value) if type(value) is int else value for value in values]
		if any(not isinstance(value, str) or not value for value in values):
			frappe.throw("Search filter values must be non-empty text.")
		if anonymous and (len(values) > MAX_FILTER_VALUES or any(len(value) > 140 for value in values)):
			frappe.throw("Each search filter must contain at most 20 short text values.")
		if field == "doctype" and any(value not in GameplanSearch.INDEXABLE_DOCTYPES for value in values):
			frappe.throw("Search contains an unsupported document type.")
		validated[field] = values.copy()
	return validated


def highlight_text(value):
	"""Render index text safely while keeping the FTS engine's highlight markers."""
	return escape(value or "").replace("&lt;mark&gt;", "<mark>").replace("&lt;/mark&gt;", "</mark>")
