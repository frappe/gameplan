# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""Package-level setup that must be in effect before any Gameplan test is imported.

The SQLite search index is a file next to the site, outside the MariaDB transaction, so a
rolled-back test document still leaves a permanent row in it. The redirect has to happen
here rather than in a base test case for two reasons: it covers the suite regardless of
which base class a test uses, and it lands before the first ``GameplanSearch`` is
constructed (``SQLiteSearch.__init__`` resolves ``db_path`` once per instance, including
inside the ``update_doc_index`` doc_event, so a later patch cannot retro-fix an instance).

This package is test-only; importing it in a running site would repoint search for that
process. See :mod:`gameplan.tests.search_isolation` for the guards layered on top.
"""

from gameplan.tests.search_isolation import redirect_default_index_to_throwaway_file

redirect_default_index_to_throwaway_file()
