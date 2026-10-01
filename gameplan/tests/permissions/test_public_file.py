# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""Images and files in public posts, for people who are not signed in.

frappe refuses /private/files/ to anyone not signed in, so `gameplan.api.public_file`
serves a private File by name when it is attached to a document the caller may read, and
public post bodies point at it. These pin both halves, and that the route follows the
tier: a space leaving Anonymous takes its files with it.
"""

from unittest.mock import patch

import frappe
from werkzeug.test import EnvironBuilder
from werkzeug.wrappers import Request

from gameplan.api import public_file
from gameplan.public_access import PUBLIC_ACCESS_CONFIG_KEY, VISIBILITY_ANONYMOUS, VISIBILITY_MEMBER_ACCESS
from gameplan.public_payload import public_file_url
from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import create_comment, create_community, create_discussion, create_space

ANONYMOUS = "Guest"
PIXEL = b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,"


def switched(on=True):
	return patch.dict(frappe.conf, {PUBLIC_ACCESS_CONFIG_KEY: 1 if on else 0})


def create_file(name, *, attached_to=None, is_private=1):
	doc = frappe.get_doc(
		doctype="File",
		file_name=name,
		content=PIXEL,
		is_private=is_private,
		attached_to_doctype=attached_to and attached_to.doctype,
		attached_to_name=attached_to and attached_to.name,
	)
	return doc.insert(ignore_permissions=True)


def attach_to_doctype_only(file, doctype):
	"""A File that names a doctype but no document: frappe would check the doctype alone."""
	frappe.db.set_value("File", file.name, {"attached_to_doctype": doctype, "attached_to_name": None})
	return file


class TestPublicFile(GameplanTestCase):
	def setUp(self):
		super().setUp()
		community = create_community("File Community", visibility=VISIBILITY_ANONYMOUS)
		self.space = create_space("File Space", community, visibility=VISIBILITY_ANONYMOUS)
		general_space = create_space("File General Space", community)
		self.discussion = create_discussion("File Discussion", self.space, owner=self.member)
		self.comment = create_comment(self.discussion, owner=self.member)
		self.hidden_discussion = create_discussion("File Hidden Discussion", general_space, owner=self.member)
		self.public_image = create_file("public-post.gif", attached_to=self.discussion)
		self.comment_image = create_file("public-reply.gif", attached_to=self.comment)
		self.hidden_image = create_file("general-post.gif", attached_to=self.hidden_discussion)
		self.loose_image = create_file("loose.gif")
		self.unprivate_image = create_file("unprivate.gif", attached_to=self.discussion, is_private=0)
		self.foreign_image = create_file("foreign.gif", attached_to=frappe.get_doc("User", self.member.name))
		self.doctype_only_image = attach_to_doctype_only(create_file("doctype-only.gif"), "GP Discussion")

	def fetch(self, fid, user=ANONYMOUS, on=True):
		request = Request(EnvironBuilder(path="/api/method/gameplan.api.public_file").get_environ())
		with patch.object(frappe.local, "request", request, create=True), switched(on), self.as_user(user):
			return public_file(fid)

	def assert_refused(self, fid, **kwargs):
		with self.assertRaises(frappe.PermissionError):
			self.fetch(fid, **kwargs)

	def test_a_file_in_a_public_post_loads_without_signing_in(self):
		for file in (self.public_image, self.comment_image):
			with self.subTest(file=file.file_name):
				response = self.fetch(file.name)
				self.assertEqual(response.status_code, 200)
				self.assertEqual(b"".join(response.response), PIXEL)
				self.assertTrue(response.headers["Cache-Control"].startswith("private"))

	def test_everything_else_is_refused(self):
		for label, fid in {
			"in a General space": self.hidden_image.name,
			"attached to nothing": self.loose_image.name,
			"not private (frappe serves it already)": self.unprivate_image.name,
			"attached to something outside Gameplan": self.foreign_image.name,
			"attached to a doctype but no document": self.doctype_only_image.name,
			"no such file": "does-not-exist",
			"no name at all": None,
		}.items():
			with self.subTest(label):
				self.assert_refused(fid)

	def test_switched_off_nothing_loads(self):
		for user in (ANONYMOUS, self.member.name):
			with self.subTest(user=user):
				self.assert_refused(self.public_image.name, user=user, on=False)

	def test_only_gameplan_content_is_served_even_to_someone_who_may_read_the_parent(self):
		# The member can read their own User record; the route still only serves files
		# attached to the doctypes whose public payloads point at it.
		self.assert_refused(self.foreign_image.name, user=self.member.name)

	def test_a_space_leaving_anonymous_takes_its_files_with_it(self):
		self.fetch(self.public_image.name)
		self.space.reload()
		self.space.set_visibility(VISIBILITY_MEMBER_ACCESS)
		self.assert_refused(self.public_image.name)

	def test_signed_in_readers_may_use_it_too(self):
		self.assertEqual(self.fetch(self.hidden_image.name, user=self.member.name).status_code, 200)


class TestPublicFileUrlsInPosts(GameplanTestCase):
	def setUp(self):
		super().setUp()
		community = create_community("File Url Community", visibility=VISIBILITY_ANONYMOUS)
		space = create_space("File Url Space", community, visibility=VISIBILITY_ANONYMOUS)
		self.discussion = create_discussion("File Url Discussion", space, owner=self.member)
		self.image = create_file("in-post.gif", attached_to=self.discussion)
		self.elsewhere = create_file("elsewhere.gif")
		self.discussion.db_set(
			"content",
			f'<p><img src="{self.image.file_url}"></p>'
			f'<p><img src="{self.image.file_url}?fid={self.image.name}"></p>'
			f'<p><a href="{self.elsewhere.file_url}?fid={self.elsewhere.name}">x</a></p>'
			'<p><img src="/files/already-public.png"></p>',
		)

	def read(self, user):
		with switched(), self.as_user(user):
			return frappe.get_doc("GP Discussion", self.discussion.name).as_dict().content

	def test_private_files_in_a_public_post_point_at_the_public_route(self):
		content = self.read(ANONYMOUS)
		self.assertEqual(content.count(f'src="{public_file_url(self.image.name)}"'), 2)
		self.assertNotIn(self.image.file_url, content)
		self.assertIn("/files/already-public.png", content)

	def test_a_file_not_attached_to_the_post_is_not_pointed_at(self):
		content = self.read(ANONYMOUS)
		self.assertNotIn(public_file_url(self.elsewhere.name), content)

	def test_signed_in_readers_get_the_post_as_it_was_written(self):
		self.assertIn(f'src="{self.image.file_url}"', self.read(self.member.name))
