# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt
import re
import time

import frappe
from frappe.search.sqlite_search import (
	MIN_RECENCY_BOOST,
	RECENCY_DECAY_RATE,
	RECENT_HOURS_BOOST,
	RECENT_MONTH_BOOST,
	RECENT_QUARTER_BOOST,
	RECENT_WEEK_BOOST,
	SQLiteSearch,
	SQLiteSearchIndexMissingError,
)
from frappe.utils import cstr

from gameplan.permissions import project_access_criterion

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

	def build_index(self, **kwargs):
		"""Build search index with optimized tag loading."""
		# Pre-load all tags for bulk indexing performance
		self._load_all_tags()

		try:
			# Call parent build_index method
			super().build_index(**kwargs)
		finally:
			# Clear tags cache after indexing to free memory
			if hasattr(self, "_tags_cache"):
				delattr(self, "_tags_cache")

	def get_search_filters(self):
		"""
		Return permission filters based on accessible projects.
		"""
		accessible_projects = self._get_accessible_projects()
		# Frappe's SQLiteSearch overwrites a user filter when a permission filter uses
		# the same field. An upstream intersection API still needs opening; until then,
		# fold the selected spaces into Gameplan's permission filter so it only narrows.
		requested_projects = getattr(self, "_requested_projects", None)
		if requested_projects is not None:
			requested_projects = {
				cstr(project)
				for project in (
					requested_projects
					if isinstance(requested_projects, list | tuple | set)
					else [requested_projects]
				)
			}
			accessible_projects = [
				project for project in accessible_projects if cstr(project) in requested_projects
			]

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
		Project = frappe.qb.DocType("GP Project")
		query = frappe.qb.from_(Project).select(Project.name).distinct()
		criterion = project_access_criterion(Project)
		if criterion is not None:
			query = query.where(criterion)
		projects = query.run(pluck=True)
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

	def _get_base_score(self, row, query):
		bm25_score = row["bm25_score"]
		if bm25_score is None:
			return 0.5
		if bm25_score < 0:
			return abs(bm25_score)
		if bm25_score == 0:
			return 1.0
		return 1.0 / (1.0 + bm25_score)

	def _get_title_boost(self, row, query, query_words):
		title_words = self._get_words(row["original_title"])
		query_words = self._get_words(query)

		if self._has_title_phrase_match(title_words, query_words):
			return 3.0

		if not query_words:
			return 1.0

		matched_words = sum(1 for word in query_words if self._has_matching_title_word(title_words, word))
		if not matched_words:
			return 1.0

		return 1.0 + (0.5 * matched_words / len(query_words))

	def _get_recency_boost(self, row, query):
		modified = self._get_row_value(row, "modified")
		if modified in (None, ""):
			return 1.0

		try:
			doc_timestamp = float(modified)
		except (TypeError, ValueError):
			return 1.0

		hours_old = (time.time() - doc_timestamp) / 3600
		days_old = hours_old / 24

		if hours_old <= 24:
			return RECENT_HOURS_BOOST
		if days_old <= 7:
			return RECENT_WEEK_BOOST
		if days_old <= 30:
			return RECENT_MONTH_BOOST
		if days_old <= 90:
			return RECENT_QUARTER_BOOST

		days_beyond_90 = days_old - 90
		return max(MIN_RECENCY_BOOST, RECENT_QUARTER_BOOST - (days_beyond_90 * RECENCY_DECAY_RATE))

	def _get_row_value(self, row, field, default=None):
		if hasattr(row, "keys") and field not in row.keys():
			return default

		try:
			return row[field]
		except (KeyError, IndexError, TypeError):
			return default

	def _get_words(self, text):
		return re.findall(r"\w+", (text or "").lower())

	def _has_title_phrase_match(self, title_words, query_words):
		if not query_words or len(query_words) > len(title_words):
			return False

		for index in range(len(title_words) - len(query_words) + 1):
			phrase_words = title_words[index : index + len(query_words)]
			if all(
				self._is_matching_title_word(title_word, query_word)
				for title_word, query_word in zip(phrase_words, query_words, strict=True)
			):
				return True

		return False

	def _has_matching_title_word(self, title_words, query_word):
		return any(self._is_matching_title_word(title_word, query_word) for title_word in title_words)

	def _is_matching_title_word(self, title_word, query_word):
		if title_word == query_word:
			return True
		return len(query_word) > 2 and title_word == f"{query_word}s"

	def search(self, query, title_only=False, filters=None):
		"""
		Enhanced search method that handles tag filtering using LIKE operations.
		"""
		filters = filters.copy() if filters else {}
		self._requested_projects = filters.get("project")
		try:
			# Convert tag filters to LIKE filters for the parent search
			if "tags" in filters:
				tag_filters = filters.pop("tags")
				if tag_filters and isinstance(tag_filters, list) and len(tag_filters) > 0:
					# Convert to LIKE filter format for space-separated tag matching
					filters["tags"] = ["LIKE", tag_filters]

			# Call parent search with the converted filters
			return super().search(query, title_only, filters)
		finally:
			del self._requested_projects

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


def rebuild_index():
	"""Rebuild the search index from scratch in the current process.

	Dropping the file first is what makes this a *re*build. ``SQLiteSearch.build_index``
	only issues ``DELETE FROM search_fts`` on the fresh-file path — the ``DELETE`` is
	guarded by ``temp_db_path``, which is set only when ``index_exists()`` is false — so
	calling it over an existing index upserts the current database on top of whatever
	the index already held. Every row for a document that has since been deleted
	survives, which is how an index ends up with orders of magnitude more rows than the
	site has documents.

	Callers are the flows that have just replaced the entire corpus (demo reseed, UI
	test scenario reset), so a stale row is never merely out of date — it points at a
	document that no longer exists.
	"""
	search = GameplanSearch()
	search.drop_index()
	search.build_index()
