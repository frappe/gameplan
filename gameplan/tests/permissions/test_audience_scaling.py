from time import perf_counter
from unittest.mock import patch

import frappe

from gameplan.permissions import (
	can_view_content,
	can_view_space,
	get_audience_roles,
	users_who_can_view_content,
	users_who_can_view_space,
)
from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import create_community, create_space
from gameplan.visibility import VISIBILITY_MEMBER_ACCESS


class TestAudienceScaling(GameplanTestCase):
	def test_batch_matches_scalar_permissions_without_per_user_role_reads(self):
		community = create_community("Audience", members=[self.member])
		space = create_space("Members", community, visibility=VISIBILITY_MEMBER_ACCESS, members=[self.member])
		users = [
			self.member.name,
			self.second_member.name,
			self.admin.name,
			self.guest.name,
			"Guest",
			"Administrator",
		]
		expected = [user for user in users if can_view_space(user, space.name)]
		with patch.object(frappe, "get_roles", side_effect=AssertionError("Per-user role lookup")):
			self.assertEqual(users_who_can_view_space(users, space.name), expected)

	def test_personal_content_audience_uses_batched_roles_and_excludes_anonymous(self):
		page = frappe.get_doc(doctype="GP Page", title="Personal", content="Private", owner=self.member.name)
		users = [self.member.name, self.second_member.name, self.admin.name, "Guest", "Administrator"]
		expected = [user for user in users if can_view_content(user, page)]
		with patch.object(frappe, "get_roles", side_effect=AssertionError("Per-user role lookup")):
			self.assertEqual(users_who_can_view_content(users, page), expected)

	def test_large_community_preview_has_no_per_recipient_role_reads(self):
		community = create_community("Large audience", members=[self.member])
		for index in range(18):
			create_space(f"Audience {index}", community)
		users = [self.member.name, self.admin.name, self.guest.name]
		roles = {user: frappe.get_roles(user) for user in users}
		users += [f"scale_{index}@example.test" for index in range(32146)]
		lookups = 0

		def counted_roles(user=None):
			nonlocal lookups
			lookups += 1
			return roles.get(user, ["Gameplan Member"])

		with (
			self.as_user("Administrator"),
			patch("gameplan.mixins.visibility.gameplan_users", return_value=users),
			patch.object(frappe, "get_roles", new=counted_roles),
			patch("gameplan.mixins.visibility.get_audience_roles", wraps=get_audience_roles) as roles_query,
		):
			started = perf_counter()
			impact = community.get_visibility_change_impact(VISIBILITY_MEMBER_ACCESS)
			elapsed = perf_counter() - started
		print(f"Visibility preview: {len(users)} candidates, 19 Spaces, {lookups} role reads, {elapsed:.3f}s")
		self.assertEqual(lookups, 0)
		self.assertEqual(roles_query.call_count, 1)
		self.assertEqual(impact["users_losing_access"], 32146)
		self.assertEqual(frappe.db.get_value("GP Team", community.name, "visibility"), "General")

	def test_role_precedence_and_system_managers_match_the_scalar_rules(self):
		community = create_community("Role precedence")
		space = create_space("General", community)
		self.guest.add_roles("Gameplan Member")
		self.second_member.add_roles("System Manager", "Gameplan Guest")
		users = [self.guest.name, self.second_member.name, "Guest", "Administrator"]
		expected = [user for user in users if can_view_space(user, space.name)]
		self.assertEqual(users_who_can_view_space(users, space.name), expected)

	def test_anonymous_is_not_the_owner_of_personal_content(self):
		page = frappe.get_doc(doctype="GP Page", title="Personal", content="Private", owner="Guest")
		self.assertEqual(users_who_can_view_content(["Guest"], page), [])

	def test_unread_audience_has_no_per_user_role_reads(self):
		from gameplan.gameplan.doctype.gp_unread_record.gp_unread_record import GPUnreadRecord

		community = create_community("Unread audience", members=[self.member])
		space = create_space("General", community)
		with patch.object(frappe, "get_roles", side_effect=AssertionError("Per-user role lookup")):
			self.assertIn(self.member.name, GPUnreadRecord._get_project_members(space.name))

	def test_private_community_outsiders_get_no_unread_records_or_events(self):
		from gameplan.realtime import UNREAD_COUNTS_CHANGED

		community = create_community(
			"Private unread", visibility=VISIBILITY_MEMBER_ACCESS, members=[self.member]
		)
		space = create_space("General", community)
		with self.as_user(self.member), patch("frappe.realtime.publish_realtime") as publish:
			discussion = frappe.get_doc(
				doctype="GP Discussion", title="Private topic", project=space.name, content="Body"
			).insert()
		self.assertFalse(
			frappe.db.exists("GP Unread Record", {"discussion": discussion.name, "user": self.outsider.name})
		)
		self.assertNotIn(
			self.outsider.name,
			[
				call.kwargs.get("user")
				for call in publish.call_args_list
				if call.args and call.args[0] == UNREAD_COUNTS_CHANGED
			],
		)

	def test_anonymous_cannot_enter_task_comment_audiences(self):
		from gameplan.tests.fixtures import create_task

		with patch.dict(frappe.conf, gameplan_public_access_enabled=1, gameplan_demo_enabled=0):
			community = create_community("Public task", visibility="Anonymous")
			space = create_space("Public task Space", community, visibility="Anonymous")
			task = create_task("Private task", space, owner=self.member)
			reply = frappe.get_doc(
				doctype="GP Comment",
				reference_doctype="GP Task",
				reference_name=task.name,
				content="Private reply",
			)
			self.assertFalse(can_view_content("Guest", reply))
			self.assertEqual(users_who_can_view_content(["Guest"], reply), [])
