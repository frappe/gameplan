# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt


import frappe


class HasReactions:
	@frappe.whitelist()
	def react(self, operations: list[dict] = None):
		if not isinstance(operations, list):
			frappe.throw("Invalid reactions payload")

		if not operations:
			return self.get("reactions")

		user = frappe.session.user
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
