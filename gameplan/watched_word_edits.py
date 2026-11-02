import hashlib

import frappe

from gameplan.approval_files import published_content
from gameplan.approvals import hold
from gameplan.permissions import can_edit_content, can_moderate_space, get_content_project
from gameplan.watched_word_actions import check_block, requires_approval


def target(doctype, name):
	if doctype not in {"GP Discussion", "GP Comment"}:
		frappe.throw("Only discussions and replies support watched-word edits")
	doc = frappe.get_doc(doctype, name, for_update=True)
	doc.check_permission("write")
	from gameplan.mixins.archivable import check_if_space_is_archived
	from gameplan.mixins.moderation import content_is_removed

	if content_is_removed(doc) or doc.get("deleted_at"):
		frappe.throw("Restore this content before editing it", frappe.PermissionError)
	check_if_space_is_archived(doc, action="edit", content_type="posts")
	if not can_edit_content(frappe.session.user, doc):
		frappe.throw("You cannot edit this post", frappe.PermissionError)
	return doc


@frappe.whitelist(methods=["GET", "POST"])
def original(doctype: str, name: str):
	"""Return original post text only to its author/editor or an authorized moderator."""
	doc = target(doctype, name)
	from gameplan.watched_word_actions import community_for
	from gameplan.watched_word_matching import censor

	if doc.owner != frappe.session.user and not can_moderate_space(
		frappe.session.user, get_content_project(doc)
	):
		community = community_for(doc)
		if censor(community, doc.content, html=True) != doc.content or censor(
			community, doc.get("title")
		) != doc.get("title"):
			frappe.throw(
				"Only the author or a moderator can retrieve a censored original", frappe.PermissionError
			)
	return {"title": doc.get("title"), "content": doc.content, "modified": str(doc.modified)}


@frappe.whitelist(methods=["POST"])
def submit(doctype: str, name: str, expected_modified: str, content: str, title: str = "", draft: str = ""):
	"""Save an edit, or hold its proposed version privately while the published post stays visible."""
	frappe.db.get_value("User", frappe.session.user, "name", for_update=True)
	original(doctype, name)
	doc = target(doctype, name)
	if str(doc.modified) != expected_modified:
		frappe.throw("This post changed. Reload before editing.", frappe.TimestampMismatchError)
	if not isinstance(content, str) or not content.strip():
		frappe.throw("Add content before submitting")
	proposed = frappe.get_doc(doc.as_dict())
	proposed.content = content
	if doctype == "GP Discussion":
		if not title.strip():
			frappe.throw("Add a discussion title")
		proposed.title = title
	proposed.sanitize_content()
	from gameplan.community_bans import require_participation

	require_participation(proposed)
	check_block(proposed)
	if requires_approval(proposed):
		key = (
			"edit:"
			+ hashlib.sha256(frappe.as_json([name, expected_modified, title, content]).encode()).hexdigest()
		)
		return hold(proposed, key, draft, edit=doc)
	doc.content = proposed.content
	if doctype == "GP Discussion":
		doc.title = proposed.title
	doc.save()
	return {"doctype": doctype, "name": str(doc.name)}


def edited_document(submission, proposed):
	doc = target(submission.edit_doctype, submission.edit_name)
	if str(doc.modified) != submission.edit_modified:
		frappe.throw(
			"The published post changed. Reject this edit and request a fresh review.",
			frappe.TimestampMismatchError,
		)
	if doc.doctype == "GP Discussion" and doc.project != proposed.project:
		frappe.throw("The discussion moved. Request a fresh review.", frappe.TimestampMismatchError)
	if doc.doctype == "GP Comment" and doc.reference_name != proposed.reference_name:
		frappe.throw("The reply moved. Request a fresh review.", frappe.TimestampMismatchError)
	doc.content = published_content(submission.content)
	if doc.doctype == "GP Discussion":
		doc.title = submission.title
	return doc


def validate_edit_draft(name, doc):
	stored = frappe.get_doc("GP Draft", name, for_update=True)
	stored.require_owner()
	if (
		stored.mode != "Edit"
		or stored.reference_doctype != doc.doctype
		or str(stored.reference_name) != str(doc.name)
	):
		frappe.throw("This draft belongs to another edit")
	return stored
