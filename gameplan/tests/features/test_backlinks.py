# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""Backlinks: links to a discussion recorded on save and listed on the linked discussion."""

import frappe

from gameplan.gameplan.doctype.gp_backlink.patches import backfill_backlinks
from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import create_comment, create_community, create_discussion, create_space


def link_to(discussion):
	return f'<p>See <a href="/g/space/{discussion.project}/discussion/{discussion.name}">this</a></p>'


class BacklinkTestCase(GameplanTestCase):
	def setUp(self):
		super().setUp()
		self.community = create_community("Backlink Community", members=[self.member, self.second_member])
		self.space = create_space("Open Space", self.community)
		self.private_space = create_space(
			"Private Space", self.community, is_private=1, members=[self.member]
		)
		self.target = create_discussion("Q3 Roadmap", self.space, owner=self.member)
		self.source = create_discussion("Hiring sync", self.space, owner=self.member)

	def backlinks(self, user=None):
		with self.as_user(user or self.member):
			return frappe.get_doc("GP Discussion", self.target.name).get_backlinks()

	def test_comment_link_is_listed_on_target(self):
		comment = create_comment(self.source, content=link_to(self.target))
		backlinks = self.backlinks()
		self.assertEqual(len(backlinks), 1)
		self.assertEqual(backlinks[0].comment, comment.name)
		self.assertEqual(backlinks[0].discussion, str(self.source.name))
		self.assertEqual(backlinks[0].title, "Hiring sync")

	def test_discussion_link_is_listed_on_target(self):
		post = create_discussion("Planning", self.space, content=link_to(self.target))
		backlinks = self.backlinks()
		self.assertEqual([b.discussion for b in backlinks], [str(post.name)])
		self.assertIsNone(backlinks[0].get("comment"))

	def test_absolute_link_on_same_site_counts(self):
		url = frappe.utils.get_url(f"/g/space/{self.target.project}/discussion/{self.target.name}/q3-roadmap")
		create_comment(self.source, content=f'<p><a href="{url}">roadmap</a></p>')
		self.assertEqual(len(self.backlinks()), 1)

	def test_removing_link_removes_backlink(self):
		comment = create_comment(self.source, content=link_to(self.target))
		comment.content = "<p>No link anymore</p>"
		comment.save(ignore_permissions=True)
		self.assertEqual(self.backlinks(), [])

	def test_deleting_source_removes_backlink(self):
		comment = create_comment(self.source, content=link_to(self.target))
		comment.delete(ignore_permissions=True)
		self.assertEqual(self.backlinks(), [])

	def test_target_can_be_deleted_while_linked(self):
		create_comment(self.source, content=link_to(self.target))
		self.target.delete(ignore_permissions=True)
		self.assertFalse(frappe.db.exists("GP Backlink", {"discussion": self.target.name}))

	def test_ignored_links(self):
		content = "".join(
			[
				link_to(self.source),
				'<p><a href="https://example.org/g/space/1/discussion/1">elsewhere</a></p>',
				'<p><a href="/g/space/1/discussion/999999999">missing</a></p>',
			]
		)
		comment = create_comment(self.source, content=content)
		self.assertEqual(comment.backlinks, [])

	def test_source_hidden_from_user_who_cannot_see_it(self):
		hidden = create_discussion("Salaries", self.private_space, content=link_to(self.target))
		self.assertEqual([b.discussion for b in self.backlinks()], [str(hidden.name)])
		self.assertEqual(self.backlinks(self.second_member), [])

	def test_backfill_restores_backlinks(self):
		create_comment(self.source, content=link_to(self.target))
		frappe.db.delete("GP Backlink")
		backfill_backlinks.execute()
		self.assertEqual(len(self.backlinks()), 1)
