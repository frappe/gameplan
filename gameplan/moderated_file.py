import frappe
from frappe.core.doctype.file.file import File

from gameplan.mixins.moderation import content_is_removed
from gameplan.permissions import can_moderate_space, get_content_project


def moderation_allows_file(doc, user=None):
	if doc.attached_to_doctype == "GP Submission" and doc.attached_to_name:
		from gameplan.approval_access import can_read_submission

		if not frappe.db.exists("GP Submission", doc.attached_to_name):
			return False
		return can_read_submission(frappe.get_doc("GP Submission", doc.attached_to_name), user)
	if doc.attached_to_doctype not in {"GP Discussion", "GP Comment", "GP Poll"} or not doc.attached_to_name:
		return True
	if not frappe.db.exists(doc.attached_to_doctype, doc.attached_to_name):
		return True
	parent = frappe.get_doc(doc.attached_to_doctype, doc.attached_to_name)
	if not content_is_removed(parent):
		return True
	return can_moderate_space(user or frappe.session.user, get_content_project(parent))


def file_has_permission(doc, ptype=None, user=None, **kwargs):
	if hasattr(doc, "doctype") and not moderation_allows_file(doc, user):
		# A False answer can be overridden by Frappe's explicit File-share fallback.
		frappe.throw("This attachment is unavailable", frappe.PermissionError)
	return True


class ModeratedFile(File):
	# Download and ZIP paths call File methods directly, bypassing document permission hooks.
	def is_downloadable(self):
		return moderation_allows_file(self) and super().is_downloadable()

	def get_content(self, encodings=None):
		file_has_permission(self)
		return super().get_content(encodings=encodings)

	def validate(self):
		before = self.get_doc_before_save()
		file_has_permission(before or self)
		from gameplan.approval_files import protect_submission_file

		protect_submission_file(self, before)
		from gameplan.community_bans import content_is_banned

		for attachment in [self, before] if before else [self]:
			if (
				attachment.attached_to_doctype
				in {"GP Discussion", "GP Comment", "GP Poll", "GP Task", "GP Page"}
				and attachment.attached_to_name
			):
				parent = frappe.get_doc(attachment.attached_to_doctype, attachment.attached_to_name)
				if content_is_banned(parent):
					frappe.throw(
						"You are banned from participating in this community", frappe.PermissionError
					)
		if self.is_new() and self.file_url:
			copies = frappe.get_all(
				"File",
				filters={"file_url": self.file_url},
				fields=["attached_to_doctype", "attached_to_name"],
			)
			if copies and not any(moderation_allows_file(row) for row in copies):
				frappe.throw("This attachment is unavailable", frappe.PermissionError)
		super().validate()

	def on_trash(self):
		if (
			self.attached_to_doctype == "GP Submission"
			and frappe.db.get_value("GP Submission", self.attached_to_name, "status") != "Approved"
		):
			frappe.throw("Unpublished submission attachments cannot be deleted", frappe.PermissionError)
		super().on_trash()
