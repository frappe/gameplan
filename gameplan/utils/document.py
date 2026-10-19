# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

from functools import wraps

import frappe


def with_stored_document(method):
	"""Run a controller action with stored fields and read permission."""

	@wraps(method)
	def wrapped(self, *args, **kwargs):
		stored = frappe.get_doc(self.doctype, self.name)
		stored.check_permission("read")
		# Keep the instance used in the method response, including its child rows.
		self.__dict__.clear()
		self.__dict__.update(stored.__dict__)
		return method(self, *args, **kwargs)

	return wrapped
