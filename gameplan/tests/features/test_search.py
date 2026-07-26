from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from gameplan.search_sqlite import GameplanSearch
from gameplan.tests.fixtures import create_community, create_space


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


class TestSearchRanking(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
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
		self.search.drop_index()
		frappe.db.rollback()

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


class TestSearchIndexLifecycle(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		community = create_community("Search Index Lifecycle Community")
		self.space = create_space("Search Index Lifecycle Space", community)
		self.search = GameplanSearch()
		self.search.drop_index()
		self.search.build_index()

	def tearDown(self):
		frappe.set_user("Administrator")
		self.search.drop_index()
		frappe.db.rollback()

	def create_discussion(self, title, content, space=None):
		return frappe.get_doc(
			doctype="GP Discussion",
			title=title,
			project=(space or self.space).name,
			content=content,
		).insert(ignore_permissions=True)

	def result_ids(self, query):
		return {result["id"] for result in self.search.search(query)["results"]}

	def test_content_is_indexed_on_create(self):
		discussion = self.create_discussion(
			"Create hook coverage",
			"createhookneedle appears only after the index already exists",
		)

		self.assertIn(f"GP Discussion:{discussion.name}", self.result_ids("createhookneedle"))

	def test_content_is_reindexed_on_update(self):
		discussion = self.create_discussion(
			"Update hook coverage",
			"oldhookneedle is replaced when the discussion changes",
		)

		discussion.content = "newhookneedle appears only in the saved revision"
		discussion.save(ignore_permissions=True)

		self.assertNotIn(f"GP Discussion:{discussion.name}", self.result_ids("oldhookneedle"))
		self.assertIn(f"GP Discussion:{discussion.name}", self.result_ids("newhookneedle"))

	def test_content_is_removed_from_index_on_delete(self):
		discussion = self.create_discussion(
			"Delete hook coverage",
			"deletehookneedle disappears with the discussion",
		)
		self.assertIn(f"GP Discussion:{discussion.name}", self.result_ids("deletehookneedle"))

		discussion.delete(ignore_permissions=True)

		self.assertNotIn(f"GP Discussion:{discussion.name}", self.result_ids("deletehookneedle"))

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

		results = self.search.search(
			"spacefilterneedle",
			filters={"project": [self.space.name]},
		)["results"]

		self.assertEqual([result["id"] for result in results], [f"GP Discussion:{expected.name}"])
