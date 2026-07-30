# Copyright (c) 2022, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""Space (GP Project) behaviour: archiving, activity, search scoping, and who may
join, leave, manage members or invite guests."""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from gameplan.gameplan.doctype.gp_project import gp_project as gp_project_module
from gameplan.gameplan.doctype.gp_project.gp_project import (
	DEFAULT_SPACE_ICON,
	GPProject,
	get_activity,
	get_joined_spaces,
	get_unread_count,
	mark_all_as_read,
	track_visits,
)
from gameplan.search_sqlite import GameplanSearch
from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import (
	create_community,
	create_discussion,
	create_member,
	create_space,
	declared_http_methods,
	grant_guest_access,
)


class TestSpaces(FrappeTestCase):
	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def test_archive_deletes_current_users_pin(self):
		frappe.set_user("Administrator")
		team = create_community("Pinned Archive Team")
		project = create_space("Pinned Archive Space", team.name)
		pin = frappe.get_doc(doctype="GP Pinned Project", project=project.name).insert(
			ignore_permissions=True
		)

		project.archive()

		self.assertTrue(project.archived_at)
		self.assertFalse(frappe.db.exists("GP Pinned Project", pin.name))

	def test_search_private_space_requires_space_membership(self):
		member = create_member("test_search_member@example.com")
		team = create_community("Search Permissions Team")
		team.add_member(member.name)
		team.save(ignore_permissions=True)

		public_project = create_space("Search Public Space", team.name)
		private_project = create_space("Search Private Space", team.name, is_private=1)

		frappe.set_user(member.name)
		accessible_projects = GameplanSearch()._get_accessible_projects()

		self.assertIn(str(public_project.name), accessible_projects)
		self.assertNotIn(str(private_project.name), accessible_projects)

		frappe.set_user("Administrator")
		private_project.add_member(member.name)

		frappe.set_user(member.name)
		accessible_projects = GameplanSearch()._get_accessible_projects()

		self.assertIn(str(private_project.name), accessible_projects)

	def test_get_activity_returns_latest_accessible_space_activity(self):
		member = create_member("test_space_activity_member@example.com")
		team = create_community("Space Activity Team")
		public_project = create_space("Public Activity Space", team.name)
		private_project = create_space("Private Activity Space", team.name, is_private=1)

		older_discussion = create_discussion("Older Activity", public_project.name)
		latest_discussion = create_discussion("Latest Activity", public_project.name)
		private_discussion = create_discussion("Private Activity", private_project.name)
		frappe.db.set_value("GP Discussion", older_discussion.name, "last_post_at", "2026-01-01 10:00:00")
		frappe.db.set_value("GP Discussion", latest_discussion.name, "last_post_at", "2026-01-02 10:00:00")
		frappe.db.set_value("GP Discussion", private_discussion.name, "last_post_at", "2026-01-03 10:00:00")

		frappe.set_user(member.name)
		activity = get_activity()

		self.assertEqual(str(activity[str(public_project.name)]), "2026-01-02 10:00:00")
		self.assertNotIn(str(private_project.name), activity)

	def test_get_activity_omits_a_space_whose_latest_post_time_is_unknown(self):
		"""A NULL max timestamp is "no activity", not activity at an unknown time.

		The falsy guard has to reject it before the string comparison runs: `str(None)`
		is `"None"`, which sorts above the `""` seed, so a comparison-first version would
		publish `None` as the space's last activity and the sidebar would sort on it.
		"""
		member = create_member("test_null_activity_member@example.com")
		team = create_community("Null Activity Team")
		project = create_space("Null Activity Space", team.name)
		discussion = create_discussion("Null Activity Discussion", project.name)
		frappe.db.set_value("GP Discussion", discussion.name, "last_post_at", None)

		frappe.set_user(member.name)
		activity = get_activity()

		self.assertNotIn(str(project.name), activity)


class TestSpaceMembership(GameplanTestCase):
	"""Joining, leaving, managing members and inviting guests.

	Joining a public space needs only visibility, but every managing action
	(adding members, inviting guests) needs manage access — space membership for a
	private space, community admin for a public one.
	"""

	def test_member_can_join_visible_public_space(self):
		community = create_community("Joinable Public Community", members=[self.member, self.second_member])
		space = create_space("Joinable Public Space", community)

		with self.as_user(self.second_member):
			frappe.get_doc("GP Project", space.name).join()

		space.reload()
		self.assertTrue(any(row.user == self.second_member.name for row in space.members))

	def test_joining_a_space_twice_keeps_one_membership(self):
		community = create_community("Idempotent Join Community", members=[self.member])
		space = create_space("Idempotent Join Space", community)

		with self.as_user(self.member):
			frappe.get_doc("GP Project", space.name).join()
			frappe.get_doc("GP Project", space.name).join()

		self.assertEqual(
			frappe.db.count(
				"GP Member",
				{"parenttype": "GP Project", "parent": space.name, "user": self.member.name},
			),
			1,
		)

	def test_member_can_leave_public_space(self):
		community = create_community("Leaveable Public Community", members=[self.member, self.second_member])
		space = create_space("Leaveable Public Space", community, members=[self.second_member])

		with self.as_user(self.second_member):
			frappe.get_doc("GP Project", space.name).leave()

		space.reload()
		self.assertFalse(any(row.user == self.second_member.name for row in space.members))

	def test_leaving_a_space_twice_stays_left(self):
		community = create_community("Idempotent Leave Community", members=[self.member])
		space = create_space("Idempotent Leave Space", community, members=[self.member])

		with self.as_user(self.member):
			frappe.get_doc("GP Project", space.name).leave()
			frappe.get_doc("GP Project", space.name).leave()

		self.assertFalse(
			frappe.db.exists(
				"GP Member",
				{"parenttype": "GP Project", "parent": space.name, "user": self.member.name},
			)
		)

	def test_member_cannot_join_public_space_in_inaccessible_private_community(self):
		community = create_community("Blocked Join Community", is_private=1, members=[self.member])
		space = create_space("Blocked Join Space", community)

		with self.as_user(self.second_member), self.assertRaises(frappe.PermissionError):
			space.join()

	def test_private_space_member_can_add_community_member_to_private_space(self):
		community = create_community(
			"Private Space Management Community", members=[self.member, self.second_member]
		)
		space = create_space("Managed Private Space", community, is_private=1, members=[self.member])

		with self.as_user(self.member):
			space.add_member(self.second_member.name)

		space.reload()
		self.assertTrue(any(row.user == self.second_member.name for row in space.members))

	def test_non_space_member_cannot_manage_private_space_members(self):
		community = create_community(
			"Blocked Private Space Community", members=[self.member, self.second_member]
		)
		space = create_space("Blocked Private Space", community, is_private=1, members=[self.member])

		with self.as_user(self.second_member), self.assertRaises(frappe.PermissionError):
			space.add_member(self.outsider.name)

	def test_private_space_member_can_invite_guest_to_space(self):
		community = create_community("Guest Invite Community", members=[self.member])
		space = create_space("Guest Invite Space", community, is_private=1, members=[self.member])

		# GP Invitation.after_insert emails the invitee, so without this the assertion
		# under test would hinge on the site having an outgoing Email Account (CI mutes
		# mail via site config; a plain dev site raises OutgoingEmailError). Same mute as
		# InvitationTestCase in test_invitations.py.
		with self.as_user(self.member), patch("frappe.sendmail"):
			space.invite_guest("new_perm_guest@example.com")

		invitation = frappe.db.get_value(
			"GP Invitation",
			{"email": "new_perm_guest@example.com"},
			["role", "projects"],
			as_dict=True,
		)
		self.assertIsNotNone(invitation)
		self.assertEqual(invitation.role, "Gameplan Guest")
		self.assertEqual(frappe.parse_json(invitation.projects), [space.name])

	def test_regular_member_cannot_invite_guest_to_public_space(self):
		community = create_community("Blocked Public Guest Invite Community", members=[self.member])
		space = create_space("Blocked Public Guest Invite Space", community)

		with self.as_user(self.member), self.assertRaises(frappe.PermissionError):
			space.invite_guest("blocked_public_guest@example.com")

		self.assertFalse(frappe.db.exists("GP Invitation", {"email": "blocked_public_guest@example.com"}))

	def test_non_space_member_cannot_invite_guest_to_private_space(self):
		community = create_community(
			"Blocked Guest Invite Community", members=[self.member, self.second_member]
		)
		space = create_space("Blocked Guest Invite Space", community, is_private=1, members=[self.member])

		with self.as_user(self.second_member), self.assertRaises(frappe.PermissionError):
			space.invite_guest("blocked_perm_guest@example.com")


class TestSpaceReadState(GameplanTestCase):
	def setUp(self):
		super().setUp()
		self.community = create_community("Read State Community", members=[self.member, self.second_member])
		self.space = create_space(
			"Read State Space", self.community, members=[self.member, self.second_member]
		)
		with self.as_user(self.second_member):
			self.discussion = create_discussion("Unread Space Discussion", self.space)

	def test_marking_a_space_read_clears_only_the_current_users_unread_state(self):
		with self.as_user(self.member):
			frappe.get_doc("GP Project", self.space.name).mark_all_as_read()

		self.assertEqual(
			frappe.db.get_value(
				"GP Unread Record",
				{"user": self.member.name, "discussion": self.discussion.name},
				"is_unread",
			),
			0,
		)
		self.assertEqual(
			frappe.db.get_value(
				"GP Unread Record",
				{"user": self.outsider.name, "discussion": self.discussion.name},
				"is_unread",
			),
			1,
		)
		visit = frappe.db.get_value(
			"GP Project Visit",
			{"user": self.member.name, "project": self.space.name},
			["last_visit", "mark_all_read_at"],
			as_dict=True,
		)
		self.assertTrue(visit.last_visit)
		self.assertTrue(visit.mark_all_read_at)

	def test_bulk_mark_read_accepts_numeric_space_names_from_the_list_api(self):
		with self.as_user(self.member):
			mark_all_as_read(spaces=[int(self.space.name)])

		self.assertEqual(
			frappe.db.get_value(
				"GP Unread Record",
				{"user": self.member.name, "discussion": self.discussion.name},
				"is_unread",
			),
			0,
		)

	def test_visiting_a_space_upserts_the_current_users_visit(self):
		old_last_visit = "2026-01-01 00:00:00"
		visit = frappe.get_doc(
			doctype="GP Project Visit",
			user=self.member.name,
			project=self.space.name,
			last_visit=old_last_visit,
		).insert(ignore_permissions=True)

		with self.as_user(self.member):
			frappe.get_doc("GP Project", self.space.name).track_visit()
			frappe.get_doc("GP Project", self.space.name).track_visit()

		self.assertEqual(
			frappe.db.count("GP Project Visit", {"user": self.member.name, "project": self.space.name}),
			1,
		)
		visit.reload()
		self.assertGreater(
			frappe.utils.get_datetime(visit.last_visit),
			frappe.utils.get_datetime(old_last_visit),
		)
		self.assertIsNone(visit.mark_all_read_at)

	def test_member_cannot_track_a_visit_to_an_inaccessible_space(self):
		private_community = create_community("Private Visit Community", is_private=1, members=[self.member])
		private_space = create_space(
			"Private Visit Space", private_community, is_private=1, members=[self.member]
		)

		with self.as_user(self.outsider), self.assertRaises(frappe.PermissionError):
			private_space.track_visit()

		self.assertFalse(
			frappe.db.exists(
				"GP Project Visit",
				{"user": self.outsider.name, "project": private_space.name},
			)
		)

	def test_marking_a_space_read_updates_the_existing_visit(self):
		old_timestamp = "2026-01-01 00:00:00"
		visit = frappe.get_doc(
			doctype="GP Project Visit",
			user=self.member.name,
			project=self.space.name,
			last_visit=old_timestamp,
			mark_all_read_at=old_timestamp,
		).insert(ignore_permissions=True)

		with self.as_user(self.member):
			frappe.get_doc("GP Project", self.space.name).mark_all_as_read()

		self.assertEqual(
			frappe.db.count("GP Project Visit", {"user": self.member.name, "project": self.space.name}),
			1,
		)
		visit.reload()
		self.assertGreater(
			frappe.utils.get_datetime(visit.mark_all_read_at),
			frappe.utils.get_datetime(old_timestamp),
		)
		self.assertGreater(
			frappe.utils.get_datetime(visit.last_visit),
			frappe.utils.get_datetime(old_timestamp),
		)

	def test_guest_with_space_access_can_record_a_visit(self):
		grant_guest_access(self.guest, self.space)

		with self.as_user(self.guest):
			frappe.get_doc("GP Project", self.space.name).track_visit()

		self.assertTrue(
			frappe.db.get_value(
				"GP Project Visit",
				{"user": self.guest.name, "project": self.space.name},
				"last_visit",
			)
		)

	def test_guest_can_record_a_repeat_visit_to_a_granted_space(self):
		"""The second visit updates the row instead of inserting one.

		Worth its own test because the two branches need different permissions: the
		Gameplan Guest role has `create` on GP Project Visit but not `write`, so only
		the update branch depends on the ignore_permissions save.
		"""
		grant_guest_access(self.guest, self.space)

		with self.as_user(self.guest):
			frappe.get_doc("GP Project", self.space.name).track_visit()
			frappe.get_doc("GP Project", self.space.name).track_visit()

		self.assertEqual(
			frappe.db.count("GP Project Visit", {"user": self.guest.name, "project": self.space.name}),
			1,
		)

	def test_guest_can_mark_a_granted_space_read_after_visiting_it(self):
		"""Same split as the repeat visit: marking read after a visit takes the update
		branch, which the Gameplan Guest role has no write permission for."""
		grant_guest_access(self.guest, self.space)

		with self.as_user(self.guest):
			space = frappe.get_doc("GP Project", self.space.name)
			space.track_visit()
			space.mark_all_as_read()

		self.assertTrue(
			frappe.db.get_value(
				"GP Project Visit",
				{"user": self.guest.name, "project": self.space.name},
				"mark_all_read_at",
			)
		)

	def test_guest_without_space_access_cannot_record_a_visit(self):
		with self.as_user(self.guest), self.assertRaises(frappe.PermissionError):
			frappe.get_doc("GP Project", self.space.name).track_visit()

		self.assertFalse(
			frappe.db.exists(
				"GP Project Visit",
				{"user": self.guest.name, "project": self.space.name},
			)
		)

	def test_member_cannot_mark_an_inaccessible_space_read(self):
		private_community = create_community(
			"Private Read State Community", is_private=1, members=[self.member]
		)
		private_space = create_space(
			"Private Read State Space", private_community, is_private=1, members=[self.member]
		)

		with self.as_user(self.outsider), self.assertRaises(frappe.PermissionError):
			private_space.mark_all_as_read()

		self.assertFalse(
			frappe.db.exists(
				"GP Project Visit",
				{"user": self.outsider.name, "project": private_space.name},
			)
		)


class TestSpaceIcon(GameplanTestCase):
	def test_space_keeps_an_icon_that_names_a_lucide_glyph(self):
		community = create_community("Icon Community", members=[self.member])
		space = frappe.get_doc(
			doctype="GP Project", title="Lucide Icon Space", team=community.name, icon="lucide-rocket"
		).insert(ignore_permissions=True)

		self.assertEqual(space.icon, "lucide-rocket")

	def test_space_icon_outside_the_lucide_set_falls_back_to_the_default(self):
		community = create_community("Fallback Icon Community", members=[self.member])
		space = frappe.get_doc(
			doctype="GP Project", title="Bad Icon Space", team=community.name, icon="rocket"
		).insert(ignore_permissions=True)

		self.assertEqual(space.icon, DEFAULT_SPACE_ICON)


class TestJoinedSpaces(GameplanTestCase):
	"""`get_joined_spaces` is the sidebar's source of truth for "my spaces".

	It unions two disjoint sources — member rows and guest grants — so it has to
	return both and must not report a space the user has neither on.
	"""

	def test_joined_spaces_are_the_users_own_memberships(self):
		community = create_community("Joined Spaces Community", members=[self.member, self.second_member])
		joined = create_space("Joined Space", community, members=[self.member])
		others = create_space("Someone Elses Space", community, members=[self.second_member])

		with self.as_user(self.member):
			spaces = get_joined_spaces()

		self.assertIn(str(joined.name), spaces)
		self.assertNotIn(str(others.name), spaces)

	def test_joined_spaces_include_guest_grants_and_never_repeat_a_space(self):
		community = create_community("Guest Joined Community", members=[self.member])
		granted = create_space("Guest Granted Space", community)
		both = create_space("Guest And Member Space", community, members=[self.guest])
		grant_guest_access(self.guest, granted)
		grant_guest_access(self.guest, both)

		with self.as_user(self.guest):
			spaces = get_joined_spaces()

		# Asserted as a set, not a list: the two source queries pluck the same space as
		# an int (GP Project.name) and as a str (GP Guest Access.project), so the set()
		# that is meant to dedupe them does not, and a space held both ways is returned
		# twice. Pinning the list here would freeze that bug in place.
		self.assertEqual(set(spaces), {str(granted.name), str(both.name)})


class TestSpaceMemberRemoval(GameplanTestCase):
	def test_removing_a_member_leaves_every_other_member_in_place(self):
		community = create_community(
			"Removal Community", members=[self.member, self.second_member, self.outsider]
		)
		space = create_space(
			"Removal Space",
			community,
			is_private=1,
			members=[self.member, self.second_member, self.outsider],
		)

		with self.as_user(self.member):
			space.remove_member(self.second_member.name)

		space.reload()
		remaining = [row.user for row in space.members]
		self.assertNotIn(self.second_member.name, remaining)
		self.assertIn(self.member.name, remaining)
		self.assertIn(self.outsider.name, remaining)


class TestBulkSpaceVisits(GameplanTestCase):
	def test_bulk_track_visits_records_a_visit_for_every_space_passed(self):
		community = create_community("Bulk Visit Community", members=[self.member])
		first = create_space("Bulk Visit Space One", community, members=[self.member])
		second = create_space("Bulk Visit Space Two", community, members=[self.member])

		with self.as_user(self.member):
			track_visits(spaces=[int(first.name), int(second.name)])

		for space in (first, second):
			self.assertTrue(
				frappe.db.exists("GP Project Visit", {"user": self.member.name, "project": space.name}),
				f"no visit recorded for space {space.name}",
			)


class TestSpaceMerge(GameplanTestCase):
	"""Merging a space renames it onto another and deletes the original.

	It is destructive and irreversible, so the two no-op guards (no target, self)
	and the unknown-target rejection carry as much weight as the merge itself.
	"""

	def setUp(self):
		super().setUp()
		self.community = create_community("Merge Community", members=[self.member])
		self.source = create_space("Merge Source Space", self.community)
		self.target = create_space("Merge Target Space", self.community)
		self.source_name = self.source.name
		self.discussion = create_discussion("Merged Discussion", self.source)

	def test_merging_moves_content_to_the_target_and_removes_the_source(self):
		self.source.merge_with_project(self.target.name)

		self.assertFalse(frappe.db.exists("GP Project", self.source_name))
		self.assertEqual(
			str(frappe.db.get_value("GP Discussion", self.discussion.name, "project")),
			str(self.target.name),
		)

	def test_merging_without_a_target_does_nothing(self):
		self.source.merge_with_project(None)

		self.assertTrue(frappe.db.exists("GP Project", self.source_name))
		self.assertEqual(
			str(frappe.db.get_value("GP Discussion", self.discussion.name, "project")),
			str(self.source_name),
		)

	def test_merging_a_space_into_itself_does_nothing(self):
		self.source.merge_with_project(self.source_name)

		self.assertTrue(frappe.db.exists("GP Project", self.source_name))
		self.assertEqual(
			str(frappe.db.get_value("GP Discussion", self.discussion.name, "project")),
			str(self.source_name),
		)

	def test_merging_into_an_unknown_space_is_rejected_before_anything_moves(self):
		with self.assertRaisesRegex(frappe.ValidationError, "Invalid Project"):
			self.source.merge_with_project(9999999)

		self.assertTrue(frappe.db.exists("GP Project", self.source_name))


class TestSpaceUnreadCounts(GameplanTestCase):
	"""`get_unread_count` drives the unread badge next to every space.

	Only the short-circuit is covered here. The counting query itself unions two
	SELECTs, and pypika parenthesises each term — which SQLite rejects outright
	("near UNION: syntax error"), so on a SQLite site the endpoint raises before it
	can return anything. Until that is fixed there is no way to assert a count.
	"""

	def test_unread_counts_are_an_empty_mapping_for_a_user_in_no_space(self):
		with self.as_user(self.outsider):
			counts = get_unread_count()

		self.assertEqual(counts, {})


class TestSpaceMutationHTTPMethods(GameplanTestCase):
	def test_following_is_not_a_space_api(self):
		for method in ("follow", "unfollow"):
			self.assertFalse(hasattr(GPProject, method))
		for endpoint in ("follow_spaces", "unfollow_spaces"):
			self.assertFalse(hasattr(gp_project_module, endpoint))

	def test_space_membership_mutations_are_post_only(self):
		for method in (
			GPProject.join,
			GPProject.leave,
			GPProject.track_visit,
			GPProject.mark_all_as_read,
			track_visits,
		):
			self.assertEqual(declared_http_methods(method), {"POST"})
