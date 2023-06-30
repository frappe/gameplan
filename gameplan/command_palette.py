# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe
from gameplan.search import GameplanSearch


@frappe.whitelist()
def search(query):
	search = GameplanSearch()
	query = search.clean_query(query)

	query_parts = query.split(" ")
	if len(query_parts) == 1 and not query_parts[0].endswith("*"):
		query = f"{query_parts[0]}*"
	if len(query_parts) > 1:
		query = " ".join([f"%%{q}%%" for q in query_parts])

	query = f"@title:({query})"
	result = search.search(query, start=0, sort_by="modified desc", with_payloads=True)

	groups = {}
	for r in result.docs:
		doctype, name = r.id.split(":")
		r.doctype = doctype
		r.name = name

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
