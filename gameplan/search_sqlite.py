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
		"metadata_fields": [
			"team",
			"project",
			"owner",
		],
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

		# Add Gameplan-specific metadata that needs special handling
		if doc.doctype == "GP Comment":
			# For comments, we need to resolve the project from the reference
			project, team = self._get_project_team_for_comment(doc)
			document["project"] = project
			document["team"] = team

		return document

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
		"""Resolve project for a comment document."""
		# Comments are linked to other documents, need to find the project from the reference
		if doc.reference_doctype and doc.reference_name:
			result = frappe.db.get_value(doc.reference_doctype, doc.reference_name, ["project", "team"])
			if result:
				return result[0], result[1]  # Return project and team

		return None, None

	def get_scoring_pipeline(self):
		"""
		Return the scoring pipeline for Gameplan search.
		"""
		return [
			self._get_base_score,
			self._get_title_boost,
			self._get_recency_boost,
			self._get_gameplan_doctype_boost,
		]

	def _get_gameplan_doctype_boost(self, row, query, query_words):
		"""
		Provide custom scoring boosts for Gameplan document types.
		"""
		doctype = row["doctype"]
		if doctype == "GP Discussion":
			return 1.2
		return 1.0

	def get_filter_options(self):
		"""
		Return filter options for the search interface.

		Returns:
			dict: Available filter options with counts
				- authors: dict mapping user names to counts
				- projects: dict mapping project names to counts
				- teams: dict mapping team names to counts
				- doctypes: dict mapping doctype names to counts
		"""
		if not self.is_search_enabled() or not self.index_exists():
			return {"authors": {}, "projects": {}, "teams": {}, "doctypes": {}}

		accessible_projects = self._get_accessible_projects()

		# If no accessible projects, return empty results
		if not accessible_projects:
			return {"authors": {}, "projects": {}, "teams": {}, "doctypes": {}}

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

		finally:
			conn.close()

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
		}


class GameplanSearchIndexMissingError(SQLiteSearchIndexMissingError):
	pass


# Module-level Functions


def build_index():
	"""Build search index in the current process."""
	search = GameplanSearch()
	frappe.cache().set_value(INDEX_BUILD_FLAG, True)
	search.build_index()
	frappe.cache().set_value(INDEX_BUILD_FLAG, False)


def build_index_in_background():
	"""Enqueue index building in background."""
	search = GameplanSearch()
	if not search.is_search_enabled():
		return
	if not frappe.cache().get_value("discussions_index_in_progress"):
		frappe.enqueue("gameplan.search_sqlite.build_index", queue="long")


def build_index_if_not_exists():
	"""Build index if it doesn't exist."""
	search = GameplanSearch()
	if not search.is_search_enabled():
		return
	if not search.index_exists() or not frappe.cache.exists(INDEX_BUILD_FLAG):
		build_index_in_background()


def index_document(doctype, docname):
	"""Index a single document (background job)."""
	search = GameplanSearch()
	if not search.is_search_enabled():
		return
	search._index_doc(doctype, docname)


def remove_document(doctype, docname):
	"""Remove a single document from index (background job)."""
	search = GameplanSearch()
	if not search.is_search_enabled():
		return
	search._remove_doc(doctype, docname)
