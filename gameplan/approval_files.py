from contextvars import ContextVar

import frappe
from bs4 import BeautifulSoup

from gameplan.utils import extract_file_references, file_reference_from_url

publishing_submission = ContextVar("publishing_submission", default=None)


def published_content(content):
	soup = BeautifulSoup(content, "html.parser")
	for tag in soup.find_all(["img", "a", "video", "source"]):
		attribute = "src" if tag.has_attr("src") else "href"
		reference = file_reference_from_url(tag.get(attribute))
		if reference and reference.file_name:
			tag[attribute] = reference.file_url
	return str(soup)


def validate_submission_files(doc):
	for reference in extract_file_references(doc.content):
		if not reference.file_url.startswith("/private/files/"):
			frappe.throw("Upload a private attachment before submitting for approval")
		filters = {"name": reference.file_name} if reference.file_name else {"file_url": reference.file_url}
		files = frappe.get_all(
			"File",
			filters=filters,
			fields=["name", "owner", "file_url", "is_private", "attached_to_doctype", "attached_to_name"],
		)
		if not files or any(
			not file.is_private
			or file.file_url != reference.file_url
			or file.owner != frappe.session.user
			or (file.attached_to_doctype and file.attached_to_doctype != "GP Draft")
			for file in files
		):
			frappe.throw("Approval attachments must be private uploads owned by you", frappe.PermissionError)


def protect_submission_file(doc, before=None):
	publication = publishing_submission.get()
	for file in [doc, before] if before else [doc]:
		if file.attached_to_doctype != "GP Submission" or not file.attached_to_name:
			continue
		status = frappe.db.get_value("GP Submission", file.attached_to_name, "status")
		if status == "Approved" or (publication and publication[1] == file.attached_to_name):
			continue
		if before:
			frappe.throw("Unpublished submission attachments cannot be changed", frappe.PermissionError)
	if doc.is_new() and doc.file_url:
		copies = frappe.get_all(
			"File",
			filters={"file_url": doc.file_url, "attached_to_doctype": "GP Submission"},
			pluck="attached_to_name",
		)
		for name in copies:
			if frappe.db.get_value("GP Submission", name, "status") != "Approved" and not (
				publication and publication[1] == name
			):
				frappe.throw("This attachment belongs to an unpublished submission", frappe.PermissionError)
