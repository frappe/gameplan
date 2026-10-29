import frappe
from frappe import _
from frappe.utils import cint, cstr, get_datetime
from pypika.terms import ValueWrapper

import gameplan
from gameplan.public_access import public_access_enabled
from gameplan.visibility import (
	SIGNED_IN_TIERS,
	is_anonymous_eligible_community,
	is_member_access,
	public_team_criterion,
)

# A criterion no row satisfies.
NOTHING = ValueWrapper(1) == ValueWrapper(0)

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
	if not can_invite_guest(user, get_doc_name(project)):
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
	if ptype == "create":
		from gameplan.community_bans import is_banned

		return not is_banned(doc.team, user)

	if ptype in READ_PERMISSIONS:
		return can_view_space(user, doc)
	if ptype in {"write", "delete"}:
		# Check both versions: a move or privacy change needs rights on the edited values,
		# and the user must already manage the stored Space.
		stored = _stored_version(doc)
		return can_manage_space(user, doc) and (stored is None or can_manage_space(user, stored))
	return True


def content_has_permission(doc, ptype="read", user=None, **kwargs):
	user = user or frappe.session.user
	if ptype in READ_PERMISSIONS:
		from gameplan.mixins.moderation import content_is_removed

		allowed = can_view_content(user, doc)
		if not allowed and doc.doctype == "GP Poll" and content_is_removed(doc):
			# A pre-existing share must not reopen moderated content.
			frappe.throw("This content is unavailable", frappe.PermissionError)
		return allowed
	if ptype == "create":
		return can_create_content(user, doc)
	if ptype == "write":
		return can_write_content(user, doc)
	if ptype == "delete":
		return can_delete_content(user, doc)
	# Defer, don't decide. A has_permission hook can only ever DENY — frappe's
	# has_controller_permissions treats a falsy answer as "blocked" and never grants
	# anything the role layer withheld — so True is the correct answer for a permission
	# type Gameplan does not model (submit/cancel/amend/import, or a site's custom
	# Permission Type). It also carries a live caller: frappe.permissions.get_doc_permissions
	# invokes the hook with ptype=None to evaluate the whole permission dict, and a False
	# here collapses that dict to {None: 0}, i.e. the document reads as having no
	# permissions at all. See tests/permissions/test_permission_defaults.py.
	return True


def can_manage_community(user, team):
	if gameplan.is_anonymous(user):
		return False
	if is_global_admin(user):
		return True
	if gameplan.is_guest(user):
		# Guests participate; they never manage. See can_manage_space.
		return False
	team_name = get_doc_name(team)
	return is_community_admin(user, team_name)


def can_view_community(user, team):
	if is_global_admin(user):
		return True
	team_name = get_doc_name(team)
	if is_publicly_readable_community(team):
		# Anyone at all, signed in or not. A Gameplan Guest without a grant here reads it
		# too: they could by signing out.
		return True
	if gameplan.is_anonymous(user):
		# Every other tier needs an account. Without this, an anonymous visitor would fall
		# through to the member rules below, which read a General community as visible.
		return False
	if gameplan.is_guest(user):
		# Guests never join a community, but they must be able to READ the community
		# that holds a space they've been granted — otherwise the SPA can't render the
		# shell around that space. Access is exactly the communities of their granted
		# spaces, nothing else.
		return guest_can_view_community(user, team_name)
	if not team_name:
		# A space outside every community (Uncategorized) has no community gate. A missing
		# community is open, as it always was; only a community row without a tier reads as
		# Member Access.
		return True
	visibility = (
		team.visibility
		if hasattr(team, "doctype")
		else frappe.db.get_value("GP Team", team_name, "visibility")
	)
	if not is_member_access(visibility):
		return True
	return is_community_member(user, team_name)


def can_view_space(user, project):
	if is_global_admin(user):
		return True
	project = get_project_info(project)
	if not project:
		return False
	if is_publicly_readable_space(project):
		return True
	if gameplan.is_anonymous(user):
		return False
	if gameplan.is_guest(user):
		return has_guest_access(user, project.name)
	if is_member_access(project.visibility):
		return is_space_member(user, project.name)
	return can_view_community(user, project.team)


def is_publicly_readable_space(project):
	"""Whether someone who is not signed in may read `project` (a get_project_info dict)."""
	return bool(cint(project.is_anonymous_readable)) and public_access_enabled()


def is_publicly_readable_community(team):
	"""Whether someone who is not signed in may read `team`, a doc or a name."""
	return bool(get_doc_name(team)) and public_access_enabled() and is_anonymous_eligible_community(team)


def can_manage_space(user, project):
	from gameplan.community_bans import is_banned

	if gameplan.is_anonymous(user):
		return False
	if is_global_admin(user):
		return True
	if gameplan.is_guest(user):
		# Guests participate in the spaces they are granted: they comment, react, vote and
		# post. They never manage a space: no rename, no settings, no move to another
		# community, no archive, no merge, no member changes. The private-space rule below
		# is not enough on its own, because a guest can hold a GP Member row on a granted
		# space (GPProject.join adds one).
		return False
	project = get_project_info(project)
	if not project or is_banned(project.team, user):
		return False
	if is_member_access(project.visibility):
		return is_space_member(user, project.name)
	return is_community_admin(user, project.team)


def can_moderate_space(user, project):
	if gameplan.is_anonymous(user) or gameplan.is_guest(user):
		return False
	project = get_project_info(project)
	if not project or not can_view_space(user, project.name):
		return False
	if is_global_admin(user):
		return True
	return bool(
		project.team
		and (is_community_admin(user, project.team) or is_community_moderator(user, project.team))
	)


def can_invite_guest(user, project):
	from gameplan.community_bans import is_banned

	info = get_project_info(project)
	if info and is_banned(info.team, user):
		return False
	if gameplan.is_anonymous(user):
		return False
	if gameplan.is_guest(user):
		return False
	return can_manage_space(user, project)


def can_view_content(user, doc):
	if (
		gameplan.is_anonymous(user)
		and doc.doctype == "GP Comment"
		and doc.reference_doctype != "GP Discussion"
	):
		# Tasks are never public, even when their Space is.
		return False
	from gameplan.mixins.moderation import content_is_removed

	project = get_content_project(doc)
	if content_is_removed(doc):
		return bool(project and can_moderate_space(user, project))
	if project:
		return can_view_space(user, project)
	if is_global_admin(user):
		return True
	if gameplan.is_anonymous(user):
		return False
	return get_content_owner(doc) == user


def get_content_owner(doc):
	"""The user that space-less content belongs to. A comment or activity row on a task
	belongs to the task's owner, so it is visible wherever that task is."""
	if doc.doctype in {"GP Comment", "GP Activity"} and doc.reference_doctype == "GP Task":
		return frappe.db.get_value("GP Task", doc.reference_name, "owner")
	return get_doc_value(doc, "owner")


def users_who_can_view_content(users, doc):
	"""The subset of `users` that can_view_content would return True for, order preserved.

	Same rule, resolved with a fixed handful of queries instead of two or three per
	user. For fan-outs over a whole site — an `@everyone` mention, a digest audience —
	the per-user form makes the query count grow with the member list.

	Duplicates in `users` are collapsed (the roles join hands back a user twice when
	they hold both Gameplan roles). Callers wanting to exclude someone — an @everyone
	must not notify its own author — filter before calling: this answers only "who can
	see it".

	Mirrors can_view_space/can_view_community with the membership rows loaded up front;
	keep the two in step.
	"""
	users = list(dict.fromkeys(users))
	project = get_content_project(doc)
	if not project:
		# can_view_content's own space-less fallback, inlined rather than called per
		# user: it would re-resolve the project for every user (a query each, for a
		# GP Comment) and give back exactly this answer.
		owner = get_content_owner(doc)
		return [user for user in users if is_global_admin(user) or user == owner]

	return users_who_can_view_space(users, project)


def users_who_can_view_space(users, project):
	"""The subset of `users` that can_view_space would return True for, order preserved.

	The batched form of can_view_space, for the same reason users_who_can_view_content
	exists: a fixed handful of queries however many users are asked about. Keep it in step
	with can_view_space and can_view_community.
	"""
	users = list(dict.fromkeys(users))
	project_info = get_project_info(project)
	if not project_info:
		return []

	space_members = _member_users("GP Project", project_info.name)
	community_members = _member_users("GP Team", project_info.team) if project_info.team else set()
	guests = _guest_users(project_info.name)
	community_is_member_access = (
		is_member_access(frappe.db.get_value("GP Team", project_info.team, "visibility"))
		if project_info.team
		else False
	)

	publicly_readable = is_publicly_readable_space(project_info)

	def allowed(user):
		if is_global_admin(user):
			return True
		if publicly_readable:
			return True
		if gameplan.is_anonymous(user):
			return False
		if gameplan.is_guest(user):
			return user in guests
		if is_member_access(project_info.visibility):
			return user in space_members
		return not community_is_member_access or user in community_members

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


GUEST_CREATABLE_DOCTYPES = {"GP Discussion", "GP Comment", "GP Poll"}


def can_create_content(user, doc):
	from gameplan.community_bans import content_is_banned

	if content_is_banned(doc, user):
		return False
	if gameplan.is_anonymous(user):
		return False
	if gameplan.is_guest(user):
		# Guests participate in the spaces they can reach: starting a discussion,
		# replying with a comment, and adding a poll to a discussion are all
		# participation. Tasks and pages stay closed to them.
		return doc.doctype in GUEST_CREATABLE_DOCTYPES and can_view_content(user, doc)
	if not get_content_project(doc):
		return is_global_admin(user) or not get_doc_value(doc, "owner") or get_doc_value(doc, "owner") == user
	return can_view_content(user, doc)


# Per-doctype fields that only the content's owner (or a moderator who could delete it)
# may change. Everyone who can reach a space may edit the content in it — see
# can_edit_content — but a poll's ballot and lifecycle are not shared property: stopping
# a poll, rewriting its options, or touching the recorded votes is the author's call.
# GPPoll.stop_poll enforces this for the whitelisted method; the entry below is what
# closes the plain `PUT /api/v2/document/GP Poll/<name>` route, which never reaches it.
OWNER_ONLY_FIELDS = {
	"GP Poll": {"stopped_at", "votes", "options", "total_votes"},
}

# Per-doctype fields that say where content lives, or how a space presents it to everyone.
# A guest may edit what they wrote, but not these fields, not even on their own content.
# Changing them moves a post to another space (or a comment or poll to another thread),
# or pins a post above everyone else's. Those are structural actions, and guests do not
# take structural actions (see can_manage_space). This covers every route that saves the
# document: the move methods, a plain save and frappe.client.set_value.
GUEST_LOCKED_FIELDS = {
	"GP Discussion": {"project", "team", "pinned_at", "pinned_by", "pin_scope"},
	"GP Page": {"project", "team"},
	"GP Task": {"project", "team"},
	"GP Comment": {"reference_doctype", "reference_name"},
	"GP Poll": {"discussion"},
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
	alike) and, for personal/space-less content, the user it belongs to
	(get_content_owner: the author, or for a comment on a personal task, the task's
	owner). This is the floor for the `write` permission; whether a specific *edit* is
	allowed on top of it is decided by can_edit_content and, for non-editors, by whether
	the save changes any field.

	The admin branch never fires from its only caller: can_write_content reaches here
	only once can_edit_content has said False, and a global admin is always an editor.
	It stays because this is a named predicate about who may reach content at all, not a
	private tail of can_write_content: dropping it makes this answer False for a global
	admin on another user's personal page. The owner line at the end does fire from
	there: the owner of a personal task is not an editor of a comment someone else wrote
	on it, but may still react to it.
	"""
	from gameplan.community_bans import content_is_banned

	if content_is_banned(doc, user):
		return False
	if gameplan.is_anonymous(user):
		return False
	if is_global_admin(user):
		return True
	if not can_view_content(user, doc):
		return False
	if get_content_project(doc):
		return True
	# can_view_content has already established this for space-less content. It is the
	# deny-by-default that keeps this answer False if that rule ever loosens.
	return get_content_owner(doc) == user


def can_write_content(user, doc):
	"""Back the doctype `write` permission — "may interact with this document".

	Editors (can_edit_content: global admins, space-viewing members, owners, and
	guests on their OWN content) always hold write. Non-editors who can still reach
	the content (space viewers — guests included — and owners of personal content)
	hold write only for interaction: they may call a participation method such as
	react() or submit_vote(), but they may not save any change to the document.

	This is checked in two contexts (see _fields_changed): on a CLEAN
	doc (the v2 doc-method gate and list/UI permission checks) it reports no changes,
	so a guest passes and can reach react(); on the DIRTY in-memory doc at save time it
	diffs against the DB row and rejects any edit.

	Above all of that sit two field locks that apply even to an editor.
	_owner_only_write_allowed keeps a poll's ballot and lifecycle to its author.
	_guest_locked_fields_unchanged stops a guest from moving or pinning content, their
	own included.
	"""
	from gameplan.community_bans import content_is_banned

	if content_is_banned(doc, user):
		return False
	if gameplan.is_anonymous(user):
		return False
	if not _owner_only_write_allowed(user, doc):
		return False
	if not _guest_locked_fields_unchanged(user, doc):
		return False
	if can_edit_content(user, doc):
		return True
	if not can_interact_with_content(user, doc):
		return False
	return not _fields_changed(doc, {df.fieldname for df in doc.meta.fields})


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


def _guest_locked_fields_unchanged(user, doc):
	"""Whether a guest's pending changes to `doc` keep clear of its GUEST_LOCKED_FIELDS.

	Checked ahead of the editor rule, because a guest is an editor of their own content,
	and that must not let them move it or pin it.
	"""
	fields = GUEST_LOCKED_FIELDS.get(getattr(doc, "doctype", None))
	if not fields or not gameplan.is_guest(user):
		return True
	return not _fields_changed(doc, fields)


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
		elif _comparable(df, doc.get(fieldname)) != _comparable(df, before.get(fieldname)):
			return True
	return False


def _comparable(df, value):
	"""`value` in a form that compares equal to the same value read back from the DB.

	An in-memory document keeps whatever type the caller set. A link to an autoincrement
	doctype is an int until it is saved and read back as a str, and a datetime is a str
	until it is read back as a datetime. Without this, a document the caller just inserted
	reports a link or datetime field as changed on its next save.
	"""
	if value in (None, ""):
		return None
	if df.fieldtype in ("Link", "Dynamic Link"):
		return cstr(value)
	if df.fieldtype in ("Date", "Datetime"):
		return get_datetime(value)
	return value


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

	Enforced at save time by can_write_content and _fields_changed in
	the has_permission write check. Also mirrored in the frontend
	(utils/permissions.ts::canEditContent) to gate edit affordances.
	"""
	from gameplan.community_bans import content_is_banned

	if content_is_banned(doc, user):
		return False
	if gameplan.is_anonymous(user):
		return False
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
	if gameplan.is_anonymous(user):
		return False
	if is_delete_cascade(doc):
		# The parent delete was already authorised, and its children go with it: a
		# discussion owner removing their own thread takes the comments and polls other
		# members posted in it. Re-asking the per-child rule here would let one other
		# member's poll veto the thread owner's delete, and roll the whole thing back.
		return True
	from gameplan.community_bans import content_is_banned

	if content_is_banned(doc, user):
		return False
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
		# Space-less content has no community to moderate it: only its author and the
		# global admin, both handled above. The owner of a personal task reaches this
		# line for a comment someone else wrote on it: they can see the comment, but it
		# is not theirs to delete. The line below would deny too — get_project_info(None)
		# is None — but that rests on an implicit falsy chain, and this is the one
		# function where the rule should be readable.
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
	Discussion = frappe.qb.DocType("GP Discussion")
	return criterion_sql(readable_discussion_criterion(Discussion, user))


def visible_discussion_criterion(Discussion):
	return Discussion.hidden_at.isnull() & Discussion.spam_removed_at.isnull()


def readable_discussion_criterion(Discussion, user=None):
	criterion = visible_discussion_criterion(Discussion)
	access = accessible_project_criterion(Discussion.project, user)
	return criterion & access if access is not None else criterion


def task_query_conditions(user=None, **kwargs):
	return criterion_sql(task_access_criterion(frappe.qb.DocType("GP Task"), user))


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
	return referenced_content_query_conditions("GP Comment", user)


def activity_query_conditions(user=None, **kwargs):
	return referenced_content_query_conditions("GP Activity", user)


def referenced_content_query_conditions(doctype, user=None):
	"""Rows that point at a discussion or task (reference_doctype/reference_name) follow
	that discussion's or task's space, or, for a task with no space, its owner."""
	user = user or frappe.session.user

	Row = frappe.qb.DocType(doctype)
	Task = frappe.qb.DocType("GP Task")
	Discussion = frappe.qb.DocType("GP Discussion")
	discussion_query = (
		frappe.qb.from_(Discussion)
		.select(Discussion.name)
		.where(readable_discussion_criterion(Discussion, user))
	)
	task_query = frappe.qb.from_(Task).select(Task.name)
	if access := task_access_criterion(Task, user):
		task_query = task_query.where(access)
	on_discussion = (Row.reference_doctype == "GP Discussion") & Row.reference_name.isin(discussion_query)
	on_task = (Row.reference_doctype == "GP Task") & Row.reference_name.isin(task_query)
	return criterion_sql(on_discussion if gameplan.is_anonymous(user) else on_discussion | on_task)


def poll_query_conditions(user=None, **kwargs):
	user = user or frappe.session.user

	Poll = frappe.qb.DocType("GP Poll")
	Discussion = frappe.qb.DocType("GP Discussion")
	discussion_query = (
		frappe.qb.from_(Discussion)
		.select(Discussion.name)
		.where(readable_discussion_criterion(Discussion, user))
	)
	# A poll with no discussion never reaches the UI, but it is still someone's row —
	# keep it visible to its owner only, the way a space-less page is.
	criterion = Poll.discussion.isin(discussion_query) | (Poll.discussion.isnull() & (Poll.owner == user))
	Comment = frappe.qb.DocType("GP Comment")
	visible_comments = (
		frappe.qb.from_(Comment)
		.select(Comment.name)
		.where(Comment.hidden_at.isnull() & Comment.spam_removed_at.isnull() & Comment.deleted_at.isnull())
	)
	criterion &= Poll.comment.isnull() | (Poll.comment == "") | Poll.comment.isin(visible_comments)
	return criterion_sql(criterion)


def draft_query_conditions(user=None, **kwargs):
	# Drafts are private to their owner in list/report queries. Share-by-link still works:
	# that reads a single draft by name through the doctype's open `read` permission, which
	# this does not touch — only enumeration (list/report) is scoped. Mirrors GPDraft.get_list
	# (the v2 query path); this closes the v1 frappe.client.get_list path, which does not invoke
	# the controller get_list for non-virtual doctypes and so was returning every user's drafts.
	user = user or frappe.session.user
	if gameplan.is_anonymous(user):
		return criterion_sql(NOTHING)
	Draft = frappe.qb.DocType("GP Draft")
	return criterion_sql(Draft.owner == user)


def bookmark_query_conditions(user=None, **kwargs):
	# A bookmark is a personal row — the same rule as a draft (see draft_query_conditions):
	# only the user it belongs to may enumerate it. Decision 4: deliberately no global-admin exception:
	# nothing in Gameplan reads another user's reading list, and without this every
	# Gameplan user could list everyone's bookmarks through the generic list API.
	user = user or frappe.session.user
	if gameplan.is_anonymous(user):
		return criterion_sql(NOTHING)
	Bookmark = frappe.qb.DocType("GP Bookmark")
	return criterion_sql(Bookmark.user == user)


def bookmark_has_permission(doc, ptype="read", user=None, **kwargs):
	"""A bookmark belongs to exactly one user: only they may read, add or remove it.

	Without this, the doctype's role permissions alone let any Gameplan user read,
	rewrite or delete someone else's bookmark by name — and create one in their name.
	"""
	user = user or frappe.session.user
	if gameplan.is_anonymous(user):
		return False
	if not hasattr(doc, "doctype"):
		return True
	return get_doc_value(doc, "user") == user


def activity_has_permission(doc, ptype="read", user=None, **kwargs):
	"""An activity row is part of a discussion's or task's timeline: whoever can see that
	discussion or task can see it. Rows are written by the server (HasActivity.log_activity)
	and removed with their discussion or task, never edited by hand.
	"""
	user = user or frappe.session.user
	if not hasattr(doc, "doctype"):
		return True
	if ptype in READ_PERMISSIONS:
		return can_view_content(user, doc)
	if ptype == "delete":
		return is_delete_cascade(doc) or is_global_admin(user)
	if ptype in {"create", "write"}:
		return is_global_admin(user)
	return True


def guest_access_query_conditions(user=None, **kwargs):
	user = user or frappe.session.user
	if is_global_admin(user):
		return None
	GuestAccess = frappe.qb.DocType("GP Guest Access")
	criterion = GuestAccess.user == user
	if not gameplan.is_guest(user):
		criterion = (
			criterion
			| GuestAccess.project.isin(managed_project_query(user))
			| GuestAccess.team.isin(community_admin_team_query(user))
		)
	return criterion_sql(criterion)


def guest_access_has_permission(doc, ptype="read", user=None, **kwargs):
	"""A guest's access to a space is visible to the guest and to the people who manage
	that space or its community. Rows are added by accepting an invitation and removed
	through GPProject.remove_guest / GPTeam.remove_guest_access.
	"""
	user = user or frappe.session.user
	if not hasattr(doc, "doctype"):
		return True
	if ptype in READ_PERMISSIONS:
		return get_doc_value(doc, "user") == user or can_manage_guest_access(user, doc)
	if ptype == "delete":
		return is_delete_cascade(doc) or can_manage_guest_access(user, doc)
	if ptype in {"create", "write"}:
		return is_global_admin(user)
	return True


def can_manage_guest_access(user, doc):
	project = get_project_info(get_doc_value(doc, "project"))
	if project:
		return can_manage_space(user, project) or can_manage_community(user, project.team)
	team = get_doc_value(doc, "team")
	return bool(team) and can_manage_community(user, team)


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
	public = public_team_criterion(Team) if public_access_enabled() else NOTHING
	if gameplan.is_anonymous(user):
		return public
	if gameplan.is_guest(user):
		# A guest sees exactly the communities that hold a space they've been granted
		# guest access to (via GP Guest Access), and any community open to the public.
		# Without the first, the guest's GP Team list is empty and the SPA 404s every
		# community/space/discussion route.
		return Team.name.isin(guest_accessible_team_query(user)) | public
	return Team.visibility.isin(SIGNED_IN_TIERS) | is_member_parent("GP Team", Team.name, user)


def project_access_criterion(Project, user=None):
	user = user or frappe.session.user
	if is_global_admin(user):
		return None
	public = (Project.is_anonymous_readable == 1) if public_access_enabled() else NOTHING
	if gameplan.is_anonymous(user):
		return public
	if gameplan.is_guest(user):
		GuestAccess = frappe.qb.DocType("GP Guest Access")
		return (
			Project.name.isin(
				frappe.qb.from_(GuestAccess).select(GuestAccess.project).where(GuestAccess.user == user)
			)
			| public
		)
	return (
		Project.visibility.isin(SIGNED_IN_TIERS) & Project.team.isin(accessible_team_query(user))
	) | is_member_parent("GP Project", Project.name, user)


def accessible_project_criterion(project_field, user=None):
	user = user or frappe.session.user
	if is_global_admin(user):
		return None
	return project_field.isin(accessible_project_query(user))


def task_access_criterion(Task, user=None):
	"""The tasks `user` may see, as can_view_content decides. A task in a Space follows
	the Space. A task with no Space is personal, so only its owner sees it. None for a
	global admin, who sees every task."""
	user = user or frappe.session.user
	criterion = accessible_project_criterion(Task.project, user)
	if criterion is None:
		return None
	space_less = Task.project.isnull() | (Task.project == "")
	return criterion | (space_less & (Task.owner == user))


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


def managed_project_query(user):
	"""Spaces a non-guest `user` manages: the SQL form of can_manage_space / can_manage_community."""
	Project = frappe.qb.DocType("GP Project")
	return (
		frappe.qb.from_(Project)
		.select(Project.name)
		.where(
			Project.team.isin(community_admin_team_query(user))
			| ((Project.visibility == "Member Access") & is_member_parent("GP Project", Project.name, user))
		)
	)


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


def community_admin_team_query(user):
	Member = frappe.qb.DocType("GP Member")
	return (
		frappe.qb.from_(Member)
		.select(Member.parent)
		.where(Member.parenttype == "GP Team")
		.where(Member.user == user)
		.where(Member.is_admin == 1)
	)


def is_community_moderator(user, team):
	return bool(
		frappe.db.exists(
			"GP Member",
			{"parenttype": "GP Team", "parent": team, "user": user, "is_moderator": 1},
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
	if doc.doctype not in {"GP Comment", "GP Activity"}:
		return None
	if doc.reference_doctype in {"GP Discussion", "GP Task"}:
		return frappe.db.get_value(doc.reference_doctype, doc.reference_name, "project")
	return None


def get_project_info(project):
	if hasattr(project, "doctype"):
		return frappe._dict(
			name=project.name,
			team=project.team,
			visibility=project.visibility,
			is_anonymous_readable=project.is_anonymous_readable,
		)
	if not project:
		return None
	return frappe.db.get_value(
		"GP Project", project, ["name", "team", "visibility", "is_anonymous_readable"], as_dict=True
	)


def get_doc_name(doc_or_name):
	return doc_or_name.name if hasattr(doc_or_name, "doctype") else doc_or_name


def get_doc_value(doc, fieldname):
	if hasattr(doc, "doctype"):
		return doc.get(fieldname)
	return None
