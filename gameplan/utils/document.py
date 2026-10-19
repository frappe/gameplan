# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

from functools import wraps


def with_stored_document(method):
	"""Run a controller action with stored fields and read permission.

	Server code that calls a decorated method must save pending field changes first,
	because the call reloads the document.
	"""

	@wraps(method)
	def wrapped(self, *args, **kwargs):
		doctype, name = self.doctype, self.name
		# Rebuild transient state and child rows on the instance used in the response.
		self.__dict__.clear()
		self.__init__(doctype, name)
		self.check_permission("read")
		return method(self, *args, **kwargs)

	return wrapped
