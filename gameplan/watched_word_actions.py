import frappe

from gameplan.approval_files import publishing_submission
from gameplan.approval_policy import supports_approval
from gameplan.community_bans import can_moderate_community
from gameplan.permissions import get_content_project
from gameplan.watched_word_matching import matches


def community_for(doc):
	return frappe.db.get_value("GP Project", get_content_project(doc), "team")


def applicable(doc):
	if not supports_approval(doc):
		return None
	community = community_for(doc)
	return community if community and not can_moderate_community(community) else None


def check_block(doc):
	community = applicable(doc)
	if community:
		words = matches(community, "Block", doc.get("title"), doc.content)
		if words:
			frappe.throw("Remove the blocked words or phrases: " + ", ".join(words), title="Blocked content")


def requires_approval(doc):
	community = applicable(doc)
	return bool(community and matches(community, "Require approval", doc.get("title"), doc.content))


def validate(doc, method=None):
	if not supports_approval(doc):
		return
	if not doc.is_new() and not any(
		doc.has_value_changed(f) for f in ("content", "title", "project") if doc.meta.has_field(f)
	):
		return
	check_block(doc)
	publication = publishing_submission.get()
	if requires_approval(doc) and not (publication and publication[0] is doc):
		frappe.throw("Submit this content or edit through the approval queue", frappe.PermissionError)


def flag(doc, method=None):
	if not supports_approval(doc) or (publishing_submission.get() and publishing_submission.get()[0] is doc):
		return
	if not any(doc.has_value_changed(f) for f in ("content", "title", "project") if doc.meta.has_field(f)):
		return
	community = applicable(doc)
	words = matches(community, "Flag", doc.get("title"), doc.content) if community else []
	if not words:
		return
	# Target locking shares the report decision lock, so a concurrent resolution cannot lose a flag.
	frappe.db.get_value(doc.doctype, doc.name, "name", for_update=True)
	review = frappe.db.get_value(
		"GP Review",
		{
			"reference_doctype": doc.doctype,
			"reference_name": doc.name,
			"status": "Pending",
		},
	)
	if not review:
		review = (
			frappe.get_doc(
				doctype="GP Review", reference_doctype=doc.doctype, reference_name=doc.name, status="Pending"
			)
			.insert(ignore_permissions=True)
			.name
		)
	if not frappe.db.exists("GP Report", {"review": review, "owner": "Administrator"}):
		frappe.get_doc(
			doctype="GP Report",
			review=review,
			reason="Other",
			owner="Administrator",
			automatic_rule=1,
			note=("Automatic watched-word flag: " + ", ".join(words))[:500],
			reported_title=doc.get("title"),
			reported_content=doc.content,
		).insert(ignore_permissions=True)
