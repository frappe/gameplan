# Copyright (c) 2022, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""Space (GP Project) behaviour: archiving, activity, moving between communities,
list and search scoping, and who may join, leave, manage members or invite guests."""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from gameplan.extends.client import get_list
from gameplan.gameplan.doctype.gp_project import gp_project as gp_project_module
from gameplan.gameplan.doctype.gp_project.gp_project import (
	DEFAULT_SPACE_ICON,
	GPProject,
	get_activity,
	get_joined_spaces,
	get_unread_count,
	join_spaces,
	leave_spaces,
	mark_all_as_read,
	track_visits,
)
from gameplan.search_sqlite import GameplanSearch
from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import (
	create_community,
	create_discussion,
	create_member,
	create_page,
	create_space,
	create_task,
	declared_http_methods,
	grant_guest_access,
)


class TestSpaces(FrappeTestCase):
	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

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


class TestSpaceArchive(GameplanTestCase):
	"""Archiving retires a Space for everyone, so it has to retire everyone's pin.

	A pin outliving its Space is a sidebar entry pointing at something the SPA will
	not open. The patch
	gp_pinned_project/patches/delete_pinned_projects_for_archived_spaces.py exists
	only to clear that state out, so `archive` must not keep regenerating it.
	"""

	def setUp(self):
		super().setUp()
		self.community = create_community("Archive Community", members=[self.member, self.second_member])
		self.space = create_space("Archive Space", self.community, members=[self.member, self.second_member])

	def _pin(self, user):
		"""Pin the space as `user`.

		GPPinnedProject.before_insert stamps the session user over whatever the caller
		passed, so the pin's owner is decided by who is logged in, not by a field.
		"""
		with self.as_user(user):
			return frappe.get_doc(doctype="GP Pinned Project", project=self.space.name).insert(
				ignore_permissions=True
			)

	def test_archiving_a_space_deletes_the_pins_of_everyone_who_pinned_it(self):
		archiver_pin = self._pin(self.admin)
		other_pin = self._pin(self.second_member)

		with self.as_user(self.admin):
			frappe.get_doc("GP Project", self.space.name).archive()

		self.assertTrue(frappe.db.get_value("GP Project", self.space.name, "archived_at"))
		self.assertFalse(frappe.db.exists("GP Pinned Project", archiver_pin.name))
		self.assertFalse(frappe.db.exists("GP Pinned Project", other_pin.name))

	def test_unarchiving_a_space_does_not_bring_back_the_pins_archiving_dropped(self):
		"""Recorded, not a gap: archiving deletes the rows, so there is nothing to restore.

		Re-creating them would have to invent a sidebar position for every affected user,
		and re-pinning is one click.
		"""
		self._pin(self.second_member)

		with self.as_user(self.admin):
			space = frappe.get_doc("GP Project", self.space.name)
			space.archive()
			space.unarchive()

		self.assertIsNone(frappe.db.get_value("GP Project", self.space.name, "archived_at"))
		self.assertFalse(frappe.db.exists("GP Pinned Project", {"project": self.space.name}))


class TestSpaceCommunityMove(GameplanTestCase):
	"""Moving a Space rewrites the Community cached on everything inside it.

	`team` is denormalised onto every doctype in PROJECT_TEAM_DOCTYPES, so the move
	has to rewrite those rows — and only the ones belonging to the Space that moved.
	"""

	def setUp(self):
		super().setUp()
		self.origin = create_community("Move Origin Community", members=[self.member])
		self.destination = create_community("Move Destination Community", members=[self.member])
		self.space = create_space("Moving Space", self.origin)
		self.sibling = create_space("Staying Space", self.origin)

	def _content(self, space):
		"""A discussion, a task and a page in `space`, each tagged with its Community.

		Seeded directly because nothing writes `team` on insert — the column is only
		ever filled by the move under test and by GP Discussion's own move — so without
		this the "other Spaces are untouched" assertion would compare NULL with NULL and
		hold however wide the update ran.
		"""
		rows = {
			"GP Discussion": create_discussion(f"{space.title} Discussion", space).name,
			"GP Task": create_task(f"{space.title} Task", space).name,
			"GP Page": create_page(f"{space.title} Page", space).name,
		}
		for doctype, name in rows.items():
			frappe.db.set_value(doctype, name, "team", space.team, update_modified=False)
		return rows

	def _teams(self, rows):
		return {doctype: frappe.db.get_value(doctype, name, "team") for doctype, name in rows.items()}

	def test_moving_a_space_retags_its_own_content_and_nothing_else(self):
		moved = self._content(self.space)
		untouched = self._content(self.sibling)

		frappe.get_doc("GP Project", self.space.name).move_to_team(self.destination.name)

		self.assertEqual(frappe.db.get_value("GP Project", self.space.name, "team"), self.destination.name)
		self.assertEqual(self._teams(moved), dict.fromkeys(moved, self.destination.name))
		self.assertEqual(self._teams(untouched), dict.fromkeys(untouched, self.origin.name))

	def test_moving_a_space_into_the_community_it_is_already_in_writes_nothing(self):
		rows = self._content(self.space)
		before = frappe.db.get_value("GP Project", self.space.name, "modified")

		frappe.get_doc("GP Project", self.space.name).move_to_team(self.origin.name)

		# The Space's own `modified` is the only witness: re-running the move with the
		# same Community would set every column to the value it already holds, so the
		# save is all that separates the guarded path from the unguarded one.
		self.assertEqual(frappe.db.get_value("GP Project", self.space.name, "modified"), before)
		self.assertEqual(self._teams(rows), dict.fromkeys(rows, self.origin.name))


class TestBulkSpaceMembership(GameplanTestCase):
	"""`join_spaces` / `leave_spaces` back the sidebar's multi-select membership editor."""

	def setUp(self):
		super().setUp()
		self.community = create_community("Bulk Membership Community", members=[self.member])
		self.first = create_space("Bulk Membership Space One", self.community)
		self.second = create_space("Bulk Membership Space Two", self.community)

	def _is_member(self, space):
		return bool(
			frappe.db.exists(
				"GP Member",
				{"parenttype": "GP Project", "parent": space.name, "user": self.member.name},
			)
		)

	def _add_member(self, space):
		space.append("members", {"user": self.member.name})
		space.save(ignore_permissions=True)

	def test_joining_in_bulk_adds_the_user_to_every_space_passed(self):
		with self.as_user(self.member):
			join_spaces(spaces=[int(self.first.name), int(self.second.name)])

		self.assertTrue(self._is_member(self.first))
		self.assertTrue(self._is_member(self.second))

	def test_joining_no_spaces_at_all_is_a_no_op(self):
		"""The SPA sends the selection as-is, so an empty one has to be a no-op rather
		than an iteration over None."""
		with self.as_user(self.member):
			self.assertIsNone(join_spaces())
			self.assertIsNone(join_spaces(spaces=[]))

		self.assertFalse(self._is_member(self.first))
		self.assertFalse(self._is_member(self.second))

	def test_leaving_in_bulk_removes_the_user_from_every_space_passed(self):
		self._add_member(self.first)
		self._add_member(self.second)

		with self.as_user(self.member):
			leave_spaces(spaces=[int(self.first.name), int(self.second.name)])

		self.assertFalse(self._is_member(self.first))
		self.assertFalse(self._is_member(self.second))

	def test_leaving_no_spaces_at_all_is_a_no_op(self):
		self._add_member(self.first)
		self._add_member(self.second)

		with self.as_user(self.member):
			self.assertIsNone(leave_spaces())
			self.assertIsNone(leave_spaces(spaces=[]))

		self.assertTrue(self._is_member(self.first))
		self.assertTrue(self._is_member(self.second))


class TestSpaceListVisibility(GameplanTestCase):
	def test_the_space_list_hides_a_private_space_the_user_is_not_in(self):
		"""`GPProject.get_list_query` is the only thing scoping the Space list endpoint.

		`apply_custom_filters` keeps the unfiltered query when the hook hands back None,
		so losing the filter does not fail loudly — it returns every Space on the site,
		private ones included.
		"""
		community = create_community("Listed Community", members=[self.member, self.second_member])
		public = create_space("Listed Public Space", community)
		private = create_space("Listed Private Space", community, is_private=1, members=[self.second_member])

		def listed_for(user):
			with self.as_user(user):
				rows = get_list("GP Project", fields=["name"], filters={"team": community.name}, limit=100)
			return {str(row["name"]) for row in rows}

		self.assertIn(str(public.name), listed_for(self.member))
		self.assertNotIn(str(private.name), listed_for(self.member))
		# A global admin gets no criterion at all, so the filter has to hand the query
		# back whole rather than narrow it to nothing.
		self.assertIn(str(private.name), listed_for(self.admin))


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
		"""A guest reaches a Space through a GP Guest Access grant, never a member row.

		That grant is the only thing `require_view_access` accepts from a guest, so this
		is the whole guest path through `track_visit`'s insert branch.
		"""
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
		"""The second visit updates the existing row instead of inserting a second one.

		`track_visit` is a get-then-insert, so only a repeat call reaches the update
		branch. One row per (user, Space) is what the unread badge rests on: with two, a
		discussion satisfies both read-tracking predicates on different joined rows and
		the count doubles — see TestSpaceUnreadCounts.

		It says nothing about the GP Project Visit role table. Both branches save with
		`ignore_permissions=True`, so what that table grants a guest never comes into it;
		what stands between a guest and someone else's Space is `require_view_access`,
		pinned by the two tests below.
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
		"""Marking read after a visit stamps the row `track_visit` already created.

		Same get-then-insert split as the repeat visit above, and equally independent of
		the role table — both branches save with `ignore_permissions=True`. The row count
		is asserted because `mark_all_read_at` alone reads the same whether the stamp
		landed on the existing visit or on a second one.
		"""
		grant_guest_access(self.guest, self.space)

		with self.as_user(self.guest):
			space = frappe.get_doc("GP Project", self.space.name)
			space.track_visit()
			space.mark_all_as_read()

		self.assertEqual(
			frappe.db.count("GP Project Visit", {"user": self.guest.name, "project": self.space.name}),
			1,
		)
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

		# Asserted as an exact list, not a set: the two source queries pluck the same
		# space from differently typed columns (GP Project.name is an integer,
		# GP Guest Access.project a string), and a set of mixed types cannot dedupe
		# them. A set assertion would pass while the sidebar showed the space twice.
		self.assertEqual(spaces, [str(both.name), str(granted.name)])

	def test_joined_spaces_are_strings_so_the_sidebar_can_match_them(self):
		"""The endpoint is typed `string[]` in the SPA and compared with `includes()`,
		so an integer space name would silently never match."""
		community = create_community("String Joined Community", members=[self.member])
		space = create_space("String Joined Space", community, members=[self.member])

		with self.as_user(self.member):
			spaces = get_joined_spaces()

		self.assertEqual(spaces, [str(space.name)])
		for name in spaces:
			self.assertIsInstance(name, str)


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
		"""Covers the string form because that is the only one that ever arrives.

		GP Project autoincrements, so `self.name` is an int, while MergeSpaceDialog sends
		the combobox value as a string. A guard that compares before coercing sees
		`"7" != 7`, falls through, and the rename below deletes the space and leaves every
		discussion in it pointing at nothing.
		"""
		for target in (str(self.source_name), int(self.source_name)):
			with self.subTest(target=target):
				frappe.get_doc("GP Project", self.source_name).merge_with_project(target)

				self.assertTrue(frappe.db.exists("GP Project", self.source_name))
				self.assertEqual(
					str(frappe.db.get_value("GP Discussion", self.discussion.name, "project")),
					str(self.source_name),
				)

	def test_merging_into_an_unknown_space_is_rejected_before_anything_moves(self):
		with self.assertRaisesRegex(frappe.ValidationError, "Invalid Project"):
			self.source.merge_with_project(9999999)

		self.assertTrue(frappe.db.exists("GP Project", self.source_name))

	def test_space_manager_can_merge_two_spaces_they_manage(self):
		private_community = create_community("Merge Manager Community", members=[self.member])
		source = create_space("Managed Merge Source", private_community, is_private=1, members=[self.member])
		target = create_space("Managed Merge Target", private_community, is_private=1, members=[self.member])
		source_name = source.name
		discussion = create_discussion("Managed Merge Discussion", source)

		with self.as_user(self.member):
			frappe.get_doc("GP Project", source_name).merge_with_project(target.name)

		self.assertFalse(frappe.db.exists("GP Project", source_name))
		self.assertEqual(
			str(frappe.db.get_value("GP Discussion", discussion.name, "project")),
			str(target.name),
		)

	def test_manager_of_only_the_source_cannot_merge_into_a_space_they_dont_manage(self):
		"""The merge moves every discussion, task and page into the target, so managing
		the source alone is not enough — without a gate on the target it is a way to
		push content into a space the user has no rights over."""
		community = create_community("Merge Target Gate Community", members=[self.member, self.second_member])
		source = create_space("Gated Merge Source", community, is_private=1, members=[self.member])
		target = create_space("Gated Merge Target", community, is_private=1, members=[self.second_member])
		source_name = source.name
		discussion = create_discussion("Gated Merge Discussion", source)

		with self.as_user(self.member), self.assertRaises(frappe.PermissionError):
			frappe.get_doc("GP Project", source_name).merge_with_project(target.name)

		self.assertTrue(frappe.db.exists("GP Project", source_name))
		self.assertEqual(
			str(frappe.db.get_value("GP Discussion", discussion.name, "project")),
			str(source_name),
		)

	def test_an_unknown_merge_target_is_rejected_the_same_way_a_forbidden_one_is(self):
		"""Otherwise the endpoint is an id oracle for the whole site.

		The unknown-target check runs `frappe.db.exists`, so if it is reached before the
		permission gate, any space manager can tell "Invalid Project 999" (no such space)
		from "Only space managers can merge spaces" (it exists, you just can't have it) and
		enumerate every GP Project on the site, private ones included.
		"""
		community = create_community("Merge Oracle Community", members=[self.member, self.second_member])
		source = create_space("Oracle Merge Source", community, is_private=1, members=[self.member])
		forbidden = create_space("Oracle Merge Target", community, is_private=1, members=[self.second_member])

		with self.as_user(self.member):
			with self.assertRaises(frappe.PermissionError):
				frappe.get_doc("GP Project", source.name).merge_with_project(9999999)
			with self.assertRaises(frappe.PermissionError):
				frappe.get_doc("GP Project", source.name).merge_with_project(forbidden.name)

	def test_guest_cannot_merge_a_space_they_hold_a_member_row_on(self):
		"""A guest with a GP Member row on a private space passes can_manage_space.

		Guest access is read-and-participate; merging destroys a space. Only the doctype
		role table stands between a guest and this method today, and that is the wrong
		place for a business rule — `can_invite_guest` sets the precedent of ruling guests
		out before the manage check.
		"""
		community = create_community("Guest Merge Community", members=[self.member])
		source = create_space("Guest Merge Source", community, is_private=1, members=[self.guest])
		target = create_space("Guest Merge Target", community, is_private=1, members=[self.guest])
		source_name = source.name
		discussion = create_discussion("Guest Merge Discussion", source)

		with self.as_user(self.guest), self.assertRaises(frappe.PermissionError):
			frappe.get_doc("GP Project", source_name).merge_with_project(target.name)

		self.assertTrue(frappe.db.exists("GP Project", source_name))
		self.assertEqual(
			str(frappe.db.get_value("GP Discussion", discussion.name, "project")),
			str(source_name),
		)

	def test_manager_of_only_the_target_cannot_merge_a_space_they_dont_manage(self):
		community = create_community("Merge Source Gate Community", members=[self.member, self.second_member])
		source = create_space("Ungated Merge Source", community, is_private=1, members=[self.second_member])
		target = create_space("Ungated Merge Target", community, is_private=1, members=[self.member])
		source_name = source.name

		with self.as_user(self.member), self.assertRaises(frappe.PermissionError):
			frappe.get_doc("GP Project", source_name).merge_with_project(target.name)

		self.assertTrue(frappe.db.exists("GP Project", source_name))


class TestSpaceUnreadCounts(GameplanTestCase):
	"""`get_unread_count` drives the unread badge next to every space.

	Two read-tracking regimes feed one number. A space the user has marked read
	counts every discussion posted after that space-level timestamp; a space that
	has never been marked read falls back to per-discussion visits. A space is
	counted under exactly one regime, and both must ignore other users' rows.
	"""

	MARKED_READ_AT = "2026-01-02 00:00:00"

	def setUp(self):
		super().setUp()
		self.community = create_community("Unread Count Community", members=[self.member, self.second_member])

	def _space(self, title):
		return create_space(title, self.community, members=[self.member, self.second_member])

	def _discussion(self, title, space, last_post_at):
		discussion = create_discussion(title, space)
		frappe.db.set_value(
			"GP Discussion", discussion.name, "last_post_at", last_post_at, update_modified=False
		)
		return discussion

	def _visit_space(self, space, user, last_visit, mark_all_read_at=None):
		return frappe.get_doc(
			doctype="GP Project Visit",
			user=user.name,
			project=space.name,
			last_visit=last_visit,
			mark_all_read_at=mark_all_read_at,
		).insert(ignore_permissions=True)

	def _visit_discussion(self, discussion, user, last_visit):
		return frappe.get_doc(
			doctype="GP Discussion Visit",
			user=user.name,
			discussion=discussion.name,
			last_visit=last_visit,
		).insert(ignore_permissions=True)

	def test_unread_counts_are_an_empty_mapping_for_a_user_in_no_space(self):
		with self.as_user(self.outsider):
			counts = get_unread_count()

		self.assertEqual(counts, {})

	def test_unread_counts_cover_every_read_tracking_regime_at_once(self):
		"""One assertion over five spaces, because the interesting failures are spaces
		that should be absent (fully read) or counted under the wrong regime — neither
		of which a per-space assertion would notice."""
		marked_read = self._space("Marked Read Space")
		self._discussion("Read Before Mark", marked_read, "2026-01-01 09:00:00")
		self._discussion("Posted After Mark", marked_read, "2026-01-03 09:00:00")
		self._discussion("Posted Later Still", marked_read, "2026-01-04 09:00:00")
		self._visit_space(marked_read, self.member, "2026-01-02 00:00:00", self.MARKED_READ_AT)

		fully_read = self._space("Fully Read Space")
		self._discussion("Everything Read", fully_read, "2026-01-01 09:00:00")
		self._visit_space(fully_read, self.member, "2026-01-02 00:00:00", self.MARKED_READ_AT)

		never_visited = self._space("Never Visited Space")
		self._discussion("Unseen One", never_visited, "2026-01-01 09:00:00")
		self._discussion("Unseen Two", never_visited, "2026-01-05 09:00:00")

		visited_not_marked = self._space("Visited Not Marked Space")
		seen = self._discussion("Seen Discussion", visited_not_marked, "2026-01-01 09:00:00")
		unseen = self._discussion("Unseen Since Visit", visited_not_marked, "2026-01-06 09:00:00")
		self._visit_space(visited_not_marked, self.member, "2026-01-02 00:00:00")
		self._visit_discussion(seen, self.member, "2026-01-02 00:00:00")
		self._visit_discussion(unseen, self.member, "2026-01-02 00:00:00")

		self._space("Empty Space")

		# Another member has read everything everywhere. None of it may leak into the
		# counts below — every join in the query is scoped to the session user.
		for space in (marked_read, fully_read, never_visited, visited_not_marked):
			self._visit_space(space, self.second_member, "2026-01-09 00:00:00", "2026-01-09 00:00:00")
		for discussion in (seen, unseen):
			self._visit_discussion(discussion, self.second_member, "2026-01-09 00:00:00")

		with self.as_user(self.member):
			counts = get_unread_count()

		self.assertEqual(
			self._normalized(counts),
			{
				str(marked_read.name): 2,
				str(never_visited.name): 2,
				str(visited_not_marked.name): 1,
			},
		)

	def test_unread_counts_stay_correct_when_a_space_has_duplicate_visit_rows(self):
		"""Two visit rows for one (user, space) must not count every discussion twice.

		GP Project Visit indexes (user, project) without a uniqueness constraint and
		`track_visit` is a get-then-insert with no lock, so duplicate rows are reachable.
		The two read-tracking predicates are exclusive per JOINED ROW, not per discussion:
		with one row carrying `mark_all_read_at` and one without, both fire for the same
		discussion and the badge doubles.
		"""
		space = self._space("Duplicate Visit Space")
		self._discussion("Unread One", space, "2026-01-03 09:00:00")
		self._discussion("Unread Two", space, "2026-01-04 09:00:00")
		self._discussion("Unread Three", space, "2026-01-05 09:00:00")
		self._visit_space(space, self.member, "2026-01-02 00:00:00", self.MARKED_READ_AT)
		self._visit_space(space, self.member, "2026-01-02 00:00:00")

		with self.as_user(self.member):
			counts = get_unread_count()

		self.assertEqual(self._normalized(counts), {str(space.name): 3})

	def test_a_discussion_posted_exactly_at_the_mark_read_timestamp_counts_as_read(self):
		""" "Mark all read" means everything posted up to and including now.

		`mark_all_as_read` stamps the visit with `frappe.utils.now()` and a post stamps
		`last_post_at` off the same clock, so the two land on the same second whenever a
		user marks a Space read as a post arrives. A `>=` boundary would leave the badge
		showing a discussion the user just cleared, and it would never clear.
		"""
		space = self._space("Mark Read Boundary Space")
		self._discussion("Posted At The Mark", space, self.MARKED_READ_AT)
		self._visit_space(space, self.member, self.MARKED_READ_AT, self.MARKED_READ_AT)

		with self.as_user(self.member):
			counts = get_unread_count()

		self.assertEqual(self._normalized(counts), {})

	def test_a_discussion_last_visited_exactly_when_it_was_last_posted_counts_as_read(self):
		"""The same boundary on the per-discussion regime: opening a discussion writes
		the visit with `now()`, so a visit equal to `last_post_at` is the reader having
		seen the newest post, not having missed it."""
		space = self._space("Visit Boundary Space")
		discussion = self._discussion("Read At The Post", space, "2026-01-03 09:00:00")
		self._visit_discussion(discussion, self.member, "2026-01-03 09:00:00")

		with self.as_user(self.member):
			counts = get_unread_count()

		self.assertEqual(self._normalized(counts), {})

	def test_unread_counts_are_limited_to_the_users_own_spaces(self):
		"""The joined-space list gated only the early return, not the counting query, so
		anyone in at least one space was handed unread counts for every space on the
		site — including private ones they cannot open."""
		mine = self._space("Own Unread Space")
		self._discussion("Own Unread Discussion", mine, "2026-01-03 09:00:00")

		foreign_community = create_community("Foreign Unread Community", members=[self.outsider])
		theirs = create_space(
			"Foreign Unread Space", foreign_community, is_private=1, members=[self.outsider]
		)
		self._discussion("Foreign Unread Discussion", theirs, "2026-01-03 09:00:00")

		with self.as_user(self.member):
			counts = get_unread_count()

		self.assertEqual(self._normalized(counts), {str(mine.name): 1})

	def _normalized(self, counts):
		"""Counts keyed by space name as a string.

		Keys arrive as whatever the Link column stores (int on MariaDB, str on SQLite);
		what these tests assert is which spaces appear and with what count.
		"""
		return {str(space): int(count) for space, count in counts.items()}


class TestSpaceMutationHTTPMethods(GameplanTestCase):
	def test_following_is_not_a_space_api(self):
		for method in ("follow", "unfollow"):
			self.assertFalse(hasattr(GPProject, method))
		for endpoint in ("follow_spaces", "unfollow_spaces"):
			self.assertFalse(hasattr(gp_project_module, endpoint))

	def test_link_previews_are_not_a_space_api(self):
		"""No caller ever asked a Space for a URL's meta tags. Keeping the helper kept an
		outbound HTTP fetch reachable from a doctype controller for no reason."""
		self.assertFalse(hasattr(gp_project_module, "get_meta_tags"))

	def test_space_does_not_override_document_serialisation(self):
		"""`as_dict` was overridden only to call super() and return the result. A no-op
		override shadows the framework method and is a place for behaviour to rot in."""
		self.assertNotIn("as_dict", vars(GPProject))

	def test_space_membership_mutations_are_post_only(self):
		for method in (
			GPProject.join,
			GPProject.leave,
			GPProject.track_visit,
			GPProject.mark_all_as_read,
			track_visits,
		):
			self.assertEqual(declared_http_methods(method), {"POST"})
