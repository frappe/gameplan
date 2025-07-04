# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt


import datetime
import os
import re
import sqlite3
import time

import frappe
from bs4 import BeautifulSoup
from frappe.utils import cstr, update_progress_bar

import gameplan

INDEX_BUILD_FLAG = "discussions_index_in_progress"

# Search Configuration Constants
MAX_SEARCH_RESULTS = 100
SNIPPET_LENGTH = 64
MIN_WORD_LENGTH = 3
MAX_EDIT_DISTANCE = 3
MIN_SIMILARITY_THRESHOLD = 0.6
MAX_SPELLING_SUGGESTIONS = 3
SIMILARITY_TRIGRAM_WEIGHT = 0.7
SIMILARITY_SEQUENCE_WEIGHT = 0.3
FREQUENCY_BOOST_FACTOR = 1000
MAX_FREQUENCY_BOOST = 1.2
RECENCY_DECAY_RATE = 0.01
MIN_RECENCY_BOOST = 0.3
TITLE_EXACT_MATCH_BOOST = 2.0
TITLE_PARTIAL_MATCH_BOOST = 1.5
DISCUSSION_BOOST = 1.2
COMMENT_BOOST = 1.0
DEFAULT_DOCTYPE_BOOST = 1.0

# Time-based recency categories for aggressive boosting
RECENT_HOURS_BOOST = 2.0  # Documents from last 24 hours
RECENT_WEEK_BOOST = 1.5  # Documents from last 7 days
RECENT_MONTH_BOOST = 1.2  # Documents from last 30 days
RECENT_QUARTER_BOOST = 1.1  # Documents from last 90 days


class GameplanSearchIndexMissingError(Exception):
	pass


class GameplanSearch:
	"""
	SQLite FTS5-based search engine for Gameplan documents.

	Provides full-text search with advanced features:
	- Spelling correction using trigram similarity
	- Time-based recency boost with categorical scoring (24hrs/week/month/quarter)
	- Linear decay for documents older than 90 days
	- Custom scoring with title matching and document type boosts
	- Ranking tracking (original BM25 vs modified scores)
	- Filtering by author, project, team, and document type
	- Permission-aware search results
	"""

	def __init__(self) -> None:
		self.db_path = self._get_db_path()
		self.doc_configs = {
			"GP Discussion": {
				"fields": [
					"name",
					"title",
					"content",
					"last_post_at",
					"modified",
					"project",
					"team",
					"owner",
				],
				"content_field": "content",
				"title_field": "title",
				"modified_field": "last_post_at",
			},
			"GP Task": {
				"fields": ["name", "title", "description", "modified", "project", "team", "owner"],
				"content_field": "description",
				"title_field": "title",
				"modified_field": "modified",
			},
			"GP Page": {
				"fields": ["name", "title", "content", "modified", "project", "team", "owner"],
				"content_field": "content",
				"title_field": "title",
				"modified_field": "modified",
			},
			"GP Comment": {
				"fields": ["name", "content", "modified", "reference_doctype", "reference_name", "owner"],
				"content_field": "content",
				"title_field": None,
				"modified_field": "modified",
				"filters": {"deleted_at": ("is", "not set")},
			},
		}
		self._validate_config()

	# Public API Methods

	def search(self, query, title_only=False, filters=None):
		"""
		Main search method with advanced filtering support.

		Args:
			query (str): Search query text
			title_only (bool): Whether to search only in titles
			filters (dict): Optional filters by owner, project, team, doctype

		Returns:
			dict: Search results with summary statistics
		"""
		if not self.is_search_enabled():
			return self._empty_search_result(title_only, filters)

		self.raise_if_not_indexed()

		if not query:
			return self._empty_search_result(title_only, filters)

		start_time = time.time()

		# Prepare filters if provided
		filters = filters or {}

		# Prepare FTS5 query with spelling correction
		expanded_query, corrections = self._expand_query_with_corrections(query)
		fts_query = self._prepare_fts_query(expanded_query)

		conn = self._get_connection(read_only=True)
		try:
			raw_results = self._execute_search_query(conn, fts_query, title_only, filters)
			total_matches = len(raw_results)
		finally:
			conn.close()

		# Get accessible projects for filtering
		accessible_projects = self.get_accessible_projects()

		# Process and filter results
		filtered_results = self._process_search_results(raw_results, accessible_projects, query)

		duration = time.time() - start_time

		return {
			"results": filtered_results,
			"summary": {
				"duration": round(duration, 3),
				"total_matches": total_matches,
				"returned_matches": total_matches,
				"corrected_words": corrections,
				"corrected_query": expanded_query if corrections else None,
				"title_only": title_only,
				"filtered_matches": len(filtered_results),
				"applied_filters": filters,
			},
		}

	def build_index(self):
		"""Build the complete search index from scratch using atomic replacement."""
		if not self.is_search_enabled():
			return

		# Use temporary database path for atomic replacement
		temp_db_path = self._get_db_path(is_temp=True)
		original_db_path = self.db_path

		# Remove temp file if it exists
		if os.path.exists(temp_db_path):
			os.unlink(temp_db_path)

		# Temporarily switch to temp database for building
		self.db_path = temp_db_path

		try:
			if not hasattr(frappe.local, "request"):
				update_progress_bar("Setting up search tables", 0, 100, absolute=True)

			# Setup tables in temp database
			self._ensure_fts_table()

			if not hasattr(frappe.local, "request"):
				update_progress_bar("Fetching records", 20, 100, absolute=True)

			records = self.get_records()
			documents = []

			if not hasattr(frappe.local, "request"):
				update_progress_bar("Preparing documents", 30, 100, absolute=True)

			total_records = len(records)
			for i, doc in enumerate(records):
				document = self._prepare_document(doc)
				if document:
					documents.append(document)

				# Update progress during document preparation
				if not hasattr(frappe.local, "request") and i % 100 == 0:
					progress = 30 + int((i / total_records) * 20)  # 30-50% range
					update_progress_bar("Preparing documents", progress, 100, absolute=True)

			if not hasattr(frappe.local, "request"):
				update_progress_bar("Indexing documents", 50, 100, absolute=True)

			self._index_documents(documents)

			if not hasattr(frappe.local, "request"):
				update_progress_bar("Building spell correction vocabulary", 80, 100, absolute=True)

			# Build vocabulary for spelling correction
			self._build_vocabulary(documents)

			# Atomic replacement: move temp database to final location
			if os.path.exists(original_db_path):
				os.unlink(original_db_path)
			os.rename(temp_db_path, original_db_path)

			if not hasattr(frappe.local, "request"):
				update_progress_bar("Search index build complete", 100, 100, absolute=True)

		except Exception:
			# Clean up temp file on error
			if os.path.exists(temp_db_path):
				os.unlink(temp_db_path)
			raise
		finally:
			# Restore original database path
			self.db_path = original_db_path

	def index_doc(self, doc):
		"""Index a single document in background."""
		if not self.is_search_enabled():
			return
		frappe.enqueue("gameplan.search_sqlite.index_document", doctype=doc.doctype, docname=doc.name)

	def remove_doc(self, doc):
		"""Remove a single document from the index."""
		if not self.is_search_enabled():
			return
		frappe.enqueue("gameplan.search_sqlite.remove_document", doctype=doc.doctype, docname=doc.name)

	def get_filter_options(self):
		"""
		Get available filter options for search interface.

		Returns:
			dict: Available authors, projects, teams, and doctypes with counts
		"""
		if not self.is_search_enabled() or not self.index_exists():
			return {"authors": [], "projects": [], "teams": [], "doctypes": []}

		accessible_projects = self.get_accessible_projects()

		# If no accessible projects, return empty results
		if not accessible_projects:
			return {"authors": [], "projects": [], "teams": [], "doctypes": []}

		conn = self._get_connection(read_only=True)
		try:
			project_placeholders = ",".join(["?" for _ in accessible_projects])

			# Get distinct authors from accessible projects
			authors_sql = f"""
				SELECT DISTINCT owner, COUNT(*) as count
				FROM gameplan_fts
				WHERE project IN ({project_placeholders})
				AND owner IS NOT NULL
				AND owner != ''
				GROUP BY owner
				ORDER BY count DESC, owner
			"""
			authors = conn.execute(authors_sql, accessible_projects).fetchall()

			# Get distinct teams from accessible projects
			teams_sql = f"""
				SELECT DISTINCT team, COUNT(*) as count
				FROM gameplan_fts
				WHERE project IN ({project_placeholders})
				AND team IS NOT NULL
				AND team != ''
				GROUP BY team
				ORDER BY count DESC, team
			"""
			teams = conn.execute(teams_sql, accessible_projects).fetchall()

			# Get distinct doctypes
			doctypes_sql = f"""
				SELECT DISTINCT doctype, COUNT(*) as count
				FROM gameplan_fts
				WHERE project IN ({project_placeholders})
				GROUP BY doctype
				ORDER BY count DESC, doctype
			"""
			doctypes = conn.execute(doctypes_sql, accessible_projects).fetchall()

			# Get project counts
			projects_sql = f"""
				SELECT DISTINCT project, COUNT(*) as count
				FROM gameplan_fts
				WHERE project IN ({project_placeholders})
				AND project IS NOT NULL
				AND project != ''
				GROUP BY project
				ORDER BY count DESC, project
			"""
			project_counts = conn.execute(projects_sql, accessible_projects).fetchall()

		finally:
			conn.close()

		# Get project names for accessible projects with counts
		projects = []
		if accessible_projects:
			project_data = frappe.db.get_all(
				"GP Project",
				filters={"name": ("in", accessible_projects)},
				fields=["name", "title"],
				order_by="title",
			)

			# Create a map of project counts
			project_count_map = {pc["project"]: pc["count"] for pc in project_counts}

			projects = [
				{
					"value": p.name,
					"label": p.title or p.name,
					"count": project_count_map.get(str(p.name), 0),  # Convert to string for lookup
				}
				for p in project_data
			]

		# Format user data for authors
		author_list = []
		if authors:
			user_names = [author["owner"] for author in authors]
			user_data = frappe.db.get_all(
				"User", filters={"name": ("in", user_names)}, fields=["name", "full_name", "user_image"]
			)
			user_map = {u.name: u for u in user_data}

			for author in authors:
				user = user_map.get(author["owner"])
				author_list.append(
					{
						"value": author["owner"],
						"label": user.full_name if user else author["owner"],
						"image": user.user_image if user else None,
						"count": author["count"],
					}
				)

		return {
			"authors": author_list,
			"projects": projects,
			"teams": [
				{"value": team["team"], "label": team["team"], "count": team["count"]} for team in teams
			],
			"doctypes": [
				{"value": dt["doctype"], "label": dt["doctype"].replace("GP ", ""), "count": dt["count"]}
				for dt in doctypes
			],
		}

	# Status and Validation Methods

	def index_exists(self):
		"""Check if FTS index exists and has data."""
		if not os.path.exists(self.db_path):
			return False

		conn = self._get_connection(read_only=True)
		try:
			cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='gameplan_fts'")
			table_exists = cursor.fetchone() is not None

			if not table_exists:
				return False

			# Check if table has data
			cursor = conn.execute("SELECT COUNT(*) FROM gameplan_fts LIMIT 1")
			count = cursor.fetchone()[0]
			return count > 0
		except sqlite3.Error:
			return False
		finally:
			conn.close()

	def is_search_enabled(self):
		"""Check if search functionality is disabled via site config."""
		disabled = frappe.conf.get("disable_gameplan_search", False)
		return not disabled

	def raise_if_not_indexed(self):
		"""Raise exception if search index doesn't exist."""
		if not self.index_exists():
			raise GameplanSearchIndexMissingError(
				"Search index does not exist. Please build the index first."
			)

	# Data Access Methods

	def get_accessible_projects(self):
		"""Get list of projects accessible to current user."""
		from pypika.terms import ExistsCriterion

		if gameplan.is_guest():
			GuestAccess = frappe.qb.DocType("GP Guest Access")
			return (
				frappe.qb.from_(GuestAccess)
				.select(GuestAccess.project)
				.distinct()
				.where(GuestAccess.user == frappe.session.user)
				.run(pluck=True)
			)

		Project = frappe.qb.DocType("GP Project")
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

	def get_records(self):
		"""Get all records to be indexed."""
		records = []
		for doctype, config in self.doc_configs.items():
			docs = frappe.db.get_all(doctype, fields=config["fields"], filters=config.get("filters", {}))

			for doc in docs:
				doc.doctype = doctype
				if config["modified_field"] != "modified":
					doc.modified = getattr(doc, config["modified_field"], None) or doc.modified
				records.append(doc)

		return records

	# Private Search Implementation

	def _execute_search_query(self, conn, fts_query, title_only, filters):
		"""Execute the FTS search query with optional filters."""
		# Build filter conditions
		filter_conditions = []
		filter_params = []

		if filters:
			# Build filter conditions dynamically
			for field, values in filters.items():
				if not values:  # Skip empty filters
					continue

				if isinstance(values, list):
					if len(values) == 1:
						filter_conditions.append(f"{field} = ?")
						filter_params.append(values[0])
					else:
						placeholders = ",".join(["?" for _ in values])
						filter_conditions.append(f"{field} IN ({placeholders})")
						filter_params.extend(values)
				else:
					filter_conditions.append(f"{field} = ?")
					filter_params.append(values)

		# Combine filter conditions with AND
		filter_clause = ""
		if filter_conditions:
			filter_clause = "AND " + " AND ".join(filter_conditions)

		if title_only:
			sql = f"""
				SELECT
					doc_id,
					highlight(gameplan_fts, 1, '<mark>', '</mark>') as title,
					content, timestamp, doctype, name, project, owner, team,
					reference_doctype, reference_name,
					bm25(gameplan_fts) as bm25_score,
					title as original_title
				FROM gameplan_fts
				WHERE gameplan_fts MATCH ?
				AND title MATCH ?
				{filter_clause}
				ORDER BY bm25_score
				LIMIT ?
			"""
			cursor = conn.execute(sql, (fts_query, fts_query, *filter_params, MAX_SEARCH_RESULTS))
		else:
			sql = f"""
				SELECT
					doc_id,
					highlight(gameplan_fts, 1, '<mark>', '</mark>') as title,
					snippet(gameplan_fts, 2, '<mark>', '</mark>', '...', ?) as content,
					timestamp, doctype, name, project, owner, team,
					reference_doctype, reference_name,
					bm25(gameplan_fts) as bm25_score,
					title as original_title
				FROM gameplan_fts
				WHERE gameplan_fts MATCH ?
				{filter_clause}
				ORDER BY bm25_score
				LIMIT ?
			"""
			cursor = conn.execute(sql, (SNIPPET_LENGTH, fts_query, *filter_params, MAX_SEARCH_RESULTS))

		return cursor.fetchall()

	def _process_search_results(self, raw_results, accessible_projects, query):
		"""Process and filter search results with original and modified rankings."""
		filtered_results = []
		query_words = query.split()

		# Batch collect comment references that need project lookup
		comment_refs = []
		for row in raw_results:
			if row["doctype"] == "GP Comment" and row["reference_doctype"] and row["reference_name"]:
				comment_refs.append((row["reference_doctype"], row["reference_name"]))

		# Batch query for comment projects (much more efficient)
		comment_projects = {}
		if comment_refs:
			for doctype, name in comment_refs:
				key = f"{doctype}:{name}"
				if key not in comment_projects:
					try:
						project = frappe.db.get_value(doctype, name, "project")
						comment_projects[key] = project
					except Exception:
						comment_projects[key] = None
		# 1-based ranking
		for original_rank, row in enumerate(raw_results, 1):
			project = row["project"]

			# For comments, get project from our batch lookup
			if row["doctype"] == "GP Comment" and row["reference_doctype"] and row["reference_name"]:
				key = f"{row['reference_doctype']}:{row['reference_name']}"
				project = comment_projects.get(key, None)

			if project in accessible_projects:
				# Apply advanced heuristics scoring
				score = self._calculate_advanced_score(row, query, query_words)

				filtered_results.append(
					{
						"id": row["doc_id"],
						"title": row["title"] or "",
						"content": row["content"] or "",
						"timestamp": row["timestamp"],
						"score": score,
						"original_rank": original_rank,
						"bm25_score": row["bm25_score"],
						"doctype": row["doctype"],
						"name": row["name"],
						"project": project,
						"team": row["team"],
						"reference_doctype": row["reference_doctype"],
						"reference_name": row["reference_name"],
						"author": row["owner"],
					}
				)

		# Sort by custom score (descending - higher is better)
		filtered_results.sort(key=lambda x: x["score"], reverse=True)

		# Add modified ranking after custom scoring
		for i, result in enumerate(filtered_results):
			result["modified_rank"] = i + 1

		return filtered_results

	def _calculate_advanced_score(self, row, query, query_words):
		"""Apply advanced heuristics to improve search scoring."""
		# Base BM25 score from FTS5 (negative value, lower = better)
		bm25_score = abs(row["bm25_score"]) if row["bm25_score"] is not None else 0
		base_score = 1.0 / (1.0 + bm25_score) if bm25_score > 0 else 0.5

		# Title matching boost (2x for exact matches in title)
		title_boost = 1.0
		original_title = (row["original_title"] or "").lower()
		query_lower = query.lower()

		if query_lower in original_title:
			title_boost = TITLE_EXACT_MATCH_BOOST
		elif any(word.lower() in original_title for word in query_words):
			title_boost = TITLE_PARTIAL_MATCH_BOOST

		# Time-based recency boost with aggressive categories
		current_time = time.time()
		doc_timestamp = row["timestamp"] if row["timestamp"] is not None else current_time
		hours_old = (current_time - doc_timestamp) / 3600
		days_old = hours_old / 24

		# Apply categorical time-based boosts
		if hours_old <= 24:
			recency_boost = RECENT_HOURS_BOOST
		elif days_old <= 7:
			recency_boost = RECENT_WEEK_BOOST
		elif days_old <= 30:
			recency_boost = RECENT_MONTH_BOOST
		elif days_old <= 90:
			recency_boost = RECENT_QUARTER_BOOST
		else:
			# Older documents get linear decay
			# Start linear decay from the 90-day boost value
			days_beyond_90 = days_old - 90
			recency_boost = max(
				MIN_RECENCY_BOOST, RECENT_QUARTER_BOOST - (days_beyond_90 * RECENCY_DECAY_RATE)
			)

		# Document type boost (discussions > comments > other doctypes)
		doctype_boost = {
			"GP Discussion": DISCUSSION_BOOST,
			"GP Comment": COMMENT_BOOST,
		}.get(row["doctype"], DEFAULT_DOCTYPE_BOOST)

		# Calculate final score
		final_score = base_score * title_boost * recency_boost * doctype_boost
		return final_score

	# Spelling Correction Methods

	def _expand_query_with_corrections(self, query):
		"""Expand query with spelling corrections."""
		words = query.strip().split()
		expanded_terms = []
		corrections = {}

		for word in words:
			similar_words = self._find_similar_words(word)
			if similar_words and similar_words[0] != word:
				# Replace the misspelled word with the corrected word
				corrected_word = similar_words[0]
				expanded_terms.append(corrected_word)
				corrections[word] = corrected_word
			else:
				expanded_terms.append(word)

		expanded_query = " ".join(expanded_terms)
		return expanded_query, corrections if corrections else None

	def _find_similar_words(
		self, word, max_suggestions=MAX_SPELLING_SUGGESTIONS, min_similarity=MIN_SIMILARITY_THRESHOLD
	):
		"""Find similar words using indexed trigram similarity - much faster!"""
		import difflib

		word = word.lower()
		if len(word) < MIN_WORD_LENGTH:
			return []

		word_trigrams = self._generate_trigrams(word)
		word_length = len(word)

		conn = self._get_connection(read_only=True)
		try:
			# Find candidate words that share trigrams (MUCH faster than checking all words)
			placeholders = ",".join("?" * len(word_trigrams))
			cursor = conn.execute(
				f"""
				SELECT t.word, v.frequency, v.length, COUNT(*) as shared_trigrams
				FROM gameplan_trigrams t
				JOIN gameplan_vocabulary v ON t.word = v.word
				WHERE t.trigram IN ({placeholders})
					AND ABS(v.length - ?) <= ?  -- Length filter for efficiency
				GROUP BY t.word, v.frequency, v.length
				HAVING shared_trigrams >= 1  -- Must share at least 1 trigram
				ORDER BY shared_trigrams DESC, v.frequency DESC
			""",
				(*word_trigrams, word_length, MAX_EDIT_DISTANCE),
			)

			candidates = cursor.fetchall()
		finally:
			conn.close()

		similarities = []
		word_trigram_set = set(word_trigrams)

		for candidate_word, freq, candidate_length, _ in candidates:
			# Quick length-based filter
			if abs(candidate_length - word_length) > MAX_EDIT_DISTANCE:
				continue

			candidate_trigrams = set(self._generate_trigrams(candidate_word))

			# Jaccard similarity for trigrams
			intersection = len(word_trigram_set & candidate_trigrams)
			union = len(word_trigram_set | candidate_trigrams)
			trigram_similarity = intersection / union if union > 0 else 0

			# Skip if trigram similarity is too low
			if trigram_similarity < 0.3:
				continue

			# Sequence similarity for additional accuracy (only for promising candidates)
			seq_similarity = difflib.SequenceMatcher(None, word, candidate_word).ratio()

			# Combined similarity with frequency boost
			combined_similarity = (
				trigram_similarity * SIMILARITY_TRIGRAM_WEIGHT + seq_similarity * SIMILARITY_SEQUENCE_WEIGHT
			)
			frequency_boost = min(
				MAX_FREQUENCY_BOOST, 1.0 + (freq / FREQUENCY_BOOST_FACTOR)
			)  # Slight boost for common words
			final_score = combined_similarity * frequency_boost

			if final_score >= min_similarity:
				similarities.append((candidate_word, final_score))

		# Sort by similarity and return top suggestions
		similarities.sort(key=lambda x: x[1], reverse=True)
		return [word for word, score in similarities[:max_suggestions]]

	def _build_vocabulary(self, documents):
		"""Build vocabulary and trigram index from documents for spelling correction."""
		import re
		from collections import defaultdict

		word_freq = defaultdict(int)

		# Extract words from all documents
		for doc in documents:
			title_words = re.findall(r"\w+", (doc.get("title", "") or "").lower())
			content_words = re.findall(r"\w+", (doc.get("content", "") or "").lower())

			for word in title_words + content_words:
				if len(word) > MIN_WORD_LENGTH - 1 and word.isalpha():  # Filter out short words and non-alpha
					word_freq[word] += 1

		# Store vocabulary and build trigram index
		conn = self._get_connection(read_only=False)
		try:
			conn.execute("DELETE FROM gameplan_vocabulary")
			conn.execute("DELETE FROM gameplan_trigrams")

			for word, freq in word_freq.items():
				# Store word with frequency and length
				conn.execute(
					"INSERT INTO gameplan_vocabulary (word, frequency, length) VALUES (?, ?, ?)",
					(word, freq, len(word)),
				)

				# Build trigram index
				trigrams = self._generate_trigrams(word)
				for trigram in trigrams:
					conn.execute(
						"INSERT OR IGNORE INTO gameplan_trigrams (trigram, word) VALUES (?, ?)",
						(trigram, word),
					)

			conn.commit()
		finally:
			conn.close()

	# Database and Infrastructure Methods

	def _get_connection(self, read_only=False):
		"""Get SQLite connection with FTS5 support and performance optimizations."""
		try:
			conn = sqlite3.connect(self.db_path)
			conn.row_factory = sqlite3.Row

			# Apply performance optimizations
			cursor = conn.cursor()
			self._set_pragmas(cursor, read_only)

			# Test the connection
			cursor.execute("SELECT 1")
			return conn
		except sqlite3.Error as e:
			frappe.log_error(f"Failed to connect to search database: {e}")
			raise GameplanSearchIndexMissingError(f"Search database connection failed: {e}") from e

	def _set_pragmas(self, cursor, is_read=False):
		"""Set SQLite performance pragmas."""
		cursor.execute("PRAGMA journal_mode = WAL;")  # Write-Ahead Logging for concurrency
		cursor.execute("PRAGMA synchronous = NORMAL;")  # Better performance vs FULL
		cursor.execute("PRAGMA cache_size = -8192;")  # 8MB cache
		cursor.execute("PRAGMA temp_store = MEMORY;")  # Memory temp storage
		if is_read:
			cursor.execute("PRAGMA query_only = 1;")  # Read-only optimization

	def _ensure_fts_table(self):
		"""Create FTS5 table and vocabulary table with proper schema."""
		conn = self._get_connection(read_only=False)
		try:
			# Drop existing tables to ensure clean schema
			conn.execute("DROP TABLE IF EXISTS gameplan_vocabulary")
			conn.execute("DROP TABLE IF EXISTS gameplan_trigrams")
			conn.execute("DROP TABLE IF EXISTS gameplan_fts")

			# Main FTS table
			conn.execute("""
				CREATE VIRTUAL TABLE gameplan_fts USING fts5(
					doc_id UNINDEXED,
					title,
					content,
					timestamp UNINDEXED,
					doctype UNINDEXED,
					name UNINDEXED,
					project UNINDEXED,
					owner UNINDEXED,
					team UNINDEXED,
					reference_doctype UNINDEXED,
					reference_name UNINDEXED,
					tokenize="unicode61 remove_diacritics 2 tokenchars '-_'"
				)
			""")

			# Vocabulary table for spelling correction
			conn.execute("""
				CREATE TABLE gameplan_vocabulary (
					word TEXT PRIMARY KEY,
					frequency INTEGER DEFAULT 1,
					length INTEGER
				)
			""")

			# Trigram index table for fast fuzzy matching
			conn.execute("""
				CREATE TABLE gameplan_trigrams (
					trigram TEXT,
					word TEXT,
					PRIMARY KEY (trigram, word)
				)
			""")

			# Index for fast trigram lookups
			conn.execute("""
				CREATE INDEX idx_trigram_lookup ON gameplan_trigrams(trigram)
			""")

			conn.commit()
		except sqlite3.Error as e:
			frappe.log_error(f"Failed to create FTS tables: {e}")
			raise
		finally:
			conn.close()

	def _index_documents(self, documents):
		"""Bulk index documents into SQLite FTS."""
		if not documents:
			return

		conn = self._get_connection(read_only=False)
		try:
			insert_sql = """
				INSERT INTO gameplan_fts
				(doc_id, title, content, timestamp, doctype, name,
				project, owner, team, reference_doctype, reference_name)
				VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
			"""

			for doc in documents:
				doctype, name = doc["id"].split(":", 1)

				# Get additional metadata
				if doctype == "GP Comment":
					comment_data = frappe.db.get_value(
						"GP Comment", name, ["reference_doctype", "reference_name", "owner"], as_dict=True
					)
					project = None
					team = None
					if comment_data and comment_data.reference_doctype and comment_data.reference_name:
						# Get project and team from the referenced document
						ref_data = frappe.db.get_value(
							comment_data.reference_doctype,
							comment_data.reference_name,
							["project", "team"],
							as_dict=True,
						)
						if ref_data:
							project = ref_data.project
							team = ref_data.team

					conn.execute(
						insert_sql,
						(
							doc["id"],
							doc.get("title", ""),
							doc.get("content", ""),
							doc["timestamp"],
							doctype,
							name,
							project,
							comment_data.owner if comment_data else "",
							team,
							comment_data.reference_doctype if comment_data else None,
							comment_data.reference_name if comment_data else None,
						),
					)
				else:
					doc_data = frappe.db.get_value(doctype, name, ["project", "owner", "team"], as_dict=True)
					conn.execute(
						insert_sql,
						(
							doc["id"],
							doc.get("title", ""),
							doc.get("content", ""),
							doc["timestamp"],
							doctype,
							name,
							doc_data.project if doc_data else None,
							doc_data.owner if doc_data else "",
							doc_data.team if doc_data else None,
							None,
							None,
						),
					)

			conn.commit()
		finally:
			conn.close()

	def _index_doc(self, doctype, docname):
		"""Index a single document."""
		doc = frappe.get_doc(doctype, docname)
		self.raise_if_not_indexed()
		document = self._prepare_document(doc)
		if document:
			self._index_documents([document])

	def _remove_doc(self, doctype, docname):
		"""Remove a single document from the index."""
		self.raise_if_not_indexed()
		doc_id = f"{doctype}:{docname}"

		conn = self._get_connection(read_only=False)
		try:
			conn.execute("DELETE FROM gameplan_fts WHERE doc_id = ?", (doc_id,))
			conn.commit()
		finally:
			conn.close()

	# Utility Methods

	def _validate_config(self):
		"""Validate document configuration at startup."""
		required_keys = ["fields", "content_field", "modified_field"]

		for doctype, config in self.doc_configs.items():
			# Check required keys exist
			for key in required_keys:
				if key not in config:
					raise ValueError(f"Missing required config key '{key}' for doctype '{doctype}'")

			# Validate content_field is in fields list
			if config["content_field"] and config["content_field"] not in config["fields"]:
				raise ValueError(
					f"Content field '{config['content_field']}' not in fields list for '{doctype}'"
				)

			# Validate title_field is in fields list (if specified)
			if config.get("title_field") and config["title_field"] not in config["fields"]:
				raise ValueError(f"Title field '{config['title_field']}' not in fields list for '{doctype}'")

			# Validate modified_field is in fields list
			if config["modified_field"] not in config["fields"]:
				raise ValueError(
					f"Modified field '{config['modified_field']}' not in fields list for '{doctype}'"
				)

	def _empty_search_result(self, title_only=False, filters=None):
		"""Return empty search result structure."""
		return {
			"results": [],
			"summary": {
				"total_matches": 0,
				"filtered_matches": 0,
				"duration": 0,
				"returned_matches": 0,
				"corrected_words": None,
				"corrected_query": None,
				"title_only": title_only,
				"applied_filters": filters or {},
			},
		}

	def _get_db_path(self, is_temp=False):
		"""Get the path for the SQLite FTS database."""
		site_path = frappe.get_site_path()
		db_path = os.path.join(site_path, "gameplan_search.db")
		if is_temp:
			return db_path.replace(".db", ".temp.db")
		return db_path

	def _prepare_fts_query(self, query):
		"""Prepare query for FTS5 with proper escaping and operators."""
		query = query.strip()
		if not query:
			return ""

		# Simple query - split into terms and add wildcards for partial matching
		terms = query.split()
		fts_terms = []

		for term in terms:
			# Escape special FTS5 characters
			term = term.replace('"', '""')
			# Add wildcard for prefix matching
			if len(term) > MIN_WORD_LENGTH - 1:
				fts_terms.append(f'"{term}"*')
			else:
				fts_terms.append(f'"{term}"')

		return " ".join(fts_terms)

	def _prepare_document(self, doc):
		"""Prepare a document for indexing."""
		config = self.doc_configs.get(doc.doctype)
		if not config:
			return None

		content_field = config["content_field"]
		title_field = config["title_field"]

		if not isinstance(doc.modified, datetime.datetime):
			doc.modified = frappe.utils.get_datetime(doc.modified)

		# Process content to remove HTML, links, and images
		raw_content = getattr(doc, content_field, "") or ""
		processed_content = self._process_content(raw_content)

		return {
			"id": f"{doc.doctype}:{doc.name}",
			"title": getattr(doc, title_field, "") if title_field else "",
			"content": processed_content,
			"timestamp": doc.modified.timestamp(),
		}

	def _process_content(self, content):
		"""Process content to remove HTML tags, links, and images for better indexing quality."""
		if not content:
			return ""

		soup = BeautifulSoup(content, "html.parser")
		text = soup.get_text(separator=" ").strip()  # remove tags
		text = re.sub(r"https?://[^\s]+", "[link]", text)  # replace links
		text = re.sub(r"\s+", " ", text).strip()  # normalize whitespace
		return text

	def _generate_trigrams(self, word):
		"""Generate trigrams for a word for fuzzy matching."""
		word = f"  {word.lower()}  "  # Add padding
		return [word[i : i + 3] for i in range(len(word) - 2)]


# Module-level Functions


def build_index():
	"""Build search index in the current process."""
	search = GameplanSearch()
	if not search.is_search_enabled():
		return
	frappe.cache().set_value(INDEX_BUILD_FLAG, True)
	search.build_index()
	frappe.cache().set_value(INDEX_BUILD_FLAG, False)


def build_index_in_background():
	"""Enqueue index building in background."""
	search = GameplanSearch()
	if not search.is_search_enabled():
		return
	if not frappe.cache().get_value("discussions_index_in_progress"):
		frappe.enqueue(build_index, queue="long")


def build_index_if_not_exists():
	"""Build index if it doesn't exist."""
	search = GameplanSearch()
	if not search.is_search_enabled():
		return
	if not search.index_exists() or not frappe.cache.exists(INDEX_BUILD_FLAG):
		build_index()


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
