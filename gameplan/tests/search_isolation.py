# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""Keeping the test suite out of the site's live SQLite search index.

The FTS index is a file next to the site (``gameplan_search.db``), outside the MariaDB
transaction, so ``frappe.db.rollback()`` cannot undo a write to it. Every save of an
indexable doctype goes through frappe's ``update_doc_index`` doc_event, which builds a
*fresh* ``GameplanSearch`` per call — so any test anywhere in the app that creates a
discussion, comment, task or page permanently appends a row to the site's real index.
Per-class patching cannot fix that; the leak is suite-wide.

The redirect is applied once, in ``gameplan/tests/__init__.py``: it repoints
``GameplanSearch.INDEX_NAME`` at :data:`DEFAULT_TEST_INDEX_NAME`, a filename no test
ever builds. ``update_doc_index`` returns early when ``index_exists()`` is false, so
every incidental hook write becomes a no-op instead of landing somewhere.

Two layers of enforcement sit on top of it:

- :func:`guard_real_index`, wired into ``GameplanTestCase.setUp``, fails any test in
  the suite that changes the real index file. The leak was suite-wide, so the guard is
  too.
- :class:`IsolatedSearchIndex`, opted into by the classes that genuinely build an
  index, gives each its own file, removes it (and its SQLite sidecars) afterwards, and
  asserts on the resolved ``db_path`` rather than on ``INDEX_NAME``.

The clean version of the redirect belongs upstream: ``SQLiteSearch._get_db_path``
should scope the filename when ``frappe.in_test``, the same way frappe already scopes
the MariaDB test database. Until then every app using ``SQLiteSearch`` has this leak.
"""

import os
import sqlite3
from unittest.mock import patch

import frappe

from gameplan.search_sqlite import GameplanSearch

# Captured at import time, which ``gameplan/tests/__init__.py`` guarantees happens
# before it overwrites the class attribute, so the guards below can still name the file
# the suite must not touch.
PRODUCTION_INDEX_NAME = GameplanSearch.INDEX_NAME

# Deliberately a name nothing builds: hook writes hit a missing file and no-op.
DEFAULT_TEST_INDEX_NAME = "test_gameplan_search_unused.db"

# SQLite's sidecar files. A WAL database owns both while a connection is open, and
# ``drop_index()`` unlinks neither.
_SQLITE_SIDECAR_SUFFIXES = ("-wal", "-shm")


def redirect_default_index_to_throwaway_file():
	"""Point every un-patched ``GameplanSearch`` at a file no test builds.

	Called from ``gameplan/tests/__init__.py`` so it is in effect before any test
	module is imported: ``SQLiteSearch.__init__`` resolves ``db_path`` once per
	instance, so the redirect has to land before the first construction.
	"""
	GameplanSearch.INDEX_NAME = DEFAULT_TEST_INDEX_NAME


def real_index_path() -> str:
	"""Absolute path of the site's live search index — the file tests must not touch."""
	return os.path.abspath(os.path.join(frappe.get_site_path(), PRODUCTION_INDEX_NAME))


def index_paths(index_name: str) -> list[str]:
	"""Every file an index by this name can occupy: main, temp, and their sidecars.

	Mirrors ``SQLiteSearch._get_db_path``, which derives the temp path by replacing
	``.db`` with ``.temp.db``.
	"""
	db_path = os.path.join(frappe.get_site_path(), index_name)
	bases = [db_path, db_path.replace(".db", ".temp.db")]
	return bases + [base + suffix for base in bases for suffix in _SQLITE_SIDECAR_SUFFIXES]


def remove_index_files(index_name: str):
	"""Delete a test index and every file it may have left behind.

	``drop_index()`` unlinks only the main ``.db``, and ``build_index``'s failure path
	leaves its ``.temp.db`` in place, so a failed build otherwise leaves permanent
	residue in the site directory.
	"""
	for path in index_paths(index_name):
		if os.path.exists(path):
			os.unlink(path)


def index_fingerprint(path: str) -> tuple:
	"""Stat-only signature of an index file plus its write-ahead log.

	Deliberately does *not* open SQLite. Connecting read-only to a WAL database
	creates ``-wal``/``-shm`` files next to it, and a guard whose entire job is "this
	file was not touched" must not itself write into the site directory. Stat is also
	cheap enough to run around every test in the suite.

	Any index write moves the mtime of the main file — the WAL is checkpointed when the
	last connection closes — or, if a writer died mid-flight, of the ``-wal``.
	"""
	return (_stat_signature(path), _stat_signature(path + "-wal"))


def _stat_signature(path: str) -> tuple:
	try:
		stat = os.stat(path)
	except OSError:
		return (False, None, None)
	return (True, stat.st_size, stat.st_mtime_ns)


def row_count(path: str) -> int | None:
	"""``search_fts`` row count, or ``None`` if the file is not a readable index.

	``immutable=1`` is what keeps this residue-free: a plain ``mode=ro`` connection to
	a WAL database creates the ``-wal``/``-shm`` sidecars. The cost is that rows still
	parked in an un-checkpointed WAL are invisible, which is why this only *describes*
	a change :func:`index_fingerprint` has already detected.
	"""
	try:
		connection = sqlite3.connect(f"file:{path}?mode=ro&immutable=1", uri=True)
	except sqlite3.Error:
		return None
	try:
		return connection.execute("SELECT COUNT(*) FROM search_fts").fetchone()[0]
	except sqlite3.Error:
		return None
	finally:
		connection.close()


def guard_real_index(test_case):
	"""Fail ``test_case`` if the site's live search index changes while it runs.

	Registered as a cleanup rather than asserted in ``tearDown`` so it still runs for
	subclasses that override ``tearDown`` without calling up.
	"""
	path = real_index_path()
	test_case.addCleanup(_assert_real_index_untouched, test_case, path, index_fingerprint(path))


def _assert_real_index_untouched(test_case, path, before):
	after = index_fingerprint(path)
	test_case.assertEqual(
		after,
		before,
		f"The site's real search index changed while this test ran.\n"
		f"  {path}\n"
		f"  (exists, size, mtime_ns) for the .db and its -wal: {before} -> {after}\n"
		f"  search_fts rows now: {row_count(path)}\n"
		"SQLite is outside the MariaDB transaction, so those rows cannot be rolled back. "
		"Most likely a GameplanSearch was constructed before GameplanSearch.INDEX_NAME "
		"was redirected (see gameplan/tests/__init__.py).",
	)


class IsolatedSearchIndex:
	"""Test-case mixin for classes that build a real search index.

	Set ``INDEX_NAME`` on the class and call :meth:`isolate_search_index` (or, when the
	class supplies its own ``SQLiteSearch`` subclass carrying its own ``INDEX_NAME``,
	:meth:`guard_real_search_index`) from ``setUp``, before creating any indexable
	document.
	"""

	INDEX_NAME: str

	def guard_real_search_index(self):
		"""Remove this class's index files afterwards; prove the real index is untouched.

		Cleanups run LIFO, so the removal is registered last and therefore runs first:
		test index files go, then the real-index comparison, then any patch started
		before this call.
		"""
		guard_real_index(self)
		self.addCleanup(remove_index_files, self.INDEX_NAME)

	def isolate_search_index(self):
		""":meth:`guard_real_search_index` plus repointing every ``GameplanSearch``.

		Patching the class attribute covers the doc_event hook too, because
		``update_doc_index`` constructs a new instance on every call — and that
		instance resolves ``db_path`` in ``__init__``, so this must run before the
		first indexable document is saved.
		"""
		patcher = patch.object(GameplanSearch, "INDEX_NAME", self.INDEX_NAME)
		patcher.start()
		self.addCleanup(patcher.stop)
		self.guard_real_search_index()

	def assert_uses_isolated_index(self, search):
		"""Assert the resolved database *file* is this class's, not the site's.

		``db_path`` is the value that actually decides where writes land; asserting on
		``INDEX_NAME`` would only re-read what ``patch.object`` just set and would stay
		green if the instance had been constructed before the patch.
		"""
		self.assertEqual(os.path.basename(search.db_path), self.INDEX_NAME)
		self.assertNotEqual(os.path.abspath(search.db_path), real_index_path())
