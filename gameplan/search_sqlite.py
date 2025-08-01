# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt
import frappe
from frappe.search.sqlite_search import SQLiteSearch, SQLiteSearchIndexMissingError
from frappe.utils import cstr

import gameplan

INDEX_BUILD_FLAG = "discussions_index_in_progress"


class GameplanSearch(SQLiteSearch):
	"""
	Gameplan-specific search implementation extending FrappeSQLiteSearch.

	Provides full-text search for Gameplan documents with:
	- Permission filtering based on project access
	- Gameplan-specific document types (GP Discussion, GP Task, GP Page, GP Comment)
	- Custom scoring for different document types
	- Filter options for search interface
	"""

	INDEX_NAME = "gameplan_search.db"

	INDEX_SCHEMA = {
		"metadata_fields": ["team", "project", "tags", "owner", "reference_doctype", "reference_name"],
		"tokenizer": "unicode61 remove_diacritics 2 tokenchars '-_'",
	}

	INDEXABLE_DOCTYPES = {
		"GP Discussion": {
			"fields": ["name", "title", "content", {"modified": "last_post_at"}, "project", "team", "owner"],
		},
		"GP Task": {
			"fields": ["name", "title", {"content": "description"}, "modified", "project", "team", "owner"],
		},
		"GP Page": {
			"fields": ["name", "title", "content", "modified", "project", "team", "owner"],
		},
		"GP Comment": {
			"fields": ["name", "content", "modified", "reference_doctype", "reference_name", "owner"],
			"filters": {"deleted_at": ("is", "not set")},
		},
	}

	def is_search_enabled(self):
		"""Check if search functionality is disabled via site config."""
		disabled = frappe.conf.get("disable_gameplan_search", False)
		return not disabled

	def prepare_document(self, doc):
		"""Prepare a document for indexing with Gameplan-specific handling."""
		# Get base document from parent class
		document = super().prepare_document(doc)
		if not document:
			return None

		if doc.doctype == "GP Comment":
			# For comments, we need to resolve the project from the reference
			project, team = self._get_project_team_for_comment(doc)
			document["project"] = project
			document["team"] = team

		if doc.doctype in ["GP Discussion", "GP Comment"]:
			# Use cached tags lookup instead of individual queries
			tags = self._get_tags_for_document(doc.doctype, doc.name)
			document["tags"] = " ".join(tags) if tags else None

		return document

	def _get_tags_for_document(self, doctype, docname):
		"""Get tags for a specific document using cached tag data or fallback query."""
		# If we have a tags cache (bulk indexing), use it
		if hasattr(self, "_tags_cache"):
			cache_key = f"{doctype}:{docname}"
			return self._tags_cache.get(cache_key, [])

		# Fallback: single document query (for individual reindexing)
		tags = frappe.qb.get_query(
			"GP Tag Link",
			fields=["label"],
			filters={"parenttype": doctype, "parent": docname, "parentfield": "tags"},
		).run(pluck=True)
		return tags or []

	def _load_all_tags(self):
		"""Load all tags for GP Discussion and GP Comment documents into memory."""
		self._tags_cache = {}

		# Fetch all tag links for discussions and comments in one query
		tag_links = frappe.qb.get_query(
			"GP Tag Link",
			fields=["parenttype", "parent", "label"],
			filters={"parenttype": ("in", ["GP Discussion", "GP Comment"]), "parentfield": "tags"},
		).run(as_dict=True)

		# Group tags by document
		for tag_link in tag_links:
			cache_key = f"{tag_link['parenttype']}:{tag_link['parent']}"
			if cache_key not in self._tags_cache:
				self._tags_cache[cache_key] = []
			self._tags_cache[cache_key].append(tag_link["label"])

	def build_index(self):
		"""Build search index with optimized tag loading."""
		# Pre-load all tags for bulk indexing performance
		self._load_all_tags()

		try:
			# Call parent build_index method
			super().build_index()
		finally:
			# Clear tags cache after indexing to free memory
			if hasattr(self, "_tags_cache"):
				delattr(self, "_tags_cache")

	def get_search_filters(self):
		"""
		Return permission filters based on accessible projects.
		"""
		accessible_projects = self._get_accessible_projects()

		if not accessible_projects:
			# No accessible projects - return impossible condition
			return {"project": []}

		# Filter by accessible projects - convert to both string and int to handle type mismatches
		project_filters = []
		for project in accessible_projects:
			project_filters.append(str(project))
			try:
				project_filters.append(int(project))
			except (ValueError, TypeError):
				pass

		return {"project": list(set(project_filters))}  # Remove duplicates

	def _get_accessible_projects(self):
		"""Get list of projects accessible to current user."""
		from pypika.terms import ExistsCriterion

		if gameplan.is_guest():
			GuestAccess = frappe.qb.DocType("GP Guest Access")
			projects = (
				frappe.qb.from_(GuestAccess)
				.select(GuestAccess.project)
				.distinct()
				.where(GuestAccess.user == frappe.session.user)
				.run(pluck=True)
			)
			return [cstr(p) for p in projects] if projects else []

		Project = frappe.qb.DocType("GP Project")

		# Administrator has access to all projects
		if frappe.session.user == "Administrator":
			projects = frappe.qb.from_(Project).select(Project.name).distinct().run(pluck=True)
			return [cstr(p) for p in projects]

		Member = frappe.qb.DocType("GP Member")
		member_exists = (
			frappe.qb.from_(Member)
			.select(Member.name)
			.where(Member.parenttype == "GP Team")
			.where(Member.parent == Project.team)
			.where(Member.user == frappe.session.user)
		)
		projects = (
			frappe.qb.from_(Project)
			.select(Project.name)
			.distinct()
			.where((Project.is_private == 0) | ((Project.is_private == 1) & ExistsCriterion(member_exists)))
			.run(pluck=True)
		)
		return [cstr(p) for p in projects]

	def _get_project_team_for_comment(self, doc):
		"""Resolve project for a comment document with caching."""
		# Comments are linked to other documents, need to find the project from the reference
		if doc.reference_doctype and doc.reference_name:
			if not hasattr(self, "_comment_project_cache"):
				self._comment_project_cache = {}

			cache_key = f"{doc.reference_doctype}:{doc.reference_name}"

			if cache_key in self._comment_project_cache:
				return self._comment_project_cache[cache_key]

			result = frappe.db.get_value(doc.reference_doctype, doc.reference_name, ["project", "team"])
			if result:
				project_team = (result[0], result[1])
				self._comment_project_cache[cache_key] = project_team
				return project_team
			else:
				self._comment_project_cache[cache_key] = (None, None)

		return None, None

	@SQLiteSearch.scoring_function
	def _get_gameplan_doctype_boost(self, row, query, query_words):
		"""
		Provide custom scoring boosts for Gameplan document types.
		"""
		doctype = row["doctype"]
		if doctype == "GP Discussion":
			return 1.2
		return 1.0

	def search(self, query, title_only=False, filters=None):
		"""
		Enhanced search method that handles tag filtering using LIKE operations.
		"""
		# Convert tag filters to LIKE filters for the parent search
		if filters and "tags" in filters:
			tag_filters = filters.pop("tags")
			if tag_filters and isinstance(tag_filters, list) and len(tag_filters) > 0:
				# Convert to LIKE filter format for space-separated tag matching
				filters["tags"] = ["LIKE", tag_filters]

		# Call parent search with the converted filters
		return super().search(query, title_only, filters)

	def get_filter_options(self):
		"""
		Return filter options for the search interface.

		Returns:
			dict: Available filter options with counts
				- authors: dict mapping user names to counts
				- projects: dict mapping project names to counts
				- teams: dict mapping team names to counts
				- doctypes: dict mapping doctype names to counts
				- tags: dict mapping tag names to counts
		"""
		if not self.is_search_enabled() or not self.index_exists():
			return {"authors": {}, "projects": {}, "teams": {}, "doctypes": {}, "tags": {}}

		accessible_projects = self._get_accessible_projects()

		# If no accessible projects, return empty results
		if not accessible_projects:
			return {"authors": {}, "projects": {}, "teams": {}, "doctypes": {}, "tags": {}}

		conn = self._get_connection(read_only=True)
		try:
			# Get authors
			authors_query = """
                SELECT owner, COUNT(*) as count
                FROM search_fts
                WHERE project IN ({})
                GROUP BY owner
                ORDER BY count DESC
                LIMIT 20
            """.format(",".join(["?"] * len(accessible_projects)))
			authors = conn.execute(authors_query, accessible_projects).fetchall()

			# Get projects
			projects_query = """
                SELECT project, COUNT(*) as count
                FROM search_fts
                WHERE project IN ({})
                GROUP BY project
                ORDER BY count DESC
            """.format(",".join(["?"] * len(accessible_projects)))

			projects_with_count = conn.execute(projects_query, accessible_projects).fetchall()

			# Get teams
			teams_query = """
                SELECT team, COUNT(*) as count
                FROM search_fts
                WHERE team IS NOT NULL AND project IN ({})
                GROUP BY team
                ORDER BY count DESC
            """.format(",".join(["?"] * len(accessible_projects)))
			teams = conn.execute(teams_query, accessible_projects).fetchall()

			# Get doctypes
			doctypes_query = """
                SELECT doctype, COUNT(*) as count
                FROM search_fts
                WHERE project IN ({})
                GROUP BY doctype
                ORDER BY count DESC
            """.format(",".join(["?"] * len(accessible_projects)))
			doctypes = conn.execute(doctypes_query, accessible_projects).fetchall()

			# Get tags - split the tags field and count individual tags
			tags_query = """
                SELECT tags
                FROM search_fts
                WHERE tags IS NOT NULL AND tags != '' AND project IN ({})
            """.format(",".join(["?"] * len(accessible_projects)))
			tags_result = conn.execute(tags_query, accessible_projects).fetchall()

		finally:
			conn.close()

		# Process tags - count individual tags from space-separated strings
		tag_counts = {}
		for row in tags_result:
			if row["tags"]:
				individual_tags = row["tags"].split()
				for tag in individual_tags:
					tag_counts[tag] = tag_counts.get(tag, 0) + 1

		# Get project names for accessible projects with counts
		projects = []
		if accessible_projects:
			project_counts = {p["project"]: p["count"] for p in projects_with_count}
			project_details = frappe.get_all(
				"GP Project", filters={"name": ("in", accessible_projects)}, fields=["name", "title"]
			)
			for p in project_details:
				if p.name in project_counts:
					projects.append({"value": p.name, "label": p.title, "count": project_counts[p.name]})

		# Create count dictionaries for authors, teams, projects, and doctypes (frontend has the full data)
		author_counts = {a["owner"]: a["count"] for a in authors}
		team_counts = {t["team"]: t["count"] for t in teams}
		project_counts = {p["project"]: p["count"] for p in projects_with_count}
		doctype_counts = {dt["doctype"]: dt["count"] for dt in doctypes}

		return {
			"authors": author_counts,
			"projects": project_counts,
			"teams": team_counts,
			"doctypes": doctype_counts,
			"tags": tag_counts,
		}


class GameplanSearchIndexMissingError(SQLiteSearchIndexMissingError):
	pass


def build_index():
	"""Build search index in the current process."""
	search = GameplanSearch()
	search.build_index()
