import frappe

from gameplan.utils.document import with_stored_document


def is_removed(doc):
	return bool(doc.get("hidden_at") or doc.get("spam_removed_at"))


def parent_discussion(doc):
	if doc.doctype == "GP Discussion":
		return doc.name
	if doc.doctype == "GP Poll":
		return doc.discussion
	if doc.doctype == "GP Comment" and doc.reference_doctype == "GP Discussion":
		return doc.reference_name


def discussion_is_removed(name):
	return bool(
		name
		and is_removed(
			frappe._dict(
				frappe.db.get_value("GP Discussion", name, ["hidden_at", "spam_removed_at"], as_dict=True)
				or {}
			)
		)
	)


class Moderatable:
	@frappe.whitelist(methods=["POST"])
	@with_stored_document
	def hide(self, reason: str):
		self._remove_content("Hide", reason)

	@frappe.whitelist(methods=["POST"])
	@with_stored_document
	def delete_spam(self, reason: str):
		self._remove_content("Delete Spam", reason)

	def _remove_content(self, action, reason):
		from gameplan.search_sqlite import GameplanSearch

		doc = self._moderation_target()
		field = "hidden_at" if action == "Hide" else "spam_removed_at"
		if doc.get(field):
			return
		if doc.get("deleted_at"):
			frappe.throw("Deleted replies cannot be hidden")
		if not isinstance(reason, str) or not reason.strip() or len(reason) > 500:
			frappe.throw("Enter a reason of at most 500 characters")
		doc._check_moderated_files()
		original = doc._original_content() if is_removed(doc) else doc
		frappe.get_doc(
			doctype="GP Moderation Log",
			**doc._log_filters(),
			action=action,
			reason=reason.strip(),
			content=original.content,
			title=original.get("title"),
		).insert(ignore_permissions=True)
		values = {"hidden_at": None, "spam_removed_at": None, field: frappe.utils.now()}
		label = "reply" if doc.doctype == "GP Comment" else "discussion"
		values["content"] = f"<p>This {label} was removed by a moderator.</p>"
		if doc.doctype == "GP Discussion":
			values["title"] = "Removed discussion"
		doc.db_set(values, notify=True)
		search = GameplanSearch()
		if search.is_search_enabled() and search.index_exists():
			frappe.db.after_commit.add(lambda: search.remove_doc(doc.doctype, doc.name))
		doc._notify_moderation_change()

	@frappe.whitelist(methods=["POST"])
	@with_stored_document
	def restore(self):
		from frappe.search.sqlite_search import update_doc_index

		doc = self._moderation_target()
		if not is_removed(doc):
			return
		original = doc._original_content()
		values = {"hidden_at": None, "spam_removed_at": None, "content": original.content}
		if doc.doctype == "GP Discussion":
			values["title"] = original.title
		doc.db_set(values, notify=True)
		frappe.get_doc(doctype="GP Moderation Log", **doc._log_filters(), action="Restore").insert(
			ignore_permissions=True
		)
		frappe.db.after_commit.add(lambda: update_doc_index(doc))
		if doc.doctype == "GP Discussion":
			frappe.enqueue(
				"gameplan.moderation.reindex_discussion_replies",
				discussion=doc.name,
				enqueue_after_commit=True,
			)
		doc._notify_moderation_change()

	@frappe.whitelist(methods=["POST"])
	@with_stored_document
	def get_hidden_content(self):
		doc = self._moderation_target()
		if is_removed(doc):
			return doc._original_content().content

	def validate_moderation(self):
		before = self.get_doc_before_save()
		for field in ("hidden_at", "spam_removed_at"):
			if self.has_value_changed(field) and (self.get(field) or (before and before.get(field))):
				frappe.throw("Use the Hide, Delete spam, or Restore action", frappe.PermissionError)
		if before and is_removed(before):
			frappe.throw("Restore this content before editing it", frappe.PermissionError)

	def _original_content(self):
		return frappe.get_last_doc(
			"GP Moderation Log", filters={**self._log_filters(), "action": ["in", ["Hide", "Delete Spam"]]}
		)

	def _log_filters(self):
		return {"comment" if self.doctype == "GP Comment" else "discussion": str(self.name)}

	def _check_moderated_files(self):
		targets = [(self.doctype, str(self.name))]
		if self.doctype == "GP Discussion":
			for doctype, filters in [
				("GP Comment", {"reference_doctype": self.doctype, "reference_name": self.name}),
				("GP Poll", {"discussion": self.name}),
			]:
				targets.extend(
					(doctype, str(name)) for name in frappe.get_all(doctype, filters=filters, pluck="name")
				)
		for doctype, name in targets:
			if frappe.db.exists(
				"File", {"attached_to_doctype": doctype, "attached_to_name": name, "is_private": 0}
			):
				frappe.throw("Make this content's attached files private before removing it")

	def _notify_moderation_change(self):
		frappe.publish_realtime(
			"new_activity",
			{"reference_doctype": "GP Discussion", "reference_name": str(parent_discussion(self))},
			doctype="GP Discussion",
			docname=parent_discussion(self),
			after_commit=True,
		)

	def _moderation_target(self):
		from gameplan.permissions import can_moderate_space, get_content_project

		doc = frappe.get_doc(self.doctype, self.name, for_update=True)
		project = get_content_project(doc)
		if not parent_discussion(doc) or not project or not can_moderate_space(frappe.session.user, project):
			frappe.throw("Only community moderators can perform this action", frappe.PermissionError)
		return doc
