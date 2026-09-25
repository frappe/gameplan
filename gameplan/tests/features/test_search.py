import json
import os
from unittest.mock import patch

import frappe
from frappe.search import sqlite_search as frappe_sqlite_search
from frappe.tests.utils import FrappeTestCase
from redis.exceptions import ConnectionError as RedisConnectionError

from gameplan.api import search_sqlite
from gameplan.command_palette import search_sqlite as command_palette_search
from gameplan.install import enqueue_search_index_build
from gameplan.search_sqlite import GameplanSearch, GameplanSearchIndexMissingError
from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import (
	create_comment,
	create_community,
	create_space,
	drain_search_index_queue,
	grant_guest_access,
)
from gameplan.tests.search_isolation import IsolatedSearchIndex


class TestableGameplanSearch(GameplanSearch):
	INDEX_NAME = "test_gameplan_search.db"

	def _load_all_tags(self):
		self._tags_cache = {}

	def get_documents_paginated(
		self, doctype, limit=1000, last_indexed_modified=None, last_indexed_name=None
	):
		if last_indexed_name:
			return []

		docnames = frappe.flags.gameplan_search_test_docnames.get(doctype, [])
		if not docnames:
			return []

		config = self.doc_configs.get(doctype)
		filters = config.get("filters", {}).copy()
		filters["name"] = ("in", docnames)
		fields = config["fields"].copy()
		for field in ["creation", "modified", "name"]:
			if field not in fields:
				fields.append(field)

		docs = frappe.qb.get_query(
			doctype,
			fields=fields,
			filters=filters,
			order_by="creation ASC, name ASC",
			limit=limit,
		).run(as_dict=True)

		for doc in docs:
			doc.doctype = doctype
		return docs


class TestSearchRanking(IsolatedSearchIndex, FrappeTestCase):
	# The corpus is controlled explicitly through TestableGameplanSearch, so
	# GameplanSearch.INDEX_NAME is deliberately NOT patched to this file: incidental
	# doc_event writes must stay no-ops against the package-level throwaway index
	# rather than leak into the ranking corpus.
	INDEX_NAME = TestableGameplanSearch.INDEX_NAME

	def setUp(self):
		frappe.set_user("Administrator")
		self.guard_real_search_index()
		frappe.flags.gameplan_search_test_docnames = {
			"GP Discussion": [],
			"GP Task": [],
			"GP Page": [],
			"GP Comment": [],
		}
		self.search = TestableGameplanSearch()
		self.search.drop_index()
		# Create an owned public space rather than relying on ambient data — a fresh
		# CI site has no GP Project, which made setUp raise IndexError.
		team = create_community("Search Ranking Team")
		self.project = create_space("Search Ranking Space", team.name)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def test_ranking_corpus_lives_in_an_isolated_database(self):
		self.assert_uses_isolated_index(self.search)

	def search_results(self, query):
		self.search.build_index()
		return self.search.search(query)["results"]

	def create_discussion(self, title, content):
		discussion = frappe.get_doc(
			doctype="GP Discussion",
			title=title,
			project=self.project.name,
			content=content,
		).insert(ignore_permissions=True)
		self.track_doc(discussion)
		return discussion

	def create_page(self, title, content):
		page = frappe.get_doc(
			doctype="GP Page",
			title=title,
			project=self.project.name,
			content=content,
		).insert(ignore_permissions=True)
		self.track_doc(page)
		return page

	def create_comment(self, discussion, content):
		with patch(
			"gameplan.gameplan.doctype.gp_notification.gp_notification.GPNotification.clear_notifications"
		):
			comment = frappe.get_doc(
				doctype="GP Comment",
				reference_doctype="GP Discussion",
				reference_name=discussion.name,
				content=content,
			).insert(ignore_permissions=True)
		self.track_doc(comment)
		return comment

	def track_doc(self, doc):
		frappe.flags.gameplan_search_test_docnames[doc.doctype].append(doc.name)

	def test_recency_breaks_close_body_match_ties(self):
		old = self.create_discussion(
			"Ranking Handbook",
			"rankwise sqlite relevance " * 30,
		)
		recent = self.create_discussion(
			"SQLite weekly note",
			"rankwise sqlite relevance appears once",
		)
		frappe.db.set_value(
			"GP Discussion",
			old.name,
			"last_post_at",
			"2021-01-01 00:00:00",
			update_modified=False,
		)
		frappe.db.set_value(
			"GP Discussion",
			recent.name,
			"last_post_at",
			frappe.utils.now(),
			update_modified=False,
		)

		results = self.search_results("rankwise sqlite relevance")

		self.assertGreater(len(results), 1)
		self.assertEqual(results[0]["id"], f"GP Discussion:{recent.name}")

	def test_recency_boost_applies_to_indexed_sqlite_rows(self):
		old = self.create_discussion(
			"Recency Anchor",
			"recencyanchor appears once",
		)
		recent = self.create_discussion(
			"Recency Anchor",
			"recencyanchor appears once",
		)
		frappe.db.set_value(
			"GP Discussion",
			old.name,
			"last_post_at",
			"2021-01-01 00:00:00",
			update_modified=False,
		)
		frappe.db.set_value(
			"GP Discussion",
			recent.name,
			"last_post_at",
			frappe.utils.now(),
			update_modified=False,
		)

		results = self.search_results("recencyanchor")

		self.assertGreater(len(results), 1)
		self.assertEqual(results[0]["id"], f"GP Discussion:{recent.name}")
		self.assertGreater(results[0]["score"], results[1]["score"])

	def test_exact_title_match_beats_noisy_body_match(self):
		expected = self.create_discussion(
			"Rankwise SQLite Relevance",
			"rankwise sqlite relevance appears once",
		)
		self.create_discussion(
			"Ranking Notes",
			"rankwise sqlite relevance " * 50,
		)

		results = self.search_results("rankwise sqlite relevance")

		self.assertGreater(len(results), 1)
		self.assertEqual(results[0]["id"], f"GP Discussion:{expected.name}")

	def test_title_boost_prefers_demo_token_over_democracy_prefix(self):
		self.assertEqual(
			self.search._get_title_boost({"original_title": "Demo Planning"}, "demo", ["demo"]),
			3.0,
		)
		self.assertEqual(
			self.search._get_title_boost({"original_title": "Democracy Planning"}, "demo", ["demo"]),
			1.0,
		)

	def test_parent_discussion_title_beats_dense_child_comment(self):
		discussion = self.create_discussion(
			"Parentanchor Roadmap",
			"parentanchor roadmap appears once",
		)
		self.create_comment(discussion, "parentanchor roadmap " * 60)

		results = self.search_results("parentanchor roadmap")

		self.assertGreater(len(results), 1)
		self.assertEqual(results[0]["id"], f"GP Discussion:{discussion.name}")

	def test_exact_page_title_beats_dense_comment_match(self):
		page = self.create_page("Canonanchor Release Notes", "canonanchor release notes")
		discussion = self.create_discussion(
			"Comment Container",
			"container for noisy comments",
		)
		self.create_comment(discussion, "canonanchor release notes " * 80)

		results = self.search_results("canonanchor release notes")

		self.assertGreater(len(results), 1)
		self.assertEqual(results[0]["id"], f"GP Page:{page.name}")

	def test_large_corpus_orders_canonical_and_dense_matches_before_noise(self):
		exact = self.create_discussion(
			"Corpusanchor Migration Plan",
			"corpusanchor migration plan " * 3,
		)
		dense = self.create_discussion(
			"Migration Notes",
			"corpusanchor migration plan " * 35,
		)
		partial = self.create_discussion(
			"Corpusanchor Update",
			"migration plan appears once",
		)
		for index in range(30):
			self.create_discussion(
				f"Corpusanchor Digest {index}",
				f"migration plan filler {index}",
			)

		results = self.search_results("corpusanchor migration plan")
		top_ids = [result["id"] for result in results[:3]]

		self.assertEqual(
			top_ids,
			[
				f"GP Discussion:{exact.name}",
				f"GP Discussion:{dense.name}",
				f"GP Discussion:{partial.name}",
			],
		)


class TestSearchIndexLifecycle(IsolatedSearchIndex, GameplanTestCase):
	INDEX_NAME = "test_gameplan_search_hooks.db"

	def setUp(self):
		super().setUp()
		# Must happen before the first indexable document: the doc_event hook builds a
		# fresh GameplanSearch, which resolves db_path from INDEX_NAME at construction.
		self.isolate_search_index()
		self.community = create_community(
			"Search Index Lifecycle Community",
			is_private=1,
			members=[self.member, self.second_member],
		)
		self.space = create_space(
			"Search Index Lifecycle Space",
			self.community,
			is_private=1,
			members=[self.member, self.second_member],
		)
		self.search = GameplanSearch()
		self.search.drop_index()
		self.search.build_index()

	def create_discussion(self, title, content, space=None):
		return frappe.get_doc(
			doctype="GP Discussion",
			title=title,
			project=(space or self.space).name,
			content=content,
		).insert(ignore_permissions=True)

	def result_ids(self, query):
		return {result["id"] for result in self.search.search(query)["results"]}

	def queued_ids(self):
		"""Doc ids waiting in the develop-only index queue, or None on version-16.

		``read_only=True`` is load-bearing: every other mode of ``SQLiteSearch.sql`` returns
		a cursor whose connection it has already closed in a ``finally``, so iterating the
		result raises ``ProgrammingError``. Only the read-only path fetches before closing.
		"""
		if not self.search._table_exists("search_index_queue"):
			return None
		rows = self.search.sql("SELECT doc_id FROM search_index_queue", read_only=True)
		return {row["doc_id"] for row in rows}

	def assert_hook_indexed_or_queued(self, doc, query):
		doc_id = f"{doc.doctype}:{doc.name}"
		queued_ids = self.queued_ids()
		if queued_ids is None:
			self.assertIn(doc_id, self.result_ids(query))
		else:
			self.assertIn(doc_id, queued_ids)

	def search_as(self, user, query, filters=None):
		with self.as_user(user):
			return search_sqlite(
				query,
				filters=json.dumps(filters) if filters is not None else None,
			)["results"]

	def test_index_lifecycle_uses_an_isolated_database(self):
		self.assert_uses_isolated_index(self.search)

	def test_content_is_indexed_on_create(self):
		discussion = self.create_discussion(
			"Create hook coverage",
			"createhookneedle appears only after the index already exists",
		)

		self.assert_hook_indexed_or_queued(discussion, "createhookneedle")
		drain_search_index_queue()
		self.assertIn(f"GP Discussion:{discussion.name}", self.result_ids("createhookneedle"))

	def test_content_is_reindexed_on_update(self):
		discussion = self.create_discussion(
			"Update hook coverage",
			"oldhookneedle is replaced when the discussion changes",
		)
		drain_search_index_queue()
		self.assertIn(f"GP Discussion:{discussion.name}", self.result_ids("oldhookneedle"))

		discussion.content = "newhookneedle appears only in the saved revision"
		discussion.save(ignore_permissions=True)

		self.assert_hook_indexed_or_queued(discussion, "newhookneedle")
		drain_search_index_queue()
		self.assertNotIn(f"GP Discussion:{discussion.name}", self.result_ids("oldhookneedle"))
		self.assertIn(f"GP Discussion:{discussion.name}", self.result_ids("newhookneedle"))

	def test_content_is_removed_from_index_on_delete(self):
		discussion = self.create_discussion(
			"Delete hook coverage",
			"deletehookneedle disappears with the discussion",
		)
		drain_search_index_queue()
		self.assertIn(f"GP Discussion:{discussion.name}", self.result_ids("deletehookneedle"))

		discussion.delete(ignore_permissions=True)

		self.assertNotIn(f"GP Discussion:{discussion.name}", self.result_ids("deletehookneedle"))
		queued_ids = self.queued_ids()
		if queued_ids is not None:
			self.assertNotIn(f"GP Discussion:{discussion.name}", queued_ids)

	def test_space_filter_narrows_accessible_results(self):
		other_space = create_space("Other Search Space", self.space.team)
		expected = self.create_discussion(
			"Filtered search result",
			"spacefilterneedle in the selected space",
		)
		self.create_discussion(
			"Other search result",
			"spacefilterneedle in another accessible space",
			space=other_space,
		)
		drain_search_index_queue()

		results = self.search.search(
			"spacefilterneedle",
			filters={"project": [self.space.name]},
		)["results"]

		self.assertEqual([result["id"] for result in results], [f"GP Discussion:{expected.name}"])

	def test_inaccessible_space_filter_returns_no_results(self):
		inaccessible_space = create_space(
			"Inaccessible Search Space",
			self.community,
			is_private=1,
			members=[self.member],
		)
		self.create_discussion(
			"Private filtered result",
			"privatefilterneedle must not leak through a requested space",
			space=inaccessible_space,
		)
		drain_search_index_queue()

		results = self.search_as(
			self.second_member,
			"privatefilterneedle",
			filters={"project": [str(inaccessible_space.name)]},
		)

		self.assertEqual(results, [])

	def test_mixed_space_filter_returns_only_accessible_results(self):
		inaccessible_space = create_space(
			"Mixed Inaccessible Search Space",
			self.community,
			is_private=1,
			members=[self.member],
		)
		expected = self.create_discussion(
			"Accessible mixed result",
			"mixedfilterneedle in an accessible space",
		)
		self.create_discussion(
			"Inaccessible mixed result",
			"mixedfilterneedle in a space the caller cannot access",
			space=inaccessible_space,
		)
		drain_search_index_queue()

		results = self.search_as(
			self.second_member,
			"mixedfilterneedle",
			filters={"project": [str(self.space.name), str(inaccessible_space.name)]},
		)

		self.assertEqual([result["id"] for result in results], [f"GP Discussion:{expected.name}"])

	def test_guest_space_filter_is_limited_to_granted_spaces(self):
		grant_guest_access(self.guest, self.space)
		inaccessible_space = create_space(
			"Guest Inaccessible Search Space",
			self.community,
			is_private=1,
			members=[self.member],
		)
		expected = self.create_discussion(
			"Granted guest result",
			"guestfilterneedle in the granted space",
		)
		self.create_discussion(
			"Ungranted guest result",
			"guestfilterneedle in an ungranted space",
			space=inaccessible_space,
		)
		drain_search_index_queue()

		results = self.search_as(
			self.guest,
			"guestfilterneedle",
			filters={"project": [str(self.space.name), str(inaccessible_space.name)]},
		)

		self.assertEqual([result["id"] for result in results], [f"GP Discussion:{expected.name}"])

	def test_empty_permission_intersection_blocks_all_matching_documents(self):
		inaccessible_space = create_space(
			"Empty Intersection Search Space",
			self.community,
			is_private=1,
			members=[self.member],
		)
		self.create_discussion(
			"Accessible empty-intersection result",
			"emptyintersectionneedle in an accessible space",
		)
		self.create_discussion(
			"Inaccessible empty-intersection result",
			"emptyintersectionneedle in the requested inaccessible space",
			space=inaccessible_space,
		)
		drain_search_index_queue()

		results = self.search_as(
			self.second_member,
			"emptyintersectionneedle",
			filters={"project": [str(inaccessible_space.name)]},
		)

		self.assertEqual(results, [])

	def test_tag_filter_matches_a_discussion_with_multiple_tags(self):
		discussion = self.create_discussion(
			"Multiple tag search result",
			"<p>multitagneedle belongs to two tags.</p>"
			'<span class="tag-item" data-tag-label="launch">#launch</span>'
			'<span class="tag-item" data-tag-label="planning">#planning</span>',
		)
		self.search.build_index()

		results = self.search_as(
			self.member,
			"multitagneedle",
			filters={"tags": ["launch"]},
		)

		self.assertEqual([result["id"] for result in results], [f"GP Discussion:{discussion.name}"])

	def test_tagged_discussion_is_searchable_after_incremental_indexing(self):
		discussion = self.create_discussion(
			"Incrementally tagged search result",
			"<p>incrementaltagneedle is indexed after the bulk build.</p>"
			'<span class="tag-item" data-tag-label="incremental">#incremental</span>',
		)

		self.assert_hook_indexed_or_queued(discussion, "incrementaltagneedle")
		drain_search_index_queue()
		results = self.search_as(
			self.member,
			"incrementaltagneedle",
			filters={"tags": ["incremental"]},
		)

		self.assertEqual([result["id"] for result in results], [f"GP Discussion:{discussion.name}"])

	def test_comment_hook_indexes_its_space_and_community(self):
		discussion = self.create_discussion(
			"Comment hook parent",
			"A parent for comment index coverage",
		)
		comment = create_comment(
			discussion,
			content="commenthookneedle resolves its parent space and community",
			owner=self.member,
		)

		self.assert_hook_indexed_or_queued(comment, "commenthookneedle")
		drain_search_index_queue()
		results = self.search_as(
			self.member,
			"commenthookneedle",
			filters={"project": [self.space.name], "team": [self.community.name]},
		)

		self.assertEqual([result["id"] for result in results], [f"GP Comment:{comment.name}"])


class TestSearchIndexMissing(IsolatedSearchIndex, GameplanTestCase):
	"""Search on a site whose index has not been built yet (#578).

	The recovery tests share one invariant: from any state of the index files, with no
	build running, the single job that search queues must leave a working index. A rule
	that queues a job which does nothing would loop forever when the scheduler is off.
	"""

	INDEX_NAME = "test_gameplan_search_missing.db"
	FRESH_JOB_ID = "gameplan.search_sqlite.GameplanSearch"
	RESUME_JOB_ID = "gameplan.search_sqlite.GameplanSearch_continuation"

	def setUp(self):
		super().setUp()
		self.isolate_search_index()
		self.search = GameplanSearch()
		self.search.drop_index()
		self.enqueue = self.start_patch("gameplan.search_sqlite.frappe.enqueue")
		self.build_running = self.start_patch("gameplan.search_sqlite.is_job_enqueued", return_value=False)

	def start_patch(self, target, **kwargs):
		patcher = patch(target, **kwargs)
		self.addCleanup(patcher.stop)
		return patcher.start()

	def test_missing_index_is_a_503_without_an_error_log(self):
		self.assertEqual(GameplanSearchIndexMissingError.http_status_code, 503)
		self.assertTrue(GameplanSearchIndexMissingError.skip_error_log)

	def test_a_new_site_gets_a_fresh_build(self):
		self.assert_one_job_recovers(self.FRESH_JOB_ID)
		self.assertTrue(self.enqueue.call_args.kwargs["deduplicate"])

	def test_command_palette_returns_no_results_while_the_index_builds(self):
		with self.as_user(self.member):
			self.assertEqual(command_palette_search("anything"), [])

		self.enqueue.assert_called_once()

	def test_a_running_build_is_not_queued_again(self):
		self.leave_a_stopped_build()
		self.build_running.return_value = True

		self.search_while_index_is_missing()

		self.enqueue.assert_not_called()

	def test_a_build_that_stopped_part_way_is_resumed(self):
		self.leave_a_stopped_build()

		self.assert_one_job_recovers(self.RESUME_JOB_ID)

	def test_a_build_that_failed_during_setup_is_rebuilt(self):
		# The temp database exists but has no progress rows, so a resume has nothing to do.
		open(self.temp_db_path(), "w").close()

		self.assert_one_job_recovers(self.FRESH_JOB_ID)

	def test_a_resume_that_did_nothing_is_not_repeated(self):
		# The review case: a resume ran, created nothing, and its job record has expired.
		open(self.temp_db_path(), "w").close()
		frappe_sqlite_search.build_index(
			search_class_path=self.FRESH_JOB_ID, force=True, is_continuation=True
		)
		self.assertFalse(self.search.index_exists())

		self.assert_one_job_recovers(self.FRESH_JOB_ID)

	def test_a_finished_build_that_was_never_renamed_is_rebuilt(self):
		# Every progress row is complete, so a resume returns before the rename.
		with patch("frappe.search.sqlite_search.os.rename", side_effect=OSError), self.assertRaises(OSError):
			GameplanSearch().build_index()
		self.assertTrue(os.path.exists(self.temp_db_path()))

		self.assert_one_job_recovers(self.FRESH_JOB_ID)

	def test_an_unreadable_temp_database_is_rebuilt(self):
		with open(self.temp_db_path(), "wb") as file:
			file.write(b"not a sqlite database")

		self.assert_one_job_recovers(self.FRESH_JOB_ID)

	def test_search_still_reports_a_missing_index_when_the_queue_is_down(self):
		self.enqueue.side_effect = RedisConnectionError

		self.search_while_index_is_missing()
		with self.as_user(self.member):
			self.assertEqual(command_palette_search("anything"), [])

	def test_job_lookups_failing_on_a_down_queue_still_report_a_missing_index(self):
		self.build_running.side_effect = RedisConnectionError

		self.search_while_index_is_missing()

		self.enqueue.assert_not_called()

	def test_install_queues_the_first_build(self):
		enqueue_search_index_build()

		self.enqueue.assert_called_once()
		self.assertEqual(self.enqueue.call_args.kwargs["job_id"], self.FRESH_JOB_ID)

	def test_install_survives_a_missing_queue(self):
		self.enqueue.side_effect = RedisConnectionError

		enqueue_search_index_build()

		self.enqueue.assert_called_once()

	def assert_one_job_recovers(self, job_id):
		"""Search queues exactly `job_id`, and running it the way a worker would fixes search."""
		self.search_while_index_is_missing()

		self.enqueue.assert_called_once()
		self.assertEqual(self.enqueue.call_args.kwargs["job_id"], job_id)

		method, *_ = self.enqueue.call_args.args
		job_kwargs = {
			key: value
			for key, value in self.enqueue.call_args.kwargs.items()
			if key not in {"queue", "job_id", "deduplicate", "timeout"}
		}
		frappe.get_attr(method)(**job_kwargs)

		self.assertTrue(GameplanSearch().index_exists())
		with self.as_user(self.member):
			self.assertEqual(search_sqlite("anything")["results"], [])

	def leave_a_stopped_build(self):
		"""Stop a real fresh build part way, the way a failed or killed job does.

		isolate_search_index removes the temp database afterwards, with the rest of the
		index files.
		"""
		failure = patch.object(GameplanSearch, "get_documents_paginated", side_effect=RuntimeError)
		with failure, self.assertRaises(RuntimeError):
			GameplanSearch().build_index()

		self.assertTrue(os.path.exists(self.temp_db_path()))
		self.assertFalse(self.search.index_exists())

	def temp_db_path(self):
		return self.search._get_db_path(is_temp=True)

	def search_while_index_is_missing(self):
		with self.as_user(self.member), self.assertRaises(GameplanSearchIndexMissingError):
			search_sqlite("anything")
