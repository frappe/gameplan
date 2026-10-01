# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""The move from `is_private` to the three-tier `visibility` field.

A deployed site must come through it with exactly the access it had: `is_private = 1`
becomes Member Access, `is_private = 0` becomes General, and nothing becomes Anonymous.
"""

from pathlib import Path

import frappe
from frappe.utils import get_datetime

from gameplan.patches.backfill_visibility_from_is_private import execute as backfill_visibility
from gameplan.public_access import (
	VISIBILITY_ANONYMOUS,
	VISIBILITY_GENERAL,
	VISIBILITY_MEMBER_ACCESS,
	find_visibility_backfill_mismatches,
)
from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import create_community, create_space


def set_raw(doc, **values):
	"""Write columns directly, the way a row looks before the patch has run."""
	frappe.db.set_value(doc.doctype, doc.name, values, update_modified=False)


def stored_visibility(doc):
	return frappe.db.get_value(doc.doctype, doc.name, "visibility")


class TestVisibilityBackfill(GameplanTestCase):
	def setUp(self):
		super().setUp()
		self.open_community = create_community("Backfill Open Community")
		self.closed_community = create_community("Backfill Closed Community")
		self.open_space = create_space("Backfill Open Space", self.open_community)
		self.closed_space = create_space("Backfill Closed Space", self.open_community)
		self.rows = {
			self.open_community: 0,
			self.closed_community: 1,
			self.open_space: 0,
			self.closed_space: 1,
		}
		for doc, is_private in self.rows.items():
			set_raw(doc, is_private=is_private, visibility=None)

	def test_it_maps_is_private_to_the_matching_tier(self):
		backfill_visibility()

		for doc, is_private in self.rows.items():
			expected = VISIBILITY_MEMBER_ACCESS if is_private else VISIBILITY_GENERAL
			self.assertEqual(stored_visibility(doc), expected, f"{doc.doctype} {doc.title}")

	def test_it_never_publishes_anything(self):
		backfill_visibility()

		for doctype in ("GP Team", "GP Project"):
			self.assertFalse(frappe.db.exists(doctype, {"visibility": VISIBILITY_ANONYMOUS}), doctype)

	def test_verification_passes_after_the_backfill(self):
		self.assertTrue(find_visibility_backfill_mismatches())

		backfill_visibility()

		self.assertEqual(find_visibility_backfill_mismatches(), [])

	def test_verification_reports_every_kind_of_mismatch(self):
		backfill_visibility()
		set_raw(self.open_community, visibility=None)
		set_raw(self.closed_community, visibility=VISIBILITY_GENERAL)
		set_raw(self.open_space, visibility=VISIBILITY_ANONYMOUS)

		mismatches = find_visibility_backfill_mismatches()

		self.assertEqual(len(mismatches), 3, mismatches)
		self.assertTrue(any("visibility is None" in m for m in mismatches), mismatches)
		self.assertTrue(any("but is_private was 1" in m for m in mismatches), mismatches)
		self.assertTrue(any("backfilled to Anonymous" in m for m in mismatches), mismatches)


class TestNewRecords(GameplanTestCase):
	def test_new_communities_and_spaces_default_to_general(self):
		# Not through the fixtures, which pass a tier: this is what the Desk form, the
		# generic REST route and every other caller that names no tier get.
		community = frappe.get_doc(doctype="GP Team", title="Default Tier Community").insert(
			ignore_permissions=True
		)
		space = frappe.get_doc(doctype="GP Project", title="Default Tier Space", team=community.name).insert(
			ignore_permissions=True
		)
		general_space = frappe.db.get_value(
			"GP Project", {"team": community.name, "title": "General"}, "visibility"
		)

		self.assertEqual(community.visibility, VISIBILITY_GENERAL)
		self.assertEqual(space.visibility, VISIBILITY_GENERAL)
		self.assertEqual(general_space, VISIBILITY_GENERAL)

	def test_a_data_import_that_names_no_tier_still_gets_general(self):
		# A data import skips Frappe's own defaults, so before_insert fills the tier in.
		community = create_community("Import Tier Host")
		frappe.flags.in_import = True
		try:
			space = frappe.get_doc(doctype="GP Project", title="Imported Space", team=community.name).insert(
				ignore_permissions=True
			)
		finally:
			frappe.flags.in_import = False

		self.assertEqual(space.visibility, VISIBILITY_GENERAL)

	def test_the_legacy_is_private_flag_is_refused(self):
		# A caller that still asks for a private record must not get a General one.
		for doctype, values in (
			("GP Team", {"title": "Legacy Flag Community"}),
			("GP Project", {"title": "Legacy Flag Space", "team": create_community("Legacy Host").name}),
		):
			with self.subTest(doctype=doctype), self.assertRaises(frappe.ValidationError):
				frappe.get_doc(doctype=doctype, is_private=1, **values).insert(ignore_permissions=True)

	def test_a_legacy_is_private_of_zero_still_gets_the_default(self):
		community = create_community("Legacy Zero Host")
		space = frappe.get_doc(
			doctype="GP Project", title="Legacy Zero Space", team=community.name, is_private=0
		).insert(ignore_permissions=True)

		self.assertEqual(space.visibility, VISIBILITY_GENERAL)


class TestVisibilityAuditStamp(GameplanTestCase):
	def test_creation_records_who_set_the_tier(self):
		with self.as_user(self.admin):
			community = frappe.get_doc(doctype="GP Team", title="Stamped Community").insert()

		self.assertEqual(community.visibility_set_by, self.admin.name)
		self.assertIsNotNone(community.visibility_set_at)

	def test_a_direct_save_is_recorded_too(self):
		# The Desk form and a console save never call a Gameplan method, so the stamp has
		# to come from the save itself.
		community = create_community("Directly Saved Community")
		space = create_space("Directly Saved Space", community)

		with self.as_user(self.admin):
			for doc in (community, space):
				doc.reload()
				doc.visibility = VISIBILITY_MEMBER_ACCESS
				doc.save()
				self.assertEqual(doc.visibility_set_by, self.admin.name, doc.doctype)

	def test_a_save_that_leaves_the_tier_alone_keeps_the_stamp(self):
		community = create_community("Untouched Tier Community")
		stamped_at = community.visibility_set_at

		with self.as_user(self.admin):
			community.reload()
			community.title = "Renamed, same tier"
			community.save()

		self.assertEqual(get_datetime(community.visibility_set_at), get_datetime(stamped_at))
		self.assertNotEqual(community.visibility_set_by, self.admin.name)


class TestMissingTierFailsClosed(GameplanTestCase):
	"""A row without a tier reads as Member Access, never as General.

	Between the schema sync and the backfill patch, every row is in this state.
	"""

	def test_a_space_with_no_tier_is_members_only(self):
		community = create_community("No Tier Space Host", members=[self.member, self.second_member])
		space = create_space("No Tier Space", community, members=[self.member])
		set_raw(space, visibility=None)

		self.assert_allowed(space, "read", self.member)
		self.assert_not_allowed(space, "read", self.second_member)
		with self.as_user(self.second_member):
			self.assertNotIn(space.name, frappe.get_list("GP Project", pluck="name"))

	def test_a_space_outside_every_community_stays_open(self):
		# Fail closed applies to a community without a tier, not to no community at all:
		# an Uncategorized space was readable by every member before visibility, and still is.
		space = frappe.get_doc(doctype="GP Project", title="Uncategorized Space").insert(
			ignore_permissions=True
		)

		self.assertIsNone(space.team)
		self.assert_allowed(space, "read", self.second_member)

	def test_a_community_with_no_tier_is_members_only(self):
		community = create_community("No Tier Community", members=[self.member])
		set_raw(community, visibility=None)

		self.assert_allowed(community, "read", self.member)
		self.assert_not_allowed(community, "read", self.second_member)
		with self.as_user(self.second_member):
			self.assertNotIn(community.name, frappe.get_list("GP Team", pluck="name"))


# Every file that may still say `is_private`, and how many times. Nothing reads or writes
# the GP Team / GP Project column any more, so a new occurrence is either a legacy reader
# (which would read a frozen column) or one of these, knowingly updated.
LEGACY_PRIVACY_REFERENCES = {
	# The migration itself: the backfill, its verification, and the legacy-key guard.
	"gameplan/patches/backfill_visibility_from_is_private.py": 5,
	"gameplan/public_access.py": 9,
	"gameplan/mixins/visibility.py": 6,
	# What anonymous visitors may read: the column is classified as private, never sent.
	"gameplan/public_payload.py": 2,
	# The column stays defined, so a rollback needs no data restore.
	"gameplan/gameplan/doctype/gp_project/gp_project.json": 2,
	"gameplan/gameplan/doctype/gp_team/gp_team.json": 2,
	"frontend/src/types/doctypes.ts": 2,
	# A historical patch, frozen against the schema it was written for.
	"gameplan/gameplan/doctype/gp_project/patches/migrate_members_from_team.py": 1,
	# Frappe's File.is_private, an unrelated field on another doctype.
	"gameplan/demo/seeder.py": 1,
	"gameplan/gameplan/doctype/gp_user_profile/gp_user_profile.py": 1,
	"gameplan/migrate_from_discourse/__init__.py": 1,
	"gameplan/mixins/attachments.py": 2,
	"gameplan/tests/platform/test_attachments.py": 2,
	"gameplan/tests/platform/test_profile_image_ownership.py": 4,
}
SOURCE_SUFFIXES = {".py", ".ts", ".vue", ".js", ".json", ".jsonl"}


class TestNoLegacyPrivacyReaders(GameplanTestCase):
	def test_nothing_new_reads_or_writes_is_private(self):
		repo = Path(frappe.get_app_path("gameplan")).parent
		this_file = Path(__file__).resolve()
		found = {}
		for base in ("gameplan", "frontend/src"):
			for path in (repo / base).rglob("*"):
				if (
					path.suffix not in SOURCE_SUFFIXES
					or "__pycache__" in path.parts
					or path.resolve() == this_file
					or (repo / "gameplan" / "public") in path.parents
				):
					continue
				count = path.read_text(errors="ignore").count("is_private")
				if count:
					found[path.relative_to(repo).as_posix()] = count

		self.assertEqual(found, LEGACY_PRIVACY_REFERENCES)
