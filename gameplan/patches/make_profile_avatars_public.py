# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

"""Make existing profile avatars public.

Digest emails render an avatar as `<img src>` with an absolute URL, and a mail
client sends no session cookie, so a private avatar 403s and the reader sees a
broken image. Avatars uploaded after frappe-ui started defaulting uploads to
private are in exactly that state.

Only `GP User Profile.image` is in scope. Cover images, bento card images and
editor attachments have no no-session reader, and stay private.
"""

import frappe

BATCH_SIZE = 500
PRIVATE_PREFIX = "/private/files/"
PUBLIC_PREFIX = "/files/"


def execute():
	# A URL is shared when two profiles point at the same upload, so remember where
	# each one moved to instead of looking it up again after it has already gone.
	moved = {}

	for profile in iter_profiles_with_private_avatars():
		old_url = profile.image
		if old_url not in moved:
			moved[old_url] = publish_files_at(old_url)

		new_url = moved[old_url]
		if new_url and new_url != old_url:
			# Frappe rewrites the referencing field itself, but only for a File that is
			# attached and whose attached_to_field resolves. An avatar uploaded before
			# the profile started attaching its images is neither, and a moved blob with
			# a stale URL behind it is worse than leaving it private. Writing the value
			# a second time is harmless.
			frappe.db.set_value("GP User Profile", profile.name, "image", new_url, update_modified=False)


def publish_files_at(file_url):
	"""Make every private File at `file_url` public and return the URL it moved to.

	Returns None when nothing could be moved, which leaves the profile pointing at
	the URL its bytes are still served from.
	"""
	new_url = None
	for name in get_private_files_at(file_url):
		new_url = publish_file(name) or new_url

	# A previous run may have moved the blob and stopped before repointing the
	# profile, which leaves no private File to find. Recover from that.
	return new_url or find_public_file_url(file_url)


def publish_file(name):
	try:
		file = frappe.get_doc("File", name)
	except frappe.DoesNotExistError:
		frappe.clear_last_message()
		return None

	if not file.is_private:
		return file.file_url

	file.is_private = 0
	try:
		# Saving is the point: File.handle_is_private_changed moves the blob from
		# private to public storage, rewrites file_url to match, and registers an
		# after_rollback hook that moves it back if this patch's transaction fails.
		# Writing is_private straight to the database would strand the bytes.
		file.save(ignore_permissions=True)
	except (FileNotFoundError, FileExistsError):
		# The blob is gone, or a public file already holds that name. Either way the
		# row is untouched, so it keeps pointing at bytes that are actually there.
		frappe.clear_last_message()
		return None

	return file.file_url


def find_public_file_url(private_url):
	public_url = PUBLIC_PREFIX + private_url[len(PRIVATE_PREFIX) :]
	if frappe.db.exists("File", {"file_url": public_url, "is_private": 0}):
		return public_url
	return None


def get_private_files_at(file_url):
	return frappe.qb.get_query(
		"File",
		filters={"file_url": file_url, "is_private": 1},
		fields=["name"],
		order_by="name asc",
	).run(pluck="name")


def iter_profiles_with_private_avatars():
	last_name = None
	while profiles := get_profiles_with_private_avatars(last_name):
		yield from profiles
		last_name = profiles[-1].name


def get_profiles_with_private_avatars(after=None):
	filters = [["image", "like", f"{PRIVATE_PREFIX}%"]]
	if after:
		filters.append(["name", ">", after])

	return frappe.qb.get_query(
		"GP User Profile",
		filters=filters,
		fields=["name", "image"],
		order_by="name asc",
		limit=BATCH_SIZE,
	).run(as_dict=True)
