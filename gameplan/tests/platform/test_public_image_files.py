# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""Some images have to load for a reader with no session.

Digest emails render an avatar and a community image as `<img src>` with absolute
URLs, and a mail client sends no cookie. A private file 403s there and the reader
gets a broken image instead of the initials fallback. Attaching the File does not
help: there is no session to delegate a permission to. Both have to be public.

Covers `make_profile_avatars_public` and `make_community_images_public`, which move
the files uploaded while frappe-ui defaulted uploads to private.
"""

import os

import frappe
from frappe.core.doctype.file.file import has_permission as file_has_permission
from frappe.tests.utils import FrappeTestCase

from gameplan.patches.make_community_images_public import execute as make_community_images_public
from gameplan.patches.make_profile_avatars_public import execute as make_avatars_public
from gameplan.tests.fixtures import create_community

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


class PublishedFileTestCase(FrappeTestCase):
	"""File plumbing shared by both patches. Only the reference each patch reads
	differs, so the accessors for that stay on the subclasses."""

	prefix = "file"

	def _make_private_file(self, suffix, owner=None):
		file = frappe.get_doc(
			doctype="File",
			file_name=f"{self.prefix}_{suffix}.png",
			is_private=1,
			content=f"{self.prefix}-{suffix}".encode(),
		)
		file.insert(ignore_permissions=True)
		if owner:
			frappe.db.set_value("File", file.name, "owner", owner, update_modified=False)
			file.reload()
		self._cleanup_blob(file)
		return file

	def _make_public_file(self, suffix):
		file = frappe.get_doc(
			doctype="File",
			file_name=f"{self.prefix}_{suffix}.png",
			is_private=0,
			content=f"{self.prefix}-{suffix}".encode(),
		).insert(ignore_permissions=True)
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

	def _file(self, name):
		return frappe.db.get_value("File", name, ["is_private", "file_url"], as_dict=True)


class TestAvatarVisibility(PublishedFileTestCase):
	prefix = "avatar"

	def setUp(self):
		self.member = _ensure_member("avatar_owner@example.com")
		self.other_member = _ensure_member("avatar_reader@example.com")
		self.profile = frappe.db.get_value("GP User Profile", {"user": self.member}, "name")
		self.other_profile = frappe.db.get_value("GP User Profile", {"user": self.other_member}, "name")
		self.assertIsNotNone(self.profile, "the member should have a profile")
		self.assertIsNotNone(self.other_profile, "the other member should have a profile")

	def _make_private_file(self, suffix, owner=None):
		return super()._make_private_file(suffix, owner or self.member)

	def _set_avatar(self, file_url):
		frappe.db.set_value("GP User Profile", self.profile, "image", file_url, update_modified=False)

	def _avatar(self):
		return frappe.db.get_value("GP User Profile", self.profile, "image")

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
		file = self._make_public_file("already-public")
		self._set_avatar(file.file_url)

		make_avatars_public()

		self.assertEqual(self._avatar(), file.file_url)
		self.assertEqual(self._file(file.name).is_private, 0)

	def test_it_refuses_to_publish_a_file_someone_else_uploaded(self):
		"""An avatar URL is not proof that the file belongs to the profile.

		`set_image` writes whatever URL it is handed, so a user can point their avatar at
		another user's private upload. Publishing it would hand those bytes to anyone with
		the link, and frappe would then rewrite the document that really owns the file to
		the new public URL. Both have to be refused.
		"""
		victim_file = self._make_private_file("someone-elses", owner=self.other_member)
		victim_profile = frappe.get_doc("GP User Profile", self.other_profile)
		victim_profile.cover_image = victim_file.file_url
		victim_profile.save(ignore_permissions=True)

		self._set_avatar(victim_file.file_url)

		make_avatars_public()

		row = self._file(victim_file.name)
		self.assertEqual(row.is_private, 1, "another user's private file must stay private")
		self.assertEqual(row.file_url, victim_file.file_url)
		self.assertFalse(
			file_has_permission(frappe.get_doc("File", victim_file.name), "read", user="Guest"),
			"a refused file must still be unreadable without a session",
		)
		# The victim's own document must come out of the run exactly as it went in.
		self.assertEqual(
			frappe.db.get_value("GP User Profile", self.other_profile, "cover_image"),
			victim_file.file_url,
		)
		self.assertEqual(self._avatar(), victim_file.file_url)

	def test_a_refusal_does_not_stop_the_rest_of_the_run(self):
		"""One bad reference must not cost every other profile its avatar."""
		borrowed = self._make_private_file("borrowed", owner=self.other_member)
		own = self._make_private_file("own")
		frappe.db.set_value(
			"GP User Profile", self.other_profile, "image", borrowed.file_url, update_modified=False
		)
		self._set_avatar(own.file_url)

		make_avatars_public()

		self.assertEqual(self._file(own.name).is_private, 0)
		self.assertEqual(self._avatar(), self._file(own.name).file_url)


class TestAvatarFileOwnership(FrappeTestCase):
	"""`set_image` is where the bad URL gets in, so it refuses one at the door too.

	The patch guard stands on its own (a URL can also be written before this shipped),
	but rejecting the write is what stops the reference existing in the first place.
	"""

	def setUp(self):
		self.member = _ensure_member("avatar_setter@example.com")
		self.other_member = _ensure_member("avatar_victim@example.com")
		self.profile = frappe.get_doc("GP User Profile", {"user": self.member})

	def _make_file(self, suffix, owner, is_private=1):
		file = frappe.get_doc(
			doctype="File",
			file_name=f"set_image_{suffix}.png",
			is_private=is_private,
			content=f"set-image-{suffix}".encode(),
		)
		file.insert(ignore_permissions=True)
		frappe.db.set_value("File", file.name, "owner", owner, update_modified=False)
		file.reload()
		self.addCleanup(frappe.delete_doc, "File", file.name, force=True, ignore_permissions=True)
		return file

	def test_it_accepts_a_file_the_profile_user_uploaded(self):
		file = self._make_file("own", self.member)

		self.profile.set_image(file.file_url)

		self.assertEqual(frappe.db.get_value("GP User Profile", self.profile.name, "image"), file.file_url)

	def test_it_refuses_a_private_file_someone_else_uploaded(self):
		file = self._make_file("theirs", self.other_member)

		with self.assertRaises(frappe.PermissionError):
			self.profile.set_image(file.file_url)

	def test_it_allows_clearing_the_image(self):
		self.profile.set_image(None)

		self.assertFalse(frappe.db.get_value("GP User Profile", self.profile.name, "image"))

	def test_it_accepts_a_public_file_whoever_uploaded_it(self):
		"""A public file is readable by everyone already, so naming one exposes nothing."""
		file = self._make_file("public", self.other_member, is_private=0)

		self.profile.set_image(file.file_url)

		self.assertEqual(frappe.db.get_value("GP User Profile", self.profile.name, "image"), file.file_url)


class TestCommunityImageVisibility(PublishedFileTestCase):
	"""`GP Team.image` is rendered in every digest that groups unread discussions by
	community (`email_digest.format_discussion_groups`), so it has the same
	no-session reader as an avatar. `GP Team.cover_image` does not, and stays private.
	"""

	prefix = "community"

	def setUp(self):
		self.community = create_community("Public Image Community")

	def _set_image(self, file_url, fieldname="image"):
		frappe.db.set_value("GP Team", self.community.name, fieldname, file_url, update_modified=False)

	def _image(self, fieldname="image"):
		return frappe.db.get_value("GP Team", self.community.name, fieldname)

	def test_a_community_image_is_attached_to_the_community(self):
		"""Recorded because it decides how much work the patch has to do. `image` is an
		Attach Image on a doctype that is not a child table, so Frappe's
		attach_files_to_document picks it up on save and sets attached_to_field."""
		file = self._make_private_file("attached")
		community = frappe.get_doc("GP Team", self.community.name)
		community.image = file.file_url
		community.save(ignore_permissions=True)

		row = frappe.db.get_value(
			"File",
			file.name,
			["attached_to_doctype", "attached_to_name", "attached_to_field"],
			as_dict=True,
		)
		self.assertEqual(row.attached_to_doctype, "GP Team")
		self.assertEqual(str(row.attached_to_name), str(self.community.name))
		self.assertEqual(row.attached_to_field, "image")

	def test_it_repoints_an_image_that_is_attached(self):
		"""The normal path. Saving a community attaches its image, so Frappe can resolve
		the referencing field on its own inside handle_is_private_changed and repoints it
		without help. The patch writes the same value anyway."""
		file = self._make_private_file("attached-move")
		community = frappe.get_doc("GP Team", self.community.name)
		community.image = file.file_url
		community.save(ignore_permissions=True)

		make_community_images_public()

		self.assertEqual(self._image(), self._file(file.name).file_url)

	def test_a_private_community_image_becomes_public_and_the_community_follows_it(self):
		"""Written straight to the column, so the File is never attached. Frappe cannot
		resolve a referencing field for it and the patch's own repoint is the only
		thing standing between this row and a dead URL."""
		file = self._make_private_file("move")
		self._set_image(file.file_url)

		make_community_images_public()

		row = self._file(file.name)
		self.assertEqual(row.is_private, 0)
		self.assertEqual(row.file_url, f"/files/{file.file_name}")
		self.assertEqual(self._image(), row.file_url)

	def test_the_bytes_move_with_the_url(self):
		file = self._make_private_file("bytes")
		self._set_image(file.file_url)

		make_community_images_public()

		self.assertTrue(os.path.exists(frappe.get_site_path("public", "files", file.file_name)))
		self.assertFalse(os.path.exists(frappe.get_site_path("private", "files", file.file_name)))

	def test_a_reader_with_no_session_can_read_the_community_image(self):
		file = self._make_private_file("guest")
		self._set_image(file.file_url)
		self.assertFalse(
			file_has_permission(frappe.get_doc("File", file.name), "read", user="Guest"),
			"a private community image must not be readable without a session",
		)

		make_community_images_public()

		self.assertTrue(
			file_has_permission(frappe.get_doc("File", file.name), "read", user="Guest"),
			"a published community image must be readable without a session",
		)

	def test_running_it_twice_changes_nothing(self):
		file = self._make_private_file("rerun")
		self._set_image(file.file_url)

		make_community_images_public()
		after_first = self._file(file.name)
		make_community_images_public()

		self.assertEqual(self._file(file.name), after_first)
		self.assertEqual(self._image(), after_first.file_url)

	def test_it_finishes_a_run_that_stopped_after_moving_the_file(self):
		file = self._make_private_file("half-done")
		private_url = file.file_url
		file.is_private = 0
		file.save(ignore_permissions=True)
		self._set_image(private_url)

		make_community_images_public()

		self.assertEqual(self._image(), file.file_url)
		self.assertNotEqual(file.file_url, private_url)

	def test_a_missing_file_row_leaves_the_community_alone(self):
		self._set_image("/private/files/community_that_never_existed.png")

		make_community_images_public()

		self.assertEqual(self._image(), "/private/files/community_that_never_existed.png")

	def test_a_deleted_community_does_not_stop_the_run(self):
		"""The rows are read in one pass, so a community can go away underneath it."""
		doomed = create_community("Doomed Public Image Community")
		file = self._make_private_file("survivor")
		self._set_image(file.file_url)
		frappe.db.set_value("GP Team", doomed.name, "image", file.file_url, update_modified=False)
		frappe.delete_doc("GP Team", doomed.name, force=True, ignore_permissions=True)

		make_community_images_public()

		self.assertEqual(self._file(file.name).is_private, 0)
		self.assertEqual(self._image(), self._file(file.name).file_url)

	def test_it_leaves_the_cover_image_alone(self):
		cover = self._make_private_file("cover")
		image = self._make_private_file("scoped")
		self._set_image(image.file_url)
		self._set_image(cover.file_url, fieldname="cover_image")

		make_community_images_public()

		self.assertEqual(self._file(cover.name).is_private, 1)
		self.assertEqual(self._image("cover_image"), cover.file_url)
		self.assertEqual(self._file(image.name).is_private, 0)

	def test_it_refuses_to_publish_a_file_no_community_admin_uploaded(self):
		"""Only a community admin may set the image, so only their upload is published.

		A file owned by anyone else got there by a document naming a URL it has no claim
		on, and publishing it would expose an upload that belongs to somebody else.
		"""
		outsider = _ensure_member("community_outsider@example.com")
		file = self._make_private_file("outsider", owner=outsider)
		self._set_image(file.file_url)

		make_community_images_public()

		self.assertEqual(self._file(file.name).is_private, 1)
		self.assertEqual(self._image(), file.file_url)

	def test_it_publishes_an_image_a_community_admin_uploaded(self):
		"""The creator is not the only person who may set the image."""
		admin = _ensure_member("community_admin@example.com")
		community = create_community("Admin Uploaded Image Community", admins=[admin])
		file = self._make_private_file("admin-uploaded", owner=admin)
		frappe.db.set_value("GP Team", community.name, "image", file.file_url, update_modified=False)

		make_community_images_public()

		row = self._file(file.name)
		self.assertEqual(row.is_private, 0)
		self.assertEqual(frappe.db.get_value("GP Team", community.name, "image"), row.file_url)

	def test_an_already_public_community_image_is_left_where_it_is(self):
		file = self._make_public_file("already-public")
		self._set_image(file.file_url)

		make_community_images_public()

		self.assertEqual(self._image(), file.file_url)
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
