# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

"""Publish private files that something has to fetch without a session.

A private File is readable by anyone who can read the document it is attached to,
which is enough for anything rendered inside the app. It is not enough for an image
in an email: a mail client sends no cookie, so `/private/files/...` 403s and the
reader gets a broken image. Those files have to be public.

`is_private` is not just a flag. It decides which directory the bytes live in and
which prefix `file_url` carries, so it can only be changed by saving the File and
letting `File.handle_is_private_changed` move the blob, rewrite the URL, and
register the rollback hook that moves it back if the transaction fails.
"""

import frappe

BATCH_SIZE = 500
PRIVATE_PREFIX = "/private/files/"
PUBLIC_PREFIX = "/files/"


def publish_files_referenced_by(doctype: str, fieldname: str) -> int:
	"""Make public every private file that `doctype.fieldname` points at.

	Returns the number of references repointed, which is what a patch can log.

	Safe to re-run: only private files are selected, so a second pass finds nothing.
	A missing File row, a deleted document, a vanished blob, or a run interrupted
	half way through all leave the reference pointing at a URL that still serves the
	bytes rather than at nothing.
	"""
	repointed = 0
	# One URL can be shared by several documents. Remember where each one moved to,
	# because after the first move there is no private file left to look up.
	moved: dict[str, str | None] = {}

	for row in _iter_rows_with_private_files(doctype, fieldname):
		old_url = row.get(fieldname)
		if old_url not in moved:
			moved[old_url] = _publish_files_at(old_url)

		new_url = moved[old_url]
		if not new_url or new_url == old_url:
			continue

		# Frappe repoints the referencing field itself in handle_is_private_changed,
		# but only for a File that is attached and whose attached_to_field resolves.
		# Belt and braces where it is attached; the only thing that repairs an
		# unattached file, which would otherwise be left behind a dead URL.
		frappe.db.set_value(doctype, row.name, fieldname, new_url, update_modified=False)
		repointed += 1

	return repointed


def _publish_files_at(file_url: str) -> str | None:
	"""Publish every private File at `file_url`; return the URL it moved to."""
	new_url = None
	for name in _get_private_files_at(file_url):
		new_url = _publish_file(name) or new_url

	# Nothing private left to move can mean an earlier run moved the blob and stopped
	# before repointing the document. Derive where it went so that gets finished.
	return new_url or _find_public_file_url(file_url)


def _publish_file(name: str) -> str | None:
	try:
		file = frappe.get_doc("File", name)
	except frappe.DoesNotExistError:
		frappe.clear_last_message()
		return None

	if not file.is_private:
		return file.file_url

	file.is_private = 0
	try:
		file.save(ignore_permissions=True)
	except (FileNotFoundError, FileExistsError):
		# The blob is gone, or a public file already holds that name. The row is
		# untouched either way, so it keeps pointing at bytes that are really there.
		frappe.clear_last_message()
		return None

	return file.file_url


def _find_public_file_url(private_url: str) -> str | None:
	public_url = PUBLIC_PREFIX + private_url[len(PRIVATE_PREFIX) :]
	if frappe.db.exists("File", {"file_url": public_url, "is_private": 0}):
		return public_url
	return None


def _get_private_files_at(file_url: str) -> list[str]:
	return frappe.qb.get_query(
		"File",
		filters={"file_url": file_url, "is_private": 1},
		fields=["name"],
		order_by="name asc",
	).run(pluck="name")


def _iter_rows_with_private_files(doctype: str, fieldname: str):
	last_name = None
	while rows := _get_rows_with_private_files(doctype, fieldname, last_name):
		yield from rows
		last_name = rows[-1].name


def _get_rows_with_private_files(doctype: str, fieldname: str, after: str | None = None):
	filters = [[fieldname, "like", f"{PRIVATE_PREFIX}%"]]
	if after:
		filters.append(["name", ">", after])

	return frappe.qb.get_query(
		doctype,
		filters=filters,
		fields=["name", fieldname],
		order_by="name asc",
		limit=BATCH_SIZE,
	).run(as_dict=True)
