# Copyright (c) 2025, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import re

import frappe
from frappe.model.document import Document


class GPDraft(Document):
	def before_save(self):
		from gameplan.utils.sanitizer import sanitize_content

		self.content = sanitize_content(self.content)

	@staticmethod
	def get_list(query):
		GPDraft = frappe.qb.DocType("GP Draft")
		query = query.where(GPDraft.owner == frappe.session.user)
		return query

	@frappe.whitelist(methods=["POST"])
	def publish(self):
		if self.owner != frappe.session.user:
			frappe.throw("You are not allowed to publish this draft")

		if self.type == "Discussion":
			content = remove_query_params_from_images(self.content)
			# New editor uploads are unattached and get picked up by HasAttachments on
			# insert. Older drafts can still have files attached to the draft itself;
			# move those before deleting the draft so Frappe doesn't cascade-delete them.
			discussion = frappe.new_doc(
				"GP Discussion", title=self.title, content=content, project=self.project
			).insert()
			self.move_attachments_to(discussion)

			self.delete()
			return discussion.name

	def commit(self, reference_doctype: str, reference_name: str):
		"""Finalize an edit/comment draft whose content has already been saved onto its
		target document. Reparents any draft-owned attachments onto the target (so they
		survive the draft deletion) and clears the ?fid= query params that otherwise hide
		the migrated images, then deletes the draft."""
		if self.owner != frappe.session.user:
			frappe.throw("You are not allowed to modify this draft")

		target = frappe.get_doc(reference_doctype, reference_name)
		self.move_attachments_to(target)

		cleaned = remove_query_params_from_images(target.content or "")
		if cleaned != target.content:
			target.content = cleaned
			target.save()

		self.delete()

	def move_attachments_to(self, doc):
		attachments = frappe.qb.get_query(
			"File",
			filters={"attached_to_doctype": self.doctype, "attached_to_name": self.name},
		).run(pluck="name")
		for attachment in attachments:
			frappe.db.set_value(
				"File",
				attachment,
				{"attached_to_doctype": doc.doctype, "attached_to_name": doc.name},
				update_modified=False,
			)


def _keep_newest_singleton(filters: dict) -> str | None:
	"""Resolve a singleton draft to one row, self-healing duplicates.

	A singleton is keyed by (owner, type, mode, reference), but creation is a check-then-act
	(find then insert), so two tabs/devices racing — or the offline orphan-recovery sweep — can
	rarely leave more than one row for the same logical draft. Rather than lock every create, we
	collapse on read: keep the most recently modified row and delete the stale siblings. Returns
	the surviving name, or None."""
	names = frappe.get_all("GP Draft", filters=filters, order_by="modified desc", pluck="name")
	for stale in names[1:]:
		frappe.delete_doc("GP Draft", stale, ignore_permissions=False, delete_permanently=True)
	return names[0] if names else None


@frappe.whitelist(methods=["POST"])
def find_my_draft(
	type: str,
	mode: str = "New",
	reference_doctype: str | None = None,
	reference_name: str | None = None,
):
	"""Return the current user's singleton draft for a given target, or None.

	Singleton drafts (a comment-in-progress on a discussion, an in-flight edit of a
	post/comment) are keyed by (owner, type, mode, reference) so the same logical edit
	resolves to one row across tabs and devices. New-discussion drafts are standalone
	and looked up by name instead, so they are not served here."""
	filters = {"owner": frappe.session.user, "type": type, "mode": mode}
	if not reference_name:
		# Without a reference this isn't a singleton lookup; keep the simple single-row read.
		name = frappe.db.get_value("GP Draft", filters, "name")
		return frappe.get_doc("GP Draft", name).as_dict() if name else None

	filters["reference_doctype"] = reference_doctype
	filters["reference_name"] = reference_name
	name = _keep_newest_singleton(filters)
	if not name:
		return None
	return frappe.get_doc("GP Draft", name).as_dict()


@frappe.whitelist(methods=["POST"])
def get_my_drafts():
	"""Return the current user's new-content drafts, enriched for the Drafts list.

	Covers two kinds of drafts and resolves the metadata each needs to render a row and
	route to it: new-discussion drafts (standalone), and new-comment drafts on a discussion
	(the reply composer's auto-saved buffer).

	A comment draft stores only its content plus a reference to the discussion, so we
	resolve the parent's title and its space/community here rather than forcing the client
	into N+1 lookups. Comment drafts whose discussion was deleted — or whose space the user
	can no longer access — are dropped, since they can't be shown or routed."""
	user = frappe.session.user
	rows = frappe.qb.get_query(
		"GP Draft",
		filters={"owner": user, "mode": "New", "type": ["in", ["Discussion", "Comment"]]},
		fields=[
			"name",
			"title",
			"content",
			"type",
			"project",
			"reference_doctype",
			"reference_name",
			"creation",
			"modified",
		],
		order_by="modified desc",
		ignore_permissions=False,
	).run(as_dict=True)

	# A rare create race can leave multiple drafts for one reply. This endpoint is POST-only so the
	# stale siblings are committed as deleted instead of reappearing after the newest draft is used.
	seen = set()
	deduped = []
	for r in rows:
		if r.type == "Comment" and r.reference_name:
			key = (r.reference_doctype, r.reference_name)
			if key in seen:
				frappe.delete_doc("GP Draft", r.name, ignore_permissions=False, delete_permanently=True)
				continue
			seen.add(key)
		deduped.append(r)
	rows = deduped

	# Resolve parent discussions for comment drafts (permission-checked, so inaccessible
	# ones simply fall out and their drafts get skipped below).
	discussion_ids = list(
		{
			r.reference_name
			for r in rows
			if r.type == "Comment" and r.reference_doctype == "GP Discussion" and r.reference_name
		}
	)
	discussions = {}
	if discussion_ids:
		results = frappe.qb.get_query(
			"GP Discussion",
			filters={"name": ["in", discussion_ids]},
			fields=["name", "title", "project"],
			ignore_permissions=False,
		).run(as_dict=True)
		discussions = {str(d.name): d for d in results}

	# Batch-resolve spaces (title, community, privacy) for both kinds.
	project_ids = {r.project for r in rows if r.type == "Discussion" and r.project}
	project_ids |= {d.project for d in discussions.values() if d.project}
	projects = {}
	if project_ids:
		results = frappe.qb.get_query(
			"GP Project",
			filters={"name": ["in", list(project_ids)]},
			fields=["name", "title", "team", "is_private"],
			ignore_permissions=False,
		).run(as_dict=True)
		projects = {str(p.name): p for p in results}

	drafts = []
	for r in rows:
		if r.type == "Discussion":
			# A draft pinned to a space the user can no longer reach drops out of the
			# permission-checked project query above. Skip it instead of leaking the raw
			# space id (and a route that would 404) the same way the comment branch does.
			if r.project and not projects.get(str(r.project)):
				continue
			project = projects.get(str(r.project)) if r.project else None
			drafts.append(
				{
					"name": r.name,
					"kind": "discussion",
					"owner": user,
					"title": r.title,
					"content": r.content,
					"modified": r.modified,
					"creation": r.creation,
					"space": r.project,
					"space_title": project.title if project else None,
					"community": project.team if project else None,
					"is_private": project.is_private if project else 0,
					"discussion": None,
				}
			)
		elif r.type == "Comment" and r.reference_doctype == "GP Discussion":
			discussion = discussions.get(str(r.reference_name))
			if not discussion:
				continue  # parent discussion gone or not accessible
			project = projects.get(str(discussion.project)) if discussion.project else None
			if not project:
				continue  # can't route without a resolvable space/community
			drafts.append(
				{
					"name": r.name,
					"kind": "comment",
					"owner": user,
					"title": discussion.title,
					"content": r.content,
					"modified": r.modified,
					"creation": r.creation,
					"space": discussion.project,
					"space_title": project.title,
					"community": project.team,
					"is_private": project.is_private,
					"discussion": r.reference_name,
				}
			)

	return drafts


@frappe.whitelist(methods=["POST"])
def publish_draft(name: str):
	"""Publish a discussion draft by name. Returns the new GP Discussion name."""
	return frappe.get_doc("GP Draft", name).publish()


@frappe.whitelist(methods=["POST"])
def commit_draft(name: str, reference_doctype: str, reference_name: str):
	"""Finalize an edit/comment draft after its content has been saved onto the target.
	See GPDraft.commit for the attachment-migration rationale."""
	draft = frappe.get_doc("GP Draft", name)
	draft.commit(reference_doctype, reference_name)


@frappe.whitelist(methods=["POST"])
def bulk_delete(names: list[str]):
	"""Frappe v16 shim for the per-DocType bulk-delete endpoint added in v17.

	Remove this duplicate once Gameplan's minimum supported Frappe version is v17.
	"""
	if not isinstance(names, list):
		frappe.throw("'names' must be a list", frappe.ValidationError)

	deleted = []
	failed = []
	for name in names:
		if not isinstance(name, str | int):
			failed.append({"name": name, "error": "'name' must be a string or integer"})
			continue

		name = str(name)
		frappe.db.savepoint("bulk_delete_drafts")
		try:
			draft = frappe.get_doc("GP Draft", name)
			draft.check_permission("delete")
			draft.delete()
			deleted.append(name)
		except Exception as exc:
			frappe.db.rollback(save_point="bulk_delete_drafts")
			failed.append({"name": name, "error": str(exc)})

	return {
		"deleted": deleted,
		"failed": failed,
		"total": len(names),
		"success_count": len(deleted),
		"failure_count": len(failed),
	}


def remove_query_params_from_images(content):
	# replace strings like src="/path/to/image.jpg?fid=param" with src="/path/to/image.jpg"
	# because when we publish draft, images linked to the draft are deleted
	# presence of fid=<name> in the image url prevents the image from being displayed
	pattern = r'(src="[^"]+)\?[^"]*(")'
	return re.sub(pattern, r"\1\2", content)
