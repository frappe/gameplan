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


def content_is_removed(doc):
	if is_removed(doc) or discussion_is_removed(parent_discussion(doc)):
		return True
	if doc.doctype == "GP Poll" and doc.comment:
		comment = frappe.db.get_value(
			"GP Comment", doc.comment, ["hidden_at", "spam_removed_at", "deleted_at"], as_dict=True
		)
		return not comment or is_removed(comment) or bool(comment.deleted_at)
	return False


class Moderatable:
	@frappe.whitelist(methods=["POST"])
	@with_stored_document
	def hide(self, reason: str):
		"""Hide content while preserving its restricted original."""
		self._remove_content("Hide", reason)

	@frappe.whitelist(methods=["POST"])
	@with_stored_document
	def delete_spam(self, reason: str):
		"""Remove spam reversibly while preserving its restricted original."""
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
		"""Restore removed content without sending new mention notifications."""
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
		"""Return the removed original to an authorized moderator."""
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
		elif self.doctype == "GP Comment":
			targets.extend(
				("GP Poll", str(name))
				for name in frappe.get_all("GP Poll", filters={"comment": self.name}, pluck="name")
			)
		for doctype, name in targets:
			if doctype == "GP Poll":
				Share = frappe.qb.DocType("DocShare")
				shares = (
					frappe.qb.from_(Share)
					.select(Share.name)
					.where((Share.share_doctype == doctype) & (Share.share_name == name))
					.where((Share.read == 1) | (Share.write == 1) | (Share.share == 1) | (Share.submit == 1))
					.limit(1)
					.for_update()
					.run()
				)
				if shares:
					frappe.throw("Remove this poll's document shares before removing its content")
			if frappe.db.exists(
				"File", {"attached_to_doctype": doctype, "attached_to_name": name, "is_private": 0}
			):
				frappe.throw("Make this content's attached files private before removing it")

	def _notify_moderation_change(self):
		if self.doctype == "GP Discussion":
			from gameplan.realtime import notify_notification_count_changed, notify_unread_counts_changed

			notify_unread_counts_changed(
				frappe.get_all("GP Unread Record", filters={"discussion": self.name}, pluck="user")
			)
			for user in set(
				frappe.get_all("GP Notification", filters={"discussion": self.name}, pluck="to_user")
			):
				notify_notification_count_changed(user, force_refresh=True)
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
