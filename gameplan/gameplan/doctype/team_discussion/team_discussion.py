# Copyright (c) 2022, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from gameplan.mixins.activity import HasActivity
from gameplan.utils import extract_mentions
from frappe.utils import get_fullname

class TeamDiscussion(HasActivity, Document):
	on_delete_cascade = ['Team Comment', 'Team Discussion Visit']
	on_delete_set_null = ['Team Notification']
	activities = ['Discussion Closed', 'Discussion Reopened']

	def as_dict(self, *args, **kwargs):
		d = super(TeamDiscussion, self).as_dict(*args, **kwargs)
		last_visit = frappe.db.get_value('Team Discussion Visit', {'discussion': self.name, 'user': frappe.session.user}, 'last_visit')
		result = frappe.db.get_all(
			'Team Comment',
			filters={'reference_doctype': self.doctype, 'reference_name': self.name, 'creation': ('>', last_visit)},
			order_by='creation asc',
			limit=1,
			pluck='name'
		)
		d.last_unread_comment = result[0] if result else None
		return d

	def before_insert(self):
		self.last_post_at = frappe.utils.now()

	def after_insert(self):
		self.update_discussions_count(1)

	def on_trash(self):
		self.update_discussions_count(-1)

	def on_update(self):
		mentions = extract_mentions(self.content)
		for mention in mentions:
			values = frappe._dict(
				from_user=self.owner,
				to_user=mention.email,
				discussion=self.name,
			)
			if frappe.db.exists("Team Notification", values):
				continue
			notification = frappe.get_doc(doctype='Team Notification')
			notification.message = f'{get_fullname(self.owner)} mentioned you in a post',
			notification.update(values)
			notification.insert(ignore_permissions=True)

	@frappe.whitelist()
	def track_visit(self):
		if frappe.flags.read_only:
			return

		values = {"user": frappe.session.user, "discussion": self.name}
		existing = frappe.db.get_value("Team Discussion Visit", values)
		if existing:
			visit = frappe.get_doc("Team Discussion Visit", existing)
			visit.last_visit = frappe.utils.now()
			visit.save(ignore_permissions=True)
		else:
			visit = frappe.get_doc(doctype="Team Discussion Visit")
			visit.update(values)
			visit.last_visit = frappe.utils.now()
			visit.insert(ignore_permissions=True)

	@frappe.whitelist()
	def move_to_project(self, project):
		if not project or project == self.project:
			return

		self.project = project
		self.team = frappe.db.get_value("Team Project", project, "team")
		self.save()

	@frappe.whitelist()
	def close_discussion(self):
		if self.closed_at:
			return
		self.closed_at = frappe.utils.now()
		self.closed_by = frappe.session.user
		self.log_activity('Discussion Closed')
		self.save()

	@frappe.whitelist()
	def reopen_discussion(self):
		if not self.closed_at:
			return
		self.closed_at = None
		self.closed_by = None
		self.log_activity('Discussion Reopened')
		self.save()

	def update_discussions_count(self, delta=1):
		project = frappe.get_doc("Team Project", self.project)
		project.discussions_count = project.discussions_count + delta
		project.save(ignore_permissions=True)


def make_full_text_search_index():
	frappe.db.sql('ALTER TABLE `tabTeam Discussion` ADD FULLTEXT (title, content, owner)')

