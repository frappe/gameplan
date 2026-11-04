from html import unescape

import frappe
from frappe.query_builder.functions import Count
from frappe.utils import strip_html

from gameplan.community_bans import can_moderate_community
from gameplan.permissions import accessible_project_query
from gameplan.reporting import version


@frappe.whitelist(methods=["POST"])
def preview(community: str, reviews: list):
	if not can_moderate_community(community):
		frappe.throw("Only Community moderators can review reports", frappe.PermissionError)
	if (
		not isinstance(reviews, list)
		or not 1 <= len(reviews) <= 50
		or any(not isinstance(name, str) or not name for name in reviews)
		or len(set(reviews)) != len(reviews)
	):
		frappe.throw("Select between 1 and 50 different reviews")

	items = [{"review": name} for name in reviews]
	Review = frappe.qb.DocType("GP Review")
	reviews_by_name = {
		row.name: row
		for row in (
			frappe.qb.from_(Review)
			.select(Review.name, Review.reference_doctype, Review.reference_name, Review.status)
			.where(Review.name.isin(reviews))
			.run(as_dict=True)
		)
	}
	Project = frappe.qb.DocType("GP Project")
	projects = accessible_project_query().where(Project.team == community)
	discussion_names = {
		row.reference_name for row in reviews_by_name.values() if row.reference_doctype == "GP Discussion"
	}
	comment_names = {
		row.reference_name for row in reviews_by_name.values() if row.reference_doctype == "GP Comment"
	}
	discussions = {}
	comments = {}
	if discussion_names:
		Discussion = frappe.qb.DocType("GP Discussion")
		discussions = {
			str(row.name): frappe._dict(row, doctype="GP Discussion")
			for row in (
				frappe.qb.from_(Discussion)
				.select(
					Discussion.name,
					Discussion.project,
					Discussion.owner,
					Discussion.title,
					Discussion.content,
					Discussion.hidden_at,
					Discussion.spam_removed_at,
				)
				.where(Discussion.name.isin(discussion_names) & Discussion.project.isin(projects))
				.run(as_dict=True)
			)
		}
	if comment_names:
		Comment, Discussion = frappe.qb.DocType("GP Comment"), frappe.qb.DocType("GP Discussion")
		comments = {
			str(row.name): frappe._dict(row, doctype="GP Comment")
			for row in (
				frappe.qb.from_(Comment)
				.join(Discussion)
				.on(
					(Comment.reference_doctype == "GP Discussion")
					& (Comment.reference_name == Discussion.name)
				)
				.select(
					Comment.name,
					Comment.owner,
					Comment.content,
					Comment.reference_doctype,
					Comment.reference_name,
					Comment.hidden_at,
					Comment.spam_removed_at,
					Comment.deleted_at,
					Discussion.project,
					Discussion.hidden_at.as_("discussion_hidden_at"),
					Discussion.spam_removed_at.as_("discussion_spam_removed_at"),
				)
				.where(Comment.name.isin(comment_names) & Discussion.project.isin(projects))
				.run(as_dict=True)
			)
		}
	comment_poll_rows = {}
	if comments:
		Poll = frappe.qb.DocType("GP Poll")
		polls = (
			frappe.qb.from_(Poll)
			.select(Poll.name, Poll.comment, Poll.title, Poll.anonymous, Poll.multiple_answers)
			.where(Poll.comment.isin(list(comments)))
			.run(as_dict=True)
		)
		if polls:
			Option = frappe.qb.DocType("GP Poll Option")
			options = (
				frappe.qb.from_(Option)
				.select(Option.parent, Option.idx, Option.title)
				.where(
					(Option.parenttype == "GP Poll")
					& (Option.parentfield == "options")
					& Option.parent.isin([poll.name for poll in polls])
				)
				.orderby(Option.idx)
				.run(as_dict=True)
			)
			by_poll = {}
			for option in options:
				by_poll.setdefault(str(option.parent), []).append(option)
			for poll in polls:
				poll.options = by_poll.get(str(poll.name), [])
				comment_poll_rows.setdefault(str(poll.comment), []).append(poll)

	for item in items:
		review = reviews_by_name.get(item["review"])
		doc = None
		if review:
			if review.reference_doctype == "GP Discussion":
				doc = discussions.get(review.reference_name)
			elif review.reference_doctype == "GP Comment":
				doc = comments.get(review.reference_name)
		if not doc:
			item["error"] = "This review is no longer available."
			continue
		if (
			doc.hidden_at
			or doc.spam_removed_at
			or doc.get("deleted_at")
			or doc.get("discussion_hidden_at")
			or doc.get("discussion_spam_removed_at")
		):
			item["error"] = "This content was removed. Review it individually."
			continue
		if review.status != "Pending":
			item["error"] = "This review was already resolved."
			continue
		polls = comment_poll_rows.get(str(doc.name), [])
		content = [unescape(strip_html(doc.content or ""))]
		for poll in polls:
			content.extend([poll.title, *(option.title for option in poll.options)])
		item.update(
			reference_doctype=doc.doctype,
			reference_name=str(doc.name),
			title=doc.get("title") or f"Reply #{doc.name}",
			excerpt=" ".join(" ".join(content).split())[:300],
			version=version(doc, polls),
			reasons=[],
		)

	ready = {item["review"]: item for item in items if "version" in item}
	if ready:
		Report = frappe.qb.DocType("GP Report")
		reasons = (
			frappe.qb.from_(Report)
			.select(Report.review, Report.reason, Count(Report.name).as_("count"))
			.where(Report.review.isin(list(ready)))
			.groupby(Report.review, Report.reason)
			.orderby(Report.reason)
		).run(as_dict=True)
		for reason in reasons:
			ready[reason.review]["reasons"].append({"reason": reason.reason, "count": reason.count})
	return items
