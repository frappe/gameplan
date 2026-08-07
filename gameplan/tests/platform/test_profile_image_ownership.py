# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""An avatar URL is not proof that the file belongs to the profile.

`GP User Profile.set_image` is whitelisted and takes a file URL straight from the
client. Nothing downstream re-checks it, so without a guard a user could point
their avatar at any `/private/files/...` path they can guess or read off another
page, and the profile would then render somebody else's private upload.
`check_image_is_ours` refuses that write at the door.
"""

import frappe
from frappe.tests.utils import FrappeTestCase


class TestAvatarFileOwnership(FrappeTestCase):
	"""`set_image` accepts a file the profile has a claim on, and nothing else."""

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
