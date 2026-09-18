# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class GPAwayPeriod(Document):
	"""One stretch during which a user was not to be reached: Receive notifications off
	(Toggle), or outside their active hours (Active hours).

	Rows exist for two reasons only — so a notification can say which stretch it fell in,
	and so the "while you were away" card has something to summarise. Whether a user is
	away *right now* is always computed from their profile (gameplan/notifications/away.py);
	a row is never consulted for that. A scheduled stretch in which nothing arrived never
	gets a row, which is what keeps quiet nights from producing an empty card.
	"""

	def before_insert(self):
		if not self.user:
			self.user = frappe.session.user


def on_doctype_update():
	# One row per (user, start): the lazy insert for a scheduled window must not race
	# itself into two rows. The second index is the card's "latest ended period" lookup.
	frappe.db.add_unique("GP Away Period", ["user", "starts_at"])
	frappe.db.add_index("GP Away Period", ["user", "ends_at"])
