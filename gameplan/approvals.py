import hashlib

import frappe
from frappe.utils import now_datetime

from gameplan.approval_access import can_read_submission, read_criterion, submission_project, target_criterion
from gameplan.approval_files import published_content
from gameplan.approval_policy import needs_approval, publishing_submission
from gameplan.community_bans import can_moderate_community, require_participation
from gameplan.mixins.archivable import check_if_space_is_archived
from gameplan.paging import page_start
from gameplan.permissions import can_moderate_space, moderatable_project_names
from gameplan.reporting import checked_note


@frappe.whitelist(methods=["POST"])
def submit(
	doctype: str,
	request_key: str,
	content: str,
	project: str = "",
	discussion: str = "",
	title: str = "",
	draft: str = "",
):
	"""Publish a discussion/reply or preserve a private submission for moderator approval."""
	doc = new_content(doctype, project, discussion, title, content)
	from gameplan.watched_word_actions import check_block

	check_block(doc)
	draft_found = True
	if draft:
		try:
			validate_draft(draft, doc)
		except frappe.DoesNotExistError:
			frappe.clear_last_message()
			draft_found = False
	frappe.db.get_value("User", frappe.session.user, "name", for_update=True)
	validate_destination(doc)
	existing = existing_submission(doc, request_key)
	if existing:
		return outcome(existing)
	if not draft_found:
		frappe.throw("This draft was already submitted or removed. Check My submissions.")
	if needs_approval(doc):
		return hold(doc, request_key, draft)
	doc.insert()
	return {"doctype": doc.doctype, "name": str(doc.name)}


def hold(doc, request_key, draft="", edit=None):
	frappe.db.get_value("User", frappe.session.user, "name", for_update=True)
	key = submission_key(request_key)
	existing = existing_submission(doc, request_key)
	if existing:
		return outcome(existing)
	project = (
		doc.project
		if doc.doctype == "GP Discussion"
		else frappe.db.get_value("GP Discussion", doc.reference_name, "project")
	)
	community = frappe.db.get_value("GP Project", project, "team")
	Submission, Project = frappe.qb.DocType("GP Submission"), frappe.qb.DocType("GP Project")
	projects = frappe.qb.from_(Project).select(Project.name).where(Project.team == community)
	pending = (
		frappe.qb.from_(Submission)
		.select(Submission.name)
		.where((Submission.owner == frappe.session.user) & (Submission.status == "Pending"))
		.where(target_criterion(projects))
		.limit(5)
		.for_update()
		.run()
	)
	if len(pending) >= 5:
		frappe.throw(
			"You already have five pending submissions in this Community", frappe.RateLimitExceededError
		)
	from gameplan.slow_mode import record_reply

	if not edit:
		record_reply(doc)

	submission = frappe.get_doc(
		doctype="GP Submission",
		project=project if doc.doctype == "GP Discussion" else None,
		discussion=doc.reference_name if doc.doctype == "GP Comment" else None,
		title=doc.get("title"),
		content=doc.content,
		request_key=key,
		status="Pending",
		edit_doctype=edit.doctype if edit else None,
		edit_name=edit.name if edit else None,
		edit_modified=str(edit.modified) if edit else None,
	)
	submission.insert(ignore_permissions=True)
	if draft:
		from gameplan.watched_word_edits import validate_edit_draft

		stored = validate_edit_draft(draft, edit) if edit else validate_draft(draft, doc)
		# Referenced attachments are already attached to the submission before draft cleanup.
		stored.delete()
	return outcome(submission)


def community_submissions(projects):
	"""Submissions for the Spaces in `projects`: new discussions, replies and edits.

	Join each submission to its discussion by primary key and compare the Space to a list. The
	generic read criterion repeats nested subqueries that scan the member table for every row,
	which took more than a minute on a large forum."""
	Submission = frappe.qb.DocType("GP Submission")
	Parent = frappe.qb.DocType("GP Discussion").as_("parent")
	EditedPost = frappe.qb.DocType("GP Discussion").as_("edited_post")
	EditedReply = frappe.qb.DocType("GP Comment").as_("edited_reply")
	ReplyPost = frappe.qb.DocType("GP Discussion").as_("reply_post")
	if not projects:
		return frappe.qb.from_(Submission).where(Submission.name.isnull() & Submission.name.notnull())
	projects = [str(name) for name in projects]
	is_new = Submission.edit_name.isnull() | (Submission.edit_name == "")
	has_parent = Submission.discussion.notnull() & (Submission.discussion != "")
	return (
		frappe.qb.from_(Submission)
		.left_join(Parent)
		.on(Parent.name == Submission.discussion)
		.left_join(EditedPost)
		.on((Submission.edit_doctype == "GP Discussion") & (EditedPost.name == Submission.edit_name))
		.left_join(EditedReply)
		.on((Submission.edit_doctype == "GP Comment") & (EditedReply.name == Submission.edit_name))
		.left_join(ReplyPost)
		.on(
			(EditedReply.reference_doctype == "GP Discussion")
			& (ReplyPost.name == EditedReply.reference_name)
		)
		.where(
			(is_new & ~has_parent & Submission.project.isin(projects))
			| (is_new & has_parent & Parent.project.isin(projects))
			| (~is_new & (Submission.edit_doctype == "GP Discussion") & EditedPost.project.isin(projects))
			| (~is_new & (Submission.edit_doctype == "GP Comment") & ReplyPost.project.isin(projects))
		)
	)


@frappe.whitelist(methods=["GET", "POST"])
def queue(community: str = "", status: str = "Pending", start: int = 0):
	"""List the author's submissions, or an accessible Community queue for its moderators."""
	if status not in ("Pending", "Approved", "Rejected", "Withdrawn"):
		frappe.throw("Choose a submission status")
	Submission = frappe.qb.DocType("GP Submission")
	if community:
		if not can_moderate_community(community):
			frappe.throw("Only Community moderators can review submissions", frappe.PermissionError)
		query = community_submissions(moderatable_project_names(community))
	else:
		query = frappe.qb.from_(Submission).where(
			read_criterion(frappe.session.user) & (Submission.owner == frappe.session.user)
		)
	rows = (
		query.select(
			Submission.name,
			Submission.title,
			Submission.owner,
			Submission.creation,
			Submission.discussion,
			Submission.edit_name,
			Submission.status,
		)
		.where(Submission.status == status)
		.orderby(Submission.creation, order=frappe.qb.desc)
		.orderby(Submission.name, order=frappe.qb.desc)
		.offset(page_start(start))
		.limit(41)
		.run(as_dict=True)
	)
	return {"items": rows[:40], "has_more": len(rows) > 40}


@frappe.whitelist(methods=["GET", "POST"])
def detail(name: str):
	doc = frappe.get_doc("GP Submission", name)
	doc.check_permission("read")
	result = doc.as_dict()
	result.current_project = submission_project(doc)
	result.current_community = frappe.db.get_value("GP Project", result.current_project, "team")
	return result


@frappe.whitelist(methods=["POST"])
def decide(name: str, decision: str, expected_modified: str, note: str = ""):
	submission = frappe.get_doc("GP Submission", name)
	if not can_read_submission(submission):
		frappe.throw("This submission is unavailable", frappe.PermissionError)
	actor = frappe.session.user
	frappe.db.get_value("User", submission.owner, "name", for_update=True)
	submission = frappe.get_doc("GP Submission", name, for_update=True)
	project = submission_project(submission, for_update=True)
	if not can_read_submission(submission, project=project):
		frappe.throw("This submission is unavailable", frappe.PermissionError)
	if decision == "Withdraw":
		allowed = submission.owner == actor
	else:
		allowed = can_moderate_space(actor, project)
	if not allowed:
		frappe.throw("You cannot decide this submission", frappe.PermissionError)
	states = {"Approve": "Approved", "Reject": "Rejected", "Withdraw": "Withdrawn"}
	if decision not in states:
		frappe.throw("Choose an approval decision")
	if submission.status == states[decision]:
		return outcome(submission)
	if submission.status != "Pending" or str(submission.modified) != expected_modified:
		frappe.throw("This submission changed. Refresh before deciding.", frappe.TimestampMismatchError)
	note = checked_note(note, required=decision == "Reject")
	values = {
		"status": states[decision],
		"decision_note": note,
		"decided_by": actor,
		"decided_at": now_datetime(),
	}
	if decision == "Approve":
		sid, session_data, form_dict = frappe.session.sid, frappe.session.data, frappe.local.form_dict
		try:
			frappe.set_user(submission.owner)
			if not frappe.db.get_value("User", submission.owner, "enabled", for_update=True):
				frappe.throw("The author's account is disabled", frappe.PermissionError)
			doc = new_content(
				"GP Comment" if submission.discussion else "GP Discussion",
				project,
				submission.discussion,
				submission.title,
				published_content(submission.content),
			)
			if not submission.edit_name:
				validate_destination(doc)
			if submission.edit_name:
				from gameplan.watched_word_edits import edited_document

				doc = edited_document(submission, doc)
			token = publishing_submission.set((doc, submission.name))
			try:
				doc.save() if submission.edit_name else doc.insert()
			finally:
				publishing_submission.reset(token)
		finally:
			frappe.set_user(actor)
			frappe.session.sid, frappe.session.data, frappe.local.form_dict = sid, session_data, form_dict
		values.update(published_doctype=doc.doctype, published_name=str(doc.name))
	submission.db_set(values)
	return outcome(submission)


def new_content(doctype, project, discussion, title, content):
	if doctype not in ("GP Discussion", "GP Comment"):
		frappe.throw("Only discussions and replies support approval")
	if not isinstance(content, str) or not content.strip():
		frappe.throw("Add content before submitting")
	if doctype == "GP Discussion":
		if not isinstance(title, str) or not title.strip():
			frappe.throw("Add a discussion title")
		doc = frappe.get_doc(doctype=doctype, project=project, title=title, content=content)
	else:
		doc = frappe.get_doc(
			doctype=doctype, reference_doctype="GP Discussion", reference_name=discussion, content=content
		)
	doc.sanitize_content()
	return doc


def validate_destination(doc):
	if doc.doctype == "GP Comment":
		parent = frappe.get_doc("GP Discussion", doc.reference_name, for_update=True)
		if str(parent.project) != str(frappe.db.get_value("GP Discussion", parent.name, "project")):
			frappe.throw("This discussion moved. Refresh before submitting.", frappe.TimestampMismatchError)
	doc.check_permission("create")
	require_participation(doc)
	check_if_space_is_archived(doc, action="create", content_type="posts")
	project = doc.project if doc.doctype == "GP Discussion" else parent.project
	team = frappe.db.get_value("GP Project", project, "team") if project else None
	if team and frappe.db.get_value("GP Team", team, "archived_at"):
		frappe.throw("This Community is archived")
	if doc.doctype == "GP Comment":
		if parent.closed_at or parent.hidden_at or parent.spam_removed_at:
			frappe.throw("This discussion is unavailable for new replies")


def outcome(doc):
	return {
		"doctype": "GP Submission",
		"name": doc.name,
		"status": doc.status,
		"published_doctype": doc.published_doctype,
		"published_name": doc.published_name,
	}


def submission_key(value):
	if not isinstance(value, str) or not 1 <= len(value) <= 200:
		frappe.throw("A submission key is required")
	return hashlib.sha256(f"{frappe.session.user}:{value}".encode()).hexdigest()


def existing_submission(doc, request_key):
	name = frappe.db.get_value(
		"GP Submission", {"request_key": submission_key(request_key)}, "name", for_update=True
	)
	if not name:
		return None
	stored = frappe.get_doc("GP Submission", name, for_update=True)
	if (
		stored.content != doc.content
		or (stored.discussion or "") != (doc.get("reference_name") or "")
		or (stored.title or "") != (doc.get("title") or "")
		or (not stored.discussion and stored.project != doc.project)
	):
		frappe.throw("This submission key already belongs to different content")
	return stored


def validate_draft(name, doc):
	stored = frappe.get_doc("GP Draft", name, for_update=True)
	stored.require_owner()
	expected = "Discussion" if doc.doctype == "GP Discussion" else "Comment"
	if (
		stored.mode != "New"
		or stored.type != expected
		or (expected == "Discussion" and stored.project != doc.project)
		or (
			expected == "Comment"
			and (
				stored.reference_doctype != "GP Discussion"
				or str(stored.reference_name) != str(doc.reference_name)
			)
		)
	):
		frappe.throw("This draft belongs to another submission")
	return stored
