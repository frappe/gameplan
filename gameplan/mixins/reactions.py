# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt


import frappe
from frappe import _
from frappe.query_builder import Criterion

from gameplan.notifications import records
from gameplan.notifications.preferences import wants_content_feedback
from gameplan.utils.document import with_stored_document

REACTION_FIELDS = ["name", "reference_doctype", "reference_name", "emoji", "user"]


class HasReactions:
	"""A post people can react to. Reactions are GP Reaction rows that point at the post."""

	@frappe.whitelist(methods=["POST"])
	@with_stored_document
	def react(self, operations=None):
		"""Change the current user's reactions; `operations` lists {"emoji", "operation": "add"|"remove"}."""
		from gameplan.permissions import can_view_content

		operations = frappe.parse_json(operations) or []
		if not isinstance(operations, list):
			frappe.throw("Invalid reactions payload")

		user = frappe.session.user

		# Reacting is a participation action available to anyone who can VIEW the
		# content — members and guests alike in the spaces they can reach. Each
		# operation below only ever touches the acting user's own reaction rows
		# (matched on `user` == frappe.session.user), so this cannot mutate others'
		# data or the post body.
		if not can_view_content(user, self):
			frappe.throw(_("You do not have access to react to this"), frappe.PermissionError)

		if not operations:
			return self.get_reactions()

		# Lock the post's row so that two reactions on one post apply one after another.
		# The reactions are then read with a locking read too, which returns the rows other
		# requests committed after this one began. A unique index cannot do this job: under
		# the site's collation, MariaDB compares every emoji outside the BMP as equal.
		frappe.db.get_value(self.doctype, self.name, "name", for_update=True)
		reactions = self.get_reactions(for_update=True)
		mine = [row for row in reactions if row.user == user]
		wanted = list(dict.fromkeys(row.emoji for row in mine))
		for operation in operations:
			emoji = operation.get("emoji")
			action = operation.get("operation")
			if not emoji or action not in {"add", "remove"}:
				continue
			if action == "add" and emoji not in wanted:
				wanted.append(emoji)
			elif action == "remove" and emoji in wanted:
				wanted.remove(emoji)

		removed = [row for row in mine if row.emoji not in wanted]
		added = [emoji for emoji in wanted if emoji not in {row.emoji for row in mine}]
		for row in removed:
			frappe.db.delete("GP Reaction", {"name": row.name})
		for emoji in added:
			frappe.get_doc(
				doctype="GP Reaction",
				reference_doctype=self.doctype,
				reference_name=self.name,
				emoji=emoji,
				user=user,
			).insert(ignore_permissions=True)

		reactions = self.get_reactions(for_update=True)
		self.notify_reactions(reactions, added={(user, emoji) for emoji in added})
		return reactions

	def get_reactions(self, for_update=False):
		return frappe.qb.get_query(
			"GP Reaction",
			fields=REACTION_FIELDS,
			filters={"reference_doctype": self.doctype, "reference_name": str(self.name)},
			order_by="name asc",
			for_update=for_update,
		).run(as_dict=True)

	def remove_all_reactions(self):
		"""Drop everyone's reactions on this post when the post is deleted.

		Runs privileged and in bulk: it is a consequence of an already-authorised post
		delete, and only System Manager may delete GP Reaction rows. It runs in on_trash,
		before frappe's dynamic link check would refuse the delete over these rows.
		"""
		frappe.db.delete("GP Reaction", {"reference_doctype": self.doctype, "reference_name": str(self.name)})

	def notify_reactions(self, reactions, added):
		"""Tell the post owner about the `added` (user, emoji) keys, given all `reactions`."""
		from gameplan.permissions import can_view_content

		# Only a reaction that was ADDED is news. A withdrawal is not: it would re-raise a
		# bell the owner already cleared, about a reaction that no longer exists.
		# Your own reaction never notifies you and is never counted: the row would
		# otherwise read "1 person reacted to your post" about yourself.
		if not any(user != self.owner for user, _emoji in added):
			return
		if not wants_content_feedback(self.owner):
			return
		if not can_view_content(self.owner, self):
			return
		self._relight_reaction_row(self._reaction_message(reactions))

	def _reaction_message(self, reactions) -> str:
		"""How the post stands now, not what this call changed: several reactions can land
		in one call (the frontend debounces a quick tap-tap into one batch), and the row is
		rewritten each time."""
		people = {reaction.user for reaction in reactions if reaction.user != self.owner}
		if len(people) == 1:
			return "1 person reacted to your post"
		return f"{len(people)} people reacted to your post"

	def _relight_reaction_row(self, message: str) -> None:
		"""One row per piece of content, reused every time: a reaction that arrives after
		the row was read, emailed or skipped has to surface as the news it is."""
		owned = frappe._dict(to_user=self.owner, type="Reaction")
		lookup = frappe._dict(owned, **records.content_key(self))

		# One row per post is shared by every reactor. Read it with a lock: a plain read
		# returns this request's snapshot, which misses a save another reaction just
		# committed, and saving that stale copy fails with TimestampMismatchError.
		if existing := frappe.db.get_value("GP Notification", lookup, "name", for_update=True):
			doc = frappe.get_doc("GP Notification", existing, for_update=True)
		else:
			doc = frappe.get_doc(doctype="GP Notification")
			doc.update(owned)
			doc.update(records.target_fields(self))

		doc.message = message
		records.relight(doc, self.owner)
		doc.flags.ignore_permissions = True
		doc.save()


def get_reactions_on(posts):
	"""Reactions on `posts`, given as {post doctype: post names}.

	A thread page loads the reactions of everything in it in one request, alongside its
	comments. Whoever can read a thread can read everything in it, so the thread's
	thread_reactions method checks only the thread and lists its posts."""
	Reaction = frappe.qb.DocType("GP Reaction")
	# reference_name is text and post names are numbers: compare as text, so the index applies.
	on_posts = [
		(Reaction.reference_doctype == post_doctype) & Reaction.reference_name.isin([str(n) for n in names])
		for post_doctype, names in posts.items()
		if names
	]
	if not on_posts:
		return []
	return (
		frappe.qb.from_(Reaction)
		.select(*(Reaction[field] for field in REACTION_FIELDS))
		.where(Criterion.any(on_posts))
		.orderby(Reaction.name)
	).run(as_dict=True)
