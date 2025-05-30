# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt


import datetime

import frappe
from frappe.utils import cint, cstr

import gameplan
from gameplan.utils.fts import FullTextSearch

INDEX_BUILD_FLAG = "discussions_index_in_progress"


class GameplanSearchIndexMissingError(Exception):
	pass


class GameplanSearch:
	def __init__(self) -> None:
		self.fts = FullTextSearch()
		self.doc_configs = {
			"GP Discussion": {
				"fields": [
					"name",
					"title",
					"content",
					"last_post_at",
					"modified",
					"project",
					"team",
					"owner",
				],
				"content_field": "content",
				"title_field": "title",
				"modified_field": "last_post_at",
			},
			"GP Task": {
				"fields": ["name", "title", "description", "modified", "project", "team", "owner"],
				"content_field": "description",
				"title_field": "title",
				"modified_field": "modified",
			},
			"GP Page": {
				"fields": ["name", "title", "content", "modified", "project", "team", "owner"],
				"content_field": "content",
				"title_field": "title",
				"modified_field": "modified",
			},
			"GP Comment": {
				"fields": ["name", "content", "modified", "reference_doctype", "reference_name", "owner"],
				"content_field": "content",
				"title_field": None,
				"modified_field": "modified",
				"filters": {"deleted_at": ("is", "not set")},
			},
		}

	def is_search_enabled(self):
		"""Check if search functionality is disabled via site config"""
		disabled = frappe.conf.get("disable_gameplan_search", False)
		return not disabled

	def raise_if_not_indexed(self):
		if not self.index_exists():
			raise GameplanSearchIndexMissingError(
				"Search index does not exist. Please build the index first."
			)

	def search(self, query, title_only=False):
		if not self.is_search_enabled():
			return {"results": [], "summary": {"total_matches": 0, "filtered_matches": 0}}

		self.raise_if_not_indexed()

		if not query:
			return []

		search_response = self.fts.search(query, title_only=title_only)
		results = search_response["results"]
		summary = search_response["summary"]

		comment_refs = {}
		doc_owners = {}
		comment_names = [r["id"].split(":", 1)[1] for r in results if r["id"].startswith("GP Comment:")]
		if comment_names:
			refs = frappe.get_all(
				"GP Comment",
				filters={"name": ["in", comment_names]},
				fields=["name", "reference_doctype", "reference_name", "owner"],
			)
			comment_refs = {r.name: r for r in refs}

		# Get owners for other doctypes
		for doctype in ["GP Discussion", "GP Task", "GP Page"]:
			doc_names = [r["id"].split(":", 1)[1] for r in results if r["id"].startswith(f"{doctype}:")]
			if doc_names:
				owners = frappe.get_all(
					doctype, filters={"name": ["in", doc_names]}, fields=["name", "owner"]
				)
				doc_owners.update({f"{doctype}:{o.name}": o.owner for o in owners})

		# Filter results based on project access
		accessible_projects = self.get_accessible_projects()
		filtered_results = []

		for result in results:
			doctype, name = result["id"].split(":", 1)

			if doctype == "GP Comment":
				ref = comment_refs.get(cint(name), {})
				ref_doctype = ref.get("reference_doctype")
				ref_name = ref.get("reference_name")
				project = frappe.db.get_value(ref_doctype, ref_name, "project") if ref_doctype else None
				author = ref.get("owner")
			else:
				project = frappe.db.get_value(doctype, name, "project")
				author = doc_owners.get(result["id"], "")

			if project in accessible_projects:
				filtered_results.append(
					{
						"id": result["id"],
						"title": result.get("title"),
						"content": result.get("content", ""),
						"timestamp": result["timestamp"],
						"score": result["score"],
						"doctype": doctype,
						"name": name,
						"project": project,
						"reference_doctype": ref_doctype if doctype == "GP Comment" else None,
						"reference_name": ref_name if doctype == "GP Comment" else None,
						"author": author,
					}
				)

		return {
			"results": filtered_results,
			"summary": {
				**summary,
				"filtered_matches": len(filtered_results),
			},
		}

	def build_index(self):
		if not self.is_search_enabled():
			return

		records = self.get_records()
		documents = []

		for doc in records:
			document = self._prepare_document(doc)
			if document:
				documents.append(document)

		self.fts.index_documents(documents)

	def index_doc(self, doc):
		"""Index a single document in background"""
		if not self.is_search_enabled():
			return
		frappe.enqueue("gameplan.search2.index_document", doctype=doc.doctype, docname=doc.name)

	def _index_doc(self, doctype, docname):
		doc = frappe.get_doc(doctype, docname)
		self.raise_if_not_indexed()
		document = self._prepare_document(doc)
		if document:
			self.fts.index_document(document)

	def remove_doc(self, doc):
		"""Remove a single document from the index"""
		if not self.is_search_enabled():
			return
		frappe.enqueue("gameplan.search2.remove_document", doctype=doc.doctype, docname=doc.name)

	def _remove_doc(self, doctype, docname):
		"""Remove a single document from the index"""
		self.raise_if_not_indexed()
		doc_id = f"{doctype}:{docname}"
		self.fts.remove_document(doc_id)

	def index_exists(self):
		return self.fts.index_exists()

	def _prepare_document(self, doc):
		config = self.doc_configs.get(doc.doctype)
		if not config:
			return None

		content_field = config["content_field"]
		title_field = config["title_field"]

		if not isinstance(doc.modified, datetime.datetime):
			doc.modified = frappe.utils.get_datetime(doc.modified)

		return {
			"id": f"{doc.doctype}:{doc.name}",
			"title": getattr(doc, title_field, "") if title_field else "",
			"content": getattr(doc, content_field, "") or "",
			"timestamp": doc.modified.timestamp(),
		}

	def get_records(self):
		records = []
		for doctype, config in self.doc_configs.items():
			docs = frappe.db.get_all(doctype, fields=config["fields"], filters=config.get("filters", {}))

			for doc in docs:
				doc.doctype = doctype
				if config["modified_field"] != "modified":
					doc.modified = getattr(doc, config["modified_field"], None) or doc.modified
				records.append(doc)

		return records

	def get_accessible_projects(self):
		from pypika.terms import ExistsCriterion

		if gameplan.is_guest():
			GuestAccess = frappe.qb.DocType("GP Guest Access")
			return (
				frappe.qb.from_(GuestAccess)
				.select(GuestAccess.project)
				.distinct()
				.where(GuestAccess.user == frappe.session.user)
				.run(pluck=True)
			)

		Project = frappe.qb.DocType("GP Project")
		Member = frappe.qb.DocType("GP Member")
		member_exists = (
			frappe.qb.from_(Member)
			.select(Member.name)
			.where(Member.parenttype == "GP Team")
			.where(Member.parent == Project.team)
			.where(Member.user == frappe.session.user)
		)
		projects = (
			frappe.qb.from_(Project)
			.select(Project.name)
			.distinct()
			.where((Project.is_private == 0) | ((Project.is_private == 1) & ExistsCriterion(member_exists)))
			.run(pluck=True)
		)
		return [cstr(p) for p in projects]


def build_index():
	search = GameplanSearch()
	if not search.is_search_enabled():
		return
	frappe.cache().set_value(INDEX_BUILD_FLAG, True)
	search.build_index()
	frappe.cache().set_value(INDEX_BUILD_FLAG, False)


def build_index_in_background():
	search = GameplanSearch()
	if not search.is_search_enabled():
		return
	if not frappe.cache().get_value("discussions_index_in_progress"):
		frappe.enqueue(build_index, queue="long")


def build_index_if_not_exists():
	search = GameplanSearch()
	if not search.is_search_enabled():
		return
	if not search.index_exists() or not frappe.cache.exists(INDEX_BUILD_FLAG):
		build_index()


def index_document(doctype, docname):
	search = GameplanSearch()
	if not search.is_search_enabled():
		return
	search._index_doc(doctype, docname)


def remove_document(doctype, docname):
	search = GameplanSearch()
	if not search.is_search_enabled():
		return
	search._remove_doc(doctype, docname)
