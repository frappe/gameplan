# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

import frappe
from frappe import _
from frappe.utils import cint

from gameplan.public_access import VISIBILITY_GENERAL


class HasVisibility:
	"""Visibility bookkeeping shared by GP Team and GP Project.

	Both carry `visibility`, `visibility_set_by` and `visibility_set_at`, and a legacy
	`is_private` column that nothing reads or writes any more. The controllers call these
	methods from their own lifecycle hooks.
	"""

	def set_default_visibility(self):
		"""Give a new record today's default tier, and refuse the retired `is_private` flag.

		Normally the tier is already set by now. A Select field without a default takes its
		first option (frappe/model/create_new.py), which is why General is listed first:
		reorder the options and new records silently change tier. A data import skips
		those defaults, so this fills the tier in for that path.

		A caller that still sends `is_private = 1` asked for a private record. Ignoring the
		flag would create a General one instead, readable by every signed-in user, so the
		insert fails. `is_private = 0` asks for what the default gives anyway.
		"""
		if cint(self.get("is_private")):
			frappe.throw(_("is_private is no longer accepted. Set visibility instead."))
		if not self.visibility:
			self.visibility = VISIBILITY_GENERAL

	def record_visibility_change(self):
		"""Stamp who changed the tier, and when.

		Runs on every save rather than inside one method, so a change made from Desk or a
		console is recorded as well as one made from the app.
		"""
		if self.has_value_changed("visibility"):
			self.visibility_set_by = frappe.session.user
			self.visibility_set_at = frappe.utils.now()
