# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe
import json
from redis.commands.search.field import TextField
from redis.commands.search.indexDefinition import IndexDefinition
from redis.commands.search.query import Query
from redis.exceptions import ResponseError
from frappe.utils import cstr


class Search:
	def __init__(self, index_name, prefix, schema) -> None:
		self.redis = frappe.cache()
		self.index_name = index_name
		self.prefix = prefix
		self.schema = []
		for field in schema:
			self.schema.append(frappe._dict(field))

	def create_index(self):
		index_def = IndexDefinition(
			prefix = [f"{self.redis.make_key(self.prefix).decode()}:"],
		)
		schema = []
		for field in self.schema:
			kwargs = {k: v for k, v in field.items() if k in ["weight", "sortable", "no_index", "no_stem"]}
			schema.append(TextField(field.name, **kwargs))

		self.redis.ft(self.index_name).create_index(schema, definition=index_def)

	def add_document(self, id, doc, payload=None):
		doc = frappe._dict(doc)
		doc_id = self.redis.make_key(f"{self.prefix}:{id}").decode()
		mapping = {}
		for field in self.schema:
			if field.name in doc:
				mapping[field.name] = cstr(doc[field.name])
		self.redis.ft(self.index_name).add_document(doc_id, payload=json.dumps(payload), replace=True, **mapping)

	def remove_document(self, id):
		key = self.redis.make_key(f"{self.prefix}:{id}").decode()
		self.redis.ft(self.index_name).delete_document(key)

	def search(self, query, start=0, page_length=50, sort_by=None, highlight=False, with_payloads=False):
		query = Query(query).paging(start, page_length)
		if highlight:
			query = query.highlight(tags=["<mark>", "</mark>"])
		if sort_by:
			parts = sort_by.split(" ")
			sort_field = parts[0]
			direction = parts[1] if len(parts) > 1 else "asc"
			query = query.sort_by(sort_field, asc=direction=="asc")
		if with_payloads:
			query = query.with_payloads()

		try:
			result = self.redis.ft(self.index_name).search(query)
		except ResponseError as e:
			print(e)
			return frappe._dict({
				"total": 0,
				"docs": [],
				"duration": 0
			})

		out = frappe._dict(docs=[], total=result.total, duration=result.duration)
		for doc in result.docs:
			id = doc.id.split(":", 1)[1]
			_doc = frappe._dict(doc.__dict__)
			_doc.id = id
			_doc.payload = json.loads(doc.payload) if doc.payload else None
			out.docs.append(_doc)
		return out

	def drop_index(self):
		try:
			self.redis.ft(self.index_name).dropindex(delete_documents=True)
		except ResponseError:
			pass

	def index_exists(self):
		try:
			self.redis.ft(self.index_name).info()
			return True
		except ResponseError:
			return False
