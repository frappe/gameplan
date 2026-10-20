# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

from functools import wraps

import frappe
from frappe.utils.typing_validations import validate_argument_types


def with_stored_document(method):
	"""Run a controller action with stored fields and read permission.

	Server code that calls a decorated method must save pending field changes first,
	because the call reloads the document.
	"""

	# frappe.whitelist validates positional arguments against the wrapper's own
	# parameters, so validate them here against the method's signature.
	validated_method = validate_argument_types(method, apply_condition=frappe._in_request_or_test)

	@wraps(method)
	def wrapped(self, *args, **kwargs):
		doctype, name = self.doctype, self.name
		# Rebuild transient state and child rows on the instance used in the response.
		self.__dict__.clear()
		self.__init__(doctype, name)
		self.check_permission("read")
		return validated_method(self, *args, **kwargs)

	wrapped.uses_stored_document = True
	return wrapped
