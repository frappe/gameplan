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

from gameplan.utils.file_privacy import publish_files_referenced_by


def execute():
	# `set_image` writes whatever URL it is handed, so an avatar can name a file the
	# profile's user never uploaded. Publish only a file that user uploaded themselves.
	# `profile.owner` is no help here: it is whoever created the User row, usually an
	# admin. An avatar an admin uploaded on someone else's behalf is refused and stays
	# private, which is the safe half of that trade.
	publish_files_referenced_by(
		"GP User Profile",
		"image",
		allowed_owners=lambda row: {row.user},
		row_fields=["user"],
	)
