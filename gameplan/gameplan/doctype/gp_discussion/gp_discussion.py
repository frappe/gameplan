# Copyright (c) 2022, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt
import re
import frappe
from frappe.model.document import Document
from gameplan.search import GameplanSearch
from gameplan.gameplan.doctype.gp_notification.gp_notification import GPNotification
from gameplan.mixins.activity import HasActivity
from gameplan.mixins.mentions import HasMentions
from gameplan.mixins.reactions import HasReactions
from gameplan.utils import remove_empty_trailing_paragraphs, url_safe_slug

class GPDiscussion(HasActivity, HasMentions, HasReactions, Document):
	on_delete_cascade = ['GP Comment', 'GP Discussion Visit', 'GP Activity']
	on_delete_set_null = ['GP Notification']
	activities = ['Discussion Closed', 'Discussion Reopened', 'Discussion Title Changed', 'Discussion Pinned', 'Discussion Unpinned']
	mentions_field = 'content'

	def as_dict(self, *args, **kwargs):
		d = super(GPDiscussion, self).as_dict(*args, **kwargs)
		last_visit = frappe.db.get_value('GP Discussion Visit', {'discussion': self.name, 'user': frappe.session.user}, 'last_visit')
		result = frappe.db.get_all(
			'GP Comment',
			filters={'reference_doctype': self.doctype, 'reference_name': self.name, 'creation': ('>', last_visit)},
			order_by='creation asc',
			limit=1,
			pluck='name'
		)
		d.last_unread_comment = result[0] if result else None
		polls = frappe.db.get_all(
			'GP Poll',
			filters={'discussion': self.name, 'creation': ('>', last_visit)},
			order_by='creation asc',
			limit=1,
			pluck='name'
		)
		d.last_unread_poll = polls[0] if polls else None
		return d

	def before_insert(self):
		self.last_post_at = frappe.utils.now()
		self.update_participants_count()

	def after_insert(self):
		self.update_discussions_count(1)

	def on_trash(self):
		self.update_discussions_count(-1)

	def validate(self):
		self.content = remove_empty_trailing_paragraphs(self.content)
		self.title = self.title.strip()
		self.de_duplicate_reactions()

	def on_update(self):
		self.notify_mentions()
		self.notify_reactions()
		self.log_title_update()
		self.update_participants_count()
		self.update_search_index()

	def before_save(self):
		self.update_slug()

	def update_slug(self):
		self.slug = url_safe_slug(self.title)

	def log_title_update(self):
		if self.has_value_changed('title') and self.get_doc_before_save():
			self.log_activity('Discussion Title Changed', data={
				'old_title': self.get_doc_before_save().title,
				'new_title': self.title
			})

	def update_search_index(self):
		if self.has_value_changed('title') or self.has_value_changed('content'):
			search = GameplanSearch()
			search.index_doc(self)

	def update_participants_count(self):
		participants = frappe.db.get_all('GP Comment',
			filters={
				'reference_doctype': self.doctype,
				'reference_name': self.name
			},
			pluck='owner'
		)
		participants += frappe.db.get_all("GP Poll",
			filters={"discussion": self.name},
			pluck="owner"
		)
		participants.append(self.owner)
		self.participants_count = len(list(set(participants)))

	@frappe.whitelist()
	def track_visit(self):
		if frappe.flags.read_only:
			return

		values = {"user": frappe.session.user, "discussion": self.name}
		existing = frappe.db.get_value("GP Discussion Visit", values)
		if existing:
			visit = frappe.get_doc("GP Discussion Visit", existing)
			visit.last_visit = frappe.utils.now()
			visit.save(ignore_permissions=True)
		else:
			visit = frappe.get_doc(doctype="GP Discussion Visit")
			visit.update(values)
			visit.last_visit = frappe.utils.now()
			visit.insert(ignore_permissions=True)

		# also mark notifications as read
		GPNotification.clear_notifications(discussion=self.name)


	@frappe.whitelist()
	def move_to_project(self, project):
		if not project or project == self.project:
			return

		self.project = project
		self.team = frappe.db.get_value("GP Project", project, "team")
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

	@frappe.whitelist()
	def pin_discussion(self):
		if self.pinned_at:
			return
		self.pinned_at = frappe.utils.now()
		self.pinned_by = frappe.session.user
		self.log_activity('Discussion Pinned')
		self.save()

	@frappe.whitelist()
	def unpin_discussion(self):
		if not self.pinned_at:
			return
		self.pinned_at = None
		self.pinned_by = None
		self.log_activity('Discussion Unpinned')
		self.save()

	def update_discussions_count(self, delta=1):
		project = frappe.get_doc("GP Project", self.project)
		project.discussions_count = project.discussions_count + delta
		project.save(ignore_permissions=True)
