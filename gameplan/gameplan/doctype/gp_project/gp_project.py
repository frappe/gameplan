# Copyright (c) 2022, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

from urllib.parse import urljoin

import frappe
import requests
from bs4 import BeautifulSoup
from frappe.model.document import Document

from gameplan.api import _invite_by_email
from gameplan.gameplan.doctype.gp_unread_record.gp_unread_record import GPUnreadRecord
from gameplan.mixins.archivable import Archivable
from gameplan.mixins.manage_members import ManageMembersMixin
from gameplan.permissions import (
	apply_accessible_project_filter,
	apply_project_query_filter,
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

	def as_dict(self, *args, **kwargs) -> dict:
		d = super().as_dict(*args, **kwargs)
		return d

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

	@frappe.whitelist()
	def move_to_team(self, team=None):
		if self.team == team:
			return
		self.team = team
		self.save()
		self.update_project_team_references()

	def update_project_team_references(self):
		for doctype in PROJECT_TEAM_DOCTYPES:
			update_project_team_reference(doctype, self.name, self.team)

	@frappe.whitelist()
	def merge_with_project(self, project=None):
		if not project or self.name == project:
			return
		if isinstance(project, str):
			project = int(project)
		if not frappe.db.exists("GP Project", project):
			frappe.throw(f'Invalid Project "{project}"')
		return self.rename(project, merge=True, validate_rename=False, force=True)

	@frappe.whitelist()
	def invite_guest(self, email):
		require_can_invite_guest(self)
		# Trusted path: a space member invites a guest to this space. The role is
		# hardcoded (non-escalating), so it bypasses invite_by_email's admin gate.
		_invite_by_email(email, role="Gameplan Guest", projects=[self.name])

	@frappe.whitelist()
	def remove_guest(self, email):
		require_can_invite_guest(self)
		name = frappe.db.get_value("GP Guest Access", {"project": self.name, "user": email})
		if name:
			frappe.delete_doc("GP Guest Access", name)

	@frappe.whitelist(methods=["POST"])
	def track_visit(self):
		if frappe.flags.read_only:
			return
		self.require_view_access()

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

	@property
	def is_followed(self):
		return bool(
			frappe.db.exists("GP Followed Project", {"project": self.name, "user": frappe.session.user})
		)

	@frappe.whitelist(methods=["POST"])
	def follow(self):
		self.require_view_access()
		if not self.is_followed:
			frappe.get_doc(doctype="GP Followed Project", project=self.name).insert(ignore_permissions=True)

	@frappe.whitelist(methods=["POST"])
	def unfollow(self):
		follow_id = frappe.db.get_value(
			"GP Followed Project", {"project": self.name, "user": frappe.session.user}
		)
		if follow_id:
			frappe.delete_doc("GP Followed Project", follow_id, ignore_permissions=True)

	@frappe.whitelist()
	def add_member(self, user):
		require_can_manage_space_members(self)
		self.add_member_row(user)

	@frappe.whitelist()
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
		user = frappe.session.user
		for member in self.members:
			if member.user == user:
				self.remove(member)
				self.save(ignore_permissions=True)
				break

	@frappe.whitelist()
	def archive(self):
		super().archive()
		# delete pinned projects
		for pin in frappe.db.get_all(
			"GP Pinned Project", filters={"project": self.name, "user": frappe.session.user}, pluck="name"
		):
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


def get_meta_tags(url):
	response = requests.get(url, timeout=2, allow_redirects=True)
	soup = BeautifulSoup(response.text, "html.parser")
	title = soup.find("title").text.strip()

	image = None
	favicon = soup.find("link", rel="icon")
	if favicon:
		image = favicon["href"]

	if image and image.startswith("/"):
		image = urljoin(url, image)

	return {"title": title, "image": image}


@frappe.whitelist()
def get_joined_spaces():
	user = frappe.session.user
	projects = frappe.qb.get_query(
		"GP Project",
		filters={"members.user": user},
		fields=["name"],
	).run(as_dict=True, pluck="name")
	guest_access_projects = frappe.qb.get_query(
		"GP Guest Access", filters={"user": user}, fields=["project"]
	).run(as_dict=True, pluck="project")

	return list(map(str, set(projects + guest_access_projects)))


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
def join_spaces(spaces: list[str] = None):
	if not spaces:
		return
	for space in spaces:
		frappe.get_doc("GP Project", space).join()


@frappe.whitelist(methods=["POST"])
def leave_spaces(spaces: list[str] = None):
	if not spaces:
		return
	for space in spaces:
		frappe.get_doc("GP Project", space).leave()


@frappe.whitelist(methods=["POST"])
def track_visits(spaces: list[str] = None):
	if not spaces:
		return
	for space in spaces:
		frappe.get_doc("GP Project", space).track_visit()


@frappe.whitelist(methods=["POST"])
def follow_spaces(spaces: list[str] = None):
	if not spaces:
		return
	for space in spaces:
		frappe.get_doc("GP Project", space).follow()


@frappe.whitelist(methods=["POST"])
def unfollow_spaces(spaces: list[str] = None):
	if not spaces:
		return
	for space in spaces:
		frappe.get_doc("GP Project", space).unfollow()


@frappe.whitelist(methods=["POST"])
def mark_all_as_read(spaces: list[str] = None):
	"""Mark all unread discussions as read for multiple spaces at once."""
	if not spaces:
		return
	for space in spaces:
		frappe.get_doc("GP Project", space).mark_all_as_read()


@frappe.whitelist()
def get_unread_count():
	from frappe.query_builder.functions import Count, Sum

	user = frappe.session.user
	joined_projects = get_joined_spaces()

	if not joined_projects:
		return {}

	gd = frappe.qb.DocType("GP Discussion").as_("gd")
	gdv = frappe.qb.DocType("GP Discussion Visit").as_("gdv")
	gpv = frappe.qb.DocType("GP Project Visit").as_("gpv")

	# Case 1: Projects with mark_all_read_at timestamp
	# Check if discussion's last_post_at is after the project's mark_all_read_at
	query1 = (
		frappe.qb.from_(gd)
		.select(gd.project, Count(gd.name).as_("unread_count"))
		.inner_join(gpv)
		.on((gd.project == gpv.project) & (gpv.user == user) & gpv.mark_all_read_at.isnotnull())
		.where(gd.last_post_at > gpv.mark_all_read_at)
		.groupby(gd.project)
	)

	# Case 2: Projects without mark_all_read_at (or NULL)
	# Fall back to individual discussion visit tracking
	query2 = (
		frappe.qb.from_(gd)
		.select(gd.project, Count(gd.name).as_("unread_count"))
		.left_join(gpv)
		.on((gd.project == gpv.project) & (gpv.user == user))
		.left_join(gdv)
		.on((gd.name == gdv.discussion) & (gdv.user == user))
		.where(
			(gpv.name.isnull() | gpv.mark_all_read_at.isnull())
			& (gdv.name.isnull() | (gd.last_post_at > gdv.last_visit))
		)
		.groupby(gd.project)
	)

	# Combine both queries using pypika's UNION operator
	union_query = query1 + query2

	# Create outer query to sum the unread counts per project
	combined = union_query.as_("combined")

	final_query = (
		frappe.qb.from_(combined)
		.select(combined.project, Sum(combined.unread_count).as_("unread_count"))
		.groupby(combined.project)
	)

	result = final_query.run(as_dict=True)
	unread_counts_dict = {row["project"]: row["unread_count"] for row in result}

	return unread_counts_dict
