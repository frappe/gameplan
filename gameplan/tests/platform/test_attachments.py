# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

"""Tests for frappe/security#206: editor uploads are private and get attached to
their parent doc on save so other members can still read them via permission
delegation. Covers the extract_file_urls util and the HasAttachments mixin wired
into GP Discussion / GP Comment / GP Page / GP User Profile.
"""

import os

import frappe
from frappe.tests.utils import FrappeTestCase

from gameplan.patches.backfill_private_file_attachments import execute as backfill_attachments
from gameplan.utils import extract_file_references, extract_file_urls


class TestExtractFileUrls(FrappeTestCase):
	def test_returns_local_file_paths(self):
		html = '<p>x</p><img src="/files/a.png"><a href="/private/files/b.pdf">b</a>'
		self.assertEqual(sorted(extract_file_urls(html)), ["/files/a.png", "/private/files/b.pdf"])

	def test_strips_fid_query_and_decodes_path(self):
		# the editor appends ?fid=<File.name>; the stored file_url is unquoted, so the
		# lookup path must drop the query and decode %20 -> space
		html = '<img src="/files/Screen%20Shot.png?fid=abc123">'
		self.assertEqual(extract_file_urls(html), ["/files/Screen Shot.png"])

	def test_extracts_exact_file_id_from_query(self):
		html = '<img src="/private/files/Screen%20Shot.png?fid=abc123">'
		self.assertEqual(
			extract_file_references(html),
			[("/private/files/Screen Shot.png", "abc123")],
		)

	def test_accepts_absolute_same_origin_file_urls(self):
		src = frappe.utils.get_url("/private/files/Screen%20Shot.png?fid=abc123")
		html = f'<img src="{src}">'
		self.assertEqual(
			extract_file_references(html),
			[("/private/files/Screen Shot.png", "abc123")],
		)

	def test_skips_external_and_data_urls(self):
		html = (
			'<img src="https://cdn.example.com/x.png">'
			'<img src="//evil.test/y.png">'
			'<img src="data:image/png;base64,zzz">'
		)
		self.assertEqual(extract_file_urls(html), [])

	def test_dedupes_and_handles_empty(self):
		html = '<img src="/private/files/dup.png"><img src="/private/files/dup.png">'
		self.assertEqual(extract_file_urls(html), ["/private/files/dup.png"])
		self.assertEqual(extract_file_urls(""), [])
		self.assertEqual(extract_file_urls(None), [])


class TestContentAttachments(FrappeTestCase):
	def setUp(self):
		self.member_a = _ensure_member("member_a_sec206@example.com")
		self.member_b = _ensure_member("member_b_sec206@example.com")
		self.project = frappe.get_doc(doctype="GP Project", title="Sec206 Space").insert(
			ignore_permissions=True
		)

	def _make_private_file(self, suffix, owner="Administrator"):
		"""Create a private, unattached File with real bytes on disk (unlinked on
		teardown). Returns the inserted File doc."""
		f = frappe.get_doc(
			doctype="File",
			file_name=f"sec206_{suffix}.txt",
			is_private=1,
			content=f"content-{suffix}".encode(),
		)
		f.insert(ignore_permissions=True)
		path = f.get_full_path()
		self.addCleanup(lambda: os.path.exists(path) and os.remove(path))
		if owner != "Administrator":
			frappe.db.set_value("File", f.name, "owner", owner, update_modified=False)
			f.reload()
		return f

	def _attached_to(self, file_name):
		return frappe.db.get_value(
			"File", file_name, ["attached_to_doctype", "attached_to_name"], as_dict=True
		)

	def _attachments_for_url(self, file_url):
		return frappe.get_all(
			"File",
			filters={"file_url": file_url},
			fields=["name", "attached_to_doctype", "attached_to_name"],
			order_by="creation asc",
		)

	def test_discussion_attaches_referenced_private_file(self):
		f = self._make_private_file("disc")
		d = frappe.get_doc(
			doctype="GP Discussion",
			title="has image",
			project=self.project.name,
			content=f'<p>hi</p><img src="{f.file_url}?fid={f.name}">',
		).insert(ignore_permissions=True)

		row = self._attached_to(f.name)
		self.assertEqual(row.attached_to_doctype, "GP Discussion")
		self.assertEqual(str(row.attached_to_name), str(d.name))

	def test_discussion_attaches_absolute_same_origin_private_file_url(self):
		f = self._make_private_file("absolute")
		d = frappe.get_doc(
			doctype="GP Discussion",
			title="absolute image",
			project=self.project.name,
			content=f'<img src="{frappe.utils.get_url(f.file_url)}">',
		).insert(ignore_permissions=True)

		row = self._attached_to(f.name)
		self.assertEqual(row.attached_to_doctype, "GP Discussion")
		self.assertEqual(str(row.attached_to_name), str(d.name))

	def test_attach_is_idempotent_across_edits(self):
		f = self._make_private_file("idem")
		d = frappe.get_doc(
			doctype="GP Discussion",
			title="edit me",
			project=self.project.name,
			content=f'<img src="{f.file_url}">',
		).insert(ignore_permissions=True)

		d.content = f'<p>edited</p><img src="{f.file_url}">'
		d.save(ignore_permissions=True)

		row = self._attached_to(f.name)
		self.assertEqual(str(row.attached_to_name), str(d.name))

	def test_does_not_steal_file_attached_to_another_doc(self):
		f = self._make_private_file("steal")
		first = frappe.get_doc(
			doctype="GP Discussion",
			title="first owner",
			project=self.project.name,
			content=f'<img src="{f.file_url}">',
		).insert(ignore_permissions=True)

		# a second discussion references the same file — it must NOT re-point it
		frappe.get_doc(
			doctype="GP Discussion",
			title="second",
			project=self.project.name,
			content=f'<img src="{f.file_url}">',
		).insert(ignore_permissions=True)

		row = self._attached_to(f.name)
		self.assertEqual(str(row.attached_to_name), str(first.name))

	def test_copies_file_attachment_when_same_image_is_used_in_another_doc(self):
		f = self._make_private_file("shared")
		first = frappe.get_doc(
			doctype="GP Discussion",
			title="first copy owner",
			project=self.project.name,
			content=f'<img src="{f.file_url}?fid={f.name}">',
		).insert(ignore_permissions=True)
		second = frappe.get_doc(
			doctype="GP Discussion",
			title="second copy owner",
			project=self.project.name,
			content=f'<img src="{f.file_url}?fid={f.name}">',
		).insert(ignore_permissions=True)

		attachments = self._attachments_for_url(f.file_url)
		self.assertEqual(
			{(row.attached_to_doctype, str(row.attached_to_name)) for row in attachments},
			{("GP Discussion", str(first.name)), ("GP Discussion", str(second.name))},
		)

	def test_does_not_attach_another_users_file(self):
		# file owned by member_a; discussion created by Administrator -> guard skips
		f = self._make_private_file("guard", owner=self.member_a)
		frappe.get_doc(
			doctype="GP Discussion",
			title="not mine",
			project=self.project.name,
			content=f'<img src="{f.file_url}">',
		).insert(ignore_permissions=True)

		row = self._attached_to(f.name)
		self.assertIsNone(row.attached_to_doctype)

	def test_comment_attaches_referenced_private_file(self):
		discussion = frappe.get_doc(
			doctype="GP Discussion",
			title="thread",
			project=self.project.name,
			content="<p>start</p>",
		).insert(ignore_permissions=True)
		f = self._make_private_file("cmt")
		c = frappe.get_doc(
			doctype="GP Comment",
			reference_doctype="GP Discussion",
			reference_name=discussion.name,
			content=f'<img src="{f.file_url}">',
		).insert(ignore_permissions=True)

		row = self._attached_to(f.name)
		self.assertEqual(row.attached_to_doctype, "GP Comment")
		self.assertEqual(str(row.attached_to_name), str(c.name))

	def test_fid_targets_exact_private_file_when_url_is_shared(self):
		exact = self._make_private_file("exact")
		shared_url = self._make_private_file("shared-url")
		frappe.db.set_value("File", shared_url.name, "file_url", exact.file_url, update_modified=False)

		d = frappe.get_doc(
			doctype="GP Discussion",
			title="exact file id",
			project=self.project.name,
			content=f'<img src="{exact.file_url}?fid={exact.name}">',
		).insert(ignore_permissions=True)

		exact_row = self._attached_to(exact.name)
		shared_row = self._attached_to(shared_url.name)
		self.assertEqual(exact_row.attached_to_doctype, "GP Discussion")
		self.assertEqual(str(exact_row.attached_to_name), str(d.name))
		self.assertIsNone(shared_row.attached_to_doctype)
		self.assertIsNone(shared_row.attached_to_name)

	def test_repairs_incomplete_private_file_attachment(self):
		f = self._make_private_file("incomplete")
		frappe.db.set_value(
			"File",
			f.name,
			{"attached_to_doctype": "GP Discussion", "attached_to_name": None},
			update_modified=False,
		)

		d = frappe.get_doc(
			doctype="GP Discussion",
			title="repair half link",
			project=self.project.name,
			content=f'<img src="{f.file_url}">',
		).insert(ignore_permissions=True)

		row = self._attached_to(f.name)
		self.assertEqual(row.attached_to_doctype, "GP Discussion")
		self.assertEqual(str(row.attached_to_name), str(d.name))

	def test_patch_repairs_existing_unattached_private_file(self):
		f = self._make_private_file("patch")
		d = frappe.get_doc(
			doctype="GP Discussion",
			title="pre-existing broken image",
			project=self.project.name,
			content="<p>no image yet</p>",
		).insert(ignore_permissions=True)
		frappe.db.set_value(
			"GP Discussion",
			d.name,
			"content",
			f'<img src="{f.file_url}">',
			update_modified=False,
		)

		backfill_attachments()

		row = self._attached_to(f.name)
		self.assertEqual(row.attached_to_doctype, "GP Discussion")
		self.assertEqual(str(row.attached_to_name), str(d.name))

	def test_patch_does_not_attach_file_only_owned_by_session_user(self):
		f = self._make_private_file("patch-session-owner")
		d = frappe.get_doc(
			doctype="GP Discussion",
			title="not owned by file owner",
			project=self.project.name,
			content="<p>no image yet</p>",
		).insert(ignore_permissions=True)
		frappe.db.set_value("GP Discussion", d.name, "owner", self.member_a, update_modified=False)
		frappe.db.set_value(
			"GP Discussion",
			d.name,
			"content",
			f'<img src="{f.file_url}">',
			update_modified=False,
		)

		backfill_attachments()

		row = self._attached_to(f.name)
		self.assertIsNone(row.attached_to_doctype)
		self.assertIsNone(row.attached_to_name)

	def test_patch_copies_existing_attachment_for_shared_image(self):
		f = self._make_private_file("patch-shared")
		first = frappe.get_doc(
			doctype="GP Discussion",
			title="existing attachment owner",
			project=self.project.name,
			content=f'<img src="{f.file_url}">',
		).insert(ignore_permissions=True)
		second = frappe.get_doc(
			doctype="GP Discussion",
			title="existing shared image",
			project=self.project.name,
			content="<p>no image yet</p>",
		).insert(ignore_permissions=True)
		frappe.db.set_value(
			"GP Discussion",
			second.name,
			"content",
			f'<img src="{f.file_url}">',
			update_modified=False,
		)

		backfill_attachments()

		attachments = self._attachments_for_url(f.file_url)
		self.assertEqual(
			{(row.attached_to_doctype, str(row.attached_to_name)) for row in attachments},
			{("GP Discussion", str(first.name)), ("GP Discussion", str(second.name))},
		)

	def test_page_attaches_referenced_private_file(self):
		f = self._make_private_file("page")
		p = frappe.get_doc(
			doctype="GP Page",
			title="notes",
			project=self.project.name,
			content=f'<img src="{f.file_url}">',
		).insert(ignore_permissions=True)

		row = self._attached_to(f.name)
		self.assertEqual(row.attached_to_doctype, "GP Page")
		self.assertEqual(str(row.attached_to_name), str(p.name))

	def test_user_profile_readme_attaches_referenced_private_file(self):
		# a user edits their own "About me" while logged in as themselves, so the
		# uploaded file (owned by them) passes the owner guard and attaches
		profile = frappe.db.get_value("GP User Profile", {"user": self.member_a}, "name")
		self.assertIsNotNone(profile, "member_a should have a profile")
		frappe.set_user(self.member_a)
		try:
			f = self._make_private_file("readme", owner=self.member_a)
			doc = frappe.get_doc("GP User Profile", profile)
			doc.readme = f'<p>about</p><img src="{f.file_url}">'
			doc.save(ignore_permissions=True)
		finally:
			frappe.set_user("Administrator")

		row = self._attached_to(f.name)
		self.assertEqual(row.attached_to_doctype, "GP User Profile")
		self.assertEqual(str(row.attached_to_name), str(profile))

	def test_attachment_grants_read_permission_to_other_members(self):
		"""The payoff: a private file is invisible to non-owners until it is attached
		to a doc they can read, then permission delegation grants access."""
		frappe.set_user(self.member_a)
		try:
			f = self._make_private_file("perm", owner=self.member_a)

			# before attachment: only the owner can read the private file
			self.assertFalse(
				frappe.has_permission("File", "read", doc=f.name, user=self.member_b),
				"unattached private file must not be readable by another member",
			)

			d = frappe.get_doc(
				doctype="GP Discussion",
				title="shared image",
				project=self.project.name,
				content=f'<img src="{f.file_url}">',
			).insert()

			row = self._attached_to(f.name)
			self.assertEqual(str(row.attached_to_name), str(d.name))

			# after attachment: delegation through the discussion grants read access
			self.assertTrue(
				frappe.has_permission("File", "read", doc=f.name, user=self.member_b),
				"attached private file must be readable by members who can read the discussion",
			)
		finally:
			frappe.set_user("Administrator")

	def test_draft_publish_moves_legacy_attached_file_to_discussion(self):
		f = self._make_private_file("draft")
		draft = frappe.get_doc(
			doctype="GP Draft",
			title="draft with image",
			type="Discussion",
			project=self.project.name,
			content=f'<p>draft</p><img src="{f.file_url}?fid={f.name}">',
		).insert(ignore_permissions=True)
		frappe.db.set_value(
			"File",
			f.name,
			{"attached_to_doctype": "GP Draft", "attached_to_name": draft.name},
			update_modified=False,
		)

		discussion_name = draft.publish()

		self.assertFalse(frappe.db.exists("GP Draft", draft.name))
		self.assertTrue(frappe.db.exists("File", f.name))
		row = self._attached_to(f.name)
		self.assertEqual(row.attached_to_doctype, "GP Discussion")
		self.assertEqual(str(row.attached_to_name), str(discussion_name))


def _ensure_member(email):
	if not frappe.db.exists("User", email):
		frappe.get_doc(
			doctype="User",
			email=email,
			first_name=email.split("@")[0],
			send_welcome_email=0,
			roles=[{"role": "Gameplan Member"}],
		).insert(ignore_permissions=True)
	return email
