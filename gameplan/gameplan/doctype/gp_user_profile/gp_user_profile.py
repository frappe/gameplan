# Copyright (c) 2022, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import re
from urllib.parse import urlparse

import frappe
from frappe.model.document import Document
from frappe.model.naming import append_number_if_name_exists
from frappe.query_builder.functions import Count
from frappe.website.utils import cleanup_page_name

import gameplan
from gameplan.api import get_user_info, require_admin
from gameplan.extends.client import check_permissions
from gameplan.mixins.attachments import HasAttachments

PROFILE_BENTO_CARD_TYPES = {"Card", "Blank"}
PROFILE_BENTO_CARD_SIZES = {"1x1", "1x2", "2x1", "2x2", "4x1", "4x2"}
PROFILE_BENTO_IMAGE_RENDERING = {"Cover", "Natural", "Fit"}
PROFILE_BENTO_CARD_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,80}$")
PROFILE_BENTO_URL_CONTROL_CHAR_PATTERN = re.compile(r"[\x00-\x20\x7f]")
PROFILE_BENTO_ALLOWED_URL_SCHEMES = {"http", "https"}
PROFILE_BENTO_MAX_CARDS = 40
QUICK_REACTION_MAX_SLOTS = 20


class GPUserProfile(HasAttachments, Document):
	attachments_field = "readme"

	def validate(self):
		self.quick_reaction_emojis = normalize_quick_reaction_emojis(self.quick_reaction_emojis)

	def autoname(self):
		self.name = self.generate_name()

	def on_update(self):
		self.attach_files_in_content()

	def generate_name(self):
		full_name = frappe.db.get_value("User", self.user, "full_name")
		return append_number_if_name_exists(self.doctype, cleanup_page_name(full_name))

	@frappe.whitelist(methods=["POST"])
	def set_image(self, image):
		self.image = image
		self.is_image_background_removed = False
		self.image_background_color = None
		self.original_image = None
		self.save()
		gameplan.refetch_resource("Users")

	@frappe.whitelist(methods=["POST"])
	def change_user_role(self, role):
		require_admin()

		if role not in ["Gameplan Guest", "Gameplan Member", "Gameplan Admin"]:
			return get_user_info(self.user)[0]

		user_doc = frappe.get_doc("User", self.user)
		for _role in list(user_doc.roles):
			if _role.role in ["Gameplan Guest", "Gameplan Member", "Gameplan Admin"]:
				user_doc.remove(_role)
		user_doc.append_roles(role)
		# Admin-gated by require_admin() above; bypass User's own permission checks so an
		# admin can change another user's roles.
		user_doc.save(ignore_permissions=True)

		return get_user_info(self.user)[0]

	@frappe.whitelist(methods=["POST"])
	def disable_user(self):
		require_admin()

		user_doc = frappe.get_doc("User", self.user)
		user_doc.enabled = 0
		# Admin-gated by require_admin() above; bypass User's own permission checks so an
		# admin can disable another user.
		user_doc.save(ignore_permissions=True)

		return self.user


def has_permission(doc, ptype="read", user=None):
	user = user or frappe.session.user

	# Everyone is allowed to read profiles.
	if ptype in ("read", "select", "print", "email", "export", "share"):
		return True

	# Administrators and Gameplan Admins can manage any profile.
	if user == "Administrator":
		return True
	if "Gameplan Admin" in frappe.get_roles(user) or "System Manager" in frappe.get_roles(user):
		return True

	# Otherwise a user may only modify their own profile.
	return doc.user == user


def create_user_profile(doc, method=None):
	if not frappe.db.exists("GP User Profile", {"user": doc.name}):
		frappe.get_doc(doctype="GP User Profile", user=doc.name).insert(ignore_permissions=True)
		frappe.db.commit()


def delete_user_profile(doc, method=None):
	exists = frappe.db.exists("GP User Profile", {"user": doc.name})
	if exists:
		return frappe.get_doc("GP User Profile", {"user": doc.name}).delete()


def on_user_update(doc, method=None):
	create_user_profile(doc)
	if any(doc.has_value_changed(field) for field in ["full_name", "enabled"]):
		profile = frappe.get_doc("GP User Profile", {"user": doc.name})
		profile.enabled = doc.enabled
		profile.full_name = doc.full_name
		profile.save(ignore_permissions=True)


@frappe.whitelist()
def get_list(
	fields=None,
	filters: dict | None = None,
	order_by=None,
	start=0,
	limit=20,
	group_by=None,
	parent=None,
	debug=False,
):
	doctype = "GP User Profile"
	check_permissions(doctype, parent)
	query = frappe.qb.get_query(
		table=doctype,
		fields=fields,
		filters=filters,
		order_by=order_by,
		offset=start,
		limit=limit,
		group_by=group_by,
	)
	data = query.run(as_dict=True, debug=debug)
	users = [d.user for d in data]

	Discussion = frappe.qb.DocType("GP Discussion")
	discussions_count = (
		frappe.qb.from_(Discussion)
		.select(Count(Discussion.name).as_("count"), Discussion.owner)
		.where(Discussion.owner.isin(users))
		.groupby(Discussion.owner)
	).run(as_dict=True)
	discussions_by_user = {d.owner: d.count for d in discussions_count}

	Comment = frappe.qb.DocType("GP Comment")
	comments_count = (
		frappe.qb.from_(Comment)
		.select(Count(Comment.name).as_("count"), Comment.owner)
		.where(Comment.owner.isin(users) & Comment.deleted_at.isnull())
		.groupby(Comment.owner)
	).run(as_dict=True)
	comments_by_user = {d.owner: d.count for d in comments_count}

	Reaction = frappe.qb.DocType("GP Reaction")
	reactions_given = (
		frappe.qb.from_(Reaction)
		.select(Count(Reaction.name).as_("count"), Reaction.user)
		.where(Reaction.user.isin(users))
		.groupby(Reaction.user)
	).run(as_dict=True)
	reactions_given_by_user = {r.user: r.count for r in reactions_given}

	reactions_received_by_user = {}

	discussion_reactions = (
		frappe.qb.from_(Reaction)
		.join(Discussion)
		.on(Discussion.name == Reaction.parent)
		.select(Count(Reaction.name).as_("count"), Discussion.owner)
		.where((Reaction.parenttype == "GP Discussion") & Discussion.owner.isin(users))
		.groupby(Discussion.owner)
	).run(as_dict=True)
	for r in discussion_reactions:
		reactions_received_by_user[r.owner] = reactions_received_by_user.get(r.owner, 0) + r.count

	comment_reactions = (
		frappe.qb.from_(Reaction)
		.join(Comment)
		.on(Comment.name == Reaction.parent)
		.select(Count(Reaction.name).as_("count"), Comment.owner)
		.where(
			(Reaction.parenttype == "GP Comment") & Comment.owner.isin(users) & Comment.deleted_at.isnull()
		)
		.groupby(Comment.owner)
	).run(as_dict=True)
	for r in comment_reactions:
		reactions_received_by_user[r.owner] = reactions_received_by_user.get(r.owner, 0) + r.count

	for user in data:
		user.discussions_count = discussions_by_user.get(user.user, 0)
		user.comments_count = comments_by_user.get(user.user, 0)
		user.reactions_given = reactions_given_by_user.get(user.user, 0)
		user.reactions_received = reactions_received_by_user.get(user.user, 0)

	return data


@frappe.whitelist(methods=["GET", "POST"])
def get_my_bento_cards():
	profile = get_session_user_profile()
	profile.check_permission("read")
	return get_profile_bento_response(profile, include_starter_cards=True)


@frappe.whitelist(methods=["POST"])
def save_my_bento_cards(cards: list | str):
	profile = get_session_user_profile()
	check_profile_bento_save_permission(profile)
	profile.set("bento_cards", normalize_bento_cards(cards))
	profile.save(ignore_permissions=True)
	return get_profile_bento_response(profile)


@frappe.whitelist(methods=["GET", "POST"])
def get_bento_cards(profile: str):
	profile_doc = frappe.get_doc("GP User Profile", profile)
	profile_doc.check_permission("read")
	return get_profile_bento_response(profile_doc)


def get_session_user_profile():
	if frappe.session.user == "Guest":
		frappe.throw("Login required", frappe.PermissionError)

	if not frappe.db.exists("GP User Profile", {"user": frappe.session.user}):
		create_user_profile(frappe.get_doc("User", frappe.session.user))

	return frappe.get_doc("GP User Profile", {"user": frappe.session.user})


def get_profile_bento_cards(profile):
	return [profile_bento_row_to_card(row) for row in profile.get("bento_cards")]


def get_profile_bento_response(profile, include_starter_cards=False):
	response = {
		"profile": profile.name,
		"cards": get_profile_bento_cards(profile),
		"is_default": not has_saved_bento_cards(profile),
	}
	if include_starter_cards and response["is_default"]:
		response["starter_cards"] = get_profile_bento_starter_cards(profile)
	return response


def has_saved_bento_cards(profile):
	return bool(profile.get("bento_cards"))


def check_profile_bento_save_permission(profile):
	user = frappe.session.user
	if user == "Guest":
		frappe.throw("Login required", frappe.PermissionError)
	if user == profile.user:
		return
	if has_permission(profile, ptype="write", user=user):
		return
	frappe.throw("Not permitted to save this profile layout", frappe.PermissionError)


def normalize_bento_cards(cards):
	cards = frappe.parse_json(cards) if isinstance(cards, str) else cards
	if not isinstance(cards, list):
		frappe.throw("Bento cards must be a list")
	if len(cards) > PROFILE_BENTO_MAX_CARDS:
		frappe.throw(f"Profiles can have at most {PROFILE_BENTO_MAX_CARDS} bento cards")

	seen_card_ids = set()
	return [normalize_bento_card(card, seen_card_ids) for card in cards]


def normalize_bento_card(card, seen_card_ids):
	if not isinstance(card, dict):
		frappe.throw("Each bento card must be an object")

	card_id = require_card_value(card.get("id") or card.get("card_id"), "Card ID")
	if not PROFILE_BENTO_CARD_ID_PATTERN.match(card_id):
		frappe.throw("Card ID may only contain letters, numbers, underscores, and hyphens")
	if card_id in seen_card_ids:
		frappe.throw(f"Duplicate bento card ID: {card_id}")
	seen_card_ids.add(card_id)

	card_type = require_allowed_value(card.get("type"), PROFILE_BENTO_CARD_TYPES, "Card type")
	size = require_allowed_value(card.get("size"), PROFILE_BENTO_CARD_SIZES, "Card size")
	image_rendering = optional_allowed_value(
		card.get("imageRendering") or card.get("image_rendering") or "Cover",
		PROFILE_BENTO_IMAGE_RENDERING,
		"Image rendering",
	)
	text = normalize_bento_card_text(card.get("text"), card_type)
	image = normalize_bento_card_image(card.get("image"), card_type)
	if card_type == "Card" and not text and not image:
		frappe.throw("Cards must have text or an image")

	return {
		"card_id": card_id,
		"type": card_type,
		"size": size,
		"title": truncate(card.get("title"), 140),
		"text": text,
		"url": normalize_bento_card_url(card.get("url")),
		"image": image,
		"image_rendering": image_rendering,
		"image_position": optional_int_range(
			pick_card_value(card, "imagePosition", "image_position"),
			0,
			100,
			"Image position",
		),
	}


def profile_bento_row_to_card(row):
	card = {
		"id": row.card_id,
		"type": row.type,
		"size": row.size,
		"title": row.title,
		"imageRendering": row.image_rendering or "Cover",
	}
	if row.text:
		card["text"] = row.text
	if row.url:
		card["url"] = row.url
	if row.image:
		card["image"] = row.image
	if row.image_position is not None:
		card["imagePosition"] = row.image_position

	return card


def get_profile_bento_starter_cards(profile):
	display_name = profile.full_name or frappe.db.get_value("User", profile.user, "full_name") or profile.user
	cards = get_default_profile_image_cards(profile)
	cards.extend(
		[
			{
				"id": "full-name",
				"type": "Card",
				"size": "1x1",
				"title": "Full name",
				"text": display_name,
			},
			{
				"id": "bio",
				"type": "Card",
				"size": "2x1",
				"title": "Bio",
				"text": profile.bio or "No bio yet.",
			},
		]
	)
	return cards


def get_default_profile_image_cards(profile):
	cards = []
	if profile.cover_image:
		cards.append(
			{
				"id": "cover",
				"type": "Card",
				"size": "4x1",
				"title": "Cover image",
				"image": profile.cover_image,
				"imageRendering": "Cover",
				"imagePosition": profile.cover_image_position
				if profile.cover_image_position is not None
				else 50,
			}
		)
	if profile.image:
		cards.append(
			{
				"id": "avatar",
				"type": "Card",
				"size": "1x1",
				"title": "Avatar",
				"image": profile.image,
				"imageRendering": "Cover",
				"imagePosition": 50,
			}
		)
	return cards


def require_card_value(value, label):
	value = (value or "").strip()
	if not value:
		frappe.throw(f"{label} is required")
	return value


def require_allowed_value(value, allowed_values, label):
	value = require_card_value(value, label)
	if value not in allowed_values:
		frappe.throw(f"Invalid {label.lower()}: {value}")
	return value


def optional_allowed_value(value, allowed_values, label):
	value = (value or "").strip()
	if not value:
		return None
	if value not in allowed_values:
		frappe.throw(f"Invalid {label.lower()}: {value}")
	return value


def normalize_bento_card_text(value, card_type):
	if card_type != "Card":
		return None

	text = str(value or "").strip()
	return text[:140] if text else None


def normalize_bento_card_image(value, card_type):
	if card_type != "Card":
		return None

	image = str(value or "").strip()
	return image[:500] if image else None


def normalize_bento_card_url(value):
	if value is None:
		return None

	url = str(value).strip()
	if not url:
		return None
	if len(url) > 500:
		frappe.throw("URL must be 500 characters or fewer")
	if PROFILE_BENTO_URL_CONTROL_CHAR_PATTERN.search(url):
		frappe.throw("URL cannot contain spaces or control characters")

	parsed_url = urlparse(url)
	if parsed_url.scheme.lower() not in PROFILE_BENTO_ALLOWED_URL_SCHEMES or not parsed_url.netloc:
		frappe.throw("URL must start with http:// or https://")
	return url


def pick_card_value(card, camel_key, snake_key):
	if camel_key in card:
		return card.get(camel_key)
	return card.get(snake_key)


def optional_int_range(value, min_value, max_value, label):
	if value is None or value == "":
		return None
	try:
		value = int(value)
	except (TypeError, ValueError):
		frappe.throw(f"{label} must be a number")
	return min(max_value, max(min_value, value))


def truncate(value, length):
	if value is None:
		return None
	return str(value)[:length]


def normalize_quick_reaction_emojis(value):
	if value in (None, ""):
		return None

	try:
		slots = frappe.parse_json(value)
	except (TypeError, ValueError):
		frappe.throw("Quick reactions must be valid JSON")

	if not isinstance(slots, list):
		frappe.throw("Quick reactions must be a list")
	if len(slots) > QUICK_REACTION_MAX_SLOTS:
		frappe.throw(f"Profiles can have at most {QUICK_REACTION_MAX_SLOTS} quick reactions")

	normalized_slots = []
	seen = set()
	for slot in slots:
		if not isinstance(slot, str):
			frappe.throw("Each quick reaction must be a string")

		emoji = slot.strip()
		if emoji and emoji in seen:
			frappe.throw(f"Duplicate quick reaction: {emoji}")
		if emoji:
			seen.add(emoji)
		normalized_slots.append(emoji)

	return frappe.as_json(normalized_slots, indent=None, separators=(",", ":"), ensure_ascii=False)


@frappe.whitelist()
def get_last_post():
	discussions = frappe.db.get_list(
		"GP Discussion",
		filters={"owner": frappe.session.user},
		fields=["creation"],
		order_by="creation desc",
		limit=1,
		pluck="creation",
	)
	comments = frappe.db.get_list(
		"GP Comment",
		filters={"owner": frappe.session.user},
		fields=["creation"],
		order_by="creation desc",
		limit=1,
		pluck="creation",
	)
	posts = discussions + comments
	if not posts:
		return None
	posts.sort(reverse=True)
	return posts[0]
