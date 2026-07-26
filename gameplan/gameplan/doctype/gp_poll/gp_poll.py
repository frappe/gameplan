# Copyright (c) 2023, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from gameplan.mixins.reactions import HasReactions
from gameplan.permissions import (
	can_delete_content,
	can_view_content,
	content_has_permission,
	poll_query_conditions,
)

from .gp_poll_attributes import GPPollAttributes


class GPPoll(HasReactions, Document, GPPollAttributes):
	"""A poll posted inside a discussion.

	It carries a `reactions` table and the UI hangs the same Reactions component off it
	as it does off a discussion or a comment, so it mixes in HasReactions and notifies
	its author when another user reacts. The notification carries both the poll and its
	discussion for routing; HasReactions keeps its lookup distinct from the discussion's
	own reaction notification.
	"""

	on_delete_set_null = ["GP Discussion", "GP Notification"]

	def before_insert(self):
		self.check_if_discussion_is_closed()
		if self.anonymous and self.multiple_answers:
			frappe.throw(_("Anonymous polls cannot allow multiple answers"))
		self.options = [d for d in self.options if d.title]
		for option in self.options:
			option.title = option.title.strip()
		# dont allow duplicate options
		options = [d.title for d in self.options]
		if len(set(options)) != len(options):
			frappe.throw(_("Duplicate options not allowed"))

	def check_if_discussion_is_closed(self):
		"""A poll is a post in the thread just like a comment, so a closed discussion
		refuses it too (GPComment.before_insert does the same). The UI hides the whole
		composer when a discussion is closed, which left this unenforced on the server.
		"""
		if not self.discussion:
			return
		if frappe.db.get_value("GP Discussion", self.discussion, "closed_at"):
			frappe.throw(_("Cannot add a poll to a closed discussion"))

	def validate(self):
		self.total_votes = len(self.votes)
		self.de_duplicate_reactions()

	def after_insert(self):
		self.update_discussion_meta()

	def after_delete(self):
		self.update_discussion_meta()

	def on_update(self):
		self.notify_reactions()

	def update_discussion_meta(self):
		if not self.discussion:
			return
		discussion = frappe.get_doc("GP Discussion", self.discussion)
		discussion.update_last_post()
		discussion.update_post_count()
		discussion.update_participants_count()
		discussion.track_visit()
		discussion.save(ignore_permissions=True)

	@frappe.whitelist(methods=["POST"])
	def submit_vote(self, option):
		self.discard_client_state()
		self.check_can_participate()
		self.check_if_stopped()
		selected = self.get_option(option)

		if self.anonymous:
			# An anonymous vote records the voter without their choice, so there is no row
			# to tie a second answer to (or to retract later): one vote per voter, always.
			if self.has_voted():
				return
			self.append("votes", {"user": frappe.session.user})
			selected.votes = (selected.votes or 0) + 1
		else:
			# One vote per user — or, on a multiple-answer poll, one vote per user per
			# option, so voting again for the same option stays a no-op.
			if self.has_voted(option=selected.title if self.multiple_answers else None):
				return
			self.append("votes", {"user": frappe.session.user, "option": selected.title})

		self.update_tallies()
		self.save_after_voting()

	@frappe.whitelist(methods=["POST"])
	def retract_vote(self, option=None):
		self.discard_client_state()
		self.check_can_participate()
		self.check_if_stopped()
		if self.anonymous:
			frappe.throw(_("Cannot retract vote for anonymous poll"))
		user = frappe.session.user
		self.votes = [
			d for d in self.votes if not (d.user == user and (option is None or d.option == option))
		]
		self.update_tallies()
		self.save_after_voting()

	@frappe.whitelist(methods=["POST"])
	def stop_poll(self):
		self.discard_client_state()
		if not can_delete_content(frappe.session.user, self):
			frappe.throw(_("Only the owner or an admin can stop the poll"), frappe.PermissionError)
		self.stopped_at = frappe.utils.now()
		self.save()

	def discard_client_state(self):
		"""Re-read the stored poll, dropping any field values the caller sent.

		The v2 document-method route loads the stored document, but its POST permission
		is deliberately Gameplan's interaction tier: guests and members who may
		participate can invoke these methods without being allowed to edit poll fields.
		The vote save then bypasses write permission so it can persist that interaction.
		Reloading before the business checks makes the method's invariant explicit:
		`stopped_at`, `discussion`, `anonymous`, `multiple_answers`, options, and every
		field written back come from storage, even if another whitelisted document
		surface or in-process caller hands the method a dirty instance.
		"""
		self.reload()

	def save_after_voting(self):
		"""Persist a vote without requiring write access to the poll itself.

		Voting is participation, like reacting: the gate is `check_can_participate`, and
		the vote methods only ever touch the acting user's own vote row plus the derived
		tallies. A plain `save()` would instead ask for `write`, which a guest only holds
		while nothing outside the interaction-safe fields changed — that check exists to
		stop a non-editor rewriting a poll's title or options, and it must keep doing so.

		Bypassing that check is only safe because `discard_client_state` has already
		thrown away everything the caller sent, so this save can carry nothing but the
		server-computed vote rows and tallies.
		"""
		self.save(ignore_permissions=True)

	def check_can_participate(self):
		if not can_view_content(frappe.session.user, self):
			frappe.throw(_("You do not have access to this poll"), frappe.PermissionError)

	def get_option(self, title):
		for option in self.options:
			if option.title == title:
				return option
		frappe.throw(_("{0} is not an option in this poll").format(title))

	def has_voted(self, option=None, user=None):
		user = user or frappe.session.user
		return any(d.user == user and (option is None or d.option == option) for d in self.votes)

	def update_tallies(self):
		"""Recompute the derived counts from the vote rows.

		`total_votes` counts vote rows, so on a multiple-answer poll it counts answers
		rather than voters — which keeps the option percentages adding up to 100%.
		"""
		self.total_votes = len(self.votes)
		if not self.anonymous:
			# An anonymous vote row has no option, so its per-option counter is
			# incremented when the vote is cast and cannot be recomputed here.
			for option in self.options:
				option.votes = len([d for d in self.votes if d.option == option.title])
		for option in self.options:
			option.percentage = (
				flt((option.votes or 0) * 100 / self.total_votes, 2) if self.total_votes else 0
			)

	def check_if_stopped(self):
		if self.stopped_at and self.stopped_at < frappe.utils.now_datetime():
			frappe.throw(_("Poll has ended"))


def get_permission_query_conditions(user):
	return poll_query_conditions(user)


def has_permission(doc, ptype="read", user=None):
	return content_has_permission(doc, ptype, user)
