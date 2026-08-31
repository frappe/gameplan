# Copyright (c) 2025, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""Draft behaviour: the one-draft-per-target rule and self-healing on read."""

import frappe

from gameplan.gameplan.doctype.gp_draft.gp_draft import (
	GPDraft,
	commit_draft,
	find_my_draft,
	get_my_drafts,
	publish_draft,
)
from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import (
	create_comment,
	create_community,
	create_discussion,
	create_member,
	create_space,
	set_owner,
)


class TestDrafts(GameplanTestCase):
	"""On GameplanTestCase for its per-test rollback: these tests insert drafts and
	switch users, and without one the rows stay visible to the next test method."""

	def test_draft_is_writable_only_by_its_owner(self):
		"""A draft is readable by any member (a shared draft URL resolves), but writes are
		owner-scoped (if_owner): one member must not edit another's draft through the generic
		client API even with its name."""
		alice = create_member("draft_alice@example.com", "Alice")
		bob = create_member("draft_bob@example.com", "Bob")

		frappe.set_user(alice.name)
		draft = frappe.get_doc(
			doctype="GP Draft", type="Discussion", mode="New", content="Alice's private draft"
		).insert()

		# The owner can read and write their own draft.
		self.assertTrue(draft.has_permission("read"))
		self.assertTrue(draft.has_permission("write"))

		# Another member can read it (e.g. a shared URL) but cannot write to it.
		frappe.set_user(bob.name)
		self.assertTrue(frappe.has_permission("GP Draft", "read", doc=draft.name, user=bob.name))
		self.assertFalse(frappe.has_permission("GP Draft", "write", doc=draft.name, user=bob.name))
		with self.assertRaises(frappe.PermissionError):
			frappe.client.set_value("GP Draft", draft.name, "content", "Bob's edit")

	def test_drafts_are_not_enumerable_across_users(self):
		"""Share-by-link only: a member can read another's draft by name (the share URL), but a
		list/report query must not enumerate it — permission_query_conditions scopes lists to the
		owner. Guards the v1 frappe.client.get_list path, which bypasses the controller get_list."""
		alice = create_member("draft_alice@example.com", "Alice")
		bob = create_member("draft_bob@example.com", "Bob")

		frappe.set_user(alice.name)
		draft = frappe.get_doc(
			doctype="GP Draft", type="Discussion", mode="New", content="Alice's private draft"
		).insert()

		frappe.set_user(bob.name)
		# Enumeration (the leak path) must not surface Alice's draft for Bob.
		names = frappe.get_list("GP Draft", pluck="name")
		self.assertNotIn(draft.name, names)

		# Share-by-link still works: a direct read by name resolves.
		self.assertTrue(frappe.has_permission("GP Draft", "read", doc=draft.name, user=bob.name))

	def test_duplicate_singleton_drafts_self_heal_on_read(self):
		"""Singleton draft creation is a find-then-insert, so a rare race can leave two rows for
		one reply. Reads collapse them: find_my_draft keeps the newest and deletes the rest, so the
		composer resumes a single draft and the duplicate can't linger."""
		# reference_name is a Dynamic Link, validated on insert — point at a real discussion.
		team = create_community("Draft Heal Team")
		project = create_space("Draft Heal Space", team.name)
		discussion = create_discussion("Draft Heal Target", project.name)

		alice = create_member("draft_alice@example.com", "Alice")
		frappe.set_user(alice.name)

		# Simulate the race: two rows for the same (owner, type, mode, reference). reference_name is
		# a Dynamic Link stored as a string, and find_my_draft (whitelisted) type-checks it as str —
		# mirror the client, which always sends the name as a string.
		ref = dict(
			type="Comment",
			mode="New",
			reference_doctype="GP Discussion",
			reference_name=str(discussion.name),
		)
		older = frappe.get_doc(doctype="GP Draft", content="older", **ref).insert()
		newer = frappe.get_doc(doctype="GP Draft", content="newer", **ref).insert()

		result = find_my_draft(**ref)

		# The newest survives; the stale duplicate is gone.
		self.assertEqual(result["name"], newer.name)
		remaining = frappe.get_all("GP Draft", filters={"owner": alice.name, **ref}, pluck="name")
		self.assertEqual(remaining, [newer.name])
		self.assertFalse(frappe.db.exists("GP Draft", older.name))
		# Permanently, not archived: a discarded autosave still holds the user's typing, and
		# a Deleted Document copy would keep it readable long after the draft is gone.
		self.assertFalse(
			frappe.db.exists("Deleted Document", {"deleted_doctype": "GP Draft", "deleted_name": older.name})
		)

	def test_deleting_a_comment_removes_its_edit_draft(self):
		alice = create_member("draft_comment_owner@example.com", "Draft Comment Owner")
		community = create_community("Draft Comment Community", members=[alice])
		space = create_space("Draft Comment Space", community)
		discussion = create_discussion("Draft Comment Discussion", space, owner=alice)
		comment = create_comment(discussion, content="Comment with an edit draft", owner=alice)

		frappe.set_user(alice.name)
		draft = frappe.get_doc(
			doctype="GP Draft",
			type="Comment",
			mode="Edit",
			reference_doctype="GP Comment",
			reference_name=str(comment.name),
			content="Uncommitted edit",
		).insert()

		frappe.delete_doc("GP Comment", comment.name)

		self.assertFalse(frappe.db.exists("GP Comment", comment.name))
		self.assertFalse(frappe.db.exists("GP Draft", draft.name))


def _insert_draft(**fields):
	"""Insert a draft as the current session user."""
	return frappe.get_doc(doctype="GP Draft", **fields).insert()


class TestDraftListScoping(GameplanTestCase):
	"""The v2 list hook is one of the two independent layers that keep drafts private."""

	def test_controller_list_query_scopes_drafts_to_the_session_user(self):
		"""`GPDraft.get_list` is the hook `/api/v2/document/GP Draft` hands its query to, and
		v2 keeps the *unnarrowed* query when the hook returns None. So the hook has to narrow
		on its own merits: this exercises it against a query built with permissions off, which
		is the only way to see the hook rather than the permission_query_conditions layer
		underneath it (gameplan.permissions.draft_query_conditions, which mirrors this rule)."""
		with self.as_user(self.member):
			mine = _insert_draft(type="Discussion", mode="New", content="my draft")
		with self.as_user(self.second_member):
			theirs = _insert_draft(type="Discussion", mode="New", content="their draft")

			query = frappe.qb.get_query(
				"GP Draft",
				fields=["name"],
				filters={"name": ["in", [mine.name, theirs.name]]},
				ignore_permissions=True,
			)
			narrowed = GPDraft.get_list(query)
			self.assertIsNotNone(narrowed, "get_list must return the narrowed query; v2 discards None")
			names = [row.name for row in narrowed.run(as_dict=True)]

		self.assertEqual(names, [theirs.name])


class TestDraftPublish(GameplanTestCase):
	"""Publishing turns a draft into a discussion and destroys the draft — a one-way step."""

	def setUp(self):
		super().setUp()
		self.community = create_community("Draft Publish Community", members=[self.member])
		self.space = create_space("Draft Publish Space", self.community)

	def _draft(self, content="<p>draft body</p>"):
		with self.as_user(self.member):
			return _insert_draft(
				type="Discussion",
				mode="New",
				title="Draft title",
				content=content,
				project=self.space.name,
			)

	def test_publishing_creates_the_discussion_and_removes_the_draft(self):
		draft = self._draft()

		with self.as_user(self.member):
			discussion_name = publish_draft(draft.name)

		# The client routes to the new discussion using this name, so returning nothing
		# strands the author on a draft that no longer exists.
		self.assertIsNotNone(discussion_name)
		discussion = frappe.get_doc("GP Discussion", discussion_name)
		self.assertEqual(discussion.title, "Draft title")
		self.assertIn("draft body", discussion.content)
		self.assertEqual(str(discussion.project), str(self.space.name))
		self.assertFalse(frappe.db.exists("GP Draft", draft.name))

	def test_publishing_strips_image_query_params_from_the_content(self):
		"""Draft images carry a ?fid= pointer to the file attached to the draft. The draft is
		deleted on publish, so a surviving ?fid= renders as a broken image in the discussion."""
		draft = self._draft(content='<p><img src="/files/pic.png?fid=abc123"></p>')

		with self.as_user(self.member):
			discussion_name = publish_draft(draft.name)

		content = frappe.db.get_value("GP Discussion", discussion_name, "content")
		self.assertIn('src="/files/pic.png"', content)
		self.assertNotIn("fid=", content)

	def test_only_the_owner_can_publish_a_draft(self):
		"""Drafts are readable by name (share-by-link), so the publish gate is the only thing
		stopping another member turning someone's half-written draft into a public post."""
		draft = self._draft()

		with self.as_user(self.second_member):
			with self.assertRaises(frappe.ValidationError):
				publish_draft(draft.name)

		self.assertTrue(frappe.db.exists("GP Draft", draft.name))
		self.assertEqual(frappe.db.count("GP Discussion", {"project": self.space.name}), 0)


class TestDraftCommit(GameplanTestCase):
	"""Committing finalises an edit whose content is already on the target document."""

	def setUp(self):
		super().setUp()
		self.community = create_community("Draft Commit Community", members=[self.member])
		self.space = create_space("Draft Commit Space", self.community)
		self.discussion = create_discussion("Draft Commit Discussion", self.space, owner=self.member)

	def _target_and_draft(self, content):
		comment = create_comment(self.discussion, content=content, owner=self.member)
		with self.as_user(self.member):
			draft = _insert_draft(
				type="Comment",
				mode="Edit",
				reference_doctype="GP Comment",
				reference_name=str(comment.name),
				content=content,
			)
		return comment, draft

	def test_committing_leaves_already_clean_target_content_untouched(self):
		"""The target holds the finished text; commit only migrates attachments and deletes the
		draft. Rewriting the target here would silently blank an edit the user just saved."""
		comment, draft = self._target_and_draft("<p>the final wording</p>")
		saved = frappe.db.get_value("GP Comment", comment.name, "content")

		with self.as_user(self.member):
			commit_draft(draft.name, "GP Comment", str(comment.name))

		self.assertEqual(frappe.db.get_value("GP Comment", comment.name, "content"), saved)
		self.assertFalse(frappe.db.exists("GP Draft", draft.name))

	def test_committing_strips_image_query_params_from_the_target(self):
		"""Images pasted while editing point at the draft's copy of the file (?fid=). Commit
		reparents the file and must clear the pointer, or the edited comment shows a broken image."""
		comment, draft = self._target_and_draft('<p><img src="/files/pic.png?fid=abc123"></p>')

		with self.as_user(self.member):
			commit_draft(draft.name, "GP Comment", str(comment.name))

		content = frappe.db.get_value("GP Comment", comment.name, "content")
		self.assertIn('src="/files/pic.png"', content)
		self.assertNotIn("fid=", content)

	def test_only_the_owner_can_commit_a_draft(self):
		comment, draft = self._target_and_draft("<p>the final wording</p>")

		with self.as_user(self.second_member):
			with self.assertRaises(frappe.ValidationError):
				commit_draft(draft.name, "GP Comment", str(comment.name))

		self.assertTrue(frappe.db.exists("GP Draft", draft.name))


class TestFindMyDraft(GameplanTestCase):
	def test_find_my_draft_resolves_a_draft_that_has_no_reference(self):
		"""Not every singleton draft points at a target: an in-flight new post is keyed by
		(owner, type, mode) alone. That branch still has to hand the row back, or the composer
		reopens empty and the user's typing looks lost."""
		with self.as_user(self.member):
			draft = _insert_draft(type="Discussion", mode="New", content="resume this")

			result = find_my_draft(type="Discussion", mode="New")

		self.assertIsNotNone(result)
		self.assertEqual(result["name"], draft.name)
		self.assertIn("resume this", result["content"])


class TestMyDrafts(GameplanTestCase):
	"""The Drafts list: what it shows, what metadata it resolves, and what it must hide."""

	def setUp(self):
		super().setUp()
		self.community = create_community("My Drafts Community", members=[self.member])
		self.space = create_space("My Drafts Space", self.community)

	def test_lists_discussion_drafts_with_their_space(self):
		"""The row carries the space's title, community and privacy so the list can render and
		route without an N+1 round trip per draft."""
		with self.as_user(self.member):
			draft = _insert_draft(
				type="Discussion",
				mode="New",
				title="Half-written post",
				content="body",
				project=self.space.name,
			)

			drafts = get_my_drafts()

		self.assertEqual([row["name"] for row in drafts], [draft.name])
		row = drafts[0]
		self.assertEqual(row["kind"], "discussion")
		self.assertEqual(row["title"], "Half-written post")
		self.assertEqual(str(row["space"]), str(self.space.name))
		self.assertEqual(row["space_title"], "My Drafts Space")
		self.assertEqual(str(row["community"]), str(self.community.name))
		self.assertEqual(row["is_private"], 0)
		self.assertIsNone(row["discussion"])

	def test_lists_comment_drafts_with_their_parent_discussion(self):
		"""A reply draft stores only its text and a reference, so the list resolves the parent
		discussion's title and space here — without them the row is unrenderable and unroutable."""
		discussion = create_discussion("Reply Target", self.space)
		with self.as_user(self.member):
			draft = _insert_draft(
				type="Comment",
				mode="New",
				reference_doctype="GP Discussion",
				reference_name=str(discussion.name),
				content="half-written reply",
			)

			drafts = get_my_drafts()

		self.assertEqual([row["name"] for row in drafts], [draft.name])
		row = drafts[0]
		self.assertEqual(row["kind"], "comment")
		self.assertEqual(row["title"], "Reply Target")
		self.assertEqual(str(row["discussion"]), str(discussion.name))
		self.assertEqual(str(row["space"]), str(self.space.name))
		self.assertEqual(row["space_title"], "My Drafts Space")
		self.assertEqual(str(row["community"]), str(self.community.name))

	def test_hides_a_draft_in_a_space_the_user_can_no_longer_reach(self):
		"""Membership can be revoked after the draft was written. The space lookup is the gate:
		if it stops checking permissions the list leaks the private space's title and hands back
		a route the user cannot open."""
		private_space = create_space("Locked Space", self.community, is_private=1)
		draft = frappe.get_doc(
			doctype="GP Draft",
			type="Discussion",
			mode="New",
			title="Written before I lost access",
			content="body",
			project=private_space.name,
		).insert(ignore_permissions=True)
		set_owner(draft, self.member)

		with self.as_user(self.member):
			drafts = get_my_drafts()

		self.assertEqual(drafts, [])

	def test_marks_a_draft_with_no_space_as_public(self):
		"""A new post drafted before a space is chosen has no space at all. Defaulting it to
		private would put a lock badge on a draft nobody has restricted."""
		with self.as_user(self.member):
			_insert_draft(type="Discussion", mode="New", title="No space yet", content="body")

			drafts = get_my_drafts()

		row = drafts[0]
		self.assertIsNone(row["space"])
		self.assertIsNone(row["space_title"])
		self.assertIsNone(row["community"])
		self.assertEqual(row["is_private"], 0)

	def test_the_list_collapses_duplicate_reply_drafts_without_deleting_them(self):
		"""One row per reply on the list path, but the stale sibling stays on disk.

		get_my_drafts is a GET so the Drafts page can be a useList, and Frappe rolls a GET
		back — a delete here would look like cleanup and change nothing. The permanent
		delete lives on find_my_draft, which runs when that reply composer next opens
		(test_duplicate_singleton_drafts_self_heal_on_read)."""
		discussion = create_discussion("Duplicate Reply Target", self.space)
		reference = dict(
			type="Comment",
			mode="New",
			reference_doctype="GP Discussion",
			reference_name=str(discussion.name),
		)
		with self.as_user(self.member):
			older = _insert_draft(content="older", **reference)
			newer = _insert_draft(content="newer", **reference)

			drafts = get_my_drafts()

		self.assertEqual([row["name"] for row in drafts], [newer.name])
		self.assertTrue(frappe.db.exists("GP Draft", older.name))
