# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

"""Attach bento card images that were uploaded before the profile started attaching them.

`GP Profile Bento Card` is a child table, and Frappe's `attach_files_to_document` only
walks Attach fields declared on the parent doctype, so a card image was never attached
to anything. An unattached private File falls through `File.has_permission` to deny, so
those cards render for their owner and 403 for everyone else.
"""

import frappe

BATCH_SIZE = 500


def execute():
	for name in iter_profiles_with_bento_images():
		try:
			profile = frappe.get_doc("GP User Profile", name)
		except frappe.DoesNotExistError:
			frappe.clear_last_message()
			continue

		# No session user to trust in a patch, so only files uploaded by the profile's
		# own user are attached. Mirrors backfill_private_file_attachments.
		profile.attach_bento_card_images(allow_session_owner=False)


def iter_profiles_with_bento_images():
	last_name = None
	while names := get_profiles_with_bento_images(last_name):
		yield from names
		last_name = names[-1]


def get_profiles_with_bento_images(last_name=None):
	filters = {"parenttype": "GP User Profile", "image": ("is", "set")}
	if last_name:
		filters["parent"] = (">", last_name)

	rows = frappe.qb.get_query(
		"GP Profile Bento Card",
		filters=filters,
		fields=["parent"],
		order_by="parent asc",
		group_by="parent",
		limit=BATCH_SIZE,
	).run(pluck="parent")

	# `group_by` keeps the batch cursor moving one profile at a time even when a
	# profile has several image cards, so a profile is never processed twice.
	return rows
