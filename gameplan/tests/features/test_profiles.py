# Copyright (c) 2022, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from gameplan.gameplan.doctype.gp_user_profile.gp_user_profile import (
	get_bento_cards,
	get_my_bento_cards,
	has_permission,
	save_my_bento_cards,
)
from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import create_member


def get_profile(user):
	return frappe.get_doc("GP User Profile", {"user": user})


def reset_profile(user):
	profile = get_profile(user)
	profile.set("bento_cards", [])
	profile.image = None
	profile.cover_image = None
	profile.cover_image_position = None
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


def create_custom_emoji(title="party-parrot"):
	return frappe.get_doc(
		doctype="GP Custom Emoji",
		title=title,
		image=f"/files/{title}.gif",
		keywords="party, celebrate",
	).insert()


def get_quick_reactions(user):
	return frappe.parse_json(get_profile(user).quick_reaction_emojis)


class TestProfiles(FrappeTestCase):
	def setUp(self):
		self.alice = create_member("test_alice@example.com", "Alice")
		self.bob = create_member("test_bob@example.com", "Bob")
		reset_profile(self.alice.name)
		reset_profile(self.bob.name)

	def tearDown(self):
		frappe.set_user("Administrator")

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

	def test_new_profile_page_is_off_by_default(self):
		frappe.set_user(self.alice.name)
		profile = get_profile(self.alice.name)
		profile.image = "/files/avatar.png"
		profile.cover_image = "/files/cover.png"
		profile.save(ignore_permissions=True)

		response = get_my_bento_cards()

		self.assertTrue(response["is_default"])
		self.assertEqual(response["cards"], [])

	def test_starter_bento_cards_use_title_case_select_values(self):
		frappe.set_user(self.alice.name)
		profile = get_profile(self.alice.name)
		profile.image = "/files/avatar.png"
		profile.cover_image = "/files/cover.png"
		profile.save(ignore_permissions=True)

		response = get_my_bento_cards()
		card_types = [card["type"] for card in response["starter_cards"]]
		card_sizes = [card["size"] for card in response["starter_cards"]]
		rendering_values = [card["imageRendering"] for card in response["starter_cards"] if card.get("image")]

		self.assertEqual(card_types, ["Card", "Card", "Card", "Card"])
		self.assertEqual(card_sizes, ["4x1", "1x1", "1x1", "2x1"])
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
			["avatar", "full-name", "bio"],
		)

	def test_first_bento_save_persists_starter_cards(self):
		frappe.set_user(self.alice.name)
		profile = get_profile(self.alice.name)
		profile.image = "/files/avatar.png"
		profile.cover_image = "/files/cover.png"
		profile.save(ignore_permissions=True)

		default_response = get_my_bento_cards()
		save_response = save_my_bento_cards(default_response["starter_cards"])
		profile = get_profile(self.alice.name)

		self.assertFalse(save_response["is_default"])
		self.assertEqual(len(profile.bento_cards), 4)
		self.assertEqual(profile.bento_cards[0].card_id, "cover")

	def test_saved_starter_bento_cards_are_not_rehydrated(self):
		frappe.set_user(self.alice.name)
		default_response = get_my_bento_cards()
		bio_card = next(card for card in default_response["starter_cards"] if card["id"] == "bio")
		original_bio_text = bio_card["text"]
		save_my_bento_cards(default_response["starter_cards"])
		profile = get_profile(self.alice.name)
		profile.bio = "Updated profile bio"
		profile.save()

		response = get_my_bento_cards()
		bio_card = next(card for card in response["cards"] if card["id"] == "bio")

		self.assertFalse(response["is_default"])
		self.assertEqual(bio_card["text"], original_bio_text)

	def test_any_member_can_read_profile_bento_cards(self):
		alice_profile = get_profile(self.alice.name)
		frappe.set_user(self.bob.name)
		response = get_bento_cards(alice_profile.name)

		self.assertEqual(response["profile"], alice_profile.name)
		self.assertTrue(response["is_default"])
		self.assertEqual(response["cards"], [])
		self.assertNotIn("starter_cards", response)

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

	def test_unrelated_profile_save_preserves_quick_reaction_json_representation(self):
		quick_reactions = '["👍",""]'

		with self.as_user(self.member):
			profile = get_profile(self.member.name)
			profile.quick_reaction_emojis = quick_reactions
			profile.save()
			profile.bio = "Unrelated profile edit"
			profile.save()

		self.assertEqual(get_profile(self.member.name).quick_reaction_emojis, quick_reactions)
