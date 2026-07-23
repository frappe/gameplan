# Copyright (c) 2025, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""Draft behaviour: the one-draft-per-target rule and self-healing on read."""

import frappe
from frappe.tests import IntegrationTestCase

from gameplan.tests.fixtures import create_member


class TestDrafts(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")

	def tearDown(self):
		frappe.set_user("Administrator")

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
		from gameplan.gameplan.doctype.gp_draft.gp_draft import find_my_draft
		from gameplan.tests.fixtures import create_community, create_discussion, create_space

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
