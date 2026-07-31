# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt


import frappe
from frappe import _


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
		from gameplan.permissions import can_view_content

		# Only a reaction that was ADDED is news. Sizes are the wrong test in both
		# directions: a withdrawal changes the count too (and would re-raise a bell the
		# owner already cleared, about a reaction that no longer exists), while swapping
		# one emoji for another in a single save leaves the count equal even though the
		# new emoji is a reaction the owner has never been told about.
		previous = self.get_doc_before_save()
		previous_keys = previous.reaction_keys() if previous else set()
		# Your own reaction never notifies you and is never counted: the row would
		# otherwise read "1 person reacted to your post" about yourself.
		added = {key for key in self.reaction_keys() - previous_keys if key[0] != self.owner}
		if not added:
			return

		# Several changes can land in one save (the frontend debounces a quick tap-tap
		# into one batch). The message describes the post as it now stands, not the
		# delta, so it stays true however many rows moved.
		people = list({r.user for r in self.get("reactions") if r.user != self.owner})
		if not can_view_content(self.owner, self):
			return

		match len(people):
			case 1:
				message = "1 person reacted to your post"
			case _:
				message = f"{len(people)} people reacted to your post"
		values = frappe._dict(
			to_user=self.owner,
			type="Reaction",
		)
		if self.doctype == "GP Discussion":
			values.discussion = self.name
		elif self.doctype == "GP Comment":
			values.comment = self.name
		elif self.doctype == "GP Poll":
			values.poll = self.name
			values.discussion = self.discussion

		lookup = values.copy()
		if self.doctype == "GP Discussion":
			# Poll and comment notifications also carry their discussion for routing.
			# Excluding both keeps a later discussion reaction from overwriting either row.
			lookup.poll = ["is", "not set"]
			lookup.comment = ["is", "not set"]

		if frappe.db.exists("GP Notification", lookup):
			doc = frappe.get_doc("GP Notification", lookup)
		else:
			doc = frappe.get_doc(doctype="GP Notification")
			doc.update(values)
			if self.doctype == "GP Comment":
				doc.discussion = self.reference_name if self.reference_doctype == "GP Discussion" else None
				doc.task = self.reference_name if self.reference_doctype == "GP Task" else None
		doc.message = message
		doc.read = 0
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
