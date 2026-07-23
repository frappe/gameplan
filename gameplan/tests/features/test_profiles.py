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
from gameplan.tests.fixtures import create_member


def get_profile(user):
	return frappe.get_doc("GP User Profile", {"user": user})


def reset_profile(user):
	profile = get_profile(user)
	profile.set("bento_cards", [])
	profile.image = None
	profile.cover_image = None
	profile.cover_image_position = None
	profile.save(ignore_permissions=True)


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
				with self.assertRaises(frappe.ValidationError):
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
		with self.assertRaises(frappe.ValidationError):
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
