# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt


import frappe

from gameplan.utils import extract_file_references, file_reference_from_url


class HasAttachments:
	"""Attach files referenced in a doc's HTML content to the doc itself.

	Editor uploads are created private and unattached (frappe/security#206), which
	means only the uploader can read them. Attaching each referenced File to its
	parent doc makes Frappe's File.has_permission delegate access to the parent's
	read permission, so other members who can read the doc can read its images.

	Doctypes opt in by setting `attachments_field` (defaults to "content") and
	calling `attach_files_in_content()` from `on_update`, mirroring HasMentions.
	"""

	def attach_files_in_content(self, allow_session_owner=True):
		field = getattr(self, "attachments_field", "content")
		references = extract_file_references(self.get(field))
		if not references:
			return

		self._attach_referenced_files(references, self.allowed_file_owners(allow_session_owner))

	def attach_files_at_urls(self, urls, allowed_owners):
		"""Attach files named by plain URL fields rather than by HTML content.

		Frappe attaches `Attach`/`Attach Image` values on its own, but only for fields
		declared on the parent doctype's meta (`attach_files_to_document`). A child
		table's Attach field is never scanned, so its File stays unattached and, if it
		is private, readable only by whoever uploaded it. Doctypes with such a child
		table call this from `on_update` for the rows they own.
		"""
		references = {reference for url in urls if (reference := file_reference_from_url(url))}
		if not references:
			return

		self._attach_referenced_files(references, allowed_owners)

	def allowed_file_owners(self, allow_session_owner=True):
		owners = {self.owner}
		if allow_session_owner:
			owners.add(frappe.session.user)
		return owners

	def _attach_referenced_files(self, references, allowed_owners):
		for file in self._get_referenced_files(references):
			self._maybe_attach_file(file, allowed_owners)

	def _get_referenced_files(self, references):
		exact_file_names = {reference.file_name for reference in references if reference.file_name}
		fallback_urls = {reference.file_url for reference in references if not reference.file_name}

		files = {}
		if exact_file_names:
			for file in self._get_private_files({"name": ("in", list(exact_file_names))}):
				files[file.name] = file

		if fallback_urls:
			for file in self._get_private_files({"file_url": ("in", list(fallback_urls))}):
				files[file.name] = file

		return files.values()

	def _get_private_files(self, filters):
		if not filters:
			return []

		query = frappe.qb.get_query(
			"File",
			filters={**filters, "is_private": 1},
			fields=[
				"name",
				"owner",
				"file_url",
				"attached_to_doctype",
				"attached_to_name",
			],
		)
		return query.run(as_dict=True)

	def _maybe_attach_file(self, file, allowed_owners):
		# Only attach files the saver uploaded — attaching someone else's private
		# file would expose it to everyone who can read this doc.
		if file.owner not in allowed_owners:
			return

		if file.attached_to_doctype == self.doctype and file.attached_to_name == self.name:
			return
		if file.attached_to_doctype and file.attached_to_name:
			self._copy_attachment(file)
			return
		if file.attached_to_doctype and file.attached_to_doctype != self.doctype:
			return
		if file.attached_to_name and file.attached_to_name != self.name:
			return

		# Bare db.set_value avoids File.validate (disk moves / private-access checks
		# that can throw in another user's session) and the modified-timestamp bump.
		frappe.db.set_value(
			"File",
			file.name,
			{"attached_to_doctype": self.doctype, "attached_to_name": self.name},
			update_modified=False,
		)

	def _copy_attachment(self, file):
		if frappe.db.exists(
			"File",
			{
				"file_url": file.file_url,
				"attached_to_doctype": self.doctype,
				"attached_to_name": self.name,
				"is_private": 1,
			},
		):
			return

		frappe.get_doc("File", file.name).create_attachment_copy(
			self.doctype,
			self.name,
			ignore_permissions=True,
		)
