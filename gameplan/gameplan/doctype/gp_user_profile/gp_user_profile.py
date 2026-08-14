# Copyright (c) 2022, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import re
from urllib.parse import urlparse

import frappe
from frappe.model.document import Document
from frappe.model.naming import append_number_if_name_exists
from frappe.query_builder.functions import Count
from frappe.website.utils import cleanup_page_name

from gameplan.api import get_user_info, require_admin
from gameplan.extends.client import check_permissions
from gameplan.mixins.attachments import HasAttachments
from gameplan.realtime import notify_users_changed

PROFILE_BENTO_CARD_TYPES = {"Card", "Blank"}
PROFILE_BENTO_CARD_SOURCES = {"custom", "field"}
PROFILE_BENTO_CARD_SIZES = {"1x1", "1x2", "2x1", "2x2", "4x1", "4x2"}
PROFILE_BENTO_IMAGE_RENDERING = {"Cover", "Natural", "Fit"}
PROFILE_BENTO_CARD_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,80}$")
PROFILE_BENTO_URL_CONTROL_CHAR_PATTERN = re.compile(r"[\x00-\x20\x7f]")
PROFILE_BENTO_ALLOWED_URL_SCHEMES = {"http", "https"}
PROFILE_BENTO_MAX_CARDS = 40
PROFILE_BENTO_DEFAULT_IMAGE_POSITION = 50
PROFILE_BENTO_HTML_TAG_PATTERN = re.compile(r"<[^>]*>")
PROFILE_BENTO_HTML_MEDIA_PATTERN = re.compile(r"<\s*(img|video|audio|iframe|embed)\b", re.IGNORECASE)
QUICK_REACTION_MAX_SLOTS = 20

# Profile fields a bento card may bind to. The order is the default layout order:
# row 1 is the cover (4 columns), row 2 is avatar + name + bio (1 + 1 + 2), and
# About fills rows 3-4.
PROFILE_BENTO_BOUND_FIELDS = {
	"cover_image": {"id": "cover", "size": "4x1", "title": "Cover image", "kind": "image"},
	"image": {"id": "avatar", "size": "1x1", "title": "Avatar", "kind": "image"},
	"full_name": {"id": "full-name", "size": "1x1", "title": "Full name", "kind": "text"},
	"bio": {"id": "bio", "size": "2x1", "title": "Bio", "kind": "text"},
	"readme": {"id": "about", "size": "4x2", "title": "About", "kind": "html"},
}


class GPUserProfile(HasAttachments, Document):
	attachments_field = "readme"

	def validate(self):
		self.quick_reaction_emojis = normalize_quick_reaction_emojis(self.quick_reaction_emojis)

	def autoname(self):
		self.name = self.generate_name()

	def on_update(self):
		self.attach_files_in_content()
		self.attach_bento_card_images()

	def attach_bento_card_images(self, allow_session_owner=True):
		"""Attach the images on this profile's bento cards to the profile.

		`GP Profile Bento Card` is a child table, and Frappe only auto-attaches Attach
		fields declared on the parent doctype, so a card image is never attached to
		anything. An unattached private File falls through `File.has_permission` to
		deny, which would leave the card visible to its uploader and 403 for everyone
		else. Attached to the profile, it inherits the profile's read permission,
		which every signed-in user has.
		"""
		# The profile's own user is the only person who uploads their card images;
		# `self.owner` is whoever created the User row, which is usually an admin.
		allowed_owners = {self.user}
		if allow_session_owner:
			allowed_owners.add(frappe.session.user)

		self.attach_files_at_urls((row.image for row in self.get("bento_cards")), allowed_owners)

	def generate_name(self):
		full_name = frappe.db.get_value("User", self.user, "full_name")
		return append_number_if_name_exists(self.doctype, cleanup_page_name(full_name))

	@frappe.whitelist(methods=["POST"])
	def set_image(self, image):
		self.check_image_is_ours(image)
		self.image = image
		self.is_image_background_removed = False
		self.image_background_color = None
		self.original_image = None
		self.save()
		notify_users_changed()

	def check_image_is_ours(self, image):
		"""Refuse an avatar URL naming a private file this profile has no claim on.

		The URL comes straight from the client and nothing downstream re-checks it, so
		without this a user can point their avatar at any `/private/files/...` path they
		can guess or read off another page. Same rule as
		`HasAttachments._maybe_attach_file`: the file has to have been uploaded by the
		profile's own user, or by whoever is setting it (an admin uploading on someone's
		behalf). Only private files are checked, because a public file is readable by
		everyone already and naming one exposes nothing.
		"""
		if not image:
			return

		owners = frappe.qb.get_query(
			"File",
			filters={"file_url": image, "is_private": 1},
			fields=["owner"],
		).run(pluck="owner")

		allowed_owners = {self.user, frappe.session.user}
		if any(owner not in allowed_owners for owner in owners):
			frappe.throw("You can only use an image you uploaded", frappe.PermissionError)

	@frappe.whitelist(methods=["POST"])
	def set_cover_image_position(self, position):
		"""Reposition the cover from the profile page.

		`cover_image_position` is what every read path reports for a bound cover (see
		`bound_bento_image_position`), so this is the only write that matters. The bound
		row is mirrored anyway so a stored row never holds a misleading value. Doing it
		here rather than re-posting the whole layout also avoids dropping the rows of
		bound fields that are currently empty, because the read path omits them.
		"""
		check_profile_bento_save_permission(self)

		position = optional_int_range(position, 0, 100, "Image position")
		if position is None:
			frappe.throw("Image position is required")

		self.cover_image_position = position
		for row in self.get("bento_cards"):
			if row.get("source") == "field" and row.get("field") == "cover_image":
				row.image_position = position
		self.save(ignore_permissions=True)

		return {"cover_image_position": self.cover_image_position}

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
		# A rename changes what *other* sessions render, and their cached user list has
		# no other reason to refetch.
		notify_users_changed()


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

	# The five count queries below all filter on `IN (users)`. An empty list renders as
	# `IN ()`, which MariaDB rejects, so a page or filter that matched nobody returned
	# HTTP 500 rather than an empty list.
	if not users:
		return data

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
	return get_profile_bento_response(profile)


@frappe.whitelist(methods=["POST"])
def save_my_bento_cards(cards: list | str):
	profile = get_session_user_profile()
	check_profile_bento_save_permission(profile)
	profile.set("bento_cards", normalize_bento_cards(cards))
	# Set unconditionally, so saving an empty layout ("nothing on my profile") sticks
	# instead of falling back to the computed default on the next read.
	profile.layout_customized = 1
	profile.save(ignore_permissions=True)
	return get_profile_bento_response(profile)


@frappe.whitelist(methods=["POST"])
def reset_my_bento_cards():
	"""Drop the saved layout so the profile follows the computed default again.

	The inverse of `save_my_bento_cards`, and it has to clear both halves: the rows
	are what a read returns, and `layout_customized` is what makes it prefer them.
	Bound values are untouched — they live on the profile, never on the layout.
	"""
	profile = get_session_user_profile()
	check_profile_bento_save_permission(profile)
	profile.set("bento_cards", [])
	profile.layout_customized = 0
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
	cards = (profile_bento_row_to_card(row, profile) for row in profile.get("bento_cards"))
	# Bound cards resolve to None when the profile field they point at is empty.
	return [card for card in cards if card is not None]


def get_profile_bento_response(profile):
	is_default = not profile.layout_customized
	return {
		"profile": profile.name,
		"cards": get_profile_bento_default_cards(profile) if is_default else get_profile_bento_cards(profile),
		"is_default": is_default,
	}


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
	seen_bound_fields = set()
	return [normalize_bento_card(card, seen_card_ids, seen_bound_fields) for card in cards]


def normalize_bento_card(card, seen_card_ids, seen_bound_fields):
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
	source = normalize_bento_card_source(card.get("source"))
	field = normalize_bento_card_field(card, source, card_type, seen_bound_fields)
	image_rendering = optional_allowed_value(
		card.get("imageRendering") or card.get("image_rendering") or "Cover",
		PROFILE_BENTO_IMAGE_RENDERING,
		"Image rendering",
	)
	# A bound card never stores its value; it is resolved from the profile on every read.
	text = None if source == "field" else normalize_bento_card_text(card.get("text"), card_type)
	image = None if source == "field" else normalize_bento_card_image(card.get("image"), card_type)
	if source == "custom" and card_type == "Card" and not text and not image:
		frappe.throw("Cards must have text or an image")

	return {
		"card_id": card_id,
		"source": source,
		"field": field,
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


def normalize_bento_card_source(value):
	return optional_allowed_value(value, PROFILE_BENTO_CARD_SOURCES, "Card source") or "custom"


def normalize_bento_card_field(card, source, card_type, seen_bound_fields):
	field = (card.get("field") or "").strip() or None
	if source != "field":
		return None

	if card_type != "Card":
		frappe.throw("Only cards of type Card can be bound to a profile field")
	if not field:
		frappe.throw("Bound cards must name a profile field")
	if field not in PROFILE_BENTO_BOUND_FIELDS:
		frappe.throw(f"Invalid bound field: {field}")
	if field in seen_bound_fields:
		frappe.throw(f"Duplicate bound field: {field}")
	seen_bound_fields.add(field)
	return field


def profile_bento_row_to_card(row, profile):
	"""Build the API shape for one stored row, or None when a bound field is empty."""
	source = row.get("source") or "custom"
	if source == "field":
		return build_bound_bento_card(
			profile,
			row.get("field"),
			card_id=row.card_id,
			size=row.size,
			title=row.title,
			image_rendering=row.image_rendering or "Cover",
			image_position=row.image_position,
			url=row.url,
		)

	card = {
		"id": row.card_id,
		"type": row.type,
		"size": row.size,
		"title": row.title,
		"imageRendering": row.image_rendering or "Cover",
		"source": "custom",
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


def build_bound_bento_card(
	profile,
	field,
	card_id,
	size,
	title,
	image_rendering="Cover",
	image_position=None,
	url=None,
):
	spec = PROFILE_BENTO_BOUND_FIELDS.get(field)
	if not spec:
		return None

	value = resolve_profile_bound_value(profile, field)
	if value is None:
		return None

	kind = spec["kind"]
	image_position = bound_bento_image_position(profile, field, image_position)
	card = {
		"id": card_id,
		"type": "Card",
		"size": size,
		"title": title,
		"imageRendering": image_rendering,
		"source": "field",
		"field": field,
		"format": kind,
	}
	card["image" if kind == "image" else "text"] = value
	if url:
		card["url"] = url
	if image_position is not None:
		card["imagePosition"] = image_position

	return card


def resolve_profile_bound_value(profile, field):
	"""Current value of a bound profile field, or None when it counts as empty."""
	if field == "full_name":
		full_name = profile.full_name or frappe.db.get_value("User", profile.user, "full_name")
		return full_name or profile.user or None

	value = profile.get(field)
	if field == "readme":
		return value if html_has_content(value) else None
	if isinstance(value, str):
		value = value.strip()
	return value or None


def html_has_content(value):
	"""True when HTML carries visible content. An empty TipTap doc is `<p></p>`."""
	if not value:
		return False
	if PROFILE_BENTO_HTML_MEDIA_PATTERN.search(value):
		return True
	text = PROFILE_BENTO_HTML_TAG_PATTERN.sub("", value).replace("&nbsp;", " ")
	return bool(text.strip())


def get_profile_bento_default_cards(profile):
	"""The computed default layout: one bound card per non-empty profile field."""
	cards = []
	for field, spec in PROFILE_BENTO_BOUND_FIELDS.items():
		card = build_bound_bento_card(
			profile,
			field,
			card_id=spec["id"],
			size=spec["size"],
			title=spec["title"],
			image_position=PROFILE_BENTO_DEFAULT_IMAGE_POSITION,
		)
		if card is not None:
			cards.append(card)
	return cards


def bound_bento_image_position(profile, field, stored_position=None):
	"""Where a bound card's image sits.

	For a bound cover the profile is the single source of truth: the position belongs
	to the image, not to the layout, so `profile.cover_image_position` wins over
	whatever a stored row carries. That makes the computed default and a saved layout
	agree by construction — a stale `imagePosition` posted back with the layout can no
	longer revert a reposition. Every other bound field keeps the layout's value.
	"""
	if field != "cover_image":
		return stored_position
	if profile.cover_image_position is None:
		return PROFILE_BENTO_DEFAULT_IMAGE_POSITION
	# cover_image_position is a Float on the profile, image_position an Int on the card.
	# Clamp to the same range the save path uses.
	return min(100, max(0, int(profile.cover_image_position)))


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
