import hashlib
from datetime import timedelta

import frappe
from frappe.query_builder import Criterion
from frappe.query_builder.functions import Count
from frappe.utils import now_datetime

import gameplan
from gameplan.community_bans import can_moderate_community, require_participation
from gameplan.mixins.moderation import parent_discussion
from gameplan.paging import page_start
from gameplan.permissions import (
	apply_accessible_project_filter,
	can_moderate_space,
	can_view_content,
	get_content_project,
	has_guest_access,
)

REASONS = ("Spam", "Abuse/inappropriate", "Off-topic", "AI-generated", "Other")
DECISIONS = ("Dismiss", "Uphold", "Hide", "Delete Spam")


@frappe.whitelist(methods=["POST"])
def submit(doctype: str, name: str, reason: str, note: str = ""):
	user = frappe.session.user
	roles = set(frappe.get_roles(user))
	if gameplan.is_anonymous(user) or not (
		roles.intersection({"Gameplan Member", "Gameplan Guest"}) or gameplan.is_admin(user)
	):
		frappe.throw("Sign in to report content", frappe.PermissionError)
	doc = target(doctype, name)
	project = get_content_project(doc)
	if (
		doc.owner == user
		or doc.get("deleted_at")
		or not can_view_content(user, doc)
		or (gameplan.is_guest(user) and not has_guest_access(user, project))
	):
		frappe.throw("You cannot report this content", frappe.PermissionError)
	require_participation(doc)
	if reason not in REASONS:
		frappe.throw("Choose a report reason")
	note = checked_note(note, required=reason == "Other")
	# Lock the account before checking pending reviews across different targets.
	frappe.db.get_value("User", user, "name", for_update=True)
	Review = frappe.qb.DocType("GP Review")
	pending = (
		frappe.qb.from_(Review)
		.select(Review.name)
		.where(
			(Review.reference_doctype == doctype)
			& (Review.reference_name == name)
			& (Review.status == "Pending")
		)
		.for_update()
		.run(pluck=True)
	)
	Report = frappe.qb.DocType("GP Report")
	if pending:
		existing = (
			frappe.qb.from_(Report)
			.select(Report.name)
			.where((Report.review == pending[0]) & (Report.owner == user))
			.for_update()
			.run(pluck=True)
		)
		if existing:
			return {"name": existing[0]}
	recent = (
		frappe.qb.from_(Report)
		.select(Report.name)
		.where((Report.owner == user) & (Report.creation > now_datetime() - timedelta(hours=1)))
		.limit(10)
		.for_update()
		.run()
	)
	if len(recent) >= 10:
		frappe.throw("You can submit 10 reports per hour. Try again later.", frappe.RateLimitExceededError)
	review = (
		pending[0]
		if pending
		else frappe.get_doc(
			doctype="GP Review", reference_doctype=doctype, reference_name=name, status="Pending"
		)
		.insert(ignore_permissions=True)
		.name
	)
	# A locked existing review can be newer than MariaDB's read snapshot.
	report = frappe.get_doc(
		doctype="GP Report",
		review=review,
		reason=reason,
		note=note,
		reported_title=doc.get("title"),
		reported_content=doc.content,
	).insert(ignore_permissions=True, ignore_links=bool(pending))
	frappe.db.sql(
		"""
		UPDATE `tabGP Review`
		SET `report_count` = `report_count` + 1, `last_reported_at` = %s
		WHERE `name` = %s
		""",
		(report.creation, review),
	)
	return {"name": report.name}


@frappe.whitelist(methods=["GET", "POST"])
def queue(community: str, status: str = "Pending", start: int = 0, sort_by: str = "recent"):
	if not can_moderate_community(community):
		frappe.throw("Only Community moderators can review reports", frappe.PermissionError)
	if status not in ("Pending", "Resolved"):
		frappe.throw("Unsupported review status")
	if sort_by not in ("recent", "most_reported"):
		frappe.throw("Unsupported report sort")
	Project, Discussion, Comment, Review = [
		frappe.qb.DocType(dt) for dt in ("GP Project", "GP Discussion", "GP Comment", "GP Review")
	]
	projects = apply_accessible_project_filter(
		frappe.qb.from_(Project).select(Project.name).where(Project.team == community), Project.name
	)
	discussions = frappe.qb.from_(Discussion).select(Discussion.name).where(Discussion.project.isin(projects))
	replies = (
		frappe.qb.from_(Comment)
		.select(Comment.name)
		.where((Comment.reference_doctype == "GP Discussion") & Comment.reference_name.isin(discussions))
	)
	visible = Criterion.any(
		[
			(Review.reference_doctype == "GP Discussion") & Review.reference_name.isin(discussions),
			(Review.reference_doctype == "GP Comment") & Review.reference_name.isin(replies),
		]
	)
	rows_query = (
		frappe.qb.from_(Review)
		.select(
			Review.name,
			Review.reference_doctype,
			Review.reference_name,
			Review.status,
			Review.report_count,
			Review.last_reported_at,
			Review.decision,
			Review.decided_by,
			Review.decided_at,
			Review.decision_note,
		)
		.where(visible & (Review.status == status))
	)
	if sort_by == "most_reported":
		rows_query = rows_query.orderby(Review.report_count, order=frappe.qb.desc)
	rows = (
		rows_query.orderby(Review.last_reported_at, order=frappe.qb.desc)
		.orderby(Review.name, order=frappe.qb.desc)
		.offset(page_start(start))
		.limit(41)
		.run(as_dict=True)
	)
	has_more = len(rows) > 40
	rows = rows[:40]
	Report = frappe.qb.DocType("GP Report")
	report_reasons = {}
	if rows:
		for result in (
			frappe.qb.from_(Report)
			.select(Report.review, Report.reason, Count(Report.name).as_("count"))
			.where(Report.review.isin([row.name for row in rows]))
			.groupby(Report.review, Report.reason)
			.orderby(Report.reason)
			.run(as_dict=True)
		):
			report_reasons.setdefault(result.review, []).append(
				{"reason": result.reason, "count": result.count}
			)
	comment_names = {row.reference_name for row in rows if row.reference_doctype == "GP Comment"}
	comment_discussions = {}
	if comment_names:
		comments = (
			frappe.qb.from_(Comment)
			.select(Comment.name, Comment.reference_name)
			.where(Comment.name.isin(comment_names))
		).run(as_dict=True)
		comment_discussions = {comment.name: comment.reference_name for comment in comments}
	discussion_names = {row.reference_name for row in rows if row.reference_doctype == "GP Discussion"} | set(
		comment_discussions.values()
	)
	discussion_titles = {}
	if discussion_names:
		titles = (
			frappe.qb.from_(Discussion)
			.select(Discussion.name, Discussion.title)
			.where(Discussion.name.isin(discussion_names))
		).run(as_dict=True)
		discussion_titles = {str(discussion.name): discussion.title for discussion in titles}
	for row in rows:
		discussion = (
			row.reference_name
			if row.reference_doctype == "GP Discussion"
			else comment_discussions.get(row.reference_name)
		)
		row["discussion_title"] = discussion_titles.get(discussion, "")
		row["report_reasons"] = report_reasons.get(row.name, [])
	return {"items": rows, "has_more": has_more}


@frappe.whitelist(methods=["GET", "POST"])
def detail(community: str, review: str, start: int = 0, report: str = ""):
	"""Read report metadata and current content; load evidence only when explicitly selected."""
	review, doc = review_target(community, review)
	reports = frappe.get_all(
		"GP Report",
		filters={"review": review.name},
		fields=["name", "owner", "creation", "reason", "note"],
		order_by="creation asc, name asc",
		limit_start=page_start(start),
		limit_page_length=41,
	)
	evidence = (
		frappe.db.get_value(
			"GP Report",
			{"review": review.name, "name": report},
			["name", "reported_title", "reported_content"],
			as_dict=True,
		)
		if report
		else None
	)
	if report and not evidence:
		frappe.throw("Report does not belong to this review", frappe.PermissionError)
	polls = review_polls(doc)
	return {
		"review": {
			field: review.get(field)
			for field in ("name", "status", "decision", "decision_note", "decided_by", "decided_at")
		},
		"current": {
			"title": doc.get("title"),
			"content": doc.content,
			"version": version(doc, polls),
			"owner": doc.owner,
			"discussion": str(parent_discussion(doc)),
			"project": str(get_content_project(doc)),
		},
		"reports": reports[:40],
		"evidence": evidence,
		"polls": [poll.as_dict() for poll in polls],
		"has_more": len(reports) > 40,
	}


@frappe.whitelist(methods=["POST"])
def resolve(community: str, review: str, decision: str, note: str, expected_version: str):
	review, doc = review_target(community, review)
	if review.status != "Pending":
		frappe.throw("This review was already resolved. Refresh the queue.", frappe.TimestampMismatchError)
	if expected_version != version(doc):
		frappe.throw(
			"This post changed. Refresh and review its current content.", frappe.TimestampMismatchError
		)
	if decision not in DECISIONS:
		frappe.throw("Choose a review decision")
	note = checked_note(note, required=True)
	if decision in ("Hide", "Delete Spam"):
		getattr(doc, "hide" if decision == "Hide" else "delete_spam")(note)
	review.db_set(
		{
			"status": "Resolved",
			"decision": decision,
			"decision_note": note,
			"decided_by": frappe.session.user,
			"decided_at": now_datetime(),
		}
	)


def target(doctype, name):
	if doctype not in ("GP Discussion", "GP Comment"):
		frappe.throw("Unsupported report target")
	doc = frappe.get_doc(doctype, name, for_update=True)
	if doctype == "GP Comment" and doc.reference_doctype != "GP Discussion":
		frappe.throw("Only discussion replies can be reported", frappe.PermissionError)
	return doc


def review_target(community, name):
	reference = frappe.db.get_value("GP Review", name, ["reference_doctype", "reference_name"], as_dict=True)
	if not reference or not can_moderate_community(community):
		frappe.throw("Only Community moderators can review reports", frappe.PermissionError)
	doc = target(reference.reference_doctype, reference.reference_name)
	project = get_content_project(doc)
	if frappe.db.get_value("GP Project", project, "team") != community or not can_moderate_space(
		frappe.session.user, project
	):
		frappe.throw("You cannot review this content", frappe.PermissionError)
	return frappe.get_doc("GP Review", name, for_update=True), doc


def protect_pending_reviews(doc, method=None):
	if method == "validate" and (
		doc.is_new()
		or not doc.has_value_changed("reference_doctype")
		or doc.reference_doctype == "GP Discussion"
	):
		return
	Review = frappe.qb.DocType("GP Review")
	pending = (
		frappe.qb.from_(Review)
		.select(Review.name)
		.where(
			(Review.reference_doctype == doc.doctype)
			& (Review.reference_name == str(doc.name))
			& (Review.status == "Pending")
		)
		.limit(1)
		.for_update()
		.run()
	)
	if pending:
		frappe.throw("Resolve pending reports before deleting this content or moving it outside discussions")


def review_polls(doc):
	if doc.doctype != "GP Comment":
		return []
	doc.check_permission("read")
	Poll = frappe.qb.DocType("GP Poll")
	rows = (
		frappe.qb.from_(Poll)
		.select(Poll.star)
		.where(Poll.comment == str(doc.name))
		.orderby(Poll.name)
		.for_update()
		.run(as_dict=True)
	)
	if not rows:
		return []
	children = {}
	for field, doctype in (("options", "GP Poll Option"), ("votes", "GP Poll Vote")):
		Child = frappe.qb.DocType(doctype)
		children[field] = {}
		for row in (
			frappe.qb.from_(Child)
			.select(Child.star)
			.where(
				(Child.parenttype == "GP Poll")
				& (Child.parentfield == field)
				& Child.parent.isin([str(row.name) for row in rows])
			)
			.orderby(Child.idx)
			.for_update()
			.run(as_dict=True)
		):
			children[field].setdefault(str(row.parent), []).append(row)
	return [
		frappe.get_doc(
			dict(
				row,
				doctype="GP Poll",
				**{field: parents.get(str(row.name), []) for field, parents in children.items()},
			)
		)
		for row in rows
	]


def version(doc, polls=None):
	polls = review_polls(doc) if polls is None else polls
	content = [
		[
			poll.name,
			poll.title,
			poll.anonymous,
			poll.multiple_answers,
			[(row.idx, row.title) for row in poll.options],
		]
		for poll in polls
	]
	return hashlib.sha256(frappe.as_json([doc.get("title"), doc.content, content]).encode()).hexdigest()


def checked_note(note, required):
	if not isinstance(note, str) or len(note) > 500 or (required and not note.strip()):
		frappe.throw("Enter a note of at most 500 characters")
	return note.strip()
