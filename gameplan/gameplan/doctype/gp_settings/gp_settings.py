# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import cint

OFFLINE_WINDOW_CHOICES = (7, 30, 90)


class GPSettings(Document):
	pass


def get_offline_downloads_settings():
	"""What the admin allows, read without a permission check: every user needs it at boot."""
	settings = frappe.get_cached_doc("GP Settings")
	max_window = cint(settings.max_offline_window_days)
	return frappe._dict(
		enabled=bool(cint(settings.enable_offline_downloads)),
		max_window_days=max_window if max_window in OFFLINE_WINDOW_CHOICES else max(OFFLINE_WINDOW_CHOICES),
	)
