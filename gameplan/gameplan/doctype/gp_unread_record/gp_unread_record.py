# Copyright (c) 2025, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

from datetime import timedelta

import frappe
from frappe.model.document import Document, bulk_insert

from gameplan.permissions import get_audience_roles, users_who_can_view_space
from gameplan.realtime import notify_unread_counts_changed
from gameplan.visibility import is_member_access

# Above this many users, creating the records runs in a background job.
LARGE_AUDIENCE = 1_000
BULK_CHUNK = 5_000


def next_ids(doctype, count):
	"""Reserve `count` ids of an autoincrement doctype, in one query where the database allows."""
	if frappe.db.db_type == "mariadb":
		sequence = frappe.scrub(doctype) + "_id_seq"
		return [row[0] for row in frappe.db.sql(f"select nextval(`{sequence}`) from seq_1_to_{int(count)}")]
	return [frappe.db.get_next_sequence_val(doctype) for _ in range(count)]


def create_unread_records(discussion, project, author, comment=None):
	"""Create the unread records of a new discussion or reply, and tell the users they have news."""
	if not frappe.db.exists("GP Discussion", discussion):
		return
	users = [user for user in GPUnreadRecord._get_project_members(project) if user != author]
	GPUnreadRecord._insert_unread_records(users, discussion, project, comment)
	notify_unread_counts_changed(users)


class GPUnreadRecord(Document):
	@staticmethod
	def create_unread_records_for_discussion(discussion_doc):
		"""Create unread records for all project members when discussion is created"""
		if frappe.flags.in_migrate or frappe.flags.in_patch:
			return

		GPUnreadRecord._fan_out(discussion_doc.name, discussion_doc.project, discussion_doc.owner)

	@staticmethod
	def create_unread_records_for_comment(comment_doc):
		"""Create unread records for all project members when comment is created"""
		if frappe.flags.in_migrate or frappe.flags.in_patch:
			return

		if comment_doc.reference_doctype != "GP Discussion":
			return

		project = frappe.db.get_value("GP Discussion", comment_doc.reference_name, "project")
		GPUnreadRecord._fan_out(comment_doc.reference_name, project, comment_doc.owner, comment_doc.name)

	@staticmethod
	def _fan_out(discussion, project, author, comment=None):
		"""Create the records now for a small audience, or in a background job for a large one.

		A Space everyone can see has one record per enabled user: 100,000 rows and as many
		realtime events for a single reply, which kept the request busy for minutes."""
		frappe.enqueue(
			"gameplan.gameplan.doctype.gp_unread_record.gp_unread_record.create_unread_records",
			queue="long",
			enqueue_after_commit=True,
			now=frappe.in_test or GPUnreadRecord._audience_size(project) <= LARGE_AUDIENCE,
			discussion=str(discussion),
			project=str(project),
			author=author,
			comment=str(comment) if comment else None,
		)

	@staticmethod
	def _audience_size(project):
		"""A cheap upper bound of how many users get a record, without resolving who they are."""
		visibility = frappe.db.get_value("GP Project", project, "visibility")
		if is_member_access(visibility):
			return frappe.db.count("GP Member", {"parent": project, "parenttype": "GP Project"})
		return frappe.db.count("GP User Profile", {"enabled": 1})

	@staticmethod
	def _insert_unread_records(users, discussion, project, comment=None):
		"""Insert one record per user in chunks, with one query for each chunk's ids."""
		fields = [
			"name",
			"owner",
			"creation",
			"modified",
			"modified_by",
			"docstatus",
			"idx",
			"user",
			"discussion",
			"project",
			"comment",
			"is_unread",
		]
		now, owner = frappe.utils.now(), frappe.session.user
		for start in range(0, len(users), BULK_CHUNK):
			chunk = users[start : start + BULK_CHUNK]
			ids = next_ids("GP Unread Record", len(chunk))
			frappe.db.bulk_insert(
				"GP Unread Record",
				fields,
				[
					(ids[i], owner, now, now, owner, 0, 0, user, discussion, project, comment, 1)
					for i, user in enumerate(chunk)
				],
				ignore_duplicates=True,
				chunk_size=BULK_CHUNK,
			)

	@staticmethod
	def delete_unread_records_for_discussion(discussion: str):
		"""Delete unread records for the discussion"""
		if frappe.flags.in_migrate or frappe.flags.in_patch:
			return

		UnreadRecord = frappe.qb.DocType("GP Unread Record")
		frappe.qb.from_("GP Unread Record").where(UnreadRecord.discussion == str(discussion)).delete().run()

	@staticmethod
	def delete_unread_records_for_comment(comment: str):
		"""Delete unread records for a specific comment"""
		if frappe.flags.in_migrate or frappe.flags.in_patch:
			return

		UnreadRecord = frappe.qb.DocType("GP Unread Record")
		frappe.qb.from_("GP Unread Record").where(UnreadRecord.comment == str(comment)).delete().run()

	@staticmethod
	def delete_unread_records_for_project(project: str):
		"""Delete unread records for a specific project"""
		if frappe.flags.in_migrate or frappe.flags.in_patch:
			return

		UnreadRecord = frappe.qb.DocType("GP Unread Record")
		frappe.qb.from_(UnreadRecord).where(UnreadRecord.project == str(project)).delete().run()

	@staticmethod
	def update_project_for_discussion(discussion: str, project: str):
		"""Keep a discussion's unread records pointing at its current space.

		Moving a discussion changes its `project`, but the unread records keep the old one.
		The unread count groups by the record's project and `mark_all_as_read_for_team`
		clears by it, so a stale project misattributes the count to the old space and can
		leave it uncleared (e.g. when the old space is archived or inaccessible).
		"""
		if frappe.flags.in_migrate or frappe.flags.in_patch:
			return

		UnreadRecord = frappe.qb.DocType("GP Unread Record")
		(
			frappe.qb.update(UnreadRecord)
			.set(UnreadRecord.project, str(project))
			.where((UnreadRecord.discussion == str(discussion)) & (UnreadRecord.project != str(project)))
		).run()

	@staticmethod
	def mark_discussion_as_read_for_user(discussion, user):
		"""Mark all unread records for this discussion and user as read"""
		UnreadRecord = frappe.qb.DocType("GP Unread Record")
		query = (
			frappe.qb.update(UnreadRecord)
			.set(UnreadRecord.is_unread, 0)
			.where(
				(UnreadRecord.user == user)
				& (UnreadRecord.discussion == discussion)
				& (UnreadRecord.is_unread == 1)
			)
		)
		result = query.run(as_dict=1)
		GPUnreadRecord._notify_unread_counts_changed(user)
		return result

	@staticmethod
	def mark_discussion_as_unread_for_user(discussion, user):
		"""Mark a discussion unread for a user by restoring the discussion-level unread record."""
		discussion_level_record = frappe.db.get_value(
			"GP Unread Record",
			{
				"user": user,
				"discussion": discussion,
				"comment": ["is", "not set"],
			},
			"name",
		)

		if discussion_level_record:
			frappe.db.set_value(
				"GP Unread Record", discussion_level_record, "is_unread", 1, update_modified=False
			)
			GPUnreadRecord._notify_unread_counts_changed(user)
			return discussion_level_record

		project = frappe.db.get_value("GP Discussion", discussion, "project")
		if not project:
			return

		name = (
			frappe.get_doc(
				{
					"doctype": "GP Unread Record",
					"user": user,
					"discussion": discussion,
					"project": project,
					"comment": None,
					"is_unread": 1,
				}
			)
			.insert(ignore_permissions=True)
			.name
		)
		GPUnreadRecord._notify_unread_counts_changed(user)
		return name

	@staticmethod
	def mark_all_as_read_for_project(project, user):
		"""Mark all discussions in project as read for user"""

		UnreadRecord = frappe.qb.DocType("GP Unread Record")
		query = (
			frappe.qb.update(UnreadRecord)
			.set(UnreadRecord.is_unread, 0)
			.where(
				(UnreadRecord.user == user)
				& (UnreadRecord.project == project)
				& (UnreadRecord.is_unread == 1)
			)
		)
		result = query.run(as_dict=1)
		GPUnreadRecord._notify_unread_counts_changed(user)
		return result

	@staticmethod
	def mark_all_as_read_for_team(team, user, before=None):
		projects = GPUnreadRecord.get_accessible_project_names_for_team(team, user)
		if not projects:
			return []

		# `before` (a date) marks only discussions last active up to and including that
		# day; `cutoff` is the exclusive upper bound (start of the next day).
		cutoff = frappe.utils.add_days(before, 1) if before else None

		UnreadRecord = frappe.qb.DocType("GP Unread Record")
		condition = (
			(UnreadRecord.user == user)
			& (UnreadRecord.project.isin(projects))
			& (UnreadRecord.is_unread == 1)
		)
		if cutoff:
			Discussion = frappe.qb.DocType("GP Discussion")
			# `last_post_at` is always set: `before_insert` defaults it to the creation time and the
			# `backfill_null_last_post_at` patch repaired legacy NULL rows, so a plain `< cutoff` is
			# safe and no longer drops NULLs.
			# Repeat the project filter here so the subquery can use the (project, last_post_at)
			# index range scan instead of full-scanning every discussion across all communities.
			discussions_within_cutoff = (
				frappe.qb.from_(Discussion)
				.select(Discussion.name)
				.where(Discussion.project.isin(projects) & (Discussion.last_post_at < cutoff))
			)
			condition &= UnreadRecord.discussion.isin(discussions_within_cutoff)

		(frappe.qb.update(UnreadRecord).set(UnreadRecord.is_unread, 0).where(condition)).run()

		GPUnreadRecord.update_project_visits_for_mark_all_read(projects, user, cutoff)
		GPUnreadRecord._notify_unread_counts_changed(user)
		return projects

	@staticmethod
	def get_accessible_project_names_for_team(team, user):
		from gameplan.permissions import apply_project_query_filter

		Project = frappe.qb.DocType("GP Project")
		query = (
			frappe.qb.from_(Project)
			.select(Project.name)
			.where((Project.team == team) & Project.archived_at.isnull())
		)
		query = apply_project_query_filter(query, user)
		return [str(row.name) for row in query.run(as_dict=True)]

	@staticmethod
	def update_project_visits_for_mark_all_read(projects: list[str], user, cutoff=None):
		# `last_visit` reflects that the user acted now (it orders recent spaces), while the
		# read watermark drives the per-discussion read indicator (last_post_at > watermark
		# means unread). `cutoff` aligns the watermark with a "before date" action; without
		# one we mark everything read up to now.
		now = frappe.utils.now()
		# The unread query reads `last_post_at < cutoff`; the watermark check reads
		# `last_post_at > mark_all_read_at`. Store the inclusive supremum (cutoff minus one
		# microsecond) so both agree exactly — no post at the midnight boundary is read by
		# one system and unread by the other.
		read_at = str(frappe.utils.get_datetime(cutoff) - timedelta(microseconds=1)) if cutoff else now
		existing_visits = GPUnreadRecord.get_project_visit_names(projects, user)

		if existing_visits:
			GPUnreadRecord.update_existing_project_visits(list(existing_visits.values()), now, read_at)

		missing_projects = [project for project in projects if project not in existing_visits]
		if missing_projects:
			# Project access is already scoped by get_accessible_project_names_for_team;
			# these visit rows are system-managed on behalf of the authenticated user.
			GPUnreadRecord.create_project_visits(missing_projects, user, now, read_at)

	@staticmethod
	def get_project_visit_names(projects: list[str], user):
		if not projects:
			return {}

		return {
			row.project: row.name
			for row in frappe.qb.get_query(
				"GP Project Visit",
				fields=["name", "project"],
				filters={"user": user, "project": ["in", projects]},
			).run(as_dict=True)
		}

	@staticmethod
	def update_existing_project_visits(project_visit_names: list[str], last_visit, mark_all_read_at):
		from frappe.query_builder import Case
		from frappe.query_builder.functions import Coalesce

		ProjectVisit = frappe.qb.DocType("GP Project Visit")
		current = Coalesce(ProjectVisit.mark_all_read_at, mark_all_read_at)
		# Only ever move the watermark forward. A "before date" run computes an earlier
		# `mark_all_read_at`; without this guard it would rewind an existing, newer
		# watermark and resurface already-read discussions as unread. Expressed as a
		# CASE (= GREATEST(current, mark_all_read_at)) so it runs on both MariaDB and
		# SQLite, which lack each other's two-argument max function.
		forward_watermark = Case().when(current > mark_all_read_at, current).else_(mark_all_read_at)
		(
			frappe.qb.update(ProjectVisit)
			.set(ProjectVisit.last_visit, last_visit)
			.set(ProjectVisit.mark_all_read_at, forward_watermark)
			.where(ProjectVisit.name.isin(project_visit_names))
		).run()

	@staticmethod
	def create_project_visits(projects: list[str], user, last_visit, mark_all_read_at):
		visits = []
		for project in projects:
			visit = frappe.get_doc(
				{
					"doctype": "GP Project Visit",
					"name": frappe.generate_hash(length=10),
					"user": user,
					"project": project,
					"last_visit": last_visit,
					"mark_all_read_at": mark_all_read_at,
				}
			)
			visits.append(visit)

		bulk_insert("GP Project Visit", visits, ignore_duplicates=True)

	@staticmethod
	def get_unread_count_for_projects(user, projects: list[str] = None):
		"""Get unread count for a single project for user"""
		from frappe.query_builder import functions

		UnreadRecord = frappe.qb.DocType("GP Unread Record")

		if projects:
			condition = (
				(UnreadRecord.user == user)
				& (UnreadRecord.project.isin(projects))
				& (UnreadRecord.is_unread == 1)
			)
		else:
			condition = (UnreadRecord.user == user) & (UnreadRecord.is_unread == 1)

		from gameplan.permissions import visible_discussion_criterion

		Discussion = frappe.qb.DocType("GP Discussion")
		visible = (
			frappe.qb.from_(Discussion)
			.select(Discussion.name)
			.where(visible_discussion_criterion(Discussion))
		)
		condition &= UnreadRecord.discussion.isin(visible)

		result = (
			frappe.qb.from_(UnreadRecord)
			.select(
				UnreadRecord.project,
				functions.Count(UnreadRecord.discussion).distinct().as_("unread_discussions_count"),
			)
			.where(condition)
			.groupby(UnreadRecord.project)
			.run(as_dict=True)
		)

		out = {}
		if projects:
			for project in projects:
				out[project] = 0

		for row in result:
			out[row.project] = row.unread_discussions_count

		return out

	@staticmethod
	def get_participating_unread_count(user, team=None):
		"""Count distinct unread discussions the user participates in.

		Mirrors the `participating` feed filter (owned or commented) intersected with
		the user's unread records so the menu badge always matches the feed contents.
		"""
		from frappe.query_builder.functions import Count
		from frappe.utils import cint
		from pypika.terms import ExistsCriterion

		from gameplan.gameplan.doctype.gp_discussion.api import clause_discussions_commented_by_user
		from gameplan.permissions import apply_accessible_project_filter

		Discussion = frappe.qb.DocType("GP Discussion")
		Project = frappe.qb.DocType("GP Project")
		UnreadRecord = frappe.qb.DocType("GP Unread Record")

		unread_record_exists = (
			frappe.qb.from_(UnreadRecord)
			.select(UnreadRecord.name)
			.where(
				(UnreadRecord.user == user)
				& (UnreadRecord.discussion == Discussion.name)
				& (UnreadRecord.is_unread == 1)
			)
		)

		query = (
			frappe.qb.from_(Discussion)
			.left_join(Project)
			.on(Discussion.project == Project.name)
			.where(Project.archived_at.isnull())
			.where(ExistsCriterion(unread_record_exists))
			.where((Discussion.owner == user) | clause_discussions_commented_by_user(user))
			.select(Count(Discussion.name).distinct())
		)
		from gameplan.permissions import visible_discussion_criterion

		query = query.where(visible_discussion_criterion(Discussion))
		query = apply_accessible_project_filter(query, Discussion.project)

		if team:
			query = query.where(Project.team == team)

		return cint(query.run()[0][0])

	@staticmethod
	def _get_project_members(project_name):
		"""Get all users who have access to the project"""
		project = frappe.db.get_value("GP Project", project_name, ["name", "visibility"], as_dict=True)

		all_users = set()

		if is_member_access(project.visibility):
			members = frappe.qb.get_query(
				"GP Member",
				fields=["user"],
				filters={"parent": project.name, "parenttype": "GP Project"},
			).run(pluck=True)
			all_users.update(members)
		else:
			enabled_users = frappe.qb.get_query(
				"GP User Profile", filters={"enabled": 1}, fields=["user"]
			).run(pluck=True)

			all_users.update(enabled_users)

		# Include guest users with explicit project access
		guest_users = frappe.qb.get_query(
			"GP Guest Access",
			fields=["user"],
			filters={"project": project.name},
		).run(pluck=True)
		all_users.update(guest_users)
		role_sets = get_audience_roles(all_users)
		if not is_member_access(project.visibility):
			all_users.difference_update(role_sets[1] - set(guest_users))
		return users_who_can_view_space(all_users, project_name, role_sets=role_sets)

	@staticmethod
	def _notify_unread_counts_changed(users):
		"""Signal each user's open tabs that their unread counts are stale.

		Without this, `frontend/src/data/unreadCount.ts` only refreshes after this tab's own
		mark-as-read/visit calls, so another tab (or a space getting a new unread discussion
		while you're looking elsewhere) stays stale until a manual reload.
		"""
		notify_unread_counts_changed(users)

	@staticmethod
	def _bulk_create_unread_records(records):
		"""Bulk insert unread records with error handling"""
		if not records:
			return

		for doc in records:
			if not doc.name:
				doc.name = frappe.db.get_next_sequence_val("GP Unread Record")

		try:
			bulk_insert("GP Unread Record", records, ignore_duplicates=True)
		except Exception:
			frappe.log_error(title="Unread Record Creation Error")


def on_doctype_update():
	add_indexes()


def add_indexes():
	frappe.db.add_index("GP Unread Record", ["user", "discussion", "is_unread"], "user_discussion_unread")
	frappe.db.add_index("GP Unread Record", ["user", "project", "is_unread"], "user_project_unread")
	# Records of one discussion: moving it, hiding it, and telling its readers. Without it each
	# of those scanned every unread record on the site.
	frappe.db.add_index("GP Unread Record", ["discussion"], "discussion_records")


# Re-exported so the thin whitelisted unread-count endpoints resolve under the
# `GP Unread Record/<method>` endpoint while their implementation lives in api.py.
from gameplan.gameplan.doctype.gp_unread_record.api import (  # noqa: E402, F401
	get_participating_unread_count,
	get_unread_count,
	mark_all_as_read_for_team,
)
