# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt


import re

import frappe
from frappe.core.utils import html2text
from frappe.utils import cstr, update_progress_bar

import gameplan
from gameplan.utils.search import Search

UNSAFE_CHARS = re.compile(r"[\[\]{}<>+]")

INDEX_BUILD_FLAG = "discussions_index_in_progress"


class GameplanSearch(Search):
	def __init__(self) -> None:
		schema = [
			{"name": "title", "weight": 5},
			{"name": "content", "weight": 2},
			{"name": "team", "type": "tag"},
			{"name": "project", "type": "tag"},
			{"name": "modified", "sortable": True},
		]
		super().__init__("gameplan_idx", "search_doc", schema)

	def search(self, query, **kwargs):
		if query:
			accessible_projects = "|".join(self.get_accessible_projects())
			projects_query = f"@project:{{{accessible_projects}}}"
			query = f"{query} {projects_query}"
		return super().search(query, **kwargs)

	def clean_query(self, query):
		query = query.strip().replace("-*", "*")
		query = UNSAFE_CHARS.sub(" ", query)
		query = query.strip()
		return query

	def build_index(self):
		self.drop_index()
		self.create_index()
		records = self.get_records()
		total = len(records)
		for i, doc in enumerate(records):
			self.index_doc(doc)
			if not hasattr(frappe.local, "request"):
				update_progress_bar("Indexing", i, total)
		if not hasattr(frappe.local, "request"):
			print()

	def index_doc(self, doc):
		id, fields, payload = None, None, None
		if doc.doctype == "GP Discussion":
			id = f"GP Discussion:{doc.name}"
			fields = {
				"title": doc.title,
				"content": html2text(doc.content),
				"modified": doc.modified,
				"team": doc.team,
				"project": doc.project,
			}
			payload = {
				"team": doc.team,
				"project": doc.project,
			}
		elif doc.doctype == "GP Task":
			id = f"GP Task:{doc.name}"
			fields = {
				"title": doc.title,
				"content": html2text(doc.description),
				"modified": doc.modified,
				"team": doc.team,
				"project": doc.project,
			}
			payload = {
				"team": doc.team,
				"project": doc.project,
			}
		elif doc.doctype == "GP Page":
			id = f"GP Page:{doc.name}"
			fields = {
				"title": doc.title,
				"content": html2text(doc.content),
				"modified": doc.modified,
				"team": doc.team,
				"project": doc.project,
			}
			payload = {
				"team": doc.team,
				"project": doc.project,
			}
		elif doc.doctype == "GP Comment":
			id = f"GP Comment:{doc.name}"
			team = frappe.db.get_value(doc.reference_doctype, doc.reference_name, "team", cache=True)
			project = frappe.db.get_value(doc.reference_doctype, doc.reference_name, "project", cache=True)

			fields = {
				"content": html2text(doc.content),
				"modified": doc.modified,
				"team": team,
				"project": project,
			}
			payload = {
				"reference_doctype": doc.reference_doctype,
				"reference_name": doc.reference_name,
			}
		if id and fields and payload:
			self.add_document(id, fields, payload=payload)

	def remove_doc(self, doc):
		id = None
		if doc.doctype == "GP Discussion":
			id = f"GP Discussion:{doc.name}"
		elif doc.doctype == "GP Task":
			id = f"GP Task:{doc.name}"
		elif doc.doctype == "GP Page":
			id = f"GP Page:{doc.name}"
		elif doc.doctype == "GP Comment":
			id = f"GP Comment:{doc.name}"
		if id:
			self.remove_document(id)

	def get_records(self):
		records = []
		for d in frappe.db.get_all(
			"GP Discussion",
			fields=["name", "title", "content", "last_post_at", "modified", "project", "team"],
		):
			d.doctype = "GP Discussion"
			d.modified = d.last_post_at or d.modified
			records.append(d)

		for d in frappe.db.get_all(
			"GP Task", fields=["name", "title", "description", "modified", "project", "team"]
		):
			d.doctype = "GP Task"
			records.append(d)

		for d in frappe.db.get_all(
			"GP Page", fields=["name", "title", "content", "modified", "project", "team"]
		):
			d.doctype = "GP Page"
			records.append(d)

		for d in frappe.db.get_all(
			"GP Comment",
			fields=["name", "content", "modified", "reference_doctype", "reference_name"],
			filters={"deleted_at": ("is", "not set")},
		):
			d.doctype = "GP Comment"
			records.append(d)

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
	frappe.cache().set_value(INDEX_BUILD_FLAG, True)
	search = GameplanSearch()
	search.build_index()
	frappe.cache().set_value(INDEX_BUILD_FLAG, False)


def build_index_in_background():
	if not frappe.cache().get_value("discussions_index_in_progress"):
		frappe.enqueue(build_index, queue="long")


def build_index_if_not_exists():
	search = GameplanSearch()
	if not search.index_exists() or not frappe.cache.exists(INDEX_BUILD_FLAG):
		build_index()
