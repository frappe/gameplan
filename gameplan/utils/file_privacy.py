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

from collections.abc import Callable, Iterable
from typing import NamedTuple

import frappe

BATCH_SIZE = 500
PRIVATE_PREFIX = "/private/files/"
PUBLIC_PREFIX = "/files/"


def publish_files_referenced_by(
	doctype: str,
	fieldname: str,
	allowed_owners: Callable[[frappe._dict], Iterable[str]],
	row_fields: list[str] | None = None,
) -> int:
	"""Make public every private file that `doctype.fieldname` points at.

	A File is resolved by URL, and nothing stops a document from naming a URL whose
	bytes belong to somebody else: `GP User Profile.set_image` writes whatever URL it
	is given. Publishing that file would hand a stranger's private upload to anyone
	with the link, and frappe's `File.handle_is_private_changed` would then rewrite
	the *victim's* own document to the new public URL. So every file is checked
	against `allowed_owners(row)` first, the same rule `HasAttachments` uses before it
	attaches a file to a document: only a file uploaded by someone entitled to put it
	there is published. Which owners those are depends on who may write the field, so
	each call site passes its own rule. `row_fields` names the extra columns the rule
	needs, on top of `name` and `fieldname`.

	The cost is a file an admin uploaded on someone else's behalf: it is refused, and
	the count is logged so an operator can tell "nothing to do" from "refused 12".

	Returns the number of references repointed, which is what a patch can log.

	Safe to re-run: only private files are selected, so a second pass finds nothing.
	A missing File row, a deleted document, a vanished blob, or a run interrupted
	half way through all leave the reference pointing at a URL that still serves the
	bytes rather than at nothing.
	"""
	repointed = 0
	refused: set[str] = set()
	# One URL can be shared by several documents. Remember where each one moved to,
	# because after the first move there is no private file left to look up. Only a
	# move is remembered: whether a file may be published depends on the row asking,
	# so one row being refused must not decide the answer for the next one.
	moved: dict[str, str] = {}

	for row in _iter_rows_with_private_files(doctype, fieldname, row_fields):
		old_url = row.get(fieldname)
		new_url = moved.get(old_url)
		if not new_url:
			attempt = _publish_files_at(old_url, set(allowed_owners(row)))
			refused.update(attempt.refused)
			new_url = attempt.new_url
		if not new_url:
			continue

		moved[old_url] = new_url
		if new_url == old_url:
			continue

		# Frappe repoints the referencing field itself in handle_is_private_changed,
		# but only for a File that is attached and whose attached_to_field resolves.
		# Belt and braces where it is attached; the only thing that repairs an
		# unattached file, which would otherwise be left behind a dead URL.
		frappe.db.set_value(doctype, row.name, fieldname, new_url, update_modified=False)
		repointed += 1

	if refused:
		_log_refused_files(doctype, fieldname, refused)

	return repointed


class _PublishAttempt(NamedTuple):
	"""What came of trying to publish the files at one URL.

	`refused` is what separates "there is no private File at this URL" from "there is
	one and it belongs to somebody else". Both leave `new_url` empty and they need
	opposite handling, so the difference is carried here rather than left for the
	caller to guess from a `None`.
	"""

	new_url: str | None
	refused: frozenset[str]


def _publish_files_at(file_url: str, allowed_owners: set[str]) -> _PublishAttempt:
	"""Publish every private File at `file_url` and say where it went.

	A file whose owner is not in `allowed_owners` is left private and reported as a
	refusal instead.
	"""
	new_url = None
	refused: set[str] = set()
	for file in _get_private_files_at(file_url):
		if file.owner not in allowed_owners:
			refused.add(file.name)
			continue
		new_url = _publish_file(file.name) or new_url

	if refused:
		# Nothing was derived for a refusal on purpose. The refused bytes are still at
		# this URL, and the public path below is guessed from the file name alone, which
		# for an avatar is routinely something like avatar.png. Following it would swap a
		# file we just declined to publish for whatever unrelated image happens to sit at
		# that name. A refused reference is left exactly as it was.
		return _PublishAttempt(new_url, frozenset(refused))

	# Nothing private left to move can mean an earlier run moved the blob and stopped
	# before repointing the document. Derive where it went so that gets finished.
	return _PublishAttempt(new_url or _find_public_file_url(file_url), frozenset())


def _log_refused_files(doctype: str, fieldname: str, refused: set[str]) -> None:
	"""Say out loud that files were skipped, so a broken image later has an answer."""
	message = (
		f"Refused to publish {len(refused)} private file(s) referenced by {doctype}.{fieldname}: "
		f"each is owned by someone who is not allowed to set that field, so publishing it "
		f"would expose an upload that belongs to somebody else. Files: {sorted(refused)}"
	)
	print(message)
	frappe.log_error(title=f"Skipped publishing files for {doctype}.{fieldname}", message=message)


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


def _get_private_files_at(file_url: str):
	return frappe.qb.get_query(
		"File",
		filters={"file_url": file_url, "is_private": 1},
		fields=["name", "owner"],
		order_by="name asc",
	).run(as_dict=True)


def _iter_rows_with_private_files(doctype: str, fieldname: str, row_fields: list[str] | None = None):
	last_name = None
	while rows := _get_rows_with_private_files(doctype, fieldname, row_fields, last_name):
		yield from rows
		last_name = rows[-1].name


def _get_rows_with_private_files(
	doctype: str,
	fieldname: str,
	row_fields: list[str] | None = None,
	after: str | None = None,
):
	filters = [[fieldname, "like", f"{PRIVATE_PREFIX}%"]]
	if after:
		filters.append(["name", ">", after])

	fields = ["name", fieldname]
	fields += [field for field in (row_fields or []) if field not in fields]

	return frappe.qb.get_query(
		doctype,
		filters=filters,
		fields=fields,
		order_by="name asc",
		limit=BATCH_SIZE,
	).run(as_dict=True)
