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

import frappe

from gameplan.utils.file_privacy import publish_files_referenced_by


def execute():
	# A File is found by URL alone, so a community image can name a file nobody here
	# uploaded. Publish only files uploaded by someone who may set the field:
	# `team_has_permission` gives write to community admins, and the creator is added
	# as an admin on insert, so that is the admins plus the row's own owner. A file a
	# global admin uploaded from outside the community is refused and stays private.
	publish_files_referenced_by(
		"GP Team",
		"image",
		allowed_owners=lambda row: {row.owner} | _community_admins(row.name),
		row_fields=["owner"],
	)


def _community_admins(team: str) -> set[str]:
	Member = frappe.qb.DocType("GP Member")
	rows = (
		frappe.qb.from_(Member)
		.select(Member.user)
		.where(Member.parenttype == "GP Team")
		.where(Member.parent == team)
		.where(Member.is_admin == 1)
		.run()
	)
	return {row[0] for row in rows}
