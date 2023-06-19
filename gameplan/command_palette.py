# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe
from gameplan.search import Search

@frappe.whitelist()
def search(query):
	query = query.strip()
	query_parts = query.split(' ')
	if len(query_parts) == 1:
		query = f'{query_parts[0]}*'

	search = get_search()
	result = search.search(query, start=0, sort_by="modified desc")

	groups = {}
	for r in result.docs:
		doctype, name = r.id.split(':')
		r.doctype = doctype
		r.name = name

		if doctype == 'GP Discussion':
			groups.setdefault('Discussions', []).append(r)
		elif doctype == 'GP Task':
			groups.setdefault('Tasks', []).append(r)
		elif doctype == 'GP Page':
			groups.setdefault('Pages', []).append(r)

	out = []
	for key in groups:
		out.append({
			'title': key,
			'items': groups[key]
		})
	return out

def build_index():
	search = get_search()
	search.drop_index()
	search.create_index()
	discussions = frappe.db.get_all('GP Discussion', fields=['name', 'title', 'team', 'project', 'last_post_at', 'modified'])
	for d in discussions:
		d.modified = d.last_post_at or d.modified
		search.add_document(f'GP Discussion:{d.name}', d)

	tasks = frappe.db.get_all('GP Task', fields=['name', 'title', 'team', 'project', 'modified'])
	for t in tasks:
		search.add_document(f'GP Task:{t.name}', t)

	pages = frappe.db.get_all('GP Page', fields=['name', 'title', 'team', 'project', 'modified'])
	for p in pages:
		search.add_document(f'GP Page:{p.name}', p)

def get_search():
	schema = [
		{'name': 'title'},
		{'name': 'modified', 'sortable': True},
		{'name': 'team', 'no_index': True, 'sortable': True},
		{'name': 'project', 'no_index': True, 'sortable': True}
	]
	return Search('command_palette', 'command_palette', schema)
