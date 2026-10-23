# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

from html import escape
from unittest.mock import patch

import frappe

from gameplan import public_sitemap
from gameplan.public_seo import discussion_path, get_public_page, space_path
from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import (
	create_comment,
	create_community,
	create_discussion,
	create_poll,
	create_space,
	public_access,
)
from gameplan.visibility import VISIBILITY_ANONYMOUS, VISIBILITY_MEMBER_ACCESS


class TestPublicSEO(GameplanTestCase):
	def setUp(self):
		super().setUp()
		self.community = create_community("SEO Community", visibility=VISIBILITY_ANONYMOUS)
		self.space = create_space("SEO Space", self.community, visibility=VISIBILITY_ANONYMOUS)
		self.post = create_discussion(
			"Public SEO title", self.space, content="<p>Public <b>body</b>.</p>", owner=self.member
		)
		self.comment = create_comment(self.post, content="<p>Public reply</p>", owner=self.second_member)
		self.hidden_space = create_space("Secret Space", self.community)
		self.hidden = create_discussion("Secret title", self.hidden_space, content="Secret body")

	def page(self, path, user="Guest"):
		with public_access(), self.as_request(path, user=user):
			return get_public_page()

	def sitemap(self, **params):
		with public_access(), patch.object(frappe.local, "form_dict", frappe._dict(params)):
			return public_sitemap.get_context(frappe._dict())

	def test_html_contains_public_content_and_safe_metadata(self):
		seo = self.page(discussion_path(self.post))
		head = frappe.render_template("gameplan/templates/public/head.html", {"seo": seo})
		body = frappe.render_template("gameplan/templates/public/body.html", {"seo": seo})
		self.assertIn("Public SEO title", head)
		self.assertIn('rel="canonical"', head)
		self.assertIn('property="og:description"', head)
		self.assertIn("Public <b>body</b>", body)
		self.assertIn("Public reply", body)
		self.assertNotIn(self.member.name, head + body)
		self.assertNotIn(self.second_member.name, head + body)
		self.assertNotIn("Secret", head + body)

	def test_signed_in_private_pages_have_no_public_payload(self):
		self.assertIsNone(self.page(discussion_path(self.hidden), user=self.admin.name))

	def test_private_and_missing_links_are_not_found(self):
		for path in (
			discussion_path(self.hidden),
			space_path(self.hidden_space),
			discussion_path(self.post).replace(str(self.post.name) + "/", "999999999/"),
		):
			with self.subTest(path=path), self.assertRaises(frappe.DoesNotExistError):
				self.page(path)

	def test_metadata_escapes_markup_and_body_removes_document_tags(self):
		frappe.db.set_value(
			"GP Discussion",
			self.post.name,
			{
				"title": '<script>alert("title")</script>',
				"content": '<meta http-equiv="refresh" content="0;url=https://evil.test"><p>Safe</p><a href="https://example.com">Link</a>',
			},
		)
		seo = self.page(discussion_path(self.post))
		head = frappe.render_template("gameplan/templates/public/head.html", {"seo": seo})
		self.assertNotIn("<script>", head)
		self.assertNotIn("<meta", seo.discussion.content)
		self.assertIn('rel="ugc nofollow noopener noreferrer"', seo.discussion.content)

	def test_stale_slug_and_space_redirect_to_the_current_public_url(self):
		path = discussion_path(self.post).replace(self.post.slug, "old-slug")
		with self.assertRaises(frappe.Redirect) as redirect:
			self.page(path)
		self.assertEqual(redirect.exception.http_status_code, 301)
		self.assertEqual(frappe.flags.redirect_location, discussion_path(self.post))

	def test_unicode_identifiers_do_not_redirect_to_themselves(self):
		community = create_community("Café", visibility=VISIBILITY_ANONYMOUS)
		space = create_space("International", community, visibility=VISIBILITY_ANONYMOUS)
		post = create_discussion("An international discussion", space)
		path = discussion_path(post)
		self.assertIn("caf%C3%A9", path)
		self.assertEqual(self.page(path).path, path)

	def test_replies_have_real_pagination_and_distinct_canonicals(self):
		with patch("gameplan.public_seo.PAGE_SIZE", 1):
			create_comment(self.post, content="<p>Later reply</p>")
			first = self.page(discussion_path(self.post))
			second = self.page(discussion_path(self.post) + "?page=2")
		self.assertEqual(first.next, discussion_path(self.post) + "?page=2")
		self.assertIn("?page=2", second.url)
		self.assertEqual(second.previous, discussion_path(self.post))
		self.assertEqual(second.comments[0].content, "<p>Later reply</p>")

	def test_polls_remain_reachable_when_there_are_no_more_comments(self):
		create_poll("First question", self.post)
		create_poll("Second question", self.post)
		with patch("gameplan.public_seo.PAGE_SIZE", 1):
			first = self.page(discussion_path(self.post))
			second = self.page(discussion_path(self.post) + "?page=2")
		self.assertTrue(first.next)
		self.assertEqual(second.comments, [])
		self.assertEqual(second.polls[0].title, "Second question")
		body = frappe.render_template("gameplan/templates/public/body.html", {"seo": second})
		self.assertIn("Second question", body)
		self.assertIn("Yes", body)

	def test_direct_reply_links_redirect_to_the_reply_page(self):
		comment = create_comment(self.post, content="Later reply")
		with patch("gameplan.public_seo.PAGE_SIZE", 1), self.assertRaises(frappe.Redirect):
			self.page(discussion_path(self.post) + f"?comment={comment.name}")
		self.assertEqual(
			frappe.flags.redirect_location, discussion_path(self.post) + f"?page=2&comment={comment.name}"
		)

	def test_embedded_polls_follow_their_comment_page_and_links(self):
		draft = escape(
			frappe.as_json(
				{"title": "Later embedded question", "options": [{"title": "Yes"}, {"title": "No"}]}
			),
			quote=True,
		)
		comment = create_comment(
			self.post, content=f'<p>Later reply</p><div data-type="poll" data-poll-draft="{draft}"></div>'
		)
		poll = frappe.db.get_value("GP Poll", {"comment": comment.name})
		with patch("gameplan.public_seo.PAGE_SIZE", 1):
			first = self.page(discussion_path(self.post))
			second = self.page(discussion_path(self.post) + "?page=2")
			self.assertEqual(first.polls, [])
			self.assertEqual([str(p.name) for p in second.polls], [str(poll)])
			with self.assertRaises(frappe.Redirect):
				self.page(discussion_path(self.post) + f"?poll={poll}")
			self.assertEqual(
				frappe.flags.redirect_location, discussion_path(self.post) + f"?page=2&poll={poll}"
			)
			frappe.db.set_value("GP Comment", comment.name, "deleted_at", frappe.utils.now())
			self.assertEqual(self.page(discussion_path(self.post) + "?page=2").polls, [])

	def test_edits_and_deleted_replies_are_reflected_in_the_next_render(self):
		self.page(discussion_path(self.post))
		frappe.db.set_value("GP Discussion", self.post.name, "content", "<p>Updated body</p>")
		frappe.db.set_value("GP Comment", self.comment.name, "deleted_at", frappe.utils.now())
		seo = self.page(discussion_path(self.post))
		body = frappe.render_template("gameplan/templates/public/body.html", {"seo": seo})
		self.assertIn("Updated body", body)
		self.assertNotIn("Public reply", body)
		self.assertIn("This message is deleted.", body)

	def test_archiving_a_space_removes_its_public_html_and_sitemap_urls(self):
		self.space.archive()
		with self.assertRaises(frappe.DoesNotExistError):
			self.page(discussion_path(self.post))
		data = self.sitemap(section="discussions", page="1")
		self.assertFalse(any(discussion_path(self.post) in link.loc for link in data.links))

	def test_invalid_and_empty_pages_are_not_found(self):
		for page in ("0", "-1", "bad", "999999999", "2"):
			with self.subTest(page=page), self.assertRaises(frappe.DoesNotExistError):
				self.page(discussion_path(self.post) + "?page=" + page)

	def test_community_and_space_feeds_link_to_public_discussions(self):
		for path in (f"/g/community/{self.community.name}/discussions", space_path(self.space)):
			seo = self.page(path)
			self.assertIn(discussion_path(self.post), [row.path for row in seo.rows])
			self.assertNotIn(self.hidden.title, [row.title for row in seo.rows])

	def test_sitemap_uses_anonymous_permissions_even_for_an_admin(self):
		data = self.sitemap(section="discussions", page="1")
		urls = [link.loc for link in data.links]
		self.assertTrue(any(discussion_path(self.post) in url for url in urls))
		self.assertFalse(any(discussion_path(self.hidden) in url for url in urls))
		self.assertEqual(frappe.session.user, "Administrator")

	def test_public_rendering_preserves_the_real_session_and_request(self):
		session = frappe.local.session
		form_dict = frappe.local.form_dict
		snapshot = dict(session)
		self.sitemap(section="discussions", page="1")
		self.assertIs(frappe.local.session, session)
		self.assertEqual(dict(session), snapshot)
		self.assertIs(frappe.local.form_dict, form_dict)

	def test_sitemap_and_html_follow_visibility_changes_without_a_cache(self):
		self.sitemap(section="discussions", page="1")
		self.space.set_visibility(VISIBILITY_MEMBER_ACCESS)
		with self.assertRaises(frappe.DoesNotExistError):
			self.page(discussion_path(self.post))
		data = self.sitemap(section="discussions", page="1")
		self.assertFalse(any(discussion_path(self.post) in link.loc for link in data.links))

	def test_sitemap_index_splits_large_collections(self):
		with patch.object(public_sitemap, "SITEMAP_SIZE", 1):
			index = self.sitemap()
		self.assertTrue(index.sitemaps)
		self.assertTrue(any("section=discussions" in url for url in index.sitemaps))

	def test_disabled_site_has_an_empty_sitemap(self):
		with public_access(False):
			data = public_sitemap.get_context(frappe._dict())
		self.assertEqual(data.links, [])
		self.assertEqual(data.sitemaps, [])
