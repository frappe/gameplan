# Copyright (c) 2022, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from gameplan.gameplan.doctype.gp_team.gp_team import update_joined_teams
from gameplan.gameplan.doctype.gp_user_profile.gp_user_profile import get_session_user_profile
from gameplan.tests.fixtures import create_discussion, create_member, create_space


class TestGPTeam(FrappeTestCase):
	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def test_after_insert_creates_general_space(self):
		team = frappe.get_doc(doctype="GP Team", title="General Space Team").insert(ignore_permissions=True)

		spaces = frappe.db.get_all("GP Project", filters={"team": team.name}, fields=["title", "is_private"])
		self.assertEqual(len(spaces), 1)
		self.assertEqual(spaces[0].title, "General")
		# General must be public so all community members can see it by default.
		self.assertEqual(spaces[0].is_private, 0)

	def test_after_insert_skips_general_when_space_already_exists(self):
		team = frappe.get_doc(doctype="GP Team", title="Existing Space Team").insert(ignore_permissions=True)
		# Hook already created exactly one General space.
		self.assertEqual(frappe.db.count("GP Project", {"team": team.name}), 1)

		# Re-running the hook must not duplicate it (idempotency rule).
		team.create_general_space()
		self.assertEqual(frappe.db.count("GP Project", {"team": team.name}), 1)

	def test_skip_general_space_flag_suppresses_hook(self):
		team = frappe.new_doc("GP Team")
		team.title = "Suppressed Space Team"
		team.flags.skip_general_space = True
		team.insert(ignore_permissions=True)

		self.assertEqual(frappe.db.count("GP Project", {"team": team.name}), 0)

	def test_update_joined_teams_saves_profile_community_order(self):
		user = create_member("community-order@example.com", "Community Order")
		first_team = frappe.get_doc(doctype="GP Team", title="Order First Team").insert(
			ignore_permissions=True
		)
		second_team = frappe.get_doc(doctype="GP Team", title="Order Second Team").insert(
			ignore_permissions=True
		)

		frappe.set_user(user.name)
		ordered_teams = [second_team.name, first_team.name]

		self.assertEqual(update_joined_teams(ordered_teams), ordered_teams)
		self.assertEqual(frappe.parse_json(get_session_user_profile().community_order), ordered_teams)

	def test_update_joined_teams_saves_profile_sidebar_badge_style(self):
		user = create_member("sidebar-badge-style@example.com", "Sidebar Badge Style")
		team = frappe.get_doc(doctype="GP Team", title="Badge Style Team").insert(ignore_permissions=True)

		frappe.set_user(user.name)

		self.assertEqual(update_joined_teams([team.name], "Dot"), [team.name])
		self.assertEqual(get_session_user_profile().sidebar_badge_style, "Dot")

	def test_update_joined_teams_rejects_invalid_sidebar_badge_style(self):
		user = create_member("invalid-sidebar-badge-style@example.com", "Invalid Badge Style")
		team = frappe.get_doc(doctype="GP Team", title="Invalid Badge Style Team").insert(
			ignore_permissions=True
		)

		frappe.set_user(user.name)

		self.assertRaises(frappe.ValidationError, update_joined_teams, [team.name], "Banner")

	def test_merge_into_team_moves_spaces_members_and_archives_source(self):
		source_member = create_member("merge-source-member@example.com", "Merge Source Member")
		source = frappe.get_doc(doctype="GP Team", title="Merge Source Team").insert(ignore_permissions=True)
		target = frappe.get_doc(doctype="GP Team", title="Merge Target Team").insert(ignore_permissions=True)
		source.add_member(source_member.name, is_admin=1)
		source.save(ignore_permissions=True)
		project = create_space("Merge Source Space", source.name)
		discussion = create_discussion("Merge Source Discussion", project.name)
		task = frappe.get_doc(doctype="GP Task", title="Merge Source Task", project=project.name).insert(
			ignore_permissions=True
		)
		page = frappe.get_doc(doctype="GP Page", title="Merge Source Page", project=project.name).insert(
			ignore_permissions=True
		)

		source.merge_into_team(target.name)

		source.reload()
		target.reload()
		self.assertTrue(source.archived_at)
		self.assertTrue(target.get_member(source_member.name).is_admin)
		self.assertEqual(frappe.db.get_value("GP Project", project.name, "team"), target.name)
		self.assertEqual(frappe.db.get_value("GP Discussion", discussion.name, "team"), target.name)
		self.assertEqual(frappe.db.get_value("GP Task", task.name, "team"), target.name)
		self.assertEqual(frappe.db.get_value("GP Page", page.name, "team"), target.name)
