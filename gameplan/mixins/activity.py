# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe
import json


class HasActivity:
	'''
	Mixin to add utility methods to log activity under "GP Activity" doctype.
	'''
	def log_activity(self, action, user=None, data=None):
		activities = getattr(self, 'activities', [])
		if not activities:
			raise Exception('No activities defined for this document')

		if action not in activities:
			raise Exception('Invalid action to log activity for this document')

		if not user:
			user = frappe.session.user

		if data and isinstance(data, dict):
			data = frappe.as_json(data, indent=None)

		activity = frappe.get_doc(
			doctype='GP Activity',
			reference_doctype=self.doctype,
			reference_name=self.name,
			action=action,
			user=user,
			data=data
		).insert(ignore_permissions=True)

		frappe.publish_realtime('new_activity', {
			'reference_doctype': self.doctype,
			'reference_name': self.name
		}, after_commit=True)

		return activity
