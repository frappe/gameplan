"""Shared limits for the offset-paged moderation lists."""

import frappe
from frappe.utils import cint

# A list read far beyond this is slow, and nobody reads that many pages. 125 pages of 40 rows.
MAX_START = 5_000


def page_start(start):
	"""The row to start a page from, refusing an offset the database would have to read past."""
	start = max(0, cint(start))
	if start > MAX_START:
		frappe.throw("That is too far back to list. Resolve some items or narrow the list to see more.")
	return start
