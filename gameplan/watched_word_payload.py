import re
from urllib.parse import unquote

import frappe

from gameplan.permissions import get_content_project
from gameplan.watched_word_matching import censor

POST_TYPES = {"GP Discussion", "GP Comment"}
PRIVATE_METHODS = {
	"gameplan.watched_word_edits.original",
	"gameplan.approvals.detail",
	"gameplan.reporting.detail",
	"gameplan.moderation.preview",
}


def community_for_target(doctype, name):
	if doctype not in POST_TYPES or not name or not frappe.db.exists(doctype, name):
		return None
	doc = frappe.get_doc(doctype, name)
	if doctype == "GP Comment" and doc.reference_doctype != "GP Discussion":
		return None
	return frappe.db.get_value("GP Project", get_content_project(doc), "team")


TEXT_FIELDS = {
	"title",
	"content",
	"description",
	"excerpt",
	"snippet",
	"highlighted_title",
	"highlighted_content",
	"last_comment_content",
	"discussion_title",
	"old_title",
	"new_title",
	"old_value",
	"new_value",
}


def text_fields():
	fields = set(TEXT_FIELDS)
	for field in frappe.parse_json(frappe.form_dict.get("fields") or "[]"):
		if isinstance(field, str) and re.search(r"\b(content|title)\b", field, re.I):
			if alias := re.search(r"\s+as\s+([\w]+)$", field, re.I):
				fields.add(alias[1])
	return fields


def clean(payload, community=None):
	if isinstance(payload, list | tuple):
		return [clean(row, community) for row in payload]
	if not isinstance(payload, dict):
		return payload
	row = frappe._dict(payload)
	reference = row.get("_watched_reference_doctype") or row.get("reference_doctype")
	if reference and reference != "GP Discussion":
		return frappe._dict({key: value for key, value in row.items() if not key.startswith("_watched_")})
	if row.get("doctype") in {
		"GP Draft",
		"GP Submission",
		"GP Report",
		"GP Review",
		"GP Moderation Log",
		"GP Watched Word",
		"GP Task",
		"GP Page",
		"GP Project",
		"GP Team",
	}:
		return row
	project = row.get("_watched_project") or row.get("project")
	if project:
		community = frappe.db.get_value("GP Project", project, "team") or community
	community = community or (row.get("team") if row.get("project") else None)
	if (row.get("_watched_reference_doctype") or row.get("reference_doctype")) == "GP Discussion":
		community = (
			community_for_target(
				"GP Discussion", row.get("_watched_reference_name") or row.get("reference_name")
			)
			or community
		)
	community = community_for_target(row.get("doctype"), row.get("name")) or community
	fields = text_fields()
	for key, value in list(row.items()):
		if key.startswith("_watched_"):
			del row[key]
		elif isinstance(value, dict | list | tuple):
			row[key] = clean(value, community)
		elif key == "data" and community and isinstance(value, str):
			try:
				row[key] = frappe.as_json(clean(frappe.parse_json(value), community))
			except (ValueError, TypeError):
				pass
		elif community and isinstance(value, str) and key in fields:
			row[key] = censor(
				community, value, html="<" in value and key not in {"title", "discussion_title"}
			)
	return row


def list_query(query, doctype):
	"""Retain private scope metadata until the HTTP response is censored, including aliased projections."""
	Table = frappe.qb.DocType(doctype)
	if doctype == "GP Discussion":
		return query.select(Table.project.as_("_watched_project"))
	return query.select(
		Table.reference_doctype.as_("_watched_reference_doctype"),
		Table.reference_name.as_("_watched_reference_name"),
	)


def context():
	path = unquote(frappe.local.request.path)
	parts = path.split("/")
	if "document" in parts or "resource" in parts:
		idx = parts.index("document") if "document" in parts else parts.index("resource")
		doctype = parts[idx + 1] if len(parts) > idx + 1 else None
		name = parts[idx + 2] if len(parts) > idx + 2 else None
		return doctype, name
	doctype = frappe.form_dict.get("doctype")
	return doctype if isinstance(doctype, str) else None, frappe.form_dict.get("name")


def guard_source_routes():
	"""Keep framework raw exports and scalar projections from bypassing watched-word serializers."""
	doctype, name = context()
	if doctype not in POST_TYPES:
		return
	path = frappe.local.request.path + " " + str(frappe.form_dict.get("cmd", ""))
	if not name and ("/api/resource/" in path or "frappe.client.get_list" in path):
		fields = frappe.parse_json(frappe.form_dict.get("fields") or '["name"]')
		if isinstance(fields, list):
			extra = (
				["project as _watched_project"]
				if doctype == "GP Discussion"
				else [
					"reference_doctype as _watched_reference_doctype",
					"reference_name as _watched_reference_name",
				]
			)
			frappe.form_dict.fields = frappe.as_json(fields + extra)
	if (
		any(part in path for part in ("export_query", "export_data", "printview", "frappe.client.get_value"))
		or frappe.form_dict.get("group_by")
		or str(frappe.form_dict.get("as_dict", "true")).lower() in {"false", "0"}
	):
		if frappe.db.exists("GP Watched Word", {"action": "Censor"}):
			frappe.throw(
				"Use the discussion view or named document/list API for censored content",
				frappe.PermissionError,
			)


def after_request(response):
	"""Censor ordinary JSON responses without changing stored content or restricted review evidence."""
	if not response.is_json or response.status_code >= 400:
		return
	path = unquote(frappe.local.request.path) + " " + str(frappe.form_dict.get("cmd", ""))
	if any(method in path for method in PRIVATE_METHODS):
		return
	try:
		doctype, name = context()
		if (
			doctype
			in {
				"GP Draft",
				"GP Submission",
				"GP Report",
				"GP Review",
				"GP Moderation Log",
				"GP Watched Word",
				"GP Project",
				"GP Team",
				"GP Task",
				"GP Page",
			}
			or "gameplan.gameplan.doctype.gp_draft.gp_draft." in path
		):
			return
		response.set_data(frappe.as_json(clean(response.get_json(), community_for_target(doctype, name))))
	except Exception:
		response.status_code = 500
		response.set_data(frappe.as_json({"message": "Unable to load moderated content"}))
		frappe.log_error(title="Gameplan watched-word response")
