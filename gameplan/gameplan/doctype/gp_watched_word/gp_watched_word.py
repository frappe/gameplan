import frappe
from frappe.model.document import Document


class GPWatchedWord(Document):
	def validate(self):
		from gameplan.watched_words import validate_rule

		validate_rule(self)

	def on_trash(self):
		from gameplan.permissions import require_can_manage_community

		require_can_manage_community(self.community)

		frappe.local.request_cache.clear()


def on_doctype_update():
	frappe.db.add_index("GP Watched Word", ["community", "action"], "community_watched_words")
