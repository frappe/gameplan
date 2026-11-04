from html import unescape

import frappe
from frappe.query_builder.functions import Count
from frappe.utils import strip_html

from gameplan.community_bans import can_moderate_community
from gameplan.reporting import check_visible, review_polls, review_target, version


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

	items = []
	for name in reviews:
		item = {"review": name}
		try:
			review, doc = review_target(community, name, for_update=False)
			if review.status != "Pending":
				frappe.throw("This review was already resolved.", frappe.TimestampMismatchError)
			check_visible(doc)
			polls = review_polls(doc)
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
		except (frappe.PermissionError, frappe.DoesNotExistError):
			frappe.clear_last_message()
			item["error"] = "This review is no longer available."
		except frappe.TimestampMismatchError as error:
			frappe.clear_last_message()
			item["error"] = str(error)
		items.append(item)

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
