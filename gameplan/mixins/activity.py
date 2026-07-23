# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt


import frappe


class HasActivity:
	"""
	Mixin to add utility methods to log activity under "GP Activity" doctype.
	"""

	def log_activity(self, action, user=None, data=None):
		activities = getattr(self, "activities", [])
		if not activities:
			raise Exception("No activities defined for this document")

		if action not in activities:
			raise Exception("Invalid action to log activity for this document")

		if not user:
			user = frappe.session.user

		if data and isinstance(data, dict):
			data = frappe.as_json(data, indent=None)

		activity = frappe.get_doc(
			doctype="GP Activity",
			reference_doctype=self.doctype,
			reference_name=self.name,
			action=action,
			user=user,
			data=data,
		).insert(ignore_permissions=True)

		# Publish into the document's own room. Without doctype/docname this falls back to the
		# site room, which only Desk (System User) sockets join - so Gameplan members, who are
		# Website Users, never saw the timeline update live. Subscribers are permission-checked
		# by the realtime server, so joining the room already implies read access.
		frappe.publish_realtime(
			"new_activity",
			{"reference_doctype": self.doctype, "reference_name": str(self.name)},
			doctype=self.doctype,
			docname=self.name,
			after_commit=True,
		)

		return activity
