# Copyright (c) 2022, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from gameplan.extends.client import check_permissions
from gameplan.gameplan.doctype.gp_notification.gp_notification import GPNotification
from gameplan.mixins.activity import HasActivity
from gameplan.mixins.archivable import check_if_space_is_archived
from gameplan.mixins.mentions import HasMentions
from gameplan.permissions import content_has_permission, task_query_conditions


class GPTask(HasMentions, HasActivity, Document):
	on_delete_cascade = ["GP Comment", "GP Activity"]
	on_delete_set_null = ["GP Notification"]
	activities = ["Task Value Changed"]
	mentions_field = "description"

	def before_insert(self):
		if not self.status:
			self.status = "Backlog"

	def validate(self):
		check_if_space_is_archived(self, action="modify", content_type="tasks")

	def after_insert(self):
		self.update_tasks_count()

	def on_update(self):
		self.notify_mentions()
		self.log_value_updates()

	def log_value_updates(self):
		fields = ["title", "description", "status", "priority", "assigned_to", "due_date", "project"]
		for field in fields:
			prev_doc = self.get_doc_before_save()
			if prev_doc and str(self.get(field)) != str(prev_doc.get(field)):
				self.log_activity(
					"Task Value Changed",
					data={
						"field": field,
						"field_label": self.meta.get_label(field),
						"old_value": prev_doc.get(field),
						"new_value": self.get(field),
					},
				)

	def update_comments_count(self):
		comments_count = frappe.db.count(
			"GP Comment", {"reference_doctype": "GP Task", "reference_name": self.name}
		)
		self.db_set("comments_count", comments_count)

	def on_trash(self):
		if not self.flags.from_gameplan_delete_cascade:
			check_if_space_is_archived(self, action="delete", content_type="tasks")
		self.update_tasks_count()

	def update_tasks_count(self):
		if not self.project:
			return
		frappe.get_doc("GP Project", self.project).update_tasks_count()

	@frappe.whitelist(methods=["POST"])
	def track_visit(self):
		GPNotification.clear_notifications(task=self.name)


@frappe.whitelist()
def get_list(
	fields: str = None,
	filters: str = None,
	order_by: str = None,
	start: int = 0,
	limit: int = 20,
	group_by: str = None,
	parent: str = None,
	debug=False,
):
	doctype = "GP Task"
	check_permissions(doctype, parent)
	fields = frappe.parse_json(fields) if fields else None
	filters = frappe.parse_json(filters) if filters else None
	assigned_or_owner = filters.pop("assigned_or_owner", None) if filters else None
	limit = int(limit)

	query = frappe.qb.get_query(
		doctype,
		fields=fields,
		filters=filters,
		order_by=order_by,
		offset=start,
		limit=limit + 1,
		group_by=group_by,
	)
	if assigned_or_owner:
		Task = frappe.qb.DocType(doctype)
		query = query.where((Task.assigned_to == assigned_or_owner) | (Task.owner == assigned_or_owner))

	data = query.run(as_dict=True, debug=debug)
	frappe.response["has_next_page"] = len(data) > limit
	return data[:limit]


def get_permission_query_conditions(user):
	return task_query_conditions(user)


def has_permission(doc, ptype="read", user=None):
	return content_has_permission(doc, ptype, user)
