# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt


import frappe
from frappe import _


class HasReactions:
	@frappe.whitelist()
	def react(self, operations=None):
		from gameplan.permissions import can_view_content

		operations = frappe.parse_json(operations) or []
		if not isinstance(operations, list):
			frappe.throw("Invalid reactions payload")

		if not operations:
			return self.get("reactions")

		user = frappe.session.user

		# Reacting is a participation action available to anyone who can VIEW the
		# content — members and guests alike in the spaces they can reach — not an
		# edit of the content itself, so it is gated on view rather than write.
		# Each operation below only ever touches the acting user's own reaction row
		# (matched on `user` == frappe.session.user), so the save can safely ignore
		# the write permission without letting anyone mutate others' data or the
		# post. This is what lets a guest react to a member's post while still being
		# unable to edit it.
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
		self.save(ignore_permissions=True)
		return self.get("reactions")

	def notify_reactions(self):
		previous = self.get_doc_before_save()
		if previous and len(previous.get("reactions")) == len(self.get("reactions")):
			return
		if len(self.get("reactions")) == 0:
			return

		people = list(set([r.user for r in self.get("reactions")]))
		match len(people):
			case 0:
				message = ""
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

		if frappe.db.exists("GP Notification", values):
			doc = frappe.get_doc("GP Notification", values)
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
