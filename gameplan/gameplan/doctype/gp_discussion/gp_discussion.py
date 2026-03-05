# Copyright (c) 2022, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.types import DF
from frappe.utils import cstr

import gameplan
from gameplan.gameplan.doctype.gp_notification.gp_notification import GPNotification
from gameplan.gameplan.doctype.gp_unread_record.gp_unread_record import GPUnreadRecord
from gameplan.mixins.activity import HasActivity
from gameplan.mixins.mentions import HasMentions
from gameplan.mixins.reactions import HasReactions
from gameplan.mixins.tags import HasTags
from gameplan.utils import get_document_revisions, remove_empty_trailing_paragraphs, url_safe_slug

PinScope = DF.Literal["Global", "Space"]


class GPDiscussion(HasActivity, HasMentions, HasReactions, HasTags, Document):
	# Class Configuration
	on_delete_cascade = ["GP Comment", "GP Discussion Visit", "GP Activity", "GP Poll"]
	on_delete_set_null = ["GP Notification"]
	activities = [
		"Discussion Closed",
		"Discussion Reopened",
		"Discussion Title Changed",
		"Discussion Pinned",
		"Discussion Unpinned",
		"Discussion Moved",
	]
	mentions_field = "content"
	tags_field = "content"

	# Lifecycle Methods
	def as_dict(self, *args, **kwargs):
		d = super(__class__, self).as_dict(*args, **kwargs)
		last_visit = frappe.db.get_value(
			"GP Discussion Visit", {"discussion": self.name, "user": frappe.session.user}, "last_visit"
		)
		if last_visit:
			result = frappe.db.get_all(
				"GP Comment",
				filters={
					"reference_doctype": self.doctype,
					"reference_name": self.name,
					"creation": (">", last_visit),
				},
				order_by="creation asc",
				limit=1,
				pluck="name",
			)
			d.last_unread_comment = cstr(result[0]) if result else None
		else:
			d.last_unread_comment = "first_post"

		polls = frappe.db.get_all(
			"GP Poll",
			filters={"discussion": self.name, "creation": (">", last_visit)},
			order_by="creation asc",
			limit=1,
			pluck="name",
		)
		d.last_unread_poll = polls[0] if polls else None
		d.is_bookmarked = self.is_bookmarked()
		d.views = frappe.db.count("GP Discussion Visit", {"discussion": self.name})
		return d

	def before_insert(self):
		self.check_if_project_is_archived()
		self.last_post_at = frappe.utils.now()
		self.update_participants_count()

	def after_insert(self):
		self.update_discussions_count()
		GPUnreadRecord.create_unread_records_for_discussion(self)

	def on_trash(self):
		self.remove_bookmark()
		self.update_discussions_count()
		GPUnreadRecord.delete_unread_records_for_discussion(self.name)

	def validate(self):
		self.sanitize_content()
		self.title = self.title.strip()
		self.de_duplicate_reactions()

	def on_update(self):
		self.notify_mentions()
		self.notify_reactions()
		self.log_title_update()
		self.update_participants_count()

	def before_save(self):
		self.update_slug()
		self.update_tags()
		self.sanitize_content()

	def sanitize_content(self):
		from gameplan.utils.sanitizer import sanitize_content

		self.content = remove_empty_trailing_paragraphs(self.content)
		self.content = sanitize_content(self.content)

	# Whitelisted Methods
	@frappe.whitelist()
	def track_visit(self):
		if frappe.flags.read_only:
			return

		# New system: Mark as read in GP Unread Record
		GPUnreadRecord.mark_discussion_as_read_for_user(self.name, frappe.session.user)

		# Keep old system for analytics/backward compatibility
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
	def get_revisions(self, fieldname: str = "content"):
		return get_document_revisions(self.doctype, self.name, fieldname)

	@frappe.whitelist()
	def move_to_project(self, project: str):
		return move_discussion(self, project)

	@frappe.whitelist()
	def close_discussion(self):
		if self.closed_at:
			return
		self.closed_at = frappe.utils.now()
		self.closed_by = frappe.session.user
		self.log_activity("Discussion Closed")
		self.save()

	@frappe.whitelist()
	def reopen_discussion(self):
		if not self.closed_at:
			return
		self.closed_at = None
		self.closed_by = None
		self.log_activity("Discussion Reopened")
		self.save()

	@frappe.whitelist()
	def pin_discussion(self, pin_scope: PinScope = "Global"):
		if self.pinned_at:
			return
		self.pinned_at = frappe.utils.now()
		self.pinned_by = frappe.session.user
		self.pin_scope = pin_scope
		self.log_activity("Discussion Pinned")
		self.save()

	@frappe.whitelist()
	def unpin_discussion(self):
		if not self.pinned_at:
			return
		self.pinned_at = None
		self.pinned_by = None
		self.pin_scope = None
		self.log_activity("Discussion Unpinned")
		self.save()

	@frappe.whitelist()
	def add_bookmark(self):
		if self.is_bookmarked():
			return
		frappe.new_doc("GP Bookmark", discussion=self.name, user=frappe.session.user).insert()

	@frappe.whitelist()
	def remove_bookmark(self):
		bookmark = frappe.db.get_value(
			"GP Bookmark", {"discussion": self.name, "user": frappe.session.user}, "name"
		)
		if not bookmark:
			return
		frappe.get_doc("GP Bookmark", bookmark).delete()

	# Utility Methods
	def is_bookmarked(self):
		return bool(frappe.db.exists("GP Bookmark", {"discussion": self.name, "user": frappe.session.user}))

	def update_slug(self):
		self.slug = url_safe_slug(self.title)

	def update_participants_count(self):
		participants = frappe.db.get_all(
			"GP Comment",
			filters={"reference_doctype": self.doctype, "reference_name": self.name},
			pluck="owner",
		)
		participants += frappe.db.get_all("GP Poll", filters={"discussion": self.name}, pluck="owner")
		participants.append(self.owner)
		self.participants_count = len(list(set(participants)))

	def update_last_post(self):
		def get_last_post(doctype, filters):
			return frappe.db.get_value(
				doctype,
				filters,
				["name", "creation", "owner"],
				order_by="creation desc",
				as_dict=True,
			)

		def update_last_post_fields(post_type, post_data):
			self.last_post_type = post_type
			self.last_post = post_data.name
			self.last_post_at = post_data.creation
			self.last_post_by = post_data.owner

		last_comment = get_last_post(
			"GP Comment", {"reference_doctype": self.doctype, "reference_name": self.name}
		)
		last_poll = get_last_post("GP Poll", {"discussion": self.name})

		if last_comment and last_poll:
			latest = last_comment if last_comment.creation > last_poll.creation else last_poll
			update_last_post_fields("GP Comment" if latest == last_comment else "GP Poll", latest)
		elif last_comment:
			update_last_post_fields("GP Comment", last_comment)
		elif last_poll:
			update_last_post_fields("GP Poll", last_poll)

	def update_post_count(self):
		comments_count = frappe.db.count(
			"GP Comment", {"reference_doctype": self.doctype, "reference_name": self.name}
		)
		polls_count = frappe.db.count("GP Poll", {"discussion": self.name})
		self.comments_count = comments_count + polls_count

	def update_discussions_count(self):
		frappe.get_doc("GP Project", self.project).update_discussions_count()

	def log_title_update(self):
		if self.has_value_changed("title") and self.get_doc_before_save():
			self.log_activity(
				"Discussion Title Changed",
				data={"old_title": self.get_doc_before_save().title, "new_title": self.title},
			)

	def check_if_project_is_archived(self):
		project_name, archived_at = frappe.db.get_value("GP Project", self.project, ["name", "archived_at"])
		if archived_at:
			frappe.throw(f"Project {project_name} is archived. Cannot create discussions.")


def on_doctype_update():
	frappe.db.add_index("GP Discussion", ["project", "last_post_at"])


def move_discussion(discussion, project):
	if not project or project == discussion.project:
		return

	old_project = discussion.project
	discussion.project = project
	discussion.team = frappe.db.get_value("GP Project", project, "team")
	discussion.save()
	# update the discussion counts
	discussion.update_discussions_count()
	frappe.get_doc("GP Project", old_project).update_discussions_count()
	discussion.log_activity("Discussion Moved", data={"old_project": old_project, "new_project": project})
	return discussion


@frappe.whitelist(methods=["POST"])
def move_discussions(discussions: list[dict]):
	if not discussions:
		return {"moved": [], "failed": [], "total": 0, "success_count": 0, "failure_count": 0}

	moved = []
	failed = []

	for item in discussions:
		if not isinstance(item, dict):
			failed.append(
				{
					"name": None,
					"error": "Discussion entry must be a dictionary with name and project fields",
				}
			)
			continue
		name = item.get("name")
		project = item.get("project")
		if not name or not project:
			missing = "name" if not name else "project"
			failed.append({"name": name, "error": f"Missing required field: {missing}"})
			continue
		try:
			doc = frappe.get_doc("GP Discussion", name)
			if not doc.has_permission("write"):
				raise frappe.PermissionError(f"You do not have write permission for discussion {name}")
			move_discussion(doc, project)
			moved.append(name)
		except Exception as exc:
			failed.append({"name": name, "error": str(exc)})

	return {
		"moved": moved,
		"failed": failed,
		"total": len(discussions),
		"success_count": len(moved),
		"failure_count": len(failed),
	}


def get_permission_query_conditions(user):
	if not user:
		user = frappe.session.user

	if not gameplan.is_guest(user):
		return None

	escaped_user = frappe.db.escape(user)
	return f"""`tabGP Discussion`.project in (
		select `tabGP Guest Access`.project
		from `tabGP Guest Access`
		where `tabGP Guest Access`.user = {escaped_user}
	)"""


def has_permission(doc, ptype="read", user=None):
	user = user or frappe.session.user

	if not gameplan.is_guest(user):
		return True

	if not doc.project:
		return False

	return bool(frappe.db.exists("GP Guest Access", {"user": user, "project": doc.project}))
