# Copyright (c) 2025, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

import frappe

from gameplan.gameplan.doctype.gp_unread_record.api import (
	get_participating_unread_count,
	get_unread_count,
)
from gameplan.gameplan.doctype.gp_unread_record.gp_unread_record import GPUnreadRecord
from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import create_community, create_discussion, create_member, create_space


class TestUnread(GameplanTestCase):
	"""Unread watermarks: mark-all-as-read across a community, and how records
	realign when a discussion moves between spaces.

	On GameplanTestCase for its per-test rollback — every method here writes users,
	communities, spaces and unread records, and its old tearDown restored the session
	user without rolling any of it back.
	"""

	def test_mark_all_as_read_for_team_marks_accessible_community_projects(self):
		suffix = frappe.generate_hash(length=8)
		user = create_member(f"team-unread-member-{suffix}@example.com", "Team Unread Member")
		source_team = create_community(f"Team Unread Source {suffix}")
		other_team = create_community(f"Team Unread Other {suffix}")
		source_project = create_space(f"Team Unread Source Space {suffix}", source_team.name)
		other_project = create_space(f"Team Unread Other Space {suffix}", other_team.name)
		source_discussion = create_discussion(f"Team Unread Source Discussion {suffix}", source_project.name)
		other_discussion = create_discussion(f"Team Unread Other Discussion {suffix}", other_project.name)
		source_unread_record = create_unread_record(user.name, source_discussion.name, source_project.name)
		other_unread_record = create_unread_record(user.name, other_discussion.name, other_project.name)

		frappe.set_user(user.name)
		projects = GPUnreadRecord.mark_all_as_read_for_team(source_team.name, user.name)

		self.assertIn(str(source_project.name), projects)
		self.assertNotIn(str(other_project.name), projects)
		self.assertEqual(frappe.db.get_value("GP Unread Record", source_unread_record, "is_unread"), 0)
		self.assertEqual(frappe.db.get_value("GP Unread Record", other_unread_record, "is_unread"), 1)
		self.assertTrue(
			frappe.db.exists("GP Project Visit", {"user": user.name, "project": source_project.name})
		)

	def test_mark_all_as_read_for_team_updates_existing_project_visit(self):
		suffix = frappe.generate_hash(length=8)
		user = create_member(f"team-visit-member-{suffix}@example.com", "Team Visit Member")
		team = create_community(f"Team Visit Source {suffix}")
		project = create_space(f"Team Visit Source Space {suffix}", team.name)
		discussion = create_discussion(f"Team Visit Source Discussion {suffix}", project.name)
		unread_record = create_unread_record(user.name, discussion.name, project.name)
		old_timestamp = frappe.utils.get_datetime("2026-01-01 00:00:00")
		visit = frappe.get_doc(
			{
				"doctype": "GP Project Visit",
				"user": user.name,
				"project": project.name,
				"last_visit": old_timestamp,
				"mark_all_read_at": old_timestamp,
			}
		).insert(ignore_permissions=True)

		frappe.set_user(user.name)
		GPUnreadRecord.mark_all_as_read_for_team(team.name, user.name)

		self.assertEqual(frappe.db.get_value("GP Unread Record", unread_record, "is_unread"), 0)
		self.assertEqual(frappe.db.count("GP Project Visit", {"user": user.name, "project": project.name}), 1)
		self.assertGreater(
			frappe.db.get_value("GP Project Visit", visit.name, "mark_all_read_at"),
			old_timestamp,
		)

	def test_mark_all_as_read_for_team_with_before_marks_only_older_discussions(self):
		suffix = frappe.generate_hash(length=8)
		user = create_member(f"team-before-member-{suffix}@example.com", "Team Before Member")
		team = create_community(f"Team Before Source {suffix}")
		project = create_space(f"Team Before Source Space {suffix}", team.name)

		old_discussion = create_discussion(f"Team Before Old Discussion {suffix}", project.name)
		new_discussion = create_discussion(f"Team Before New Discussion {suffix}", project.name)
		set_last_post_at(old_discussion.name, "2026-01-10 09:00:00")
		set_last_post_at(new_discussion.name, "2026-01-20 09:00:00")

		old_unread_record = create_unread_record(user.name, old_discussion.name, project.name)
		new_unread_record = create_unread_record(user.name, new_discussion.name, project.name)

		frappe.set_user(user.name)
		projects = GPUnreadRecord.mark_all_as_read_for_team(team.name, user.name, before="2026-01-15")

		self.assertIn(str(project.name), projects)
		self.assertEqual(frappe.db.get_value("GP Unread Record", old_unread_record, "is_unread"), 0)
		self.assertEqual(frappe.db.get_value("GP Unread Record", new_unread_record, "is_unread"), 1)

	def test_mark_all_as_read_for_team_before_is_inclusive_of_that_whole_day(self):
		suffix = frappe.generate_hash(length=8)
		user = create_member(f"team-boundary-member-{suffix}@example.com", "Team Boundary Member")
		team = create_community(f"Team Boundary Source {suffix}")
		project = create_space(f"Team Boundary Source Space {suffix}", team.name)

		# `before` is 2026-01-15: a discussion late on that day is included (inclusive),
		# one early on the next day is excluded.
		on_day_discussion = create_discussion(f"Team Boundary On Day {suffix}", project.name)
		next_day_discussion = create_discussion(f"Team Boundary Next Day {suffix}", project.name)
		set_last_post_at(on_day_discussion.name, "2026-01-15 23:59:59")
		set_last_post_at(next_day_discussion.name, "2026-01-16 00:00:01")

		on_day_unread_record = create_unread_record(user.name, on_day_discussion.name, project.name)
		next_day_unread_record = create_unread_record(user.name, next_day_discussion.name, project.name)

		frappe.set_user(user.name)
		GPUnreadRecord.mark_all_as_read_for_team(team.name, user.name, before="2026-01-15")

		self.assertEqual(frappe.db.get_value("GP Unread Record", on_day_unread_record, "is_unread"), 0)
		self.assertEqual(frappe.db.get_value("GP Unread Record", next_day_unread_record, "is_unread"), 1)

	def test_mark_all_as_read_for_team_with_before_sets_watermark_to_cutoff(self):
		suffix = frappe.generate_hash(length=8)
		user = create_member(f"team-watermark-member-{suffix}@example.com", "Team Watermark Member")
		team = create_community(f"Team Watermark Source {suffix}")
		project = create_space(f"Team Watermark Source Space {suffix}", team.name)
		discussion = create_discussion(f"Team Watermark Discussion {suffix}", project.name)
		set_last_post_at(discussion.name, "2026-01-10 09:00:00")
		create_unread_record(user.name, discussion.name, project.name)

		before = "2026-01-15"
		cutoff = frappe.utils.add_days(before, 1)
		before_action = frappe.utils.get_datetime(frappe.utils.now())

		frappe.set_user(user.name)
		GPUnreadRecord.mark_all_as_read_for_team(team.name, user.name, before=before)

		visit = frappe.db.get_value(
			"GP Project Visit",
			{"user": user.name, "project": project.name},
			["last_visit", "mark_all_read_at"],
			as_dict=True,
		)
		self.assertIsNotNone(visit)
		# Watermark is the inclusive end of the `before` day: within that day and strictly
		# below the exclusive cutoff, so the `> watermark` read check matches the `< cutoff`
		# unread query exactly (no midnight-boundary skew).
		watermark = frappe.utils.get_datetime(visit.mark_all_read_at)
		self.assertGreaterEqual(watermark, frappe.utils.get_datetime(before))
		self.assertLess(watermark, frappe.utils.get_datetime(cutoff))
		# `last_visit` reflects the action time (~now), not the cutoff date in the past.
		self.assertGreaterEqual(frappe.utils.get_datetime(visit.last_visit), before_action)

	def test_mark_all_as_read_for_team_without_before_sets_watermark_to_now(self):
		suffix = frappe.generate_hash(length=8)
		user = create_member(f"team-now-member-{suffix}@example.com", "Team Now Member")
		team = create_community(f"Team Now Source {suffix}")
		project = create_space(f"Team Now Source Space {suffix}", team.name)
		discussion = create_discussion(f"Team Now Discussion {suffix}", project.name)
		create_unread_record(user.name, discussion.name, project.name)

		before_action = frappe.utils.get_datetime(frappe.utils.now())

		frappe.set_user(user.name)
		GPUnreadRecord.mark_all_as_read_for_team(team.name, user.name)

		visit = frappe.db.get_value(
			"GP Project Visit",
			{"user": user.name, "project": project.name},
			["last_visit", "mark_all_read_at"],
			as_dict=True,
		)
		self.assertIsNotNone(visit)
		# Without a `before` date everything is marked read up to now.
		self.assertGreaterEqual(frappe.utils.get_datetime(visit.mark_all_read_at), before_action)
		self.assertGreaterEqual(frappe.utils.get_datetime(visit.last_visit), before_action)

	def test_mark_all_as_read_for_team_with_before_never_rewinds_a_newer_watermark(self):
		suffix = frappe.generate_hash(length=8)
		user = create_member(f"team-rewind-member-{suffix}@example.com", "Team Rewind Member")
		team = create_community(f"Team Rewind Source {suffix}")
		project = create_space(f"Team Rewind Source Space {suffix}", team.name)
		discussion = create_discussion(f"Team Rewind Discussion {suffix}", project.name)
		set_last_post_at(discussion.name, "2026-01-10 09:00:00")
		create_unread_record(user.name, discussion.name, project.name)

		frappe.set_user(user.name)
		# First mark everything read up to now: the watermark advances to "today".
		GPUnreadRecord.mark_all_as_read_for_team(team.name, user.name)
		newer_watermark = frappe.db.get_value(
			"GP Project Visit", {"user": user.name, "project": project.name}, "mark_all_read_at"
		)

		# Then mark "before" an OLDER date. The earlier cutoff must not rewind the watermark,
		# which would resurface discussions read between that date and now.
		GPUnreadRecord.mark_all_as_read_for_team(team.name, user.name, before="2026-01-15")

		watermark = frappe.db.get_value(
			"GP Project Visit", {"user": user.name, "project": project.name}, "mark_all_read_at"
		)
		self.assertEqual(frappe.utils.get_datetime(watermark), frappe.utils.get_datetime(newer_watermark))

	def test_mark_all_as_read_for_team_clamps_future_before_to_today(self):
		# The whitelisted endpoint clamps `before` so a client can't push the watermark into
		# the future (which would mark not-yet-posted discussions read).
		from gameplan.gameplan.doctype.gp_unread_record.api import mark_all_as_read_for_team

		suffix = frappe.generate_hash(length=8)
		user = create_member(f"team-clamp-member-{suffix}@example.com", "Team Clamp Member")
		team = create_community(f"Team Clamp Source {suffix}")
		project = create_space(f"Team Clamp Source Space {suffix}", team.name)
		discussion = create_discussion(f"Team Clamp Discussion {suffix}", project.name)
		record = create_unread_record(user.name, discussion.name, project.name)

		frappe.set_user(user.name)
		mark_all_as_read_for_team(team=team.name, before="2099-01-01")

		# Clamped to today, so today's discussion is read...
		self.assertEqual(frappe.db.get_value("GP Unread Record", record, "is_unread"), 0)
		# ...and the watermark stays near today rather than jumping to the far-future cutoff.
		watermark = frappe.db.get_value(
			"GP Project Visit", {"user": user.name, "project": project.name}, "mark_all_read_at"
		)
		self.assertLess(
			frappe.utils.get_datetime(watermark),
			frappe.utils.get_datetime(frappe.utils.add_days(frappe.utils.nowdate(), 2)),
		)

	def test_mark_all_as_read_for_team_rejects_malformed_before(self):
		# A malformed cutoff returns a controlled validation error, not a raw 500.
		from gameplan.gameplan.doctype.gp_unread_record.api import mark_all_as_read_for_team

		suffix = frappe.generate_hash(length=8)
		user = create_member(f"team-bad-date-member-{suffix}@example.com", "Team Bad Date Member")
		team = create_community(f"Team Bad Date Source {suffix}")

		frappe.set_user(user.name)
		with self.assertRaises(frappe.exceptions.ValidationError):
			mark_all_as_read_for_team(team=team.name, before="not-a-date")

	def test_mark_all_as_read_for_team_with_before_skips_null_last_post_at(self):
		# `last_post_at` is invariably set in practice: `before_insert` defaults it to the
		# creation time and the `backfill_null_last_post_at` patch repaired legacy NULL rows.
		# The dated path therefore filters on a concrete `last_post_at < cutoff`; a row forced
		# to NULL (only reachable via a raw insert) has no timestamp to place against the
		# cutoff and is intentionally left untouched rather than guessed into the read set.
		suffix = frappe.generate_hash(length=8)
		user = create_member(f"team-null-lpa-member-{suffix}@example.com", "Team Null LPA Member")
		team = create_community(f"Team Null LPA Source {suffix}")
		project = create_space(f"Team Null LPA Source Space {suffix}", team.name)
		discussion = create_discussion(f"Team Null LPA Discussion {suffix}", project.name)
		frappe.db.set_value("GP Discussion", discussion.name, "last_post_at", None, update_modified=False)
		record = create_unread_record(user.name, discussion.name, project.name)

		frappe.set_user(user.name)
		# Dated mark-all: the NULL row has no timestamp, so the cutoff filter skips it.
		GPUnreadRecord.mark_all_as_read_for_team(team.name, user.name, before=frappe.utils.today())
		self.assertEqual(frappe.db.get_value("GP Unread Record", record, "is_unread"), 1)

		# Undated mark-all has no cutoff subquery, so the same row is cleared.
		GPUnreadRecord.mark_all_as_read_for_team(team.name, user.name)
		self.assertEqual(frappe.db.get_value("GP Unread Record", record, "is_unread"), 0)

	def test_mark_all_as_read_for_team_with_before_does_not_cross_project_boundaries(self):
		# The dated subquery repeats the project filter (for the (project, last_post_at) index);
		# an old discussion in another community must not be cleared by this team's mark-all.
		suffix = frappe.generate_hash(length=8)
		user = create_member(f"team-scope-member-{suffix}@example.com", "Team Scope Member")
		source_team = create_community(f"Team Scope Source {suffix}")
		other_team = create_community(f"Team Scope Other {suffix}")
		source_project = create_space(f"Team Scope Source Space {suffix}", source_team.name)
		other_project = create_space(f"Team Scope Other Space {suffix}", other_team.name)
		source_discussion = create_discussion(f"Team Scope Source Discussion {suffix}", source_project.name)
		other_discussion = create_discussion(f"Team Scope Other Discussion {suffix}", other_project.name)
		# Both are old enough to fall before the cutoff; only the source team's should clear.
		set_last_post_at(source_discussion.name, "2026-01-10 09:00:00")
		set_last_post_at(other_discussion.name, "2026-01-10 09:00:00")
		source_record = create_unread_record(user.name, source_discussion.name, source_project.name)
		other_record = create_unread_record(user.name, other_discussion.name, other_project.name)

		frappe.set_user(user.name)
		GPUnreadRecord.mark_all_as_read_for_team(source_team.name, user.name, before="2026-01-15")

		self.assertEqual(frappe.db.get_value("GP Unread Record", source_record, "is_unread"), 0)
		self.assertEqual(frappe.db.get_value("GP Unread Record", other_record, "is_unread"), 1)

	def test_update_project_for_discussion_realigns_records_to_current_space(self):
		# A discussion's unread records must follow it when it moves, otherwise the count stays
		# attributed to (and stuck in) the old space.
		suffix = frappe.generate_hash(length=8)
		user = create_member(f"realign-member-{suffix}@example.com", "Realign Member")
		team = create_community(f"Realign Team {suffix}")
		old_project = create_space(f"Realign Old Space {suffix}", team.name)
		new_project = create_space(f"Realign New Space {suffix}", team.name)
		discussion = create_discussion(f"Realign Discussion {suffix}", new_project.name)
		# Record left pointing at the old space, as if the discussion was moved after creation.
		record = create_unread_record(user.name, discussion.name, old_project.name)

		GPUnreadRecord.update_project_for_discussion(discussion.name, new_project.name)

		self.assertEqual(frappe.db.get_value("GP Unread Record", record, "project"), str(new_project.name))

	def test_moving_discussion_realigns_unread_records(self):
		# End-to-end: moving a discussion to another space updates its unread records' project,
		# so mark_all_as_read_for_team on the new space can clear them.
		from gameplan.gameplan.doctype.gp_discussion.gp_discussion import move_discussion

		suffix = frappe.generate_hash(length=8)
		user = create_member(f"move-member-{suffix}@example.com", "Move Member")
		team = create_community(f"Move Team {suffix}")
		source_project = create_space(f"Move Source Space {suffix}", team.name)
		target_project = create_space(f"Move Target Space {suffix}", team.name)
		discussion = create_discussion(f"Move Discussion {suffix}", source_project.name)
		record = create_unread_record(user.name, discussion.name, source_project.name)

		move_discussion(discussion, target_project.name)

		self.assertEqual(frappe.db.get_value("GP Unread Record", record, "project"), str(target_project.name))


class TestUnreadRecordLifecycle(GameplanTestCase):
	"""Who gets an unread record, who does not, and what the counters then report.

	The space is private and explicitly membered on purpose: a public space fans the
	records out to every enabled non-guest user on the site (see
	`GPUnreadRecord._get_project_members`), which makes "exactly who got a record"
	impossible to assert.
	"""

	def setUp(self):
		super().setUp()
		self.reader = create_member("unread_reader@example.com", "Unread Reader")
		self.community = create_community(
			"Unread Community", members=[self.member, self.second_member, self.reader]
		)
		self.space = create_space(
			"Unread Space",
			self.community,
			is_private=1,
			members=[self.member, self.second_member, self.reader],
		)

	def post_discussion(self, user, title="Unread thread"):
		"""Insert a discussion AS `user`.

		The fan-out keys off the discussion's `owner`, and only an insert running as that
		user sets it — hence this rather than `create_discussion(..., owner=...)`, which
		rewrites the owner after `after_insert` has already run.
		"""
		with self.as_user(user):
			return frappe.get_doc(
				doctype="GP Discussion", title=title, project=self.space.name, content="Body"
			).insert()

	def post_comment(self, user, discussion, content="A reply"):
		with self.as_user(user):
			return frappe.get_doc(
				doctype="GP Comment",
				reference_doctype="GP Discussion",
				reference_name=discussion.name,
				content=content,
			).insert()

	def records_for(self, user, discussion):
		return frappe.get_all(
			"GP Unread Record",
			filters={"user": user.name, "discussion": str(discussion.name)},
			fields=["name", "comment", "is_unread"],
			order_by="name asc",
		)

	def unread_count(self, user, space=None):
		space = space or self.space
		return GPUnreadRecord.get_unread_count_for_projects(user.name, [str(space.name)])

	def test_the_author_gets_no_unread_record_for_their_own_discussion(self):
		discussion = self.post_discussion(self.member)

		self.assertEqual(self.records_for(self.member, discussion), [])
		self.assertEqual(len(self.records_for(self.second_member, discussion)), 1)
		self.assertEqual(len(self.records_for(self.reader, discussion)), 1)

	def test_the_commenter_gets_no_unread_record_for_their_own_comment(self):
		discussion = self.post_discussion(self.member)

		comment = self.post_comment(self.second_member, discussion)

		# The author of the thread is unread on the reply, and on nothing else.
		[author_record] = self.records_for(self.member, discussion)
		self.assertEqual(str(author_record.comment), str(comment.name))
		# The commenter keeps only their pre-existing discussion-level record.
		[commenter_record] = self.records_for(self.second_member, discussion)
		self.assertFalse(commenter_record.comment)

	def test_the_unread_count_is_scoped_to_the_user(self):
		self.post_discussion(self.member)

		space = str(self.space.name)
		self.assertEqual(self.unread_count(self.second_member), {space: 1})
		self.assertEqual(self.unread_count(self.reader), {space: 1})
		# The author has no record, and someone outside the space can never have one.
		self.assertEqual(self.unread_count(self.member), {space: 0})
		self.assertEqual(self.unread_count(self.outsider), {space: 0})

	def test_the_unread_count_endpoint_answers_for_the_session_user(self):
		self.post_discussion(self.member)
		space = str(self.space.name)

		with self.as_user(self.second_member):
			self.assertEqual(get_unread_count([space]), {space: 1})
		with self.as_user(self.member):
			self.assertEqual(get_unread_count([space]), {space: 0})

	def test_marking_a_space_as_read_is_idempotent(self):
		discussion = self.post_discussion(self.member)
		space = str(self.space.name)

		GPUnreadRecord.mark_all_as_read_for_project(space, self.second_member.name)
		after_first = self.records_for(self.second_member, discussion)
		GPUnreadRecord.mark_all_as_read_for_project(space, self.second_member.name)

		self.assertEqual([record.is_unread for record in after_first], [0])
		# Running it again neither resurfaces the record nor adds a second one.
		self.assertEqual(self.records_for(self.second_member, discussion), after_first)
		self.assertEqual(self.unread_count(self.second_member), {space: 0})

	def test_marking_a_space_as_read_only_clears_your_own_records(self):
		self.post_discussion(self.member)
		space = str(self.space.name)

		GPUnreadRecord.mark_all_as_read_for_project(space, self.second_member.name)

		self.assertEqual(self.unread_count(self.second_member), {space: 0})
		self.assertEqual(self.unread_count(self.reader), {space: 1})

	def test_marking_a_space_as_read_leaves_other_spaces_alone(self):
		other_space = create_space(
			"Other Unread Space",
			self.community,
			is_private=1,
			members=[self.member, self.second_member],
		)
		self.post_discussion(self.member)
		with self.as_user(self.member):
			frappe.get_doc(
				doctype="GP Discussion", title="Elsewhere", project=other_space.name, content="Body"
			).insert()

		GPUnreadRecord.mark_all_as_read_for_project(str(self.space.name), self.second_member.name)

		self.assertEqual(self.unread_count(self.second_member), {str(self.space.name): 0})
		self.assertEqual(self.unread_count(self.second_member, other_space), {str(other_space.name): 1})

	def test_deleting_a_discussion_removes_its_unread_records(self):
		discussion = self.post_discussion(self.member)
		self.assertEqual(len(self.records_for(self.second_member, discussion)), 1)

		with self.as_user(self.member):
			frappe.delete_doc("GP Discussion", discussion.name)

		self.assertEqual(self.records_for(self.second_member, discussion), [])
		self.assertEqual(self.unread_count(self.second_member), {str(self.space.name): 0})

	def test_deleting_a_comment_removes_only_that_comments_unread_records(self):
		discussion = self.post_discussion(self.member)
		comment = self.post_comment(self.second_member, discussion)

		with self.as_user(self.second_member):
			frappe.delete_doc("GP Comment", comment.name)

		# The thread author's only record was the one for that comment.
		self.assertEqual(self.records_for(self.member, discussion), [])
		# The commenter's discussion-level record predates the comment and survives it.
		self.assertEqual(len(self.records_for(self.second_member, discussion)), 1)

	def test_replying_marks_the_thread_read_for_the_replier(self):
		"""GP Comment.update_discussion_meta calls track_visit, so posting is also a read."""
		discussion = self.post_discussion(self.member)
		self.assertEqual(self.unread_count(self.second_member), {str(self.space.name): 1})

		self.post_comment(self.second_member, discussion)

		self.assertEqual(self.unread_count(self.second_member), {str(self.space.name): 0})
		# Everyone else is left unread — on the new comment for the thread's author, and
		# still on the thread itself for the bystander.
		self.assertEqual(self.unread_count(self.member), {str(self.space.name): 1})
		self.assertEqual(self.unread_count(self.reader), {str(self.space.name): 1})

	def test_participating_count_only_counts_unread_threads_you_took_part_in(self):
		# Owned but never unread: the author gets no record for their own thread.
		self.post_discussion(self.member, "Mine")
		theirs = self.post_discussion(self.second_member, "Theirs")

		# Unread but not participated in: `member` has a record for `theirs` and has not
		# posted in it.
		self.assertEqual(GPUnreadRecord.get_participating_unread_count(self.member.name), 0)

		# Participated in but no longer unread: replying marks the thread read for the
		# replier, so a reply alone cannot make it count.
		self.post_comment(self.member, theirs)
		self.assertEqual(GPUnreadRecord.get_participating_unread_count(self.member.name), 0)

		# Both: someone else posts after them.
		self.post_comment(self.second_member, theirs, "Last word")

		self.assertEqual(GPUnreadRecord.get_participating_unread_count(self.member.name), 1)
		# `reader` is unread on the same thread but has never posted in it, and nobody
		# outside the space sees it at all.
		self.assertEqual(GPUnreadRecord.get_participating_unread_count(self.reader.name), 0)
		self.assertEqual(GPUnreadRecord.get_participating_unread_count(self.outsider.name), 0)

	def test_the_participating_count_endpoint_answers_for_the_session_user(self):
		theirs = self.post_discussion(self.second_member, "Theirs")
		self.post_comment(self.member, theirs)
		self.post_comment(self.second_member, theirs, "Last word")

		with self.as_user(self.member):
			self.assertEqual(get_participating_unread_count(), 1)
		with self.as_user(self.reader):
			self.assertEqual(get_participating_unread_count(), 0)


def set_last_post_at(discussion: str, last_post_at: str):
	# `last_post_at` is auto-set to now() in GP Discussion.before_insert, so override it
	# directly to pin a specific activity time without bumping `modified`.
	frappe.db.set_value("GP Discussion", discussion, "last_post_at", last_post_at, update_modified=False)


def create_unread_record(user: str, discussion: str, project: str):
	return (
		frappe.get_doc(
			{
				"doctype": "GP Unread Record",
				"user": user,
				"discussion": discussion,
				"project": project,
				"is_unread": 1,
			}
		)
		.insert(ignore_permissions=True)
		.name
	)
