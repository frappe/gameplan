# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""Anonymous search must not turn a stale shared index into a permission bypass."""

import json
from unittest.mock import patch

import frappe

from gameplan.api import get_search_filter_options, search_sqlite
from gameplan.public_access import (
	ANONYMOUS_RATE_LIMITS,
	VISIBILITY_ANONYMOUS,
	VISIBILITY_GENERAL,
	VISIBILITY_MEMBER_ACCESS,
	VISIBILITY_TIERS,
)
from gameplan.public_search import MAX_PUBLIC_RESULTS, PublicGameplanSearch, highlight_text
from gameplan.search_sqlite import GameplanSearch
from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import (
	create_comment,
	create_community,
	create_discussion,
	create_page,
	create_space,
	create_task,
)
from gameplan.tests.search_isolation import IsolatedSearchIndex


class TestPublicSearch(IsolatedSearchIndex, GameplanTestCase):
	INDEX_NAME = "test_gameplan_public_search.db"

	def setUp(self):
		super().setUp()
		self.isolate_search_index()
		settings = patch.dict(frappe.conf, gameplan_public_access_enabled=1, gameplan_demo_enabled=0)
		settings.start()
		self.addCleanup(settings.stop)
		self.spaces = {}
		self.discussions = {}
		for community_tier in VISIBILITY_TIERS:
			community = create_community(
				f"Search {community_tier}", visibility=community_tier, members=[self.member]
			)
			for space_tier in VISIBILITY_TIERS:
				space = create_space(
					f"Search {community_tier} {space_tier}", community, visibility=space_tier
				)
				key = (community_tier, space_tier)
				self.spaces[key] = space
				self.discussions[key] = create_discussion(
					"forumneedle discussion", space, content="forumneedle body", owner=self.member
				)
		self.public_space = self.spaces[(VISIBILITY_ANONYMOUS, VISIBILITY_ANONYMOUS)]
		self.public_discussion = self.discussions[(VISIBILITY_ANONYMOUS, VISIBILITY_ANONYMOUS)]
		self.comment = create_comment(self.public_discussion, content="forumneedle reply", owner=self.member)
		self.task = create_task("forumneedle internal task", self.public_space, owner=self.member)
		self.task.description = "forumneedle internal task body"
		self.page = create_page("forumneedle internal page", self.public_space, owner=self.member)
		self.task_comment = frappe.get_doc(
			doctype="GP Comment",
			reference_doctype="GP Task",
			reference_name=self.task.name,
			content="forumneedle task reply",
		).insert(ignore_permissions=True)
		self.search = PublicGameplanSearch()
		self.search.drop_index()
		# Index this test's corpus only, not unrelated records left on the disposable site.
		self.search._ensure_fts_table()
		corpus = [*self.discussions.values(), self.comment, self.task, self.page, self.task_comment]
		self.search._index_documents([self.search.prepare_document(doc) for doc in corpus])

	def anonymous_search(self, query="forumneedle", filters=None):
		with self.as_user("Guest"):
			return search_sqlite(query, filters)

	def result_ids(self, response):
		return {result["id"] for result in response["results"]}

	def test_only_the_anonymous_anonymous_pair_returns_discussions_and_replies(self):
		response = self.anonymous_search()
		self.assertEqual(
			self.result_ids(response),
			{f"GP Discussion:{self.public_discussion.name}", f"GP Comment:{self.comment.name}"},
		)
		self.assertEqual(response["summary"]["total_matches"], 2)

	def test_anonymous_metadata_has_handles_not_emails_or_private_ranking_fields(self):
		response = self.anonymous_search()
		handle = frappe.db.get_value("GP User Profile", {"user": self.member.name}, "name")
		self.assertTrue(handle)
		for result in response["results"]:
			self.assertEqual(result["author"], handle)
			self.assertNotIn("owner", result)
			self.assertNotIn("bm25_score", result)
		self.assertNotIn(self.member.name, json.dumps(response))

	def test_selected_space_filters_only_narrow_public_permissions(self):
		private = self.spaces[(VISIBILITY_MEMBER_ACCESS, VISIBILITY_MEMBER_ACCESS)]
		self.assertEqual(self.anonymous_search(filters={"project": [str(private.name)]})["results"], [])
		mixed = self.anonymous_search(filters={"project": [str(private.name), str(self.public_space.name)]})
		self.assertEqual(self.result_ids(mixed), self.result_ids(self.anonymous_search()))

	def test_community_and_type_filters_cannot_reveal_internal_content(self):
		private = self.spaces[(VISIBILITY_MEMBER_ACCESS, VISIBILITY_MEMBER_ACCESS)]
		self.assertEqual(self.anonymous_search(filters={"team": [private.team]})["results"], [])
		for doctype in ("GP Task", "GP Page"):
			self.assertEqual(self.anonymous_search(filters={"doctype": [doctype]})["results"], [])
		response = self.anonymous_search(filters={"doctype": ["GP Comment"]})
		self.assertEqual(self.result_ids(response), {f"GP Comment:{self.comment.name}"})

	def test_author_and_arbitrary_sql_filters_are_refused(self):
		for field in ("owner", "author", "tags", "project) OR 1=1 --"):
			with self.subTest(field=field), self.assertRaises(frappe.PermissionError):
				self.anonymous_search(filters={field: [self.member.name]})

	def test_malformed_and_large_filters_are_refused(self):
		for filters in (
			"not json",
			"[]",
			{"project": [["!=", ""]]},
			{"project": ["x"] * 21},
			{"project": ["x" * 141]},
		):
			with self.subTest(filters=filters), self.assertRaises(frappe.ValidationError):
				self.anonymous_search(filters=filters)

	def test_query_size_and_type_are_bounded(self):
		for query in ("x" * 201, "word " * 13):
			with self.assertRaises(frappe.ValidationError):
				self.anonymous_search(query)
		with self.assertRaises(TypeError):
			self.anonymous_search(["forumneedle"])
		self.assertEqual(self.anonymous_search(" ")["results"], [])
		self.assertEqual(self.anonymous_search("a")["results"], [])

	def test_spelling_suggestions_never_read_the_shared_private_vocabulary(self):
		with patch.object(
			GameplanSearch, "_find_similar_words", side_effect=AssertionError("private vocabulary read")
		):
			response = self.anonymous_search("forumnedle")
		self.assertIsNone(response["summary"]["corrected_words"])
		self.assertIsNone(response["summary"]["corrected_query"])

	def test_tier_revocation_is_immediate_without_reindexing(self):
		self.public_space.reload()
		self.public_space.set_visibility(VISIBILITY_GENERAL)
		self.assertEqual(self.anonymous_search()["results"], [])

	def test_community_revocation_is_immediate_without_reindexing(self):
		community = frappe.get_doc("GP Team", self.public_space.team)
		community.set_visibility(VISIBILITY_MEMBER_ACCESS)
		self.assertEqual(self.anonymous_search()["results"], [])

	def test_archived_space_is_removed_without_reindexing(self):
		self.public_space.reload()
		self.public_space.archive()
		self.assertEqual(self.anonymous_search()["results"], [])

	def test_archived_community_is_removed_without_reindexing(self):
		frappe.get_doc("GP Team", self.public_space.team).archive()
		self.assertEqual(self.anonymous_search()["results"], [])

	def test_moved_discussion_and_its_stale_comments_are_removed(self):
		private = self.spaces[(VISIBILITY_MEMBER_ACCESS, VISIBILITY_MEMBER_ACCESS)]
		# Do not drain the asynchronous FTS queue: it must still hold the old public space.
		frappe.db.set_value(
			"GP Discussion", self.public_discussion.name, {"project": private.name, "team": private.team}
		)
		self.assertEqual(self.anonymous_search()["results"], [])

	def test_deleted_discussion_and_orphaned_indexed_comments_are_removed(self):
		frappe.db.delete("GP Discussion", {"name": self.public_discussion.name})
		self.assertEqual(self.anonymous_search()["results"], [])

	def test_soft_deleted_comment_is_removed_without_reindexing(self):
		frappe.db.set_value("GP Comment", self.comment.name, "deleted_at", frappe.utils.now())
		self.assertEqual(
			self.result_ids(self.anonymous_search()), {f"GP Discussion:{self.public_discussion.name}"}
		)

	def test_disabled_public_access_and_demo_mode_fail_closed(self):
		for settings in ({"gameplan_public_access_enabled": 0}, {"gameplan_demo_enabled": 1}):
			with patch.dict(frappe.conf, settings):
				with self.assertRaises(frappe.PermissionError):
					self.anonymous_search()
				with self.as_user("Guest"), self.assertRaises(frappe.PermissionError):
					get_search_filter_options()

	def test_filter_options_never_scan_fts_or_expose_author_and_tag_counts(self):
		with (
			self.as_user("Guest"),
			patch.object(PublicGameplanSearch, "index_exists", return_value=True),
			patch.object(PublicGameplanSearch, "_get_connection", side_effect=AssertionError("facet scan")),
		):
			options = get_search_filter_options()
		self.assertEqual(options["authors"], {})
		self.assertEqual(options["tags"], {})
		self.assertIn(str(self.public_space.name), options["projects"])
		self.assertIn(self.public_space.team, options["teams"])
		for key, space in self.spaces.items():
			if key != (VISIBILITY_ANONYMOUS, VISIBILITY_ANONYMOUS):
				self.assertNotIn(str(space.name), options["projects"])
		self.assertTrue(all(count == 0 for count in options["projects"].values()))
		self.assertTrue(all(count == 0 for count in options["teams"].values()))
		self.assertEqual(set(options["doctypes"]), {"GP Discussion", "GP Comment"})

	def test_missing_index_and_disabled_search_return_empty_results(self):
		with patch.dict(frappe.conf, disable_gameplan_search=1):
			self.assertEqual(self.anonymous_search()["results"], [])
		self.search.drop_index()
		self.assertEqual(self.anonymous_search()["results"], [])

	def test_public_results_have_a_fixed_cap_and_batched_live_queries(self):
		with patch.object(frappe.db, "sql", wraps=frappe.db.sql) as queries:
			response = self.anonymous_search()
		self.assertLessEqual(queries.call_count, 4)
		self.assertLessEqual(len(response["results"]), MAX_PUBLIC_RESULTS)
		extra = [
			create_discussion(
				f"forumneedle result {index}",
				self.public_space,
				content="forumneedle body",
				owner=self.member,
			)
			for index in range(MAX_PUBLIC_RESULTS + 5)
		]
		self.search._index_documents([self.search.prepare_document(doc) for doc in extra])
		with patch.object(frappe.db, "sql", wraps=frappe.db.sql) as queries:
			response = self.anonymous_search()
		self.assertEqual(len(response["results"]), MAX_PUBLIC_RESULTS)
		self.assertLessEqual(queries.call_count, 4)

	def test_signed_in_members_keep_private_search_and_author_filters(self):
		private = self.spaces[(VISIBILITY_MEMBER_ACCESS, VISIBILITY_MEMBER_ACCESS)]
		private.reload()
		private.add_member(self.member.name)
		private.save(ignore_permissions=True)
		with self.as_user(self.member):
			response = search_sqlite(
				"forumneedle", filters={"owner": [self.member.name], "project": [str(private.name)]}
			)
		self.assertEqual(
			self.result_ids(response),
			{f"GP Discussion:{self.discussions[(VISIBILITY_MEMBER_ACCESS, VISIBILITY_MEMBER_ACCESS)].name}"},
		)

	def test_anonymous_search_routes_are_rate_limited(self):
		self.assertEqual(ANONYMOUS_RATE_LIMITS["gameplan.api.search_sqlite"], 30)
		self.assertEqual(ANONYMOUS_RATE_LIMITS["gameplan.api.get_search_filter_options"], 30)

	def test_signed_in_filters_are_not_subject_to_anonymous_size_limits(self):
		with self.as_user(self.member):
			response = search_sqlite("forumneedle", filters={"project": [str(self.public_space.name)] * 21})
		self.assertIn(f"GP Discussion:{self.public_discussion.name}", self.result_ids(response))

	def test_highlight_text_escapes_markup_except_highlight_markers(self):
		self.assertEqual(
			highlight_text("<img src=x onerror=alert(1)><mark>forum</mark>"),
			"&lt;img src=x onerror=alert(1)&gt;<mark>forum</mark>",
		)
