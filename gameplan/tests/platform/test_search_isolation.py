# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""No test may write to the site's live SQLite search index, and rebuilds must clear it.

The index file lives outside the MariaDB transaction, so ``frappe.db.rollback()`` cannot
undo a write to it: a rolled-back test document leaves a permanent row. Frappe's
``update_doc_index`` doc_event fires on every save of an indexable doctype and builds a
fresh ``GameplanSearch`` per call, so this is not a search-test problem — it is every
test in the app. These tests pin the redirect in ``gameplan/tests/__init__.py``, the
guard wired into ``GameplanTestCase``, and the rebuild that actually discards stale rows.
"""

import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from gameplan.search_sqlite import GameplanSearch, rebuild_index
from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import create_community, create_discussion, create_space
from gameplan.tests.search_isolation import (
	DEFAULT_TEST_INDEX_NAME,
	IsolatedSearchIndex,
	guard_real_index,
	index_fingerprint,
	real_index_path,
	row_count,
)

# The files SQLite parks next to a WAL database. Named here so the cleanup and the
# assertion that follows it can never drift apart.
_SQLITE_SIDECARS = ("-wal", "-shm")


class TestSearchIndexIsolation(GameplanTestCase):
	def setUp(self):
		super().setUp()
		community = create_community("Search Isolation Community")
		self.space = create_space("Search Isolation Space", community)

	def test_an_unpatched_search_resolves_a_throwaway_file_that_no_test_builds(self):
		search = GameplanSearch()

		self.assertEqual(os.path.basename(search.db_path), DEFAULT_TEST_INDEX_NAME)
		self.assertNotEqual(os.path.abspath(search.db_path), real_index_path())
		# update_doc_index returns early when the index does not exist, which is what
		# turns every incidental hook write in the suite into a no-op.
		self.assertFalse(search.index_exists())

	def test_the_index_hook_never_resolves_the_sites_real_index(self):
		"""Site-independent: assert the path the hook resolves, not the file's contents.

		Recording ``db_path`` from inside the hook also proves the hook actually ran, so
		this cannot pass because the doc_event went missing.
		"""
		resolved_paths = []
		original_index_exists = GameplanSearch.index_exists

		def record_db_path(search):
			resolved_paths.append(os.path.abspath(search.db_path))
			return original_index_exists(search)

		with patch.object(GameplanSearch, "index_exists", record_db_path):
			create_discussion("Hook path discussion", self.space, content="hook path body")

		self.assertTrue(resolved_paths, "update_doc_index did not construct a GameplanSearch")
		self.assertNotIn(real_index_path(), resolved_paths)

	def test_the_create_update_delete_cycle_leaves_the_real_index_unchanged(self):
		"""End-to-end version of the above, named so the invariant is discoverable.

		``GameplanTestCase`` enforces the same thing around every test in the suite; this
		states it explicitly, and only bites on a site that actually has a built index.
		"""
		before = index_fingerprint(real_index_path())

		discussion = create_discussion("Real index discussion", self.space, content="realindexneedle")
		discussion.content = "realindexneedle rewritten"
		discussion.save(ignore_permissions=True)
		discussion.delete(ignore_permissions=True)

		self.assertEqual(index_fingerprint(real_index_path()), before)


class TestRealIndexGuard(FrappeTestCase):
	"""The guard itself must fail when the file it watches changes.

	Its predecessor asserted ``self.search.INDEX_NAME == "test_..."`` — that
	``mock.patch`` works — and stayed green through the whole leak it existed to catch.
	So the guard is run here against a stand-in file, in both directions.
	"""

	def setUp(self):
		directory = tempfile.TemporaryDirectory()
		self.addCleanup(directory.cleanup)
		self.watched = os.path.join(directory.name, "stand_in_search.db")

	def run_guarded(self, body) -> unittest.TestResult:
		"""Run ``body`` inside a throwaway test case that has the guard attached."""
		watched = self.watched

		class Probe(unittest.TestCase):
			def runTest(self):
				# Started before guard_real_index, which resolves real_index_path() once
				# and captures the result — so the patch has to be live at that call.
				patcher = patch("gameplan.tests.search_isolation.real_index_path", return_value=watched)
				patcher.start()
				self.addCleanup(patcher.stop)
				guard_real_index(self)
				body()

		result = unittest.TestResult()
		Probe().run(result)
		return result

	def test_a_test_that_leaves_the_index_alone_passes(self):
		_write(self.watched, b"original")

		result = self.run_guarded(lambda: None)

		self.assertEqual(result.errors, [])
		self.assertEqual(result.failures, [])

	def test_a_test_that_writes_to_the_index_fails(self):
		_write(self.watched, b"original")

		result = self.run_guarded(lambda: _write(self.watched, b"original + a leaked row"))

		self.assertEqual(len(result.failures), 1)
		self.assertIn("real search index changed", result.failures[0][1])

	def test_a_test_that_creates_a_missing_index_fails(self):
		result = self.run_guarded(lambda: _write(self.watched, b"appeared out of nowhere"))

		self.assertEqual(len(result.failures), 1)
		self.assertIn("real search index changed", result.failures[0][1])

	def test_reading_the_row_count_does_not_trip_the_guard(self):
		"""``row_count`` must not create the WAL sidecars a plain ``mode=ro`` open would.

		Those files land in the site directory next to the live index, which is exactly
		what a "this file was not touched" guard must not do.
		"""
		_write_wal_index(self.watched)
		# Whether closing a WAL writer unlinks its own -wal/-shm is a property of the local
		# SQLite build, not of anything under test: SQLite 3.51 on macOS leaves them, the
		# SQLite on CI's Ubuntu image removes them. Clearing them here is what keeps the
		# assertions below about row_count rather than about the setup writer.
		_remove_sidecars(self.watched)

		result = self.run_guarded(lambda: self.assertEqual(row_count(self.watched), 1))

		self.assertEqual(result.failures, [])
		self.assertEqual(result.errors, [])
		for suffix in _SQLITE_SIDECARS:
			self.assertFalse(
				os.path.exists(self.watched + suffix),
				f"row_count() left a {suffix} file beside the index it read",
			)


class TestSearchIndexRebuild(IsolatedSearchIndex, GameplanTestCase):
	"""``rebuild_index`` is the only way to get stale rows out of an existing index."""

	INDEX_NAME = "test_gameplan_search_rebuild.db"

	def setUp(self):
		super().setUp()
		self.isolate_search_index()
		community = create_community("Search Rebuild Community")
		self.space = create_space("Search Rebuild Space", community)

	def test_a_rebuild_removes_rows_for_documents_that_no_longer_exist(self):
		discussion = create_discussion("Rebuild stale discussion", self.space, content="rebuildstaleneedle")

		with self.index_only([discussion.name]):
			rebuild_index()
			self.assertEqual(self.indexed_names(), {str(discussion.name)})

			# Raw delete, as demo.clear() and ui_test_helpers.reset() do it: no doc_event
			# fires, so nothing removes the row incrementally.
			frappe.db.delete("GP Discussion", discussion.name)
			rebuild_index()

			self.assertEqual(self.indexed_names(), set())

	def index_only(self, names):
		"""Narrow the indexable set to these discussions.

		Keeps the assertions independent of whatever else the site holds, and keeps the
		build off every other document on it.
		"""
		config = dict(GameplanSearch.INDEXABLE_DOCTYPES["GP Discussion"])
		config["filters"] = {"name": ("in", names)}
		return patch.object(GameplanSearch, "INDEXABLE_DOCTYPES", {"GP Discussion": config})

	def indexed_names(self) -> set[str]:
		path = os.path.join(frappe.get_site_path(), self.INDEX_NAME)
		self.assertTrue(os.path.exists(path), f"rebuild_index left no index at {path}")
		connection = sqlite3.connect(f"file:{path}?mode=ro&immutable=1", uri=True)
		try:
			rows = connection.execute("SELECT name FROM search_fts").fetchall()
		finally:
			connection.close()
		return {str(row[0]) for row in rows}


def _write(path, content: bytes):
	with open(path, "wb") as f:
		f.write(content)


def _write_wal_index(path):
	"""Build a one-row WAL-mode stand-in index with every row in the main file.

	The checkpoint is load-bearing: ``row_count`` opens with ``immutable=1``, which
	ignores the write-ahead log entirely, so rows still parked in an un-checkpointed
	``-wal`` are invisible to it — it would not even find the table.
	"""
	connection = sqlite3.connect(path)
	try:
		connection.execute("PRAGMA journal_mode = WAL")
		connection.execute("CREATE TABLE search_fts (name)")
		connection.execute("INSERT INTO search_fts VALUES ('needle')")
		connection.commit()
		connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
	finally:
		connection.close()


def _remove_sidecars(path):
	for suffix in _SQLITE_SIDECARS:
		if os.path.exists(path + suffix):
			os.unlink(path + suffix)
