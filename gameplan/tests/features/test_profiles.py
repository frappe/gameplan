# Copyright (c) 2022, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

import frappe

from gameplan.api import get_user_info
from gameplan.gameplan.doctype.gp_user_profile.gp_user_profile import (
	get_bento_cards,
	get_my_bento_cards,
	has_permission,
	save_my_bento_cards,
)
from gameplan.gameplan.doctype.gp_user_profile.patches.bind_starter_bento_cards import (
	execute as bind_starter_bento_cards,
)
from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import create_member


def get_profile(user):
	return frappe.get_doc("GP User Profile", {"user": user})


def reset_profile(user):
	profile = get_profile(user)
	profile.set("bento_cards", [])
	profile.layout_customized = 0
	profile.image = None
	profile.cover_image = None
	profile.cover_image_position = None
	profile.bio = None
	profile.readme = None
	profile.quick_reaction_emojis = None
	profile.save(ignore_permissions=True)


def make_bento_card(card_id="intro", **values):
	return {
		"id": card_id,
		"type": "Card",
		"size": "1x1",
		"title": "Intro",
		"text": "Building async tools.",
		**values,
	}


def make_bound_card(card_id, field, **values):
	return {
		"id": card_id,
		"type": "Card",
		"size": "1x1",
		"title": field,
		"source": "field",
		"field": field,
		**values,
	}


def fill_profile(user, **values):
	"""Populate every bound profile field so the full default layout is produced."""
	profile = get_profile(user)
	profile.image = "/files/avatar.png"
	profile.cover_image = "/files/cover.png"
	profile.cover_image_position = 30
	profile.bio = "Building async tools."
	profile.readme = "<p>Long form about me.</p>"
	profile.update(values)
	profile.save(ignore_permissions=True)
	return profile


def create_custom_emoji(title="party-parrot"):
	return frappe.get_doc(
		doctype="GP Custom Emoji",
		title=title,
		image=f"/files/{title}.gif",
		keywords="party, celebrate",
	).insert()


def get_quick_reactions(user):
	return frappe.parse_json(get_profile(user).quick_reaction_emojis)


class TestProfiles(GameplanTestCase):
	def setUp(self):
		super().setUp()
		self.alice = create_member("test_alice@example.com", "Alice")
		self.bob = create_member("test_bob@example.com", "Bob")
		reset_profile(self.alice.name)
		reset_profile(self.bob.name)

	def test_owner_can_edit_own_bio(self):
		profile = get_profile(self.alice.name)
		self.assertTrue(has_permission(profile, ptype="write", user=self.alice.name))

	def test_member_cannot_edit_others_bio(self):
		"""A Gameplan Member must not be able to edit someone else's profile bio."""
		alice_profile = get_profile(self.alice.name)
		self.assertFalse(has_permission(alice_profile, ptype="write", user=self.bob.name))

	def test_admin_can_edit_any_bio(self):
		alice_profile = get_profile(self.alice.name)
		self.assertTrue(has_permission(alice_profile, ptype="write", user="Administrator"))

	def test_anyone_can_read_bio(self):
		alice_profile = get_profile(self.alice.name)
		self.assertTrue(has_permission(alice_profile, ptype="read", user=self.bob.name))

	def test_member_cannot_save_others_bio(self):
		"""End-to-end: saving another user's profile is blocked by permissions."""
		alice_profile = get_profile(self.alice.name)
		frappe.set_user(self.bob.name)
		alice_profile.bio = "hacked by bob"
		with self.assertRaises(frappe.PermissionError):
			alice_profile.save()

	def test_owner_can_save_own_bio(self):
		frappe.set_user(self.alice.name)
		profile = get_profile(self.alice.name)
		profile.bio = "hello, I am Alice"
		profile.save()
		self.assertEqual(get_profile(self.alice.name).bio, "hello, I am Alice")

	def test_default_bento_layout_binds_every_populated_profile_field(self):
		frappe.set_user(self.alice.name)
		fill_profile(self.alice.name)

		response = get_my_bento_cards()

		self.assertTrue(response["is_default"])
		self.assertEqual(
			[card["id"] for card in response["cards"]],
			["cover", "avatar", "full-name", "bio", "about"],
		)
		self.assertEqual(
			[card["field"] for card in response["cards"]],
			["cover_image", "image", "full_name", "bio", "readme"],
		)
		self.assertEqual(
			[card["format"] for card in response["cards"]],
			["image", "image", "text", "text", "html"],
		)
		self.assertTrue(all(card["source"] == "field" for card in response["cards"]))
		self.assertEqual(response["cards"][0]["image"], "/files/cover.png")
		self.assertEqual(response["cards"][0]["imagePosition"], 30)
		self.assertEqual(response["cards"][2]["text"], "Alice")
		self.assertEqual(response["cards"][4]["text"], "<p>Long form about me.</p>")

	def test_default_bento_layout_omits_empty_profile_fields(self):
		frappe.set_user(self.alice.name)
		profile = get_profile(self.alice.name)
		profile.image = "/files/avatar.png"
		profile.bio = "   "
		# An empty TipTap document still round-trips as markup, so it must read as empty.
		profile.readme = "<p></p>"
		profile.save(ignore_permissions=True)

		response = get_my_bento_cards()

		self.assertTrue(response["is_default"])
		self.assertEqual([card["id"] for card in response["cards"]], ["avatar", "full-name"])

	def test_starter_bento_cards_use_title_case_select_values(self):
		frappe.set_user(self.alice.name)
		fill_profile(self.alice.name)

		response = get_my_bento_cards()
		card_types = [card["type"] for card in response["starter_cards"]]
		card_sizes = [card["size"] for card in response["starter_cards"]]
		rendering_values = [card["imageRendering"] for card in response["starter_cards"] if card.get("image")]

		self.assertEqual(card_types, ["Card"] * 5)
		self.assertEqual(card_sizes, ["4x1", "1x1", "1x1", "2x1", "4x2"])
		self.assertEqual(rendering_values, ["Cover", "Cover"])

	def test_starter_bento_cards_skip_missing_images(self):
		frappe.set_user(self.alice.name)
		profile = get_profile(self.alice.name)
		profile.image = "/files/avatar.png"
		profile.save(ignore_permissions=True)

		response = get_my_bento_cards()

		self.assertTrue(response["is_default"])
		self.assertEqual(
			[card["id"] for card in response["starter_cards"]],
			["avatar", "full-name"],
		)

	def test_first_bento_save_persists_starter_cards(self):
		frappe.set_user(self.alice.name)
		fill_profile(self.alice.name)

		default_response = get_my_bento_cards()
		save_response = save_my_bento_cards(default_response["starter_cards"])
		profile = get_profile(self.alice.name)

		self.assertFalse(save_response["is_default"])
		self.assertEqual(len(profile.bento_cards), 5)
		self.assertEqual(profile.bento_cards[0].card_id, "cover")
		self.assertTrue(all(row.source == "field" for row in profile.bento_cards))
		# A bound card never stores its value; it is resolved on every read.
		self.assertTrue(all(not row.text and not row.image for row in profile.bento_cards))

	def test_saved_bento_cards_follow_later_profile_edits(self):
		frappe.set_user(self.alice.name)
		fill_profile(self.alice.name)
		save_my_bento_cards(get_my_bento_cards()["starter_cards"])

		profile = get_profile(self.alice.name)
		profile.bio = "Updated profile bio"
		profile.save()

		response = get_my_bento_cards()
		bio_card = next(card for card in response["cards"] if card["id"] == "bio")

		self.assertFalse(response["is_default"])
		self.assertEqual(bio_card["text"], "Updated profile bio")

	def test_saved_bound_card_disappears_when_its_field_is_cleared(self):
		frappe.set_user(self.alice.name)
		fill_profile(self.alice.name)
		save_my_bento_cards(get_my_bento_cards()["starter_cards"])

		profile = get_profile(self.alice.name)
		profile.bio = None
		profile.save()

		response = get_my_bento_cards()

		self.assertNotIn("bio", [card["id"] for card in response["cards"]])

	def test_default_and_saved_layouts_are_identical(self):
		"""The two read paths must agree, so a profile looks the same after its first save."""
		frappe.set_user(self.alice.name)
		fill_profile(self.alice.name)

		default_response = get_my_bento_cards()
		save_my_bento_cards(default_response["starter_cards"])
		saved_response = get_my_bento_cards()

		self.assertTrue(default_response["is_default"])
		self.assertFalse(saved_response["is_default"])
		self.assertEqual(saved_response["cards"], default_response["cards"])

	def test_any_member_can_read_profile_bento_cards(self):
		alice_profile = get_profile(self.alice.name)
		frappe.set_user(self.bob.name)
		response = get_bento_cards(alice_profile.name)

		self.assertEqual(response["profile"], alice_profile.name)
		self.assertTrue(response["is_default"])
		self.assertEqual([card["id"] for card in response["cards"]], ["full-name"])
		self.assertNotIn("starter_cards", response)

	def test_bound_bio_card_keeps_the_full_bio_while_custom_text_is_capped(self):
		frappe.set_user(self.alice.name)
		long_bio = "b" * 280
		profile = get_profile(self.alice.name)
		profile.bio = long_bio
		profile.save(ignore_permissions=True)

		response = save_my_bento_cards(
			[
				make_bound_card("bio", "bio", size="2x1"),
				make_bento_card("note", text="c" * 280),
			]
		)

		bio_card = next(card for card in response["cards"] if card["id"] == "bio")
		note_card = next(card for card in response["cards"] if card["id"] == "note")
		self.assertEqual(bio_card["text"], long_bio)
		self.assertEqual(note_card["text"], "c" * 140)

	def test_layout_customized_flips_on_the_first_save_including_an_empty_layout(self):
		frappe.set_user(self.alice.name)
		self.assertFalse(get_profile(self.alice.name).layout_customized)

		save_my_bento_cards([make_bento_card()])
		self.assertTrue(get_profile(self.alice.name).layout_customized)

		response = save_my_bento_cards([])

		self.assertTrue(get_profile(self.alice.name).layout_customized)
		self.assertFalse(response["is_default"])
		self.assertEqual(response["cards"], [])

	def test_cover_reposition_moves_the_computed_default(self):
		"""With no saved layout the cover's position comes from the profile field."""
		frappe.set_user(self.alice.name)
		fill_profile(self.alice.name)

		get_profile(self.alice.name).set_cover_image_position(80)

		response = get_my_bento_cards()
		cover_card = next(card for card in response["cards"] if card["id"] == "cover")
		self.assertTrue(response["is_default"])
		self.assertEqual(cover_card["imagePosition"], 80)
		self.assertFalse(get_profile(self.alice.name).layout_customized)

	def test_cover_reposition_moves_a_saved_layout_and_the_profile_field(self):
		"""Both read paths must land on the same position after a reposition."""
		frappe.set_user(self.alice.name)
		fill_profile(self.alice.name)
		save_my_bento_cards(get_my_bento_cards()["starter_cards"])

		get_profile(self.alice.name).set_cover_image_position(80)

		profile = get_profile(self.alice.name)
		cover_row = next(row for row in profile.bento_cards if row.field == "cover_image")
		self.assertEqual(cover_row.image_position, 80)
		self.assertEqual(int(profile.cover_image_position), 80)

		cover_card = next(card for card in get_my_bento_cards()["cards"] if card["id"] == "cover")
		self.assertEqual(cover_card["imagePosition"], 80)

	def test_cover_reposition_clamps_out_of_range_values(self):
		frappe.set_user(self.alice.name)
		fill_profile(self.alice.name)

		get_profile(self.alice.name).set_cover_image_position(140)

		self.assertEqual(int(get_profile(self.alice.name).cover_image_position), 100)

	def test_member_cannot_reposition_another_profiles_cover(self):
		alice_profile = get_profile(self.alice.name)
		frappe.set_user(self.bob.name)

		with self.assertRaises(frappe.PermissionError):
			alice_profile.set_cover_image_position(80)

	def test_bound_bento_cards_reject_a_duplicate_field(self):
		frappe.set_user(self.alice.name)

		with self.assertRaisesRegex(frappe.ValidationError, "^Duplicate bound field: bio$"):
			save_my_bento_cards([make_bound_card("bio", "bio"), make_bound_card("bio-again", "bio")])

	def test_bound_bento_cards_reject_an_unknown_field(self):
		frappe.set_user(self.alice.name)

		with self.assertRaisesRegex(frappe.ValidationError, "^Invalid bound field: email$"):
			save_my_bento_cards([make_bound_card("email", "email")])

	def test_blank_bento_cards_cannot_be_bound(self):
		frappe.set_user(self.alice.name)

		with self.assertRaisesRegex(frappe.ValidationError, "type Card"):
			save_my_bento_cards([make_bound_card("gap", "bio", type="Blank")])

	def test_patch_converts_saved_starter_cards_into_bound_cards(self):
		frappe.set_user(self.alice.name)
		save_my_bento_cards(
			[
				make_bento_card("cover", image="/files/cover.png", text=None, size="4x1"),
				make_bento_card("avatar", image="/files/avatar.png", text=None),
				make_bento_card("full-name", text="Alice"),
				make_bento_card("bio", text="Frozen bio copy", size="2x1"),
				make_bento_card("note", text="A custom card"),
			]
		)
		frappe.db.set_value("GP User Profile", get_profile(self.alice.name).name, "layout_customized", 0)

		bind_starter_bento_cards()

		profile = get_profile(self.alice.name)
		self.assertEqual(
			[(row.card_id, row.source, row.get("field")) for row in profile.bento_cards],
			[
				("cover", "field", "cover_image"),
				("avatar", "field", "image"),
				("full-name", "field", "full_name"),
				("bio", "field", "bio"),
				("note", "custom", None),
			],
		)
		self.assertTrue(all(not row.text and not row.image for row in profile.bento_cards[:4]))
		self.assertEqual(profile.bento_cards[4].text, "A custom card")
		self.assertTrue(profile.layout_customized)

	def test_owner_can_save_bento_cards(self):
		frappe.set_user(self.alice.name)
		response = save_my_bento_cards(
			[
				{
					"id": "intro",
					"type": "Card",
					"size": "2x1",
					"title": "Intro",
					"text": "Building async tools.",
					"image": "/files/intro.png",
				},
				{
					"id": "hero",
					"type": "Card",
					"size": "2x2",
					"title": "Hero",
					"image": "/files/hero.png",
					"imageRendering": "Fit",
					"imagePosition": 24,
				},
			]
		)
		profile = get_profile(self.alice.name)

		self.assertEqual([card["id"] for card in response["cards"]], ["intro", "hero"])
		self.assertFalse(response["is_default"])
		self.assertEqual(profile.bento_cards[0].type, "Card")
		self.assertEqual(profile.bento_cards[0].image, "/files/intro.png")
		self.assertEqual(profile.bento_cards[1].image, "/files/hero.png")
		self.assertEqual(profile.bento_cards[1].image_rendering, "Fit")
		self.assertEqual(profile.bento_cards[1].image_position, 24)

	def test_profile_bento_card_must_have_text_or_image(self):
		frappe.set_user(self.alice.name)
		with self.assertRaises(frappe.ValidationError):
			save_my_bento_cards(
				[
					{
						"id": "intro",
						"type": "Card",
						"size": "2x1",
						"title": "Intro",
						"text": "   ",
					}
				]
			)

	def test_split_bento_card_types_are_rejected(self):
		frappe.set_user(self.alice.name)
		for card_type in ("Text", "Image"):
			with self.subTest(card_type=card_type):
				with self.assertRaisesRegex(
					frappe.ValidationError,
					f"^Invalid card type: {card_type}$",
				):
					save_my_bento_cards(
						[
							{
								"id": card_type.lower(),
								"type": card_type,
								"size": "2x1",
								"title": card_type,
								"text": "Building async tools.",
								"image": "/files/hero.png",
							}
						]
					)

	def test_logged_out_user_cannot_save_bento_cards(self):
		frappe.set_user("Guest")
		with self.assertRaises(frappe.PermissionError):
			save_my_bento_cards(
				[
					{
						"id": "intro",
						"type": "Card",
						"size": "2x1",
						"title": "Intro",
						"text": "Intro",
					}
				]
			)

	def test_bento_card_type_must_be_title_case(self):
		frappe.set_user(self.alice.name)
		with self.assertRaisesRegex(frappe.ValidationError, "^Invalid card type: text$"):
			save_my_bento_cards(
				[
					{
						"id": "intro",
						"type": "text",
						"size": "2x1",
						"title": "Intro",
					}
				]
			)

	def test_bento_card_url_must_use_http_scheme(self):
		frappe.set_user(self.alice.name)
		with self.assertRaises(frappe.ValidationError):
			save_my_bento_cards(
				[
					{
						"id": "website",
						"type": "Card",
						"size": "1x1",
						"title": "Website",
						"text": "Website",
						"url": "javascript:alert(1)",
					}
				]
			)

	def test_bento_card_url_rejects_control_characters(self):
		frappe.set_user(self.alice.name)
		with self.assertRaises(frappe.ValidationError):
			save_my_bento_cards(
				[
					{
						"id": "website",
						"type": "Card",
						"size": "1x1",
						"title": "Website",
						"text": "Website",
						"url": "java\nscript:alert(1)",
					}
				]
			)

	def test_bento_card_url_requires_host(self):
		frappe.set_user(self.alice.name)
		with self.assertRaises(frappe.ValidationError):
			save_my_bento_cards(
				[
					{
						"id": "website",
						"type": "Card",
						"size": "1x1",
						"title": "Website",
						"text": "Website",
						"url": "https:example.com",
					}
				]
			)

	def test_blank_bento_card_can_be_saved(self):
		frappe.set_user(self.alice.name)

		response = save_my_bento_cards(
			[
				{
					"id": "gap",
					"type": "Blank",
					"size": "1x2",
				}
			]
		)

		self.assertEqual(
			response["cards"],
			[
				{
					"id": "gap",
					"type": "Blank",
					"size": "1x2",
					"title": None,
					"imageRendering": "Cover",
					"imagePosition": 50,
					"source": "custom",
				}
			],
		)

	def test_bento_card_ids_must_be_unique(self):
		frappe.set_user(self.alice.name)

		with self.assertRaises(frappe.ValidationError):
			save_my_bento_cards([make_bento_card(), make_bento_card()])

	def test_bento_card_ids_reject_unsafe_characters(self):
		frappe.set_user(self.alice.name)

		with self.assertRaises(frappe.ValidationError):
			save_my_bento_cards([make_bento_card("intro card")])

	def test_profile_bento_layout_has_a_card_limit(self):
		frappe.set_user(self.alice.name)

		with self.assertRaises(frappe.ValidationError):
			save_my_bento_cards([make_bento_card(f"card-{index}") for index in range(41)])

	def test_bento_card_size_must_be_supported(self):
		frappe.set_user(self.alice.name)

		with self.assertRaisesRegex(frappe.ValidationError, "^Invalid card size: 3x3$"):
			save_my_bento_cards([make_bento_card(size="3x3")])

	def test_bento_card_image_rendering_must_be_supported(self):
		frappe.set_user(self.alice.name)

		with self.assertRaisesRegex(frappe.ValidationError, "^Invalid image rendering: Stretch$"):
			save_my_bento_cards([make_bento_card(imageRendering="Stretch")])

	def test_bento_image_position_is_clamped_to_the_card(self):
		frappe.set_user(self.alice.name)

		response = save_my_bento_cards(
			[
				make_bento_card("top", image="/files/top.png", imagePosition=-10),
				make_bento_card("bottom", image="/files/bottom.png", imagePosition=125),
			]
		)

		self.assertEqual([card["imagePosition"] for card in response["cards"]], [0, 100])

	def test_bento_cards_accept_the_json_payload_sent_over_http(self):
		frappe.set_user(self.alice.name)

		response = save_my_bento_cards(frappe.as_json([make_bento_card()]))

		self.assertEqual([card["id"] for card in response["cards"]], ["intro"])


class TestCustomEmojis(GameplanTestCase):
	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		self.emoji = create_custom_emoji()

	def test_custom_emoji_library_is_readable_by_every_gameplan_role(self):
		for user in (self.admin, self.member, self.guest):
			with self.subTest(user=user.name), self.as_user(user):
				names = frappe.get_list("GP Custom Emoji", pluck="name")
				self.assertIn(self.emoji.name, names)

	def test_gameplan_admin_can_manage_custom_emojis(self):
		with self.as_user(self.admin):
			emoji = create_custom_emoji("ship-it")
			emoji.keywords = "ship, done"
			emoji.save()
			emoji.reload()
			self.assertEqual(emoji.keywords, "ship, done")
			emoji.delete()

		self.assertFalse(frappe.db.exists("GP Custom Emoji", emoji.name))

	def test_member_cannot_create_custom_emoji(self):
		with self.as_user(self.member), self.assertRaises(frappe.PermissionError):
			create_custom_emoji("member-emoji")

	def test_member_cannot_edit_custom_emoji(self):
		with self.as_user(self.member):
			emoji = frappe.get_doc("GP Custom Emoji", self.emoji.name)
			emoji.keywords = "changed"
			with self.assertRaises(frappe.PermissionError):
				emoji.save()

	def test_member_cannot_delete_custom_emoji(self):
		with self.as_user(self.member):
			emoji = frappe.get_doc("GP Custom Emoji", self.emoji.name)
			with self.assertRaises(frappe.PermissionError):
				emoji.delete()


class TestQuickReactions(GameplanTestCase):
	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		reset_profile(self.member.name)
		reset_profile(self.second_member.name)

	def save_quick_reactions(self, user, slots):
		with self.as_user(user):
			profile = get_profile(user.name)
			profile.quick_reaction_emojis = frappe.as_json(slots)
			profile.save()

	def test_member_can_save_unicode_and_custom_quick_reactions(self):
		slots = ["👍", "/files/party-parrot.gif", "", "🚀"]

		self.save_quick_reactions(self.member, slots)

		self.assertEqual(get_quick_reactions(self.member.name), slots)

	def test_quick_reactions_are_independent_for_each_profile(self):
		self.save_quick_reactions(self.member, ["👍"])
		self.save_quick_reactions(self.second_member, ["🚀"])

		self.assertEqual(get_quick_reactions(self.member.name), ["👍"])
		self.assertEqual(get_quick_reactions(self.second_member.name), ["🚀"])

	def test_other_members_quick_reactions_are_private_in_user_info(self):
		self.save_quick_reactions(self.member, ["👍"])

		with self.as_user(self.second_member):
			users = get_user_info(self.member.name)

		self.assertEqual(len(users), 1)
		self.assertEqual(users[0].name, self.member.name)
		self.assertNotIn("quick_reaction_emojis", users[0])

	def test_member_cannot_change_another_members_quick_reactions(self):
		with self.as_user(self.second_member):
			profile = get_profile(self.member.name)
			profile.quick_reaction_emojis = frappe.as_json(["🚀"])
			with self.assertRaises(frappe.PermissionError):
				profile.save()

	def test_quick_reactions_allow_twenty_slots(self):
		slots = [f"emoji-{index}" for index in range(20)]

		self.save_quick_reactions(self.member, slots)

		self.assertEqual(get_quick_reactions(self.member.name), slots)

	def test_quick_reactions_reject_more_than_twenty_slots(self):
		with self.assertRaises(frappe.ValidationError):
			self.save_quick_reactions(self.member, [f"emoji-{index}" for index in range(21)])

	def test_quick_reactions_reject_duplicates(self):
		with self.assertRaises(frappe.ValidationError):
			self.save_quick_reactions(self.member, ["👍", "", "👍"])

	def test_quick_reactions_reject_non_string_slots(self):
		with self.assertRaises(frappe.ValidationError):
			self.save_quick_reactions(self.member, ["👍", 42])

	def test_quick_reactions_reject_non_list_json(self):
		with self.assertRaises(frappe.ValidationError):
			self.save_quick_reactions(self.member, {"first": "👍"})

	def test_quick_reactions_are_trimmed_before_save(self):
		self.save_quick_reactions(self.member, ["  👍  ", "", "  /files/party.gif "])

		self.assertEqual(get_quick_reactions(self.member.name), ["👍", "", "/files/party.gif"])

	def test_first_save_keeps_canonical_quick_reaction_json(self):
		quick_reactions = '["👍",""]'

		with self.as_user(self.member):
			profile = get_profile(self.member.name)
			profile.quick_reaction_emojis = quick_reactions
			profile.save()

		self.assertEqual(get_profile(self.member.name).quick_reaction_emojis, quick_reactions)

	def test_caller_json_formatting_is_canonicalized(self):
		with self.as_user(self.member):
			profile = get_profile(self.member.name)
			profile.quick_reaction_emojis = '   ["👍", ""]   '
			profile.save()

		self.assertEqual(get_profile(self.member.name).quick_reaction_emojis, '["👍",""]')

	def test_trimmed_quick_reactions_use_canonical_json(self):
		with self.as_user(self.member):
			profile = get_profile(self.member.name)
			profile.quick_reaction_emojis = '["  👍  ",""]'
			profile.save()

		self.assertEqual(get_profile(self.member.name).quick_reaction_emojis, '["👍",""]')
