# Copyright (c) 2023, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import DATETIME_FORMAT, cint, cstr, flt, get_datetime

from gameplan.mixins.archivable import check_if_space_is_archived
from gameplan.mixins.reactions import HasReactions
from gameplan.permissions import (
	can_delete_content,
	can_view_content,
	content_has_permission,
	poll_query_conditions,
)
from gameplan.utils.document import with_stored_document

from .gp_poll_attributes import GPPollAttributes


def poll_has_stopped(stopped_at, now=None) -> bool:
	"""Whether a poll with this `stopped_at` is closed at `now`.

	`stopped_at` is the instant the poll stops, not the last instant it runs: `stop_poll`
	stamps it with the current time, so if that exact microsecond still counted as open a
	vote could land after the stop was recorded. The boundary is therefore inclusive — at
	`stopped_at` the ballot is shut.

	This is the one place that rule is written down. `ongoing_polls_clause` is its query
	mirror for callers that must ask the database instead (the discussion feed), and
	TestFeedOngoingPolls.test_the_feed_and_the_ballot_close_at_the_same_instant pins the
	two together so they cannot drift apart again.
	"""
	if not stopped_at:
		return False
	return get_datetime(stopped_at) <= (now or frappe.utils.now_datetime())


def ongoing_polls_clause(Poll, now=None):
	"""Query-builder mirror of `poll_has_stopped`: the polls still open at `now`.

	A poll with no `stopped_at` runs until someone stops it, so it is always ongoing.
	SQLite compares datetimes as text, so `now` is rendered in the same format Frappe
	stored the column in — otherwise the two mirrors would part company on the
	microseconds, which is the exact boundary they exist to keep in step.
	"""
	now = now or frappe.utils.now_datetime()
	return Poll.stopped_at.isnull() | (Poll.stopped_at > now.strftime(DATETIME_FORMAT))


class GPPoll(HasReactions, Document, GPPollAttributes):
	"""A poll posted inside a discussion.

	The UI hangs the same Reactions component off it as it does off a discussion or a
	comment, so it mixes in HasReactions and notifies its author when another user
	reacts. The notification carries both the poll and its discussion for routing;
	HasReactions keeps its lookup distinct from the discussion's own reaction
	notification.
	"""

	on_delete_set_null = ["GP Discussion", "GP Notification"]

	def before_insert(self):
		self.check_if_discussion_is_closed()
		self.check_comment()
		if self.anonymous and self.multiple_answers:
			frappe.throw(_("Anonymous polls cannot allow multiple answers"))
		self.options = [d for d in self.options if d.title]
		self.set("votes", [])
		for option in self.options:
			option.title = option.title.strip()
			option.votes = 0
			option.percentage = 0
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

	def check_comment(self):
		if not self.comment:
			return
		comment = frappe.db.get_value(
			"GP Comment", self.comment, ["reference_doctype", "reference_name", "owner"], as_dict=True
		)
		if comment.reference_doctype != "GP Discussion" or comment.reference_name != str(self.discussion):
			frappe.throw(_("A poll can only be attached to a comment in the same discussion"))
		if comment.owner != frappe.session.user:
			frappe.throw(_("You can only attach a poll to your own comment"), frappe.PermissionError)
		if frappe.db.exists("GP Poll", {"comment": self.comment}):
			frappe.throw(_("A comment can only have one poll"))

	def validate(self):
		self.check_comment_unchanged()
		self.check_results_unchanged()
		self.total_votes = len(self.votes)

	def check_comment_unchanged(self):
		before = self.get_doc_before_save()
		if not before:
			return
		if cstr(before.comment) != cstr(self.comment):
			frappe.throw(_("A poll cannot be moved to another comment"))
		if self.comment and cstr(before.discussion) != cstr(self.discussion):
			frappe.throw(_("A poll in a comment cannot be moved to another discussion"))

	def check_results_unchanged(self):
		"""Refuse a plain save that changes the vote rows or an option's counts.

		Results change only through `submit_vote` and `retract_vote`, which save with
		`ignore_permissions`. A plain save may still edit the title, add or remove
		options and stop the poll; a new option starts with no votes.
		"""
		if self.is_new() or self.flags.ignore_permissions:
			return
		before = self.get_doc_before_save()
		if before is None:
			return
		stored_counts = {d.name: (cint(d.votes), flt(d.percentage)) for d in before.options}
		votes_changed = [(d.user, d.option) for d in self.votes] != [(d.user, d.option) for d in before.votes]
		counts_changed = any(
			(cint(d.votes), flt(d.percentage)) != stored_counts.get(d.name, (0, 0)) for d in self.options
		)
		if votes_changed or counts_changed:
			frappe.throw(_("Poll results change only through voting"), frappe.PermissionError)

	def after_insert(self):
		self.update_discussion_meta()

	def on_trash(self):
		self.remove_all_reactions()

	def after_delete(self):
		if self.flags.from_gameplan_delete_cascade == "GP Discussion":
			# The discussion is being deleted and we are one of its children. Refreshing
			# its counters is pointless, and `track_visit` would insert a fresh GP
			# Discussion Visit row — the cascade sweeps those *before* it reaches the
			# polls, so the new row survives and trips the parent's link check.
			return
		self.update_discussion_meta()

	def update_discussion_meta(self):
		if not self.discussion or self.comment:
			return
		discussion = frappe.get_doc("GP Discussion", self.discussion)
		discussion.update_last_post()
		discussion.update_post_count()
		discussion.update_participants_count()
		discussion.save(ignore_permissions=True)
		# track_visit reloads the stored discussion, so save the counters first.
		discussion.track_visit()

	@frappe.whitelist(methods=["POST"])
	@with_stored_document
	def submit_vote(self, option):
		self.check_can_participate()
		check_if_space_is_archived(self, action="vote in", content_type="polls")
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
			if self.has_voted(option=selected.title):
				# Already this voter's answer for this option. On a multiple-answer poll
				# the way to undo an answer is retract_vote, not a second submit.
				return
			if not self.multiple_answers:
				# One answer per voter, but a voter may change their mind: the new answer
				# replaces the previous one rather than being ignored.
				self.votes = [d for d in self.votes if d.user != frappe.session.user]
			self.append("votes", {"user": frappe.session.user, "option": selected.title})

		self.update_tallies()
		self.save_after_voting()

	@frappe.whitelist(methods=["POST"])
	@with_stored_document
	def retract_vote(self, option=None):
		self.check_can_participate()
		check_if_space_is_archived(self, action="retract votes from", content_type="polls")
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
	@with_stored_document
	def stop_poll(self):
		if not can_delete_content(frappe.session.user, self):
			frappe.throw(_("Only the owner or an admin can stop the poll"), frappe.PermissionError)
		check_if_space_is_archived(self, action="stop", content_type="polls")
		self.stopped_at = frappe.utils.now()
		self.save()

	def save_after_voting(self):
		"""Persist a vote without requiring write access to the poll itself.

		Voting is participation, like reacting: the gate is `check_can_participate`, and
		the vote methods only ever touch the acting user's own vote row plus the derived
		tallies. A plain `save()` would instead ask for `write`, which a guest only holds
		while nothing changed — that check exists to stop a non-editor rewriting a poll's
		title or options, and it must keep doing so.

		Skipping that check is correct because `with_stored_document` rebuilds the poll
		from storage before the vote method runs, so this save carries only the
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
		rather than voters — which is what the UI labels "N answers from M people".

		A percentage answers "how many of the people who voted chose this?", so it is a
		share of the *voters*, not of the answer rows. On a single-answer poll those are
		the same number. On a multiple-answer poll they are not, and dividing by the
		rows would report a two-option voter as 50/50 when they in fact picked both;
		the shares add up to more than 100% instead, which is how "select all that
		apply" results are read everywhere else.
		"""
		self.total_votes = len(self.votes)
		if not self.anonymous:
			# An anonymous vote row has no option, so its per-option counter is
			# incremented when the vote is cast and cannot be recomputed here.
			for option in self.options:
				option.votes = len([d for d in self.votes if d.option == option.title])
		voters = self.count_voters()
		for option in self.options:
			option.percentage = flt((option.votes or 0) * 100 / voters, 2) if voters else 0

	def count_voters(self):
		"""How many distinct people have voted. One vote row per voter, except on a
		multiple-answer poll, where a voter has one row per option they picked."""
		return len({d.user for d in self.votes})

	def check_if_stopped(self):
		if poll_has_stopped(self.stopped_at):
			frappe.throw(_("Poll has ended"))


def get_permission_query_conditions(user):
	return poll_query_conditions(user)


def has_permission(doc, ptype="read", user=None):
	return content_has_permission(doc, ptype, user)
