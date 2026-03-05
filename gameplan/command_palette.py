# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt


import frappe


@frappe.whitelist()
def search_sqlite(query: str):
	"""Search using SQLite FTS for command palette"""
	from gameplan.search_sqlite import GameplanSearch, GameplanSearchIndexMissingError

	search = GameplanSearch()

	try:
		result = search.search(query, title_only=True)
	except GameplanSearchIndexMissingError:
		# Return empty result if search index is not available
		return []

	groups = {}
	for r in result["results"]:
		doctype = r["doctype"]

		if doctype == "GP Discussion":
			groups.setdefault("Discussions", []).append(r)
		elif doctype == "GP Task":
			groups.setdefault("Tasks", []).append(r)
		elif doctype == "GP Page":
			groups.setdefault("Pages", []).append(r)

	out = []
	for key in groups:
		out.append({"title": key, "items": groups[key]})

	return out
