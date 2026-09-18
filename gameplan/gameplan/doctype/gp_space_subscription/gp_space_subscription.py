# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class GPSpaceSubscription(Document):
	"""One user's wish to hear about new discussions in one space.

	A plain on/off: the row exists while the toggle is on and is deleted when it goes off,
	so "who is subscribed to this space?" is one query with no state column to read. The
	row is also the audience for a discussion moving in or out of the space. It never
	changes what the user hears about inside a discussion — that is the discussion
	subscription's job (see gameplan/notifications/resolver.py).
	"""

	def before_insert(self):
		if not self.user:
			self.user = frappe.session.user


def on_doctype_update():
	# One toggle per (user, space); the second index is the fan-out on a new discussion
	# ("who is subscribed to this space?").
	frappe.db.add_unique("GP Space Subscription", ["user", "project"])
	frappe.db.add_index("GP Space Subscription", ["project"])
