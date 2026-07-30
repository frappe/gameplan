# Copyright (c) 2022, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint

import gameplan
from gameplan.api import _invite_by_email
from gameplan.gameplan.doctype.gp_unread_record.gp_unread_record import GPUnreadRecord
from gameplan.mixins.archivable import Archivable
from gameplan.mixins.manage_members import ManageMembersMixin
from gameplan.permissions import (
	apply_accessible_project_filter,
	apply_project_query_filter,
	can_manage_space,
	can_view_space,
	require_can_invite_guest,
	require_can_manage_space_members,
)

DEFAULT_SPACE_ICON = "lucide-hash"
PROJECT_TEAM_DOCTYPES = [
	"GP Discussion",
	"GP Draft",
	"GP Followed Project",
	"GP Guest Access",
	"GP Notification",
	"GP Page",
	"GP Pinned Project",
	"GP Project Visit",
	"GP Task",
]


class GPProject(ManageMembersMixin, Archivable, Document):
	on_delete_cascade = [
		"GP Task",
		"GP Discussion",
		"GP Project Visit",
		"GP Followed Project",
		"GP Page",
		"GP Pinned Project",
	]
	on_delete_set_null = ["GP Notification"]

	@staticmethod
	def get_list_query(query):
		return apply_project_query_filter(query)

	def before_validate(self):
		if not self.icon or not self.icon.startswith("lucide-"):
			self.icon = DEFAULT_SPACE_ICON

	def before_insert(self):
		self.append("members", {"user": frappe.session.user})

	def on_trash(self):
		GPUnreadRecord.delete_unread_records_for_project(self.name)

	def update_discussions_count(self):
		total_discussions = frappe.db.count("GP Discussion", filters={"project": self.name})
		self.db_set("discussions_count", total_discussions)

	def update_tasks_count(self):
		total_tasks = frappe.db.count("GP Task", filters={"project": self.name})
		self.db_set("tasks_count", total_tasks)

	@frappe.whitelist(methods=["POST"])
	def move_to_team(self, team=None):
		if self.team == team:
			return
		self.team = team
		self.save()
		self.update_project_team_references()

	def update_project_team_references(self):
		for doctype in PROJECT_TEAM_DOCTYPES:
			update_project_team_reference(doctype, self.name, self.team)

	@frappe.whitelist(methods=["POST"])
	def merge_with_project(self, project=None):
		if not project:
			return
		# Coerce BEFORE comparing. GP Project autoincrements, so self.name is an int, while
		# MergeSpaceDialog sends the target as a string: comparing first sees "7" != 7, the
		# self-merge guard falls through, and the rename below deletes this Space and leaves
		# every discussion in it pointing at nothing.
		target = cint(project)
		if target == cint(self.name):
			return
		self.require_can_manage_merge(target)
		if not frappe.db.exists("GP Project", target):
			frappe.throw(f'Invalid Project "{project}"')
		# validate_rename stays off: this doctype autoincrements, and validate_rename runs
		# the new name through validate_name, which for an autoincrement doctype rewinds the
		# table's sequence to the merge target's id — every subsequent insert would then
		# collide with an existing row. Turning it off drops FIVE guards, not just that one,
		# so each is re-established above: source-exists (this is a loaded doc), old != new,
		# target-exists, and write permission on both source and target. The only one not
		# reproduced is validate_rename's `SELECT ... FOR UPDATE` lock on the target row,
		# which frappe does not expose separately.
		#
		# `force` is deliberately not passed with it: rename_doc reads force only inside
		# the `if validate:` block it hands to validate_rename, so with validate off the
		# argument reaches nothing.
		return self.rename(target, merge=True, validate_rename=False)

	def require_can_manage_merge(self, target):
		"""A merge empties this Space into `target`, so it needs manage rights on both.

		The v2 method route only checks write on the document the method is called on,
		and the rename it guards skips frappe's own "write permission on the merge target"
		check along with the rest of validate_rename — leaving the target ungated.

		Runs BEFORE the target-exists check: `frappe.db.exists` answers for every Space on
		the site, so rejecting an unknown id with a different error than a forbidden one
		would let any Space manager enumerate GP Project ids, private Spaces included.
		"""
		user = frappe.session.user
		# Guests hold GP Member rows on the private Spaces they're granted, which is enough
		# for can_manage_space — same reason can_invite_guest rules them out up front. Guest
		# access is read-and-participate; a merge destroys a Space.
		if gameplan.is_guest(user):
			frappe.throw(_("Only space managers can merge spaces"), frappe.PermissionError)
		for space in (self, target):
			if not can_manage_space(user, space):
				frappe.throw(_("Only space managers can merge spaces"), frappe.PermissionError)

	@frappe.whitelist(methods=["POST"])
	def invite_guest(self, email):
		require_can_invite_guest(self)
		# Trusted path: a space member invites a guest to this space. The role is
		# hardcoded (non-escalating), so it bypasses invite_by_email's admin gate.
		_invite_by_email(email, role="Gameplan Guest", projects=[self.name])

	@frappe.whitelist(methods=["POST"])
	def remove_guest(self, email):
		require_can_invite_guest(self)
		name = frappe.db.get_value("GP Guest Access", {"project": self.name, "user": email})
		if name:
			frappe.delete_doc("GP Guest Access", name)

	@frappe.whitelist(methods=["POST"])
	def track_visit(self):
		self.require_view_access()
		if frappe.flags.read_only:
			return

		values = {"user": frappe.session.user, "project": self.name}
		existing = frappe.db.get_value("GP Project Visit", values)
		if existing:
			visit = frappe.get_doc("GP Project Visit", existing)
			visit.last_visit = frappe.utils.now()
			visit.save(ignore_permissions=True)
		else:
			visit = frappe.get_doc(doctype="GP Project Visit")
			visit.update(values)
			visit.last_visit = frappe.utils.now()
			visit.insert(ignore_permissions=True)

	@frappe.whitelist(methods=["POST"])
	def add_member(self, user):
		require_can_manage_space_members(self)
		self.add_member_row(user)

	@frappe.whitelist(methods=["POST"])
	def remove_member(self, user):
		require_can_manage_space_members(self)
		for member in self.members:
			if member.user == user:
				self.remove(member)
				self.save(ignore_permissions=True)
				break

	@frappe.whitelist(methods=["POST"])
	def join(self):
		self.require_view_access()
		self.add_member_row(frappe.session.user)

	def require_view_access(self):
		if not can_view_space(frappe.session.user, self):
			frappe.throw("Not permitted", frappe.PermissionError)

	def add_member_row(self, user):
		if user not in [d.user for d in self.members]:
			self.append("members", {"user": user})
			self.save(ignore_permissions=True)

	@frappe.whitelist(methods=["POST"])
	def leave(self):
		self.require_view_access()
		user = frappe.session.user
		for member in self.members:
			if member.user == user:
				self.remove(member)
				self.save(ignore_permissions=True)
				break

	@frappe.whitelist(methods=["POST"])
	def archive(self):
		super().archive()
		# Everyone's pin, not just the archiver's. Archiving retires the Space for the
		# whole site, so a pin left on another user's sidebar points at something they
		# cannot open. The patch
		# gp_pinned_project/patches/delete_pinned_projects_for_archived_spaces.py exists
		# only to clear that state out, and a session-scoped delete regenerates its
		# precondition on every archive.
		pins = frappe.qb.get_query(
			"GP Pinned Project",
			filters={"project": self.name},
			fields=["name"],
			ignore_permissions=True,
		).run(pluck="name")
		for pin in pins:
			frappe.delete_doc("GP Pinned Project", pin, ignore_permissions=True)

	@frappe.whitelist(methods=["POST"])
	def mark_all_as_read(self):
		"""Mark all discussions as read using a project-level timestamp."""
		self.require_view_access()
		user = frappe.session.user
		project_name = self.name
		now = frappe.utils.now()

		# new unread record system
		GPUnreadRecord.mark_all_as_read_for_project(self.name, frappe.session.user)

		project_visit_name = frappe.db.get_value("GP Project Visit", {"user": user, "project": project_name})
		if project_visit_name:
			project_visit_doc = frappe.get_doc("GP Project Visit", project_visit_name)
			project_visit_doc.set("mark_all_read_at", now)
			project_visit_doc.last_visit = now
			project_visit_doc.save(ignore_permissions=True)
		else:
			project_visit_doc = frappe.new_doc("GP Project Visit")
			project_visit_doc.user = user
			project_visit_doc.project = project_name
			project_visit_doc.last_visit = now
			project_visit_doc.set("mark_all_read_at", now)
			project_visit_doc.insert(ignore_permissions=True)


@frappe.whitelist()
def get_joined_spaces():
	"""Every Space the user is in, whether as a member or as an invited guest.

	Both sources are normalised to `str` as they are read: GP Project autoincrements,
	so a membership row yields the name as an int while the guest grant stores the
	same name in a link column as a str. Left mixed, they dedupe against nothing and
	a Space held both ways is reported twice.
	"""
	user = frappe.session.user
	member_spaces = [
		str(name)
		for name in frappe.qb.get_query(
			"GP Project",
			filters={"members.user": user},
			fields=["name"],
		).run(pluck="name")
	]
	guest_spaces = [
		str(project)
		for project in frappe.qb.get_query("GP Guest Access", filters={"user": user}, fields=["project"]).run(
			pluck="project"
		)
	]

	# dict.fromkeys, not set: the order has to be stable so callers (and the sidebar)
	# see the same list twice in a row.
	return list(dict.fromkeys(member_spaces + guest_spaces))


@frappe.whitelist()
def get_activity():
	from frappe.query_builder.functions import Max

	activity_by_project = {}
	for doctype, timestamp_field in [
		("GP Discussion", "last_post_at"),
		("GP Task", "modified"),
		("GP Page", "modified"),
	]:
		DocType = frappe.qb.DocType(doctype)
		project = DocType.project
		timestamp = getattr(DocType, timestamp_field)
		query = (
			frappe.qb.from_(DocType)
			.select(project, Max(timestamp).as_("last_activity_at"))
			.where(project.isnotnull())
			.groupby(project)
		)
		query = apply_accessible_project_filter(query, project)

		for row in query.run(as_dict=True):
			project_name = str(row.project)
			last_activity_at = row.last_activity_at
			current_activity_at = activity_by_project.get(project_name, "")
			if last_activity_at and str(last_activity_at) > str(current_activity_at):
				activity_by_project[project_name] = last_activity_at

	return activity_by_project


def update_project_team_reference(doctype: str, project: str, team: str | None):
	DocType = frappe.qb.DocType(doctype)
	(frappe.qb.update(DocType).set(DocType.team, team).where(DocType.project == str(project))).run()


@frappe.whitelist(methods=["POST"])
def join_spaces(spaces: list[str | int] = None):
	if not spaces:
		return
	for space in spaces:
		frappe.get_doc("GP Project", str(space)).join()


@frappe.whitelist(methods=["POST"])
def leave_spaces(spaces: list[str | int] = None):
	if not spaces:
		return
	for space in spaces:
		frappe.get_doc("GP Project", str(space)).leave()


@frappe.whitelist(methods=["POST"])
def track_visits(spaces: list[str | int] = None):
	if not spaces:
		return
	for space in spaces:
		frappe.get_doc("GP Project", str(space)).track_visit()


@frappe.whitelist(methods=["POST"])
def track_visit(space: str | int):
	frappe.get_doc("GP Project", str(space)).track_visit()


@frappe.whitelist(methods=["POST"])
def mark_all_as_read(spaces: list[str | int] = None):
	"""Mark all unread discussions as read for multiple spaces at once."""
	if not spaces:
		return
	for space in spaces:
		frappe.get_doc("GP Project", str(space)).mark_all_as_read()


@frappe.whitelist()
def get_unread_count():
	from frappe.query_builder.functions import Count

	user = frappe.session.user
	# Scopes the count below — without it the query answered for every Space on the site,
	# so anyone in at least one Space was handed unread counts for private Spaces they
	# cannot open. The empty case has to short-circuit: `IN ()` is not valid SQL.
	joined_projects = get_joined_spaces()

	if not joined_projects:
		return {}

	gd = frappe.qb.DocType("GP Discussion").as_("gd")
	gdv = frappe.qb.DocType("GP Discussion Visit").as_("gdv")
	gpv = frappe.qb.DocType("GP Project Visit").as_("gpv")

	# A Space is read-tracked one of two ways: by its own "mark all read" timestamp once
	# it has one, and by per-discussion visits until then.
	marked_read = gpv.mark_all_read_at.isnotnull() & (gd.last_post_at > gpv.mark_all_read_at)
	never_marked_read = (gpv.name.isnull() | gpv.mark_all_read_at.isnull()) & (
		gdv.name.isnull() | (gd.last_post_at > gdv.last_visit)
	)

	# One OR'd predicate over a single pair of joins rather than a UNION of the two cases:
	# frappe's SQLite query builder (frappe/query_builder/builder.py::SQLite) leaves
	# pypika's wrap_set_operation_queries at its default True, so a set operation renders
	# with each term in parentheses and SQLite rejects the compound SELECT outright
	# ("near UNION: syntax error").
	#
	# COUNT is DISTINCT because the two predicates are exclusive per JOINED ROW, not per
	# discussion: GP Project Visit has no unique constraint on (user, project) and
	# track_visit is a get-then-insert, so a Space can carry two visit rows for one user —
	# one with mark_all_read_at, one without — and each discussion then satisfies both
	# branches on different rows. The UNION this replaced deduped for the same reason.
	query = (
		frappe.qb.from_(gd)
		.select(gd.project, Count(gd.name).distinct().as_("unread_count"))
		.left_join(gpv)
		.on((gd.project == gpv.project) & (gpv.user == user))
		.left_join(gdv)
		.on((gd.name == gdv.discussion) & (gdv.user == user))
		.where(gd.project.isin(joined_projects))
		.where(marked_read | never_marked_read)
		.groupby(gd.project)
	)

	return {row["project"]: row["unread_count"] for row in query.run(as_dict=True)}
