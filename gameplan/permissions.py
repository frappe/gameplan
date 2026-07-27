import frappe
from frappe import _
from frappe.utils import cint

import gameplan

READ_PERMISSIONS = {"read", "select", "print", "email", "export", "share", "report"}


def require_can_manage_community(team, user=None):
	user = user or frappe.session.user
	if not can_manage_community(user, team):
		frappe.throw(_("Only community admins can perform this action"), frappe.PermissionError)


def require_can_manage_space_members(project, user=None):
	user = user or frappe.session.user
	if not can_manage_space(user, project):
		frappe.throw(_("Only space managers can perform this action"), frappe.PermissionError)


def require_can_invite_guest(project, user=None):
	user = user or frappe.session.user
	if not can_invite_guest(user, project):
		frappe.throw(_("Only space managers can invite guests"), frappe.PermissionError)


def team_has_permission(doc, ptype="read", user=None, **kwargs):
	user = user or frappe.session.user
	if ptype in READ_PERMISSIONS:
		return can_view_community(user, doc)
	if ptype in {"write", "delete"}:
		return can_manage_community(user, doc)
	return True


def project_has_permission(doc, ptype="read", user=None, **kwargs):
	user = user or frappe.session.user
	if ptype in READ_PERMISSIONS:
		return can_view_space(user, doc)
	if ptype in {"write", "delete"}:
		return can_manage_space(user, doc)
	return True


def content_has_permission(doc, ptype="read", user=None, **kwargs):
	user = user or frappe.session.user
	if ptype in READ_PERMISSIONS:
		return can_view_content(user, doc)
	if ptype == "create":
		return can_create_content(user, doc)
	if ptype == "write":
		return can_write_content(user, doc)
	if ptype == "delete":
		return can_delete_content(user, doc)
	return True


def can_manage_community(user, team):
	if is_global_admin(user):
		return True
	team_name = get_doc_name(team)
	return is_community_admin(user, team_name)


def can_view_community(user, team):
	if is_global_admin(user):
		return True
	team_name = get_doc_name(team)
	if gameplan.is_guest(user):
		# Guests never join a community, but they must be able to READ the community
		# that holds a space they've been granted — otherwise the SPA can't render the
		# shell around that space. Access is exactly the communities of their granted
		# spaces, nothing else.
		return guest_can_view_community(user, team_name)
	is_private = (
		team.is_private
		if hasattr(team, "doctype")
		else frappe.db.get_value("GP Team", team_name, "is_private")
	)
	if not cint(is_private):
		return True
	return is_community_member(user, team_name)


def can_view_space(user, project):
	if is_global_admin(user):
		return True
	project = get_project_info(project)
	if not project:
		return False
	if gameplan.is_guest(user):
		return has_guest_access(user, project.name)
	if cint(project.is_private):
		return is_space_member(user, project.name)
	return can_view_community(user, project.team)


def can_manage_space(user, project):
	if is_global_admin(user):
		return True
	project = get_project_info(project)
	if not project:
		return False
	if cint(project.is_private):
		return is_space_member(user, project.name)
	return is_community_admin(user, project.team)


def can_invite_guest(user, project):
	if gameplan.is_guest(user):
		return False
	return can_manage_space(user, project)


def can_view_content(user, doc):
	project = get_content_project(doc)
	if project:
		return can_view_space(user, project)
	if is_global_admin(user):
		return True
	return get_doc_value(doc, "owner") == user


def users_who_can_view_content(users, doc):
	"""The subset of `users` that can_view_content would return True for.

	Same rule, resolved with a fixed handful of queries instead of two or three per
	user. For fan-outs over a whole site — an `@everyone` mention, a digest audience —
	the per-user form makes the query count grow with the member list.

	Mirrors can_view_space/can_view_community with the membership rows loaded up front;
	keep the two in step.
	"""
	users = list(dict.fromkeys(users))
	project = get_content_project(doc)
	if not project:
		return [user for user in users if can_view_content(user, doc)]

	project_info = get_project_info(project)
	if not project_info:
		return []

	space_members = _member_users("GP Project", project_info.name)
	community_members = _member_users("GP Team", project_info.team) if project_info.team else set()
	guests = _guest_users(project_info.name)
	community_is_private = (
		cint(frappe.db.get_value("GP Team", project_info.team, "is_private")) if project_info.team else 0
	)

	def allowed(user):
		if is_global_admin(user):
			return True
		if gameplan.is_guest(user):
			return user in guests
		if cint(project_info.is_private):
			return user in space_members
		return not community_is_private or user in community_members

	return [user for user in users if allowed(user)]


def _member_users(parenttype, parent):
	"""Every user on `parent`'s membership table, as a set."""
	Member = frappe.qb.DocType("GP Member")
	rows = (
		frappe.qb.from_(Member)
		.select(Member.user)
		.where(Member.parenttype == parenttype)
		.where(Member.parent == parent)
		.run()
	)
	return {row[0] for row in rows}


def _guest_users(project):
	"""Every user holding guest access to `project`, as a set."""
	GuestAccess = frappe.qb.DocType("GP Guest Access")
	rows = frappe.qb.from_(GuestAccess).select(GuestAccess.user).where(GuestAccess.project == project).run()
	return {row[0] for row in rows}


def can_create_content(user, doc):
	if gameplan.is_guest(user):
		# Guests participate in the discussions they can reach: a comment, and a poll on
		# a discussion, are both participation. Everything else (discussions, tasks,
		# pages) stays closed to them.
		return doc.doctype in {"GP Comment", "GP Poll"} and can_view_content(user, doc)
	if not get_content_project(doc):
		return is_global_admin(user) or not get_doc_value(doc, "owner") or get_doc_value(doc, "owner") == user
	return can_view_content(user, doc)


# Per-doctype fields a non-editor is allowed to change while still holding `write`.
# These are interaction (not content) fields — reacting is participation, not an
# edit — so changing only these keeps the write permission for guests/space viewers.
INTERACTION_SAFE_FIELDS = {
	"GP Discussion": {"reactions"},
	"GP Comment": {"reactions"},
	"GP Page": set(),
	"GP Task": set(),
	# Votes are deliberately NOT listed: a vote goes through GPPoll.submit_vote, which
	# gates on participation, re-reads the stored poll (GPPoll.discard_client_state) so
	# nothing the caller sent survives, and only touches the caller's own row. Leaving
	# the vote tables protected here is what stops a non-editor rewriting a poll by
	# plain save.
	"GP Poll": {"reactions"},
}

# Per-doctype fields that only the content's owner (or a moderator who could delete it)
# may change. Everyone who can reach a space may edit the content in it — see
# can_edit_content — but a poll's ballot and lifecycle are not shared property: stopping
# a poll, rewriting its options, or touching the recorded votes is the author's call.
# GPPoll.stop_poll enforces this for the whitelisted method; the entry below is what
# closes the plain `PUT /api/v2/document/GP Poll/<name>` route, which never reaches it.
OWNER_ONLY_FIELDS = {
	"GP Poll": {"stopped_at", "votes", "options", "total_votes"},
}

# Standard row-level fields ignored when diffing a child table for changes.
_ROW_META_FIELDS = {
	"name",
	"idx",
	"creation",
	"modified",
	"modified_by",
	"owner",
	"parent",
	"parentfield",
	"parenttype",
	"docstatus",
}


def can_interact_with_content(user, doc):
	"""Whether `user` can reach `doc` to participate (react/comment) at all.

	True for anyone who can view the content's space (members and granted guests
	alike) and, for personal/space-less content, its owner. This is the floor for the
	`write` permission; whether a specific *edit* is allowed on top of it is decided
	by can_edit_content / _protected_fields_changed.
	"""
	if is_global_admin(user):
		return True
	if not can_view_content(user, doc):
		return False
	if get_content_project(doc):
		return True
	return get_doc_value(doc, "owner") == user


def can_write_content(user, doc):
	"""Back the doctype `write` permission — "may interact with this document".

	Editors (can_edit_content: global admins, space-viewing members, owners, and
	guests on their OWN content) always hold write. Non-editors who can still reach
	the content (space viewers — guests included — and owners of personal content)
	hold write only for interaction: the save must not touch anything beyond the
	interaction-safe fields (reactions).

	This is checked in two contexts (see _protected_fields_changed): on a CLEAN doc
	(the v2 doc-method gate and list/UI permission checks) it reports no changes, so
	a guest passes and can reach react(); on the DIRTY in-memory doc at save time it
	diffs against the DB row and rejects any edit to protected fields.

	Above all of that sits _owner_only_write_allowed: a few fields (a poll's ballot and
	lifecycle) are the author's even for an editor, so they are ruled out first.
	"""
	if not _owner_only_write_allowed(user, doc):
		return False
	if can_edit_content(user, doc):
		return True
	if not can_interact_with_content(user, doc):
		return False
	return not _protected_fields_changed(doc)


def _owner_only_write_allowed(user, doc):
	"""Whether `doc`'s pending changes keep clear of its OWNER_ONLY_FIELDS.

	Checked ahead of the editor rule, because "any member may edit the content in a
	space they can reach" must not double as permission to stop someone else's poll or
	replace its ballot. Ownership here is exactly can_delete_content — owner, community
	admin or global admin — so moderation keeps working.
	"""
	fields = OWNER_ONLY_FIELDS.get(getattr(doc, "doctype", None))
	if not fields:
		return True
	if can_delete_content(user, doc):
		return True
	return not _fields_changed(doc, fields)


def _protected_fields_changed(doc):
	"""Whether `doc` has pending changes to any field a non-editor may not touch.

	Compares the in-memory document against its stored row, ignoring the doctype's
	interaction-safe fields.
	"""
	before = _stored_version(doc)
	if before is None:
		return False
	safe_fields = INTERACTION_SAFE_FIELDS.get(doc.doctype, set())
	protected = {df.fieldname for df in doc.meta.fields if df.fieldname not in safe_fields}
	return _any_field_changed(doc, before, protected)


def _fields_changed(doc, fieldnames):
	"""Whether `doc` has pending changes to any of `fieldnames`."""
	before = _stored_version(doc)
	if before is None:
		return False
	return _any_field_changed(doc, before, fieldnames)


def _stored_version(doc):
	"""The saved row behind `doc`, or None when there is nothing to diff against.

	Uses the mid-save snapshot (get_doc_before_save) when it is already loaded,
	otherwise reads the row from the DB — this is what makes the diffs correct for BOTH
	a clean doc (nothing loaded/changed -> no differences) and a dirty doc at the
	save-time write check (before-save snapshot not yet loaded -> read DB and diff).
	"""
	if not hasattr(doc, "doctype"):
		return None
	if doc.get("__islocal") or not doc.get("name"):
		# Create path — not this gate's concern (create is a separate permission).
		return None
	before = doc.get_doc_before_save()
	return before if before is not None else frappe.get_doc(doc.doctype, doc.name)


def _any_field_changed(doc, before, fieldnames):
	for df in doc.meta.fields:
		fieldname = df.fieldname
		if fieldname not in fieldnames:
			continue
		if df.fieldtype in ("Table", "Table MultiSelect"):
			if _child_table_changed(doc.get(fieldname), before.get(fieldname)):
				return True
		elif doc.get(fieldname) != before.get(fieldname):
			return True
	return False


def _child_table_changed(current_rows, previous_rows):
	def normalize(rows):
		normalized = []
		for row in rows or []:
			row_dict = row.as_dict() if hasattr(row, "as_dict") else dict(row)
			normalized.append({k: v for k, v in row_dict.items() if k not in _ROW_META_FIELDS})
		return normalized

	return normalize(current_rows) != normalize(previous_rows)


def can_edit_content(user, doc):
	"""Business rule for who may change a document's own content.

	Enforced at save time by can_write_content and _protected_fields_changed in
	the has_permission write check. Also mirrored in the frontend
	(utils/permissions.ts::canEditContent) to gate edit affordances.
	"""
	if is_global_admin(user):
		return True
	if not can_view_content(user, doc):
		return False
	if gameplan.is_guest(user):
		# Guests are participants in the spaces they're granted, but only on their
		# OWN content — they may edit posts/comments they authored, never anyone
		# else's.
		return get_doc_value(doc, "owner") == user
	# Gameplan is community-driven: content inside a space is owned by the
	# community, so any member who can access the space may edit it (and run
	# lifecycle actions like pin/close). Personal content with no space stays
	# editable only by its owner.
	if get_content_project(doc):
		return True
	return get_doc_value(doc, "owner") == user


def is_delete_cascade(doc):
	"""Whether `doc` is being deleted as a child of a Gameplan cascade delete.

	`gameplan/mixins/on_delete.py` sets this flag on every record it removes on behalf
	of a parent; `frappe.model.delete_doc` applies it before the delete permission check.
	Nothing reachable over HTTP can set it — `frappe.client.delete` and the v2 delete
	route pass no flags.
	"""
	flags = getattr(doc, "flags", None)
	return bool(flags and flags.get("from_gameplan_delete_cascade"))


def can_delete_content(user, doc):
	if is_delete_cascade(doc):
		# The parent delete was already authorised, and its children go with it: a
		# discussion owner removing their own thread takes the comments and polls other
		# members posted in it. Re-asking the per-child rule here would let one other
		# member's poll veto the thread owner's delete, and roll the whole thing back.
		return True
	if is_global_admin(user):
		return True
	if not can_view_content(user, doc):
		return False
	if get_doc_value(doc, "owner") == user:
		# Owners — members and guests alike — may delete content they authored.
		return True
	if gameplan.is_guest(user):
		# Beyond their own content, guests have no delete rights.
		return False
	project = get_content_project(doc)
	if not project:
		return False
	project_info = get_project_info(project)
	return bool(project_info and is_community_admin(user, project_info.team))


def team_query_conditions(user=None, **kwargs):
	user = user or frappe.session.user
	Team = frappe.qb.DocType("GP Team")
	return criterion_sql(team_access_criterion(Team, user))


def project_query_conditions(user=None, **kwargs):
	user = user or frappe.session.user
	Project = frappe.qb.DocType("GP Project")
	return criterion_sql(project_access_criterion(Project, user))


def discussion_query_conditions(user=None, **kwargs):
	return content_project_query_conditions("GP Discussion", user)


def task_query_conditions(user=None, **kwargs):
	return content_project_query_conditions("GP Task", user)


def page_query_conditions(user=None, **kwargs):
	user = user or frappe.session.user
	if is_global_admin(user):
		return None
	Page = frappe.qb.DocType("GP Page")
	criterion = (Page.project.isnull() & (Page.owner == user)) | accessible_project_criterion(
		Page.project, user
	)
	return criterion_sql(criterion)


def comment_query_conditions(user=None, **kwargs):
	user = user or frappe.session.user
	if is_global_admin(user):
		return None

	Comment = frappe.qb.DocType("GP Comment")
	Discussion = frappe.qb.DocType("GP Discussion")
	Task = frappe.qb.DocType("GP Task")
	discussion_query = (
		frappe.qb.from_(Discussion)
		.select(Discussion.name)
		.where(accessible_project_criterion(Discussion.project, user))
	)
	task_query = (
		frappe.qb.from_(Task).select(Task.name).where(accessible_project_criterion(Task.project, user))
	)
	criterion = (
		(Comment.reference_doctype == "GP Discussion") & Comment.reference_name.isin(discussion_query)
	) | ((Comment.reference_doctype == "GP Task") & Comment.reference_name.isin(task_query))
	return criterion_sql(criterion)


def poll_query_conditions(user=None, **kwargs):
	user = user or frappe.session.user
	if is_global_admin(user):
		return None

	Poll = frappe.qb.DocType("GP Poll")
	Discussion = frappe.qb.DocType("GP Discussion")
	discussion_query = (
		frappe.qb.from_(Discussion)
		.select(Discussion.name)
		.where(accessible_project_criterion(Discussion.project, user))
	)
	# A poll with no discussion never reaches the UI, but it is still someone's row —
	# keep it visible to its owner only, the way a space-less page is.
	criterion = Poll.discussion.isin(discussion_query) | (Poll.discussion.isnull() & (Poll.owner == user))
	return criterion_sql(criterion)


def draft_query_conditions(user=None, **kwargs):
	# Drafts are private to their owner in list/report queries. Share-by-link still works:
	# that reads a single draft by name through the doctype's open `read` permission, which
	# this does not touch — only enumeration (list/report) is scoped. Mirrors GPDraft.get_list
	# (the v2 query path); this closes the v1 frappe.client.get_list path, which does not invoke
	# the controller get_list for non-virtual doctypes and so was returning every user's drafts.
	user = user or frappe.session.user
	Draft = frappe.qb.DocType("GP Draft")
	return criterion_sql(Draft.owner == user)


def bookmark_query_conditions(user=None, **kwargs):
	# A bookmark is a personal row — the same rule as a draft (see draft_query_conditions):
	# only the user it belongs to may enumerate it. Decision 4: deliberately no global-admin exception:
	# nothing in Gameplan reads another user's reading list, and without this every
	# Gameplan user could list everyone's bookmarks through the generic list API.
	user = user or frappe.session.user
	Bookmark = frappe.qb.DocType("GP Bookmark")
	return criterion_sql(Bookmark.user == user)


def bookmark_has_permission(doc, ptype="read", user=None, **kwargs):
	"""A bookmark belongs to exactly one user: only they may read, add or remove it.

	Without this, the doctype's role permissions alone let any Gameplan user read,
	rewrite or delete someone else's bookmark by name — and create one in their name.
	"""
	user = user or frappe.session.user
	if not hasattr(doc, "doctype"):
		return True
	return get_doc_value(doc, "user") == user


def content_project_query_conditions(doctype, user=None):
	user = user or frappe.session.user
	if is_global_admin(user):
		return None
	DocType = frappe.qb.DocType(doctype)
	return criterion_sql(accessible_project_criterion(DocType.project, user))


def team_access_criterion(Team, user=None):
	user = user or frappe.session.user
	if is_global_admin(user):
		return None
	if gameplan.is_guest(user):
		# A guest sees exactly the communities that hold a space they've been granted
		# guest access to (via GP Guest Access). Without this the guest's GP Team list
		# is empty and the SPA 404s every community/space/discussion route.
		return Team.name.isin(guest_accessible_team_query(user))
	return (Team.is_private == 0) | is_member_parent("GP Team", Team.name, user)


def project_access_criterion(Project, user=None):
	user = user or frappe.session.user
	if is_global_admin(user):
		return None
	if gameplan.is_guest(user):
		GuestAccess = frappe.qb.DocType("GP Guest Access")
		return Project.name.isin(
			frappe.qb.from_(GuestAccess).select(GuestAccess.project).where(GuestAccess.user == user)
		)
	return ((Project.is_private == 0) & Project.team.isin(accessible_team_query(user))) | is_member_parent(
		"GP Project", Project.name, user
	)


def accessible_project_criterion(project_field, user=None):
	user = user or frappe.session.user
	if is_global_admin(user):
		return None
	return project_field.isin(accessible_project_query(user))


def apply_accessible_project_filter(query, project_field, user=None):
	criterion = accessible_project_criterion(project_field, user)
	if criterion is None:
		return query
	return query.where(criterion)


def apply_team_query_filter(query, user=None):
	"""Restrict a GP Team list query to the teams the user may see."""
	Team = frappe.qb.DocType("GP Team")
	criterion = team_access_criterion(Team, user)
	return query.where(criterion) if criterion is not None else query


def apply_project_query_filter(query, user=None):
	"""Restrict a GP Project list query to the projects the user may see."""
	Project = frappe.qb.DocType("GP Project")
	criterion = project_access_criterion(Project, user)
	return query.where(criterion) if criterion is not None else query


def accessible_project_query(user=None):
	user = user or frappe.session.user
	Project = frappe.qb.DocType("GP Project")
	query = frappe.qb.from_(Project).select(Project.name)
	criterion = project_access_criterion(Project, user)
	if criterion is not None:
		query = query.where(criterion)
	return query


def accessible_team_query(user=None):
	user = user or frappe.session.user
	Team = frappe.qb.DocType("GP Team")
	query = frappe.qb.from_(Team).select(Team.name)
	criterion = team_access_criterion(Team, user)
	if criterion is not None:
		query = query.where(criterion)
	return query


def is_member_parent(parenttype, parent_field, user):
	Member = frappe.qb.DocType("GP Member")
	member_query = (
		frappe.qb.from_(Member)
		.select(Member.parent)
		.where(Member.parenttype == parenttype)
		.where(Member.user == user)
	)
	return parent_field.isin(member_query)


def criterion_sql(criterion):
	return criterion.get_sql(quote_char="`", with_namespace=True) if criterion is not None else None


def is_global_admin(user):
	return gameplan.is_admin(user)


def is_community_member(user, team):
	return bool(frappe.db.exists("GP Member", {"parenttype": "GP Team", "parent": team, "user": user}))


def is_community_admin(user, team):
	return bool(
		frappe.db.exists(
			"GP Member",
			{"parenttype": "GP Team", "parent": team, "user": user, "is_admin": 1},
		)
	)


def is_space_member(user, project):
	return bool(frappe.db.exists("GP Member", {"parenttype": "GP Project", "parent": project, "user": user}))


def has_guest_access(user, project):
	return bool(frappe.db.exists("GP Guest Access", {"user": user, "project": project}))


def guest_accessible_team_query(user):
	"""Subquery of GP Team names that hold a space `user` has guest access to."""
	Project = frappe.qb.DocType("GP Project")
	GuestAccess = frappe.qb.DocType("GP Guest Access")
	return (
		frappe.qb.from_(GuestAccess)
		.join(Project)
		.on(GuestAccess.project == Project.name)
		.where(GuestAccess.user == user)
		.select(Project.team)
	)


def guest_can_view_community(user, team):
	"""Whether `user` (a guest) holds guest access to any space under `team`."""
	Project = frappe.qb.DocType("GP Project")
	GuestAccess = frappe.qb.DocType("GP Guest Access")
	rows = (
		frappe.qb.from_(GuestAccess)
		.join(Project)
		.on(GuestAccess.project == Project.name)
		.where(GuestAccess.user == user)
		.where(Project.team == team)
		.select(GuestAccess.name)
		.limit(1)
		.run()
	)
	return bool(rows)


def get_content_project(doc):
	if doc.doctype in {"GP Discussion", "GP Task", "GP Page"}:
		return get_doc_value(doc, "project")
	if doc.doctype == "GP Poll":
		# A poll lives in a discussion, and takes that discussion's space.
		discussion = get_doc_value(doc, "discussion")
		return frappe.db.get_value("GP Discussion", discussion, "project") if discussion else None
	if doc.doctype != "GP Comment":
		return None
	if doc.reference_doctype in {"GP Discussion", "GP Task"}:
		return frappe.db.get_value(doc.reference_doctype, doc.reference_name, "project")
	return None


def get_project_info(project):
	if hasattr(project, "doctype"):
		return frappe._dict(
			name=project.name,
			team=project.team,
			is_private=project.is_private,
		)
	if not project:
		return None
	return frappe.db.get_value("GP Project", project, ["name", "team", "is_private"], as_dict=True)


def get_doc_name(doc_or_name):
	return doc_or_name.name if hasattr(doc_or_name, "doctype") else doc_or_name


def get_doc_value(doc, fieldname):
	if hasattr(doc, "doctype"):
		return doc.get(fieldname)
	return None
