# Copyright (c) 2022, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt
import re
import frappe
from frappe.model.document import Document
from gameplan.gameplan.doctype.team_discussion.search import update_index
from gameplan.mixins.activity import HasActivity
from gameplan.mixins.mentions import HasMentions
from gameplan.mixins.reactions import HasReactions
from gameplan.utils import remove_empty_trailing_paragraphs

class TeamDiscussion(HasActivity, HasMentions, HasReactions, Document):
	on_delete_cascade = ['Team Comment', 'Team Discussion Visit']
	on_delete_set_null = ['Team Notification']
	activities = ['Discussion Closed', 'Discussion Reopened', 'Discussion Title Changed']
	mentions_field = 'content'

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
		self.update_participants_count()

	def after_insert(self):
		self.update_discussions_count(1)

	def on_trash(self):
		self.update_discussions_count(-1)

	def validate(self):
		self.content = remove_empty_trailing_paragraphs(self.content)
		self.title = self.title.strip()

	def on_update(self):
		self.notify_mentions()
		self.notify_reactions()
		self.log_title_update()
		self.update_participants_count()
		self.update_search_index()

	def before_save(self):
		self.update_slug()

	def update_slug(self):
		# remove special characters from title and set as slug
		if not self.title:
			return
		slug = re.sub('[^A-Za-z0-9\s-]+', '', self.title.lower())
		slug = slug.split(' ')
		slug = [part for part in slug if part]
		slug = '-'.join(slug)
		slug = re.sub('[-]+', '-', slug)
		self.slug = slug

	def log_title_update(self):
		if self.has_value_changed('title') and self.get_doc_before_save():
			self.log_activity('Discussion Title Changed', data={
				'old_title': self.get_doc_before_save().title,
				'new_title': self.title
			})

	def update_search_index(self):
		if self.has_value_changed('title') or self.has_value_changed('content'):
			update_index(self)

	def update_participants_count(self):
		participants = frappe.db.get_all('Team Comment',
			filters={
				'reference_doctype': self.doctype,
				'reference_name': self.name
			},
			pluck='owner'
		)
		participants.append(self.owner)
		self.participants_count = len(list(set(participants)))

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
