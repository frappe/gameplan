# Copyright (c) 2022, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe, requests
from frappe.model.document import Document
from gameplan.gemoji import get_random_gemoji
from gameplan.mixins.archivable import Archivable
from gameplan.mixins.manage_members import ManageMembersMixin
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from pypika.terms import ExistsCriterion


class TeamProject(ManageMembersMixin, Archivable, Document):
	on_delete_cascade = ["Team Task", "Team Discussion"]
	on_delete_set_null = ["Team Notification"]

	@staticmethod
	def get_list_query(query):
		Project = frappe.qb.DocType('Team Project')
		Member = frappe.qb.DocType('Team Member')
		member_exists = (
			frappe.qb.from_(Member)
				.select(Member.name)
				.where(Member.parenttype == 'Team')
				.where(Member.parent == Project.team)
				.where(Member.user == frappe.session.user)
		)
		query = query.where(
			(Project.is_private == 0) | ((Project.is_private == 1) & ExistsCriterion(member_exists))
		)
		if 'Gameplan Guest' in frappe.get_roles():
			GuestAccess = frappe.qb.DocType('GP Guest Access')
			project_list = GuestAccess.select(GuestAccess.project).where(GuestAccess.user == frappe.session.user)
			query = query.where(Project.name.isin(project_list))
		return query

	def as_dict(self, *args, **kwargs) -> dict:
		d = super().as_dict(*args, **kwargs)
		# summary
		total_tasks = frappe.db.count("Team Task", {"project": self.name})
		completed_tasks = frappe.db.count(
			"Team Task", {"project": self.name, "is_completed": 1}
		)
		pending_tasks = total_tasks - completed_tasks
		overdue_tasks = frappe.db.count(
			"Team Task",
			{"project": self.name, "is_completed": 0, "due_date": ("<", frappe.utils.today())},
		)
		d.summary = {
			"total_tasks": total_tasks,
			"completed_tasks": completed_tasks,
			"pending_tasks": pending_tasks,
			"overdue_tasks": overdue_tasks,
		}
		return d

	def before_insert(self):
		if not self.icon:
			self.icon = get_random_gemoji().emoji

		if not self.readme:
			self.readme = f"""
			<h3>Welcome to the {self.title} page!</h3>
			<p>You can add a brief introduction about this project, links, resources, and other important information here.</p>
			<p></p>
			<p></p>
		"""

		self.append(
			"members",
			{
				"user": frappe.session.user,
				"email": frappe.session.user,
				"role": "Project Owner",
				"status": "Accepted",
			},
		)

	def update_progress(self):
		result = frappe.db.get_all(
			"Team Task",
			filters={"project": self.name},
			fields=["sum(is_completed) as completed", "count(name) as total"],
		)[0]
		if result.total > 0:
			self.progress = (result.completed or 0) * 100 / result.total
			self.save()
			self.reload()

	def delete_group(self, group):
		tasks = frappe.db.count("Team Task", {"project": self.name, "status": group})
		if tasks > 0:
			frappe.throw(f"Group {group} cannot be deleted because it has {tasks} tasks")

		for state in self.task_states:
			if state.status == group:
				self.remove(state)
				self.save()
				break

	def get_activities(self):
		activities = []
		activities.append(
			{
				"type": "info",
				"title": "Project created",
				"date": self.creation,
				"user": self.owner,
			}
		)
		status_updates = frappe.db.get_all(
			"Team Project Status Update",
			{"project": self.name},
			["creation", "owner", "content", "status"],
			order_by="creation desc",
		)
		for status_update in status_updates:
			activities.append(
				{
					"type": "content",
					"title": "Status Update",
					"content": status_update.content,
					"status": status_update.status,
					"date": frappe.utils.get_datetime(status_update.creation),
					"user": status_update.owner,
				}
			)
		activities.sort(key=lambda x: x["date"], reverse=True)
		return activities

	@frappe.whitelist()
	def move_to_team(self, team):
		if not team or self.team == team:
			return
		self.team = team
		self.save()
		for doctype in ['Team Task', 'Team Discussion']:
			for name in frappe.db.get_all(doctype, {"project": self.name}, pluck="name"):
				doc = frappe.get_doc(doctype, name)
				doc.team = self.team
				doc.save()

	@frappe.whitelist()
	def invite_guest(self, email):
		frappe.utils.validate_email_address(email, True)

		user_roles = frappe.get_roles(email)
		if frappe.db.exists('User', email) and 'Gameplan Member' in user_roles or 'Gameplan Admin' in user_roles:
			frappe.throw('This user is already a Gameplan member')

		if not frappe.db.exists("GP Guest Access", {'project': self.name, 'user': email}):
			invitation = frappe.get_doc(
				doctype='GP Invitation',
				email=email,
				type='Project Guest Access',
				project=self.name,
			)
			invitation.insert(ignore_permissions=True)

	@frappe.whitelist()
	def remove_guest(self, email):
		name = frappe.db.get_value('GP Guest Access', {'project': self.name, 'user': email})
		if name:
			frappe.delete_doc('GP Guest Access', name)


def get_meta_tags(url):
	response = requests.get(url, timeout=2, allow_redirects=True)
	soup = BeautifulSoup(response.text, "html.parser")
	title = soup.find("title").text.strip()

	image = None
	favicon = soup.find("link", rel="icon")
	if favicon:
		image = favicon["href"]

	if image and image.startswith("/"):
		image = urljoin(url, image)

	return {"title": title, "image": image}
