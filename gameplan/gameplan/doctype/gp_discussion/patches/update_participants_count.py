# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import update_progress_bar


def execute():
	discussions = frappe.get_all("GP Discussion", pluck="name")
	failed = []
	for i, discussion in enumerate(discussions):
		update_progress_bar("Updating participants count", i, len(discussions), absolute=True)
		doc = frappe.get_doc("GP Discussion", discussion)
		try:
			doc.update_participants_count()
			doc.db_set("participants_count", doc.participants_count, update_modified=False)
		except:
			failed.append(discussion)

	if failed:
		print("Failed to update participants count for", failed)
