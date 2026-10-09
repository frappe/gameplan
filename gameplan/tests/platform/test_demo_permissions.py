# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""Keep the bundled fixture useful for manual permission testing."""

import json
import os
from itertools import product
from unittest.mock import patch

import frappe

from gameplan.demo.demo import FIXTURE_DIR
from gameplan.demo.seeder import Seeder
from gameplan.permissions import can_manage_community, can_manage_space, can_view_community, can_view_space
from gameplan.public_access import (
	VISIBILITY_ANONYMOUS,
	VISIBILITY_GENERAL,
	VISIBILITY_TIERS,
	find_anonymous_readable_drift,
)
from gameplan.tests.base import GameplanTestCase


class TestDemoPermissions(GameplanTestCase):
	def setUp(self):
		super().setUp()
		with open(os.path.join(FIXTURE_DIR, "events.jsonl"), encoding="utf-8") as fixture:
			self.events = [json.loads(line) for line in fixture if line.strip()]
		self.seeder = Seeder(FIXTURE_DIR)
		# Permission declarations do not need uploads or the historical discussion replay.
		with patch.object(self.seeder, "_file_url", return_value=None):
			for event in self.events:
				if event["type"] in {"user", "community", "space", "archive"}:
					self.seeder._replay(event)
		self.seeder._apply_deferred_archives()
		self.addCleanup(frappe.db.rollback)

	def test_all_nine_active_community_and_space_tier_combinations_exist(self):
		combinations = set()
		for event in self.events:
			if event["type"] != "space":
				continue
			space = self.space(event["id"])
			community = frappe.get_doc("GP Team", space.team)
			if not space.archived_at and not community.archived_at:
				combinations.add((community.visibility, space.visibility))
		self.assertEqual(combinations, set(product(VISIBILITY_TIERS, repeat=2)))

	def test_logged_out_access_requires_both_tiers_and_no_archive(self):
		with patch.dict(frappe.conf, gameplan_public_access_enabled=1, gameplan_demo_enabled=0):
			for event in self.events:
				if event["type"] != "space":
					continue
				space = self.space(event["id"])
				community = frappe.get_doc("GP Team", space.team)
				expected = (
					space.visibility == community.visibility == VISIBILITY_ANONYMOUS
					and not space.archived_at
					and not community.archived_at
				)
				self.assertEqual(can_view_space("Guest", space), bool(expected), event["id"])
			self.assertEqual(find_anonymous_readable_drift(), [])

	def test_public_switch_off_closes_every_space_to_logged_out_visitors(self):
		with patch.dict(frappe.conf, gameplan_public_access_enabled=0):
			for event in self.events:
				if event["type"] == "space":
					self.assertFalse(can_view_space("Guest", self.space(event["id"])))

	def test_members_and_nonmembers_have_distinct_read_and_manage_access(self):
		priya = self.user("priya")
		dev = self.user("dev")
		self.assertFalse(can_view_community(dev, "studio"))
		self.assertFalse(can_view_space(dev, self.space("announcements")))
		self.assertFalse(can_view_space(dev, self.space("watercooler")))
		self.assertTrue(can_view_community(priya, "studio"))
		self.assertTrue(can_view_space(priya, self.space("announcements")))
		self.assertFalse(can_manage_space(priya, self.space("announcements")))
		self.assertTrue(can_view_community(priya, "marketing-hub"))
		self.assertTrue(can_view_space(priya, self.space("player-feedback")))
		self.assertTrue(can_view_space(priya, self.space("creators-press")))
		self.assertFalse(can_view_space(priya, self.space("marketing")))
		self.assertFalse(can_view_space(priya, self.space("audio-music")))
		self.assertTrue(can_view_space(self.user("sam"), self.space("audio-music")))
		self.assertTrue(can_manage_space(self.user("sam"), self.space("audio-music")))

	def test_global_and_community_admins_are_scoped_correctly(self):
		maya = self.user("maya")
		chloe = self.user("chloe")
		for community in ("common-room", "studio", "marketing-hub", "project-bluebird"):
			self.assertTrue(can_manage_community(maya, community))
		self.assertTrue(can_manage_community(chloe, "marketing-hub"))
		self.assertFalse(can_manage_community(chloe, "common-room"))
		self.assertTrue(can_manage_space(chloe, self.space("player-feedback")))
		self.assertTrue(can_manage_space(chloe, self.space("creators-press")))
		self.assertFalse(can_manage_space(chloe, self.space("game-design")))

	def test_guest_grants_do_not_grant_management_or_sibling_access(self):
		felix = self.user("felix")
		self.assertTrue(can_view_community(felix, "studio"))
		self.assertFalse(can_view_community(felix, "marketing-hub"))
		for key in ("engineering", "audio-music", "announcements", "watercooler"):
			self.assertTrue(can_view_space(felix, self.space(key)), key)
			self.assertFalse(can_manage_space(felix, self.space(key)), key)
		for key in ("marketing", "player-feedback", "creators-press", "pitch-room", "prototype-builds"):
			self.assertFalse(can_view_space(felix, self.space(key)), key)
		self.assertFalse(can_manage_community(felix, "studio"))
		with self.as_user(felix):
			frappe.get_doc("GP Team", "studio").as_dict()
		with patch.dict(frappe.conf, gameplan_public_access_enabled=1, gameplan_demo_enabled=0):
			self.assertTrue(can_view_space(felix, self.space("releases")))
			self.assertTrue(can_view_space(felix, self.space("qa-playtests")))
			self.assertFalse(can_view_space("Guest", self.space("qa-playtests")))
		with patch.dict(frappe.conf, gameplan_public_access_enabled=0):
			self.assertFalse(can_view_space(felix, self.space("releases")))
			self.assertTrue(can_view_space(felix, self.space("engineering")))

	def test_archived_spaces_are_readable_to_members_but_reject_new_content(self):
		space = self.space("qa-playtests")
		self.assertTrue(space.archived_at)
		self.assertTrue(frappe.db.get_value("GP Team", "project-bluebird", "archived_at"))
		with self.as_user(self.user("dev")):
			self.assertTrue(can_view_space(frappe.session.user, space))
			with self.assertRaises(frappe.ValidationError):
				frappe.get_doc(
					doctype="GP Discussion", title="Archived test", content="<p>Test</p>", project=space.name
				).insert()

	def test_guest_access_revocation_closes_the_space_and_private_shell(self):
		felix = self.user("felix")
		grants = frappe.get_all("GP Guest Access", filters={"user": felix, "team": "studio"}, pluck="name")
		self.assertTrue(grants)
		for grant in grants:
			frappe.delete_doc("GP Guest Access", grant)
		self.assertFalse(can_view_community(felix, "studio"))
		self.assertFalse(can_view_space(felix, self.space("announcements")))
		self.assertFalse(can_view_space(felix, self.space("watercooler")))

	def test_removing_a_space_member_revokes_read_and_manage_access(self):
		space = self.space("audio-music")
		sam = self.user("sam")
		self.assertTrue(can_view_space(sam, space))
		space.remove_member(sam)
		self.assertFalse(can_view_space(sam, space))
		self.assertFalse(can_manage_space(sam, space))

	def test_moves_tier_changes_and_community_archives_update_public_access(self):
		with patch.dict(frappe.conf, gameplan_public_access_enabled=1, gameplan_demo_enabled=0):
			space = self.space("game-design")
			self.assertTrue(can_view_space("Guest", space))
			space.move_to_team("studio")
			self.assertFalse(can_view_space("Guest", space))
			space.move_to_team("common-room")
			self.assertTrue(can_view_space("Guest", space))
			community = frappe.get_doc("GP Team", "common-room")
			community.visibility = VISIBILITY_GENERAL
			community.save()
			self.assertFalse(can_view_space("Guest", self.space("game-design")))
			community.visibility = VISIBILITY_ANONYMOUS
			community.save()
			community.archive()
			self.assertFalse(can_view_community("Guest", community))
			self.assertFalse(can_view_space("Guest", self.space("game-design")))
			community.unarchive()
			self.assertTrue(can_view_space("Guest", self.space("game-design")))
			self.assertEqual(find_anonymous_readable_drift(), [])

	def space(self, key):
		return frappe.get_doc(*self.seeder.refs[key])

	def user(self, slug):
		return self.seeder.users[slug]
