# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

"""Make existing community images public.

Digest emails group unread discussions by community and render the community
image as `<img src>` with an absolute URL (`email_digest.format_discussion_groups`).
A mail client sends no session cookie, so a private image 403s and the reader sees
a broken image. Community images set after frappe-ui started defaulting uploads to
private are in exactly that state.

Only `GP Team.image` is in scope. `GP Team.cover_image` appears in no email and
stays private.
"""

from gameplan.utils.file_privacy import publish_files_referenced_by


def execute():
	publish_files_referenced_by("GP Team", "image")
