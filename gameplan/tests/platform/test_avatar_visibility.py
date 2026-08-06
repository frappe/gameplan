# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""An avatar has to load for a reader with no session.

Digest emails render it as `<img src>` with an absolute URL and a mail client
sends no cookie, so a private avatar 403s and the reader gets a broken image
instead of the initials fallback. Attaching the File does not help: there is no
session to delegate a permission to. The avatar has to be public.

Covers `make_profile_avatars_public`, which moves the avatars uploaded while
frappe-ui defaulted uploads to private.
"""

import os

import frappe
from frappe.core.doctype.file.file import has_permission as file_has_permission
from frappe.tests.utils import FrappeTestCase

from gameplan.patches.make_profile_avatars_public import execute as make_avatars_public

# Publishing a file moves it on disk, and frappe registers an after_rollback hook to
# move it back. That hook runs during the class-level DB rollback, which is after
# every per-test cleanup, so deleting the blob any earlier makes the rollback fail on
# a file that is no longer there. Module teardown is the first point that is safely
# after it.
_BLOBS_TO_REMOVE = []


def tearDownModule():
	for path in _BLOBS_TO_REMOVE:
		if os.path.exists(path):
			os.remove(path)


class TestAvatarVisibility(FrappeTestCase):
	def setUp(self):
		self.member = _ensure_member("avatar_owner@example.com")
		self.other_member = _ensure_member("avatar_reader@example.com")
		self.profile = frappe.db.get_value("GP User Profile", {"user": self.member}, "name")
		self.assertIsNotNone(self.profile, "the member should have a profile")

	def _make_private_file(self, suffix, owner=None):
		file = frappe.get_doc(
			doctype="File",
			file_name=f"avatar_{suffix}.png",
			is_private=1,
			content=f"avatar-{suffix}".encode(),
		)
		file.insert(ignore_permissions=True)
		frappe.db.set_value("File", file.name, "owner", owner or self.member, update_modified=False)
		file.reload()
		self._cleanup_blob(file)
		return file

	def _cleanup_blob(self, file):
		"""Queue the bytes for removal from wherever the patch and the rollback leave them."""
		_BLOBS_TO_REMOVE.extend(
			[
				frappe.get_site_path("private", "files", file.file_name),
				frappe.get_site_path("public", "files", file.file_name),
			]
		)

	def _set_avatar(self, file_url):
		frappe.db.set_value("GP User Profile", self.profile, "image", file_url, update_modified=False)

	def _avatar(self):
		return frappe.db.get_value("GP User Profile", self.profile, "image")

	def _file(self, name):
		return frappe.db.get_value("File", name, ["is_private", "file_url"], as_dict=True)

	def test_a_private_avatar_becomes_public_and_the_profile_follows_it(self):
		file = self._make_private_file("move")
		self._set_avatar(file.file_url)
		self.assertTrue(file.file_url.startswith("/private/files/"))

		make_avatars_public()

		row = self._file(file.name)
		self.assertEqual(row.is_private, 0)
		self.assertEqual(row.file_url, f"/files/{file.file_name}")
		# The profile must follow the move, or it points at a URL serving nothing.
		self.assertEqual(self._avatar(), row.file_url)

	def test_the_bytes_move_with_the_url(self):
		"""The half that a straight `is_private = 0` write would get wrong: the blob
		lives under a different directory depending on the flag."""
		file = self._make_private_file("bytes")
		self._set_avatar(file.file_url)

		make_avatars_public()

		self.assertTrue(os.path.exists(frappe.get_site_path("public", "files", file.file_name)))
		self.assertFalse(os.path.exists(frappe.get_site_path("private", "files", file.file_name)))

	def test_a_reader_with_no_session_can_read_the_avatar(self):
		"""The reason for the whole change.

		`frappe.has_permission` is not the right question for Guest, because Guest is
		refused at the role level before File's own rule is consulted. What decides an
		anonymous fetch is File.has_permission's first rule: a public file is readable
		by anyone, which is why `/files/...` is served without a session check at all.
		"""
		file = self._make_private_file("guest")
		self._set_avatar(file.file_url)
		self.assertFalse(
			file_has_permission(frappe.get_doc("File", file.name), "read", user="Guest"),
			"a private avatar must not be readable without a session",
		)

		make_avatars_public()

		published = frappe.get_doc("File", file.name)
		self.assertTrue(
			file_has_permission(published, "read", user="Guest"),
			"a published avatar must be readable without a session",
		)
		self.assertTrue(
			frappe.has_permission("File", "read", doc=file.name, user=self.other_member),
			"a published avatar must stay readable to other members",
		)

	def test_running_it_twice_changes_nothing(self):
		file = self._make_private_file("rerun")
		self._set_avatar(file.file_url)

		make_avatars_public()
		after_first = self._file(file.name)
		make_avatars_public()

		self.assertEqual(self._file(file.name), after_first)
		self.assertEqual(self._avatar(), after_first.file_url)

	def test_it_finishes_a_run_that_stopped_after_moving_the_file(self):
		"""If a previous run moved the blob but did not repoint the profile, there is no
		private File left to find. The dangling URL still has to be repaired."""
		file = self._make_private_file("half-done")
		private_url = file.file_url
		self._set_avatar(private_url)
		file.is_private = 0
		file.save(ignore_permissions=True)
		self._set_avatar(private_url)

		make_avatars_public()

		self.assertEqual(self._avatar(), file.file_url)
		self.assertNotEqual(file.file_url, private_url)

	def test_a_missing_file_row_leaves_the_profile_alone(self):
		self._set_avatar("/private/files/avatar_that_never_existed.png")

		make_avatars_public()

		self.assertEqual(self._avatar(), "/private/files/avatar_that_never_existed.png")

	def test_it_leaves_every_other_private_image_alone(self):
		"""Scope check. Covers and bento cards have no no-session reader, so they stay
		private and readable by delegation instead."""
		cover = self._make_private_file("cover")
		bento = self._make_private_file("bento")
		avatar = self._make_private_file("scoped")
		self._set_avatar(avatar.file_url)
		frappe.db.set_value(
			"GP User Profile", self.profile, "cover_image", cover.file_url, update_modified=False
		)
		profile = frappe.get_doc("GP User Profile", self.profile)
		profile.append(
			"bento_cards",
			{"card_id": "image-card", "type": "Card", "size": "2x1", "image": bento.file_url},
		)
		profile.save(ignore_permissions=True)

		make_avatars_public()

		self.assertEqual(self._file(cover.name).is_private, 1)
		self.assertEqual(self._file(bento.name).is_private, 1)
		self.assertEqual(self._file(avatar.name).is_private, 0)

	def test_an_already_public_avatar_is_left_where_it_is(self):
		file = frappe.get_doc(
			doctype="File",
			file_name="avatar_already_public.png",
			is_private=0,
			content=b"already-public",
		).insert(ignore_permissions=True)
		self._cleanup_blob(file)
		self._set_avatar(file.file_url)

		make_avatars_public()

		self.assertEqual(self._avatar(), file.file_url)
		self.assertEqual(self._file(file.name).is_private, 0)


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
