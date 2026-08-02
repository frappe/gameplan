import frappe

# Starter cards used to store a frozen copy of the profile field they were built from.
# Convert them to bound cards, keyed by the card ID the old builder assigned.
STARTER_CARD_BINDINGS = {
	"cover": "cover_image",
	"avatar": "image",
	"full-name": "full_name",
	"bio": "bio",
}


def execute():
	if not frappe.db.table_exists("GP Profile Bento Card"):
		return

	bento_card = frappe.qb.DocType("GP Profile Bento Card")
	for card_id, field in STARTER_CARD_BINDINGS.items():
		(
			frappe.qb.update(bento_card)
			.set(bento_card.source, "field")
			.set(bento_card["field"], field)
			.set(bento_card.text, None)
			.set(bento_card.image, None)
			.where((bento_card.card_id == card_id) & (bento_card.type == "Card"))
		).run()

	if not frappe.db.table_exists("GP User Profile"):
		return

	user_profile = frappe.qb.DocType("GP User Profile")
	profiles_with_cards = (
		frappe.qb.from_(bento_card)
		.select(bento_card.parent)
		.where((bento_card.parenttype == "GP User Profile") & bento_card.parent.isnotnull())
		.distinct()
	)
	(
		frappe.qb.update(user_profile)
		.set(user_profile.layout_customized, 1)
		.where(user_profile.name.isin(profiles_with_cards))
	).run()
