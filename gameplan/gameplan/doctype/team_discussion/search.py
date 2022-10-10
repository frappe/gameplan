# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe
from redis.commands.search.field import TextField, NumericField
from redis.commands.search.indexDefinition import IndexDefinition
from redis.commands.search.query import Query
from frappe.utils import strip_html_tags, update_progress_bar
from frappe.utils.redis_wrapper import RedisWrapper
from redis.exceptions import ResponseError

INDEX_NAME = "discussions_index"
PREFIX = "discussions_search_doc"


@frappe.whitelist()
def search(query, start=0):
	r = frappe.cache()
	query = Query(query).paging(start, 30).highlight(tags=["<mark>", "</mark>"]).sort_by("modified", asc=False)

	try:
		result = r.ft(INDEX_NAME).search(query)
	except ResponseError:
		return {
			"total": 0,
			"docs": [],
			"duration": 0
		}

	names = []
	for d in result.docs:
		_, name, comment = d.id.split(':')
		names.append(frappe.utils.cint(name))
	names = list(set(names))

	data_by_name = {
		d.name: d
		for d in frappe.db.get_all('Team Discussion',
			fields=['name', 'title', 'team', 'project', 'owner', 'modified', 'creation', 'last_post_at', 'last_post_by', 'comments_count', 'closed_at', 'closed_by'],
			filters={'name': ['in', names]}
		)
	}

	docs = []
	seen = []
	for d in result.docs:
		_, name, comment = d.id.split(':')
		name = frappe.utils.cint(name)
		if name in seen:
			continue
		doc = data_by_name[name]
		if d.title:
			doc.title = d.title
		doc.comment = d.comment
		doc.content = d.content
		docs.append(doc)
		seen.append(name)

	return {
		"docs": docs,
		"total": result.total,
		"duration": result.duration
	}


def rebuild_index():
	drop_index()
	r = frappe.cache()
	# Options for index creation
	index_def = IndexDefinition(
		prefix = [f"{r.make_key(PREFIX).decode()}:"],
		score = 0.5,
		score_field = "doc_score"
	)
	schema = (
		TextField("title", weight=3.0),
		TextField("content"),
		TextField("modified"),
		TextField("comment")
	)
	# Create an index and pass in the schema
	r.ft(INDEX_NAME).create_index(schema, definition=index_def)

	records_to_index = get_records_to_index()
	create_index_for_records(records_to_index)

def rebuild_index_in_background():
	frappe.enqueue(rebuild_index, queue='long')

def create_index_for_records(records):
	r = frappe.cache()
	for i, d in enumerate(records):
		if not hasattr(frappe.local, 'request'):
			update_progress_bar('Indexing discussions', i, len(records), absolute=True)

		key = r.make_key(f"{PREFIX}:{d.name}:{d.comment}").decode()
		mapping = {
			"title": d.title,
			"content": strip_html_tags(d.content),
			"modified": frappe.utils.cstr(d.modified),
			"comment": d.comment,
		}
		super(RedisWrapper, r).hset(key, mapping=mapping)

	if not hasattr(frappe.local, 'request'):
		print()


def remove_index_for_records(records):
	r = frappe.cache()
	for d in records:
		key = r.make_key(f"{PREFIX}:{d.name}:{d.comment}").decode()
		r.ft(INDEX_NAME).delete_document(key)


def update_index(doc):
	if doc.doctype == 'Team Discussion':
		record = frappe._dict({
			'name': doc.name,
			'title': doc.title,
			'content': doc.content,
			'modified': doc.modified,
			'comment': ''
		})
	elif doc.doctype == 'Team Comment':
		record = frappe._dict({
			'name': doc.reference_name,
			'title': '',
			'content': doc.content,
			'modified': doc.modified,
			'comment': doc.name
		})

	create_index_for_records([record])


def remove_index(doc):
	if doc.doctype == 'Team Discussion':
		record = frappe._dict({
			'name': doc.name,
			'comment': ''
		})
	elif doc.doctype == 'Team Comment':
		record = frappe._dict({
			'name': doc.reference_name,
			'comment': doc.name
		})
	remove_index_for_records([record])


def drop_index():
	try:
		r = frappe.cache()
		r.ft(INDEX_NAME).dropindex(delete_documents=True)
	except ResponseError:
		pass


def get_records_to_index():
	records = []
	result = frappe.db.get_all('Team Discussion', fields=['name', 'title', 'content', 'modified'])
	for d in result:
		d.comment = ''
		records.append(d)

	result = frappe.db.get_all('Team Comment',
		fields=['name', 'content', 'reference_name', 'modified'],
		filters={'reference_doctype': 'Team Discussion', 'deleted_at': ('is', 'not set')}
	)
	for d in result:
		d.title = ''
		d.comment = d.name
		d.name = d.reference_name
		records.append(d)

	return records

