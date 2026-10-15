# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt


import frappe
from frappe import _

from gameplan.notifications import records
from gameplan.notifications.away import get_active_away_period
from gameplan.notifications.preferences import wants_content_feedback


class HasReactions:
	@frappe.whitelist(methods=["POST"])
	def react(self, operations=None):
		from gameplan.permissions import can_view_content

		operations = frappe.parse_json(operations) or []
		if not isinstance(operations, list):
			frappe.throw("Invalid reactions payload")

		if not operations:
			return self.get("reactions")

		user = frappe.session.user

		# Reacting is a participation action available to anyone who can VIEW the
		# content — members and guests alike in the spaces they can reach. Each
		# operation below only ever touches the acting user's own reaction row
		# (matched on `user` == frappe.session.user), so this cannot mutate others'
		# data or the post body. The save runs through the normal permission path:
		# guests hold write ("may interact") on content in a space they can access,
		# and can_write_content lets a non-editor's save through as long as only
		# interaction-safe fields (reactions) changed.
		if not can_view_content(user, self):
			frappe.throw(_("You do not have access to react to this"), frappe.PermissionError)
		reactions = list(self.get("reactions") or [])

		for operation in operations:
			emoji = operation.get("emoji")
			action = operation.get("operation")
			if not emoji or action not in {"add", "remove"}:
				continue

			if action == "remove":
				reactions = [
					reaction
					for reaction in reactions
					if not (reaction.user == user and reaction.emoji == emoji)
				]
				continue

			if any(reaction.user == user and reaction.emoji == emoji for reaction in reactions):
				continue
			reactions.append(frappe._dict({"emoji": emoji, "user": user}))

		self.set("reactions", reactions)
		self.de_duplicate_reactions()
		self.save()
		return self.get("reactions")

	def reaction_keys(self):
		"""A reaction is identified by (user, emoji) — the same identity `react` uses."""
		return {(reaction.user, reaction.emoji) for reaction in (self.get("reactions") or [])}

	def notify_reactions(self):
		if not self._reactions_added_by_others():
			return
		if not wants_content_feedback(self.owner):
			return

		from gameplan.permissions import can_view_content

		if not can_view_content(self.owner, self):
			return
		self._relight_reaction_row(self._reaction_message())

	def _reactions_added_by_others(self) -> set:
		"""Reactions this save introduced, the owner's own excluded. A withdrawal or a
		swapped emoji leaves the count unchanged, so counts cannot answer this."""
		previous = self.get_doc_before_save()
		seen = previous.reaction_keys() if previous else set()
		return {key for key in self.reaction_keys() - seen if key[0] != self.owner}

	def _reaction_message(self) -> str:
		"""How the post stands now, not what this save changed: several reactions can land
		in one save, and the row is rewritten each time."""
		people = {reaction.user for reaction in self.get("reactions") if reaction.user != self.owner}
		if len(people) == 1:
			return "1 person reacted to your post"
		return f"{len(people)} people reacted to your post"

	def _relight_reaction_row(self, message: str) -> None:
		"""One row per piece of content, reused every time: a reaction that arrives after
		the row was read, emailed or skipped has to surface as the news it is."""
		owned = frappe._dict(to_user=self.owner, type="Reaction")
		lookup = frappe._dict(owned, **records.content_key(self))

		if frappe.db.exists("GP Notification", lookup):
			doc = frappe.get_doc("GP Notification", lookup)
		else:
			doc = frappe.get_doc(doctype="GP Notification")
			doc.update(owned)
			doc.update(records.target_fields(self))

		doc.message = message
		doc.read = 0
		doc.email_sent_at = None
		doc.email_skipped_at = None
		doc.last_event_at = frappe.utils.now()
		doc.away_period = get_active_away_period(self.owner)
		doc.flags.ignore_permissions = True
		doc.save()

	def de_duplicate_reactions(self):
		seen = []
		reactions = []
		for reaction in self.reactions:
			row = (reaction.user, reaction.emoji)
			if row not in seen:
				reactions.append(reaction)
				seen.append(row)
		self.reactions = reactions
