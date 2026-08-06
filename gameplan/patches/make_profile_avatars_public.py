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
	publish_files_referenced_by("GP User Profile", "image")
