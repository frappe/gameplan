# Copyright (c) 2022, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import json
import re

import frappe
from bs4 import BeautifulSoup
from frappe import _
from frappe.model.document import Document
from frappe.utils import cstr

from gameplan.gameplan.doctype.gp_unread_record.gp_unread_record import GPUnreadRecord
from gameplan.mixins.archivable import check_if_space_is_archived
from gameplan.mixins.attachments import HasAttachments
from gameplan.mixins.backlinks import HasBacklinks
from gameplan.mixins.mentions import HasMentions
from gameplan.mixins.reactions import HasReactions
from gameplan.mixins.tags import HasTags
from gameplan.permissions import comment_query_conditions, content_has_permission
from gameplan.utils import get_document_revisions, remove_empty_trailing_paragraphs
from gameplan.utils.document import with_stored_document

POLL_BLOCK = re.compile(r'<div\b[^>]*\bdata-type="poll"[^>]*>\s*</div>')


class GPComment(HasAttachments, HasBacklinks, HasMentions, HasReactions, HasTags, Document):
	on_delete_cascade = ["GP Draft", "GP Poll"]
	on_delete_set_null = ["GP Notification", "GP Discussion"]
	mentions_field = "content"
	tags_field = "content"
	attachments_field = "content"

	def before_insert(self):
		if self.reference_doctype not in ["GP Discussion"]:
			return

		reference_doc = frappe.get_doc(self.reference_doctype, self.reference_name)
		if reference_doc.meta.has_field("closed_at"):
			if reference_doc.closed_at:
				frappe.throw("Cannot add comment to a closed discussion")

	def after_insert(self):
		self.update_discussion_meta()
		self.update_task_meta()
		if self.reference_doctype == "GP Discussion":
			GPUnreadRecord.create_unread_records_for_comment(self)

	def on_trash(self):
		self.remove_all_reactions()
		if self.reference_doctype == "GP Discussion":
			GPUnreadRecord.delete_unread_records_for_comment(self.name)
		self.remove_all_bookmarks()

	def after_delete(self):
		if self.flags.from_gameplan_delete_cascade == "GP Discussion":
			# The discussion is being deleted and we are one of its children. Refreshing
			# its counters is pointless, and `track_visit` would insert a fresh GP
			# Discussion Visit row. That row happens to be swept today only because
			# "GP Comment" precedes "GP Discussion Visit" in GPDiscussion's cascade list
			# — reorder that list and the row survives to trip the parent's link check,
			# which is exactly how GP Poll broke. Do not rely on the ordering.
			return
		self.update_discussion_meta()
		self.update_task_meta()

	def before_save(self):
		self.set_edited_at()
		self.update_tags()
		self.update_backlinks()

	def update_discussion_meta(self):
		if self.reference_doctype != "GP Discussion":
			return
		discussion = frappe.get_doc("GP Discussion", self.reference_name)
		discussion.update_last_post()
		discussion.update_post_count()
		discussion.update_participants_count()
		discussion.save(ignore_permissions=True)
		# track_visit reloads the stored discussion, so save the counters first.
		discussion.track_visit()

	def update_task_meta(self):
		if self.reference_doctype != "GP Task":
			return
		frappe.get_doc("GP Task", self.reference_name).update_comments_count()

	def validate(self):
		# Gate the content itself, not every save, as discussions do: they only guard
		# `before_insert`.
		if self.is_new():
			check_if_space_is_archived(self, action="add", content_type="comments")
		elif self.has_value_changed("content"):
			check_if_space_is_archived(self, action="edit", content_type="comments")
		self.sanitize_content()
		self.keep_poll_with_its_discussion()

	def keep_poll_with_its_discussion(self):
		before = self.get_doc_before_save()
		if not before:
			return
		fields = ("reference_doctype", "reference_name")
		if all(cstr(before.get(field)) == cstr(self.get(field)) for field in fields):
			return
		if frappe.db.exists("GP Poll", {"comment": self.name}):
			frappe.throw(_("A comment with a poll cannot be moved to another discussion"))

	def _get_missing_mandatory_fields(self):
		missing = super()._get_missing_mandatory_fields()
		if self.has_a_poll_that_stays():
			missing = [field for field in missing if field[0] != "content"]
		return missing

	def has_a_poll_that_stays(self):
		# A block pointing at another comment's poll (one pasted from elsewhere) is dropped
		# on save, so it does not count as content.
		block = POLL_BLOCK.search(self.content or "")
		if not block:
			return False
		attrs = BeautifulSoup(block.group(), "html.parser").div.attrs
		if "data-poll-draft" in attrs:
			return True
		poll = not self.is_new() and frappe.db.get_value("GP Poll", {"comment": self.name})
		return bool(poll) and attrs.get("data-poll") == str(poll)

	def sanitize_content(self):
		from gameplan.utils.sanitizer import sanitize_content

		self.content = remove_empty_trailing_paragraphs(self.content)
		self.content = sanitize_content(self.content)

	def set_edited_at(self):
		if not self.get_doc_before_save():
			return

		if self.has_value_changed("content"):
			self.edited_at = frappe.utils.now()

	def on_update(self):
		self.notify_mentions()
		self.log_backlink_activities()
		self.attach_files_in_content()
		self.sync_poll()

	def sync_poll(self):
		if self.reference_doctype != "GP Discussion" or not self.has_value_changed("content"):
			return
		blocks = POLL_BLOCK.findall(self.content or "")
		if len(blocks) > 1:
			frappe.throw(_("A comment can only have one poll"))
		attrs = BeautifulSoup(blocks[0], "html.parser").div.attrs if blocks else {}

		poll = frappe.db.get_value("GP Poll", {"comment": self.name})
		if poll and attrs.get("data-poll") != str(poll):
			if not frappe.has_permission("GP Poll", "delete", poll):
				frappe.throw(_("Only the poll's owner can remove it"), frappe.PermissionError)
			frappe.delete_doc("GP Poll", poll)
			poll = None
		if not poll and "data-poll-draft" in attrs:
			poll = self.create_poll(attrs["data-poll-draft"])

		block = f'<div data-type="poll" data-poll="{poll}"></div>' if poll else ""
		content = POLL_BLOCK.sub(block, self.content or "")
		if content != self.content:
			self.db_set("content", content, update_modified=False)

	def create_poll(self, draft):
		try:
			draft = json.loads(draft)
		except ValueError:
			frappe.throw(_("Invalid poll"))
		options = draft.get("options") if isinstance(draft, dict) else None
		if not isinstance(options, list) or not all(isinstance(option, dict) for option in options):
			frappe.throw(_("Invalid poll"))
		return (
			frappe.get_doc(
				doctype="GP Poll",
				discussion=self.reference_name,
				comment=self.name,
				title=draft.get("title"),
				anonymous=draft.get("anonymous"),
				multiple_answers=draft.get("multiple_answers"),
				options=[{"title": option.get("title")} for option in options if option.get("title")],
			)
			.insert()
			.name
		)

	@frappe.whitelist()
	@with_stored_document
	def get_revisions(self, fieldname="content"):
		"""Return the edit history of `fieldname` (default: content) on this comment."""
		return get_document_revisions(self.doctype, self.name, fieldname)

	@frappe.whitelist(methods=["POST"])
	@with_stored_document
	def add_bookmark(self):
		"""Bookmark this comment for the current user. Only works on discussion comments."""
		if self.reference_doctype != "GP Discussion":
			return
		if frappe.db.exists("GP Bookmark", self.bookmark_filters()):
			return
		frappe.new_doc(
			"GP Bookmark", discussion=self.reference_name, comment=self.name, user=frappe.session.user
		).insert()

	@frappe.whitelist(methods=["POST"])
	@with_stored_document
	def remove_bookmark(self):
		"""Remove the current user's bookmark on this comment."""
		bookmark = frappe.db.get_value("GP Bookmark", self.bookmark_filters(), "name")
		if not bookmark:
			return
		frappe.get_doc("GP Bookmark", bookmark).delete()

	def bookmark_filters(self):
		return {"comment": self.name, "user": frappe.session.user}

	def remove_all_bookmarks(self):
		for name in frappe.get_all("GP Bookmark", filters={"comment": self.name}, pluck="name"):
			frappe.delete_doc("GP Bookmark", name, ignore_permissions=True)


def get_permission_query_conditions(user):
	return comment_query_conditions(user)


def has_permission(doc, ptype="read", user=None):
	return content_has_permission(doc, ptype, user)


def on_doctype_update():
	add_indexes()


def add_indexes():
	# Speeds up the "commented by user" lookups (participating feed and
	# get_participating_unread_count): WHERE owner = ? AND reference_doctype = ?
	# returning reference_name. Without it MariaDB full-scans GP Comment as a
	# per-row dependent subquery — ~18s on large sites vs ~20ms with the index.
	frappe.db.add_index("GP Comment", ["owner", "reference_doctype", "reference_name"], "owner_reference")
