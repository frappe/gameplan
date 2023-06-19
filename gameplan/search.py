# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe
from gameplan.utils.search import Search
from frappe.utils import strip_html_tags, update_progress_bar, cstr

class GameplanSearch(Search):
	def __init__(self) -> None:
		schema = [
			{'name': 'title', 'weight': 5},
			{'name': 'content', 'weight': 2},
			{'name': 'modified', 'sortable': True},
		]
		super().__init__('gameplan_idx', 'search_doc', schema)

	def build_index(self):
		self.drop_index()
		self.create_index()
		records = self.get_records()
		total = len(records)
		for i, doc in enumerate(records):
			self.index_doc(doc)
			if not hasattr(frappe.local, 'request'):
				update_progress_bar('Indexing', i, total)
		if not hasattr(frappe.local, 'request'):
			print()

	def index_doc(self, doc):
		id, fields, payload = None, None, None
		if doc.doctype == 'GP Discussion':
			id = f'GP Discussion:{doc.name}'
			fields = {
				'title': doc.title,
				'content': strip_html_tags(doc.content),
				'modified': doc.modified,
			}
			payload = {
				'team': doc.team,
				'project': doc.project,
			}
		elif doc.doctype == 'GP Task':
			id = f'GP Task:{doc.name}'
			fields = {
				'title': doc.title,
				'content': strip_html_tags(doc.description),
				'modified': doc.modified,
			}
			payload = {
				'team': doc.team,
				'project': doc.project,
			}
		elif doc.doctype == 'GP Page':
			id = f'GP Page:{doc.name}'
			fields = {
				'title': doc.title,
				'content': strip_html_tags(doc.content),
				'modified': doc.modified,
			}
			payload = {
				'team': doc.team,
				'project': doc.project,
			}
		elif doc.doctype == 'GP Comment':
			id = f'GP Comment:{doc.name}'
			fields = {
				'content': strip_html_tags(doc.content),
				'modified': doc.modified,
			}
			payload = {
				'reference_doctype': doc.reference_doctype,
				'reference_name': doc.reference_name,
			}
		if id and fields and payload:
			self.add_document(id, fields, payload=payload)

	def remove_doc(self, doc):
		id = None
		if doc.doctype == 'GP Discussion':
			id = f'GP Discussion:{doc.name}'
		elif doc.doctype == 'GP Task':
			id = f'GP Task:{doc.name}'
		elif doc.doctype == 'GP Page':
			id = f'GP Page:{doc.name}'
		elif doc.doctype == 'GP Comment':
			id = f'GP Comment:{doc.name}'
		if id:
			self.remove_document(id)

	def get_records(self):
		records = []
		for d in frappe.db.get_all('GP Discussion', fields=['name', 'title', 'content', 'last_post_at', 'modified', 'project', 'team']):
			d.doctype = 'GP Discussion'
			d.modified = d.last_post_at or d.modified
			records.append(d)

		for d in frappe.db.get_all('GP Task', fields=['name', 'title', 'description', 'modified', 'project', 'team']):
			d.doctype = 'GP Task'
			records.append(d)

		for d in frappe.db.get_all('GP Page', fields=['name', 'title', 'content', 'modified', 'project', 'team']):
			d.doctype = 'GP Page'
			records.append(d)

		for d in frappe.db.get_all('GP Comment',
			fields=['name', 'content', 'modified', 'reference_doctype', 'reference_name'],
			filters={'deleted_at': ('is', 'not set')
		}):
			d.doctype = 'GP Comment'
			records.append(d)

		return records


@frappe.whitelist()
def search(query, start=0):
	search = GameplanSearch()
	result = search.search(query, start=start, sort_by="modified desc", highlight=True, with_payloads=True)

	comments_by_doctype = {}
	grouped_results = {}
	for d in result.docs:
		doctype, name = d.id.split(':')
		d.doctype = doctype
		d.name = name
		del d.id
		if doctype == 'GP Comment':
			comments_by_doctype.setdefault(d.payload['reference_doctype'], []).append(d)
		else:
			d.project = d.payload.get('project')
			d.team = d.payload.get('team')
			del d.payload
			grouped_results.setdefault(doctype, []).append(d)

	discussion_names = [d.payload['reference_name'] for d in comments_by_doctype.get('GP Discussion', [])]
	task_names = [d.payload['reference_name'] for d in comments_by_doctype.get('GP Task', [])]

	if discussion_names:
		for d in frappe.get_all('GP Discussion', fields=['name', 'title', 'last_post_at', 'project', 'team'], filters={'name': ('in', discussion_names)}):
			d.doctype = 'GP Discussion'
			d.name = cstr(d.name)
			d.content = ''
			d.via_comment = True
			d.modified = d.last_post_at
			for c in comments_by_doctype.get('GP Discussion', []):
				if c.payload['reference_name'] == d.name:
					d.content = c.content
			grouped_results.setdefault('GP Discussion', []).append(d)

	if task_names:
		for d in frappe.get_all('GP Task', fields=['name', 'title', 'modified', 'project', 'team'], filters={'name': ('in', task_names)}):
			d.doctype = 'GP Task'
			d.name = cstr(d.name)
			d.content = ''
			d.via_comment = True
			for c in comments_by_doctype.get('GP Task', []):
				if c.payload['reference_name'] == d.name:
					d.content = c.content
			grouped_results.setdefault('GP Task', []).append(d)

	return {
		'results': grouped_results,
		'total': result.total,
		'duration': result.duration,
	}

def build_index():
	frappe.cache().set_value('discussions_index_in_progress', True)
	search = GameplanSearch()
	search.build_index()
	frappe.cache().set_value('discussions_index_in_progress', False)


def build_index_in_background():
	if not frappe.cache().get_value('discussions_index_in_progress'):
		frappe.enqueue(build_index, queue='long')


def build_index_if_not_exists():
	search = GameplanSearch()
	if not search.index_exists():
		build_index()
