import hashlib
import math
from datetime import timedelta

import frappe
from frappe.query_builder.functions import Coalesce
from frappe.utils import get_datetime, now_datetime

from gameplan.community_bans import can_moderate_community
from gameplan.permissions import can_moderate_space

INTERVALS = (0, 30, 60, 300, 900, 3600, 86400)


@frappe.whitelist(methods=["GET", "POST"])
def status(discussion: str):
	doc = frappe.get_doc("GP Discussion", discussion)
	doc.check_permission("read")
	seconds = doc.slow_mode_seconds or 0
	community = frappe.db.get_value("GP Project", doc.project, "team")
	exempt = can_moderate_community(community)
	return {
		"seconds": seconds,
		"can_manage": can_moderate_space(frappe.session.user, doc.project),
		"exempt": exempt,
		"retry_after": 0 if exempt or not seconds else remaining(seconds, last_submission(discussion)),
	}


@frappe.whitelist(methods=["POST"])
def set_mode(discussion: str, seconds: int, reason: str, expected_seconds: int):
	doc = frappe.get_doc("GP Discussion", discussion, for_update=True)
	doc.check_permission("read")
	if not can_moderate_space(frappe.session.user, doc.project):
		frappe.throw("Only Community moderators can change slow mode", frappe.PermissionError)
	if seconds not in INTERVALS:
		frappe.throw("Choose a supported slow-mode interval")
	if expected_seconds != (doc.slow_mode_seconds or 0):
		frappe.throw("Slow mode changed. Refresh before saving.", frappe.TimestampMismatchError)
	from gameplan.reporting import checked_note

	reason = checked_note(reason, required=True)
	if seconds != (doc.slow_mode_seconds or 0):
		frappe.get_doc(
			doctype="GP Moderation Log",
			discussion=str(doc.name),
			action="Slow Mode Changed",
			reason=reason,
			previous_slow_mode_seconds=doc.slow_mode_seconds or 0,
			slow_mode_seconds=seconds,
		).insert(ignore_permissions=True)
		doc.db_set("slow_mode_seconds", seconds)
	return status(discussion)


def protect_settings(doc, method=None):
	if doc.has_value_changed("slow_mode_seconds") and (doc.get_doc_before_save() or doc.slow_mode_seconds):
		frappe.throw("Use the slow-mode action to change this setting", frappe.PermissionError)


def record_reply(doc, method=None):
	if doc.doctype != "GP Comment" or doc.reference_doctype != "GP Discussion":
		return
	from gameplan.approval_files import publishing_submission

	publication = publishing_submission.get()
	if publication and publication[0] is doc:
		return
	user = frappe.session.user
	# All submission paths use the same account -> discussion lock order as approvals.
	frappe.db.get_value("User", user, "name", for_update=True)
	discussion = frappe.get_doc("GP Discussion", doc.reference_name, for_update=True)
	seconds = discussion.slow_mode_seconds or 0
	community = frappe.db.get_value("GP Project", discussion.project, "team")
	if seconds and not can_moderate_community(community):
		retry = remaining(seconds, last_submission(str(discussion.name), for_update=True))
		if retry:
			frappe.throw(
				f"Slow mode: wait {retry} seconds before replying again.", frappe.RateLimitExceededError
			)
	name = state_name(str(discussion.name), user)
	if frappe.db.get_value("GP Slow Mode State", name, "name", for_update=True):
		frappe.db.set_value("GP Slow Mode State", name, "last_submission", now_datetime())
	else:
		frappe.get_doc(
			doctype="GP Slow Mode State",
			discussion=str(discussion.name),
			user=user,
			last_submission=now_datetime(),
		).insert(ignore_permissions=True, set_name=name)


def preserve_deleted_reply(doc, method=None):
	if doc.reference_doctype != "GP Discussion" or doc.flags.from_gameplan_delete_cascade:
		return
	if not frappe.db.get_value("User", doc.owner, "name", for_update=True):
		return
	discussion = str(doc.reference_name)
	name = state_name(discussion, doc.owner)
	if frappe.db.get_value("GP Slow Mode State", name, "name", for_update=True):
		return
	last = last_submission(discussion, user=doc.owner, for_update=True)
	if last:
		frappe.get_doc(
			doctype="GP Slow Mode State", discussion=discussion, user=doc.owner, last_submission=last
		).insert(ignore_permissions=True, set_name=name)


def clear_state(doc, method=None):
	field = "user" if doc.doctype == "User" else "discussion"
	frappe.db.delete("GP Slow Mode State", {field: str(doc.name)})


def state_name(discussion, user):
	return hashlib.sha256(f"{discussion}:{user}".encode()).hexdigest()


def last_submission(discussion, *, user=None, for_update=False):
	user = user or frappe.session.user
	stored = frappe.db.get_value(
		"GP Slow Mode State", state_name(discussion, user), "last_submission", for_update=for_update
	)
	if stored:
		return stored
	# Existing approved replies retain their original submission time, not publication time.
	Comment, Submission = frappe.qb.DocType("GP Comment"), frappe.qb.DocType("GP Submission")
	accepted = Coalesce(Submission.creation, Comment.creation)
	replies = (
		frappe.qb.from_(Comment)
		.left_join(Submission)
		.on((Submission.published_doctype == "GP Comment") & (Submission.published_name == Comment.name))
		.select(accepted)
		.where(
			(Comment.reference_doctype == "GP Discussion")
			& (Comment.reference_name == discussion)
			& (Comment.owner == user)
		)
		.orderby(accepted, order=frappe.qb.desc)
		.limit(1)
	)
	submissions = (
		frappe.qb.from_(Submission)
		.select(Submission.creation)
		.where((Submission.discussion == discussion) & (Submission.owner == user))
		.orderby(Submission.creation, order=frappe.qb.desc)
		.limit(1)
	)
	# Legacy rows stay unlocked: deletion already holds a comment lock before checking its clock.
	times = replies.run(pluck=True) + submissions.run(pluck=True)
	return max(map(get_datetime, times)) if times else None


def remaining(seconds, last):
	if not last:
		return 0
	return max(
		0, math.ceil((get_datetime(last) + timedelta(seconds=seconds) - now_datetime()).total_seconds())
	)
