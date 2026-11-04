# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

"""Public forum search over the existing FTS index, with live permission checks."""

from html import escape

import frappe
from frappe.query_builder.functions import Count
from frappe.search.sqlite_search import MAX_SEARCH_RESULTS

import gameplan
from gameplan.public_access import public_access_enabled
from gameplan.public_payload import handles_for
from gameplan.search_sqlite import GameplanSearch, content_fingerprint
from gameplan.visibility import anonymous_readable_criterion

PUBLIC_SEARCH_DOCTYPES = ("GP Discussion", "GP Comment")
PUBLIC_SEARCH_FILTERS = frozenset({"project", "team", "doctype"})
SEARCH_FILTERS = PUBLIC_SEARCH_FILTERS | {"owner", "tags"}
MAX_QUERY_LENGTH = 200
MAX_QUERY_WORDS = 12
MAX_FILTER_VALUES = 20
MAX_PUBLIC_RESULTS = 50


class PublicGameplanSearch(GameplanSearch):
	"""Reuse ranking and snippets, but never expose the index as an authority."""

	SEARCH_DOCTYPES = PUBLIC_SEARCH_DOCTYPES
	COMMENT_PARENTS = ("GP Discussion",)
	RESULT_LIMIT = MAX_PUBLIC_RESULTS

	def require_access(self):
		require_public_search()

	def validate_filters(self, filters):
		return validate_search_filters(filters, anonymous=True)

	def space_criterion(self, Project):
		return (Project.is_anonymous_readable == 1) & anonymous_readable_criterion(Project)

	def search(self, query: str, title_only=False, filters=None):
		self.require_access()
		if not isinstance(query, str) or len(query) > MAX_QUERY_LENGTH:
			frappe.throw("Search must be text of at most 200 characters.")
		query = query.strip()
		if len(query.split()) > MAX_QUERY_WORDS:
			frappe.throw("Search must contain at most 12 words.")
		filters = self.validate_filters(filters)
		if len(query) < 2 or not self.index_exists():
			return self._empty_search_result(title_only, filters)

		effective_filters = {
			**filters,
			"doctype": [
				doctype
				for doctype in filters.get("doctype", self.SEARCH_DOCTYPES)
				if doctype in self.SEARCH_DOCTYPES
			],
		}
		response = super().search(query, title_only, effective_filters)
		results = self._public_results(response["results"])[: self.RESULT_LIMIT]
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
		self.require_access()
		options = {"authors": {}, "projects": {}, "teams": {}, "doctypes": {}, "tags": {}}
		if not self.is_search_enabled() or not self.index_exists():
			return options
		Project = frappe.qb.DocType("GP Project")
		spaces = (
			frappe.qb.from_(Project).select(Project.name, Project.team).where(self.space_criterion(Project))
		).run(as_dict=True)
		# Public facets have no counts: counting every indexed post is too expensive here.
		options["projects"] = {str(space.name): 0 for space in spaces}
		options["teams"] = {space.team: 0 for space in spaces}
		options["doctypes"] = {doctype: 0 for doctype in self.SEARCH_DOCTYPES}
		return options

	def _public_results(self, results):
		live_rows = self._live_rows(results)
		authors = handles_for({row.owner for row in live_rows.values()})
		if gameplan.is_guest():
			authors[frappe.session.user] = frappe.session.user
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
				result["reference_doctype"] != row.reference_doctype
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
		"""A fixed number of batched queries, never one permission lookup per result."""
		rows = {}
		for doctype in self.SEARCH_DOCTYPES:
			names = [result["name"] for result in results if result["doctype"] == doctype]
			if not names:
				continue
			for query, Content, Project in self.live_queries(doctype):
				content = Content.description if doctype == "GP Task" else Content.content
				query = query.select(
					Content.name,
					Content.owner,
					content.as_("content"),
					Project.name.as_("project"),
					Project.team,
				)
				if doctype == "GP Comment":
					query = query.select(Content.reference_name, Content.reference_doctype)
				else:
					query = query.select(Content.title)
				live = query.where(Content.name.isin(names)).run(as_dict=True)
				rows.update({f"{doctype}:{row.name}": row for row in live})
		return rows

	def live_queries(self, doctype):
		Content = frappe.qb.DocType(doctype)
		Project = frappe.qb.DocType("GP Project")
		parents = self.COMMENT_PARENTS if doctype == "GP Comment" else (doctype,)
		for parent_doctype in parents:
			Parent = frappe.qb.DocType(parent_doctype)
			query = frappe.qb.from_(Content)
			if doctype == "GP Comment":
				query = (
					query.join(Parent)
					.on(Content.reference_name == Parent.name)
					.where((Content.reference_doctype == parent_doctype) & Content.deleted_at.isnull())
				)
			yield (
				query.join(Project).on(Parent.project == Project.name).where(self.space_criterion(Project)),
				Content,
				Project,
			)


class GuestGameplanSearch(PublicGameplanSearch):
	"""Guests keep granted content and filters, but stale FTS rows cannot grant access."""

	SEARCH_DOCTYPES = tuple(GameplanSearch.INDEXABLE_DOCTYPES)
	COMMENT_PARENTS = ("GP Discussion", "GP Task")
	RESULT_LIMIT = MAX_SEARCH_RESULTS

	def require_access(self):
		if not gameplan.is_guest():
			frappe.throw("Not permitted", frappe.PermissionError)

	def space_criterion(self, Project):
		GuestAccess = frappe.qb.DocType("GP Guest Access")
		granted = Project.name.isin(
			frappe.qb.from_(GuestAccess)
			.select(GuestAccess.project)
			.where(GuestAccess.user == frappe.session.user)
		)
		return granted | super().space_criterion(Project) if public_access_enabled() else granted

	def validate_filters(self, filters):
		from gameplan.guest_payload import users_for_handles
		from gameplan.public_payload import looks_like_user_id

		filters = validate_search_filters(filters, bounded=True)
		owners = filters.get("owner", [])
		if any(looks_like_user_id(owner) and owner != frappe.session.user for owner in owners):
			frappe.throw("Use profile handles to filter authors.", frappe.PermissionError)
		if owners:
			users = users_for_handles(owners)
			filters["owner"] = [users.get(owner, owner) for owner in owners]
		return filters

	def search(self, *args, **kwargs):
		from gameplan.guest_payload import for_guest

		return for_guest(super().search(*args, **kwargs))

	def get_filter_options(self):
		from gameplan.guest_payload import for_guest

		options = super().get_filter_options()
		if not self.is_search_enabled() or not self.index_exists():
			return options
		Tag = frappe.qb.DocType("GP Tag Link")
		# Facets come from current readable rows, not stale indexed authors or tags.
		for doctype in self.SEARCH_DOCTYPES:
			for query, Content, Project in self.live_queries(doctype):
				counts = (
					query.select(
						Content.owner,
						Project.name.as_("project"),
						Project.team,
						Count(Content.name).as_("count"),
					)
					.groupby(Content.owner, Project.name, Project.team)
					.run(as_dict=True)
				)
				for row in counts:
					for facet, value in (
						("authors", row.owner),
						("projects", str(row.project)),
						("teams", row.team),
						("doctypes", doctype),
					):
						options[facet][value] = options[facet].get(value, 0) + row.count
				if doctype in ("GP Discussion", "GP Comment"):
					tags = (
						query.join(Tag)
						.on(
							(Tag.parenttype == doctype)
							& (Tag.parent == Content.name)
							& (Tag.parentfield == "tags")
						)
						.select(Tag.label, Count(Tag.name).as_("count"))
						.groupby(Tag.label)
						.run(as_dict=True)
					)
					for tag in tags:
						if tag.label:
							options["tags"][tag.label] = options["tags"].get(tag.label, 0) + tag.count
		return for_guest(options)


def search_for_viewer():
	if gameplan.is_anonymous():
		return PublicGameplanSearch()
	if gameplan.is_guest():
		return GuestGameplanSearch()
	return GameplanSearch()


def require_public_search():
	if not public_access_enabled():
		frappe.throw("Not permitted", frappe.PermissionError)


def validate_search_filters(filters, *, anonymous=False, bounded=False):
	"""Only plain, bounded values may reach the FTS engine's SQL filter builder."""
	if filters is None or filters == "":
		return {}
	if isinstance(filters, str):
		if (anonymous or bounded) and len(filters) > 8000:
			frappe.throw("Search filters are too long.")
		try:
			filters = frappe.parse_json(filters)
		except ValueError:
			frappe.throw("Search filters must be a JSON object.")
	if not isinstance(filters, dict):
		frappe.throw("Search filters must be an object.")
	allowed = PUBLIC_SEARCH_FILTERS if anonymous else SEARCH_FILTERS
	if set(filters) - allowed:
		frappe.throw(
			"Search contains an unsupported filter.",
			frappe.PermissionError if anonymous or bounded else frappe.ValidationError,
		)
	validated = {}
	for field, values in filters.items():
		values = values if isinstance(values, list) else [values]
		if field == "project":
			values = [str(value) if type(value) is int else value for value in values]
		if any(not isinstance(value, str) or not value for value in values):
			frappe.throw("Search filter values must be non-empty text.")
		if (anonymous or bounded) and (
			len(values) > MAX_FILTER_VALUES or any(len(value) > 140 for value in values)
		):
			frappe.throw("Each search filter must contain at most 20 short text values.")
		if field == "doctype" and any(value not in GameplanSearch.INDEXABLE_DOCTYPES for value in values):
			frappe.throw("Search contains an unsupported document type.")
		validated[field] = values.copy()
	return validated


def highlight_text(value):
	"""Render index text safely while keeping the FTS engine's highlight markers."""
	return escape(value or "").replace("&lt;mark&gt;", "<mark>").replace("&lt;/mark&gt;", "</mark>")
