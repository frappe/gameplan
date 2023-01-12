# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe

class HasReactions:
	def notify_reactions(self):
		previous = self.get_doc_before_save()
		if previous and len(previous.get('reactions')) == len(self.get('reactions')):
			return
		if len(self.get('reactions')) == 0:
			return

		people = list(set([r.user for r in self.get('reactions')]))
		match len(people):
			case 0:
				message = ''
			case 1:
				message = '1 person reacted to your post'
			case _:
				message = f"{len(people)} people reacted to your post"
		values = frappe._dict(
			to_user=self.owner,
			type='Reaction',
		)
		if self.doctype == 'GP Discussion':
			values.discussion = self.name
		elif self.doctype == 'Team Comment':
			values.comment = self.name

		if frappe.db.exists("Team Notification", values):
			doc = frappe.get_doc("Team Notification", values)
		else:
			doc = frappe.get_doc(doctype="Team Notification")
			doc.update(values)
			if self.doctype == 'Team Comment':
				doc.discussion = self.reference_name if self.reference_doctype == "GP Discussion" else None
				doc.task = self.reference_name if self.reference_doctype == "GP Task" else None
		doc.message = message
		doc.read = 0
		doc.flags.ignore_permissions = True
		doc.save()
