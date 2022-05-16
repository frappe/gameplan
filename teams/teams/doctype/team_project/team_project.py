# Copyright (c) 2022, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe, requests
from frappe.model.document import Document
from teams.gemoji import get_random_gemoji
from teams.mixins.manage_members import ManageMembersMixin
from bs4 import BeautifulSoup
from urllib.parse import urljoin


class TeamProject(ManageMembersMixin, Document):
	def as_dict(self, *args, **kwargs) -> dict:
		d = super().as_dict(*args, **kwargs)
		for member in d.members:
			if member.user:
				full_name, user_image = frappe.db.get_value(
					"User", member.user, ["full_name", "user_image"]
				)
				member.full_name = full_name
				member.user_image = user_image
		return d

	def before_insert(self):
		if not self.icon:
			self.icon = get_random_gemoji().emoji

		if not self.readme:
			self.readme = f"""
			<h3>Welcome to the {self.title} page!</h3>
			<p>You can add a brief introduction about this project, links, resources, and other important information here.</p>

			<h3>What this project is about</h3>
			<p>This project is about...</p>

			<h3>How we'll collaborate</h3>
			<p>We'll do a weekly standup every Thursday...</p>
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

	def on_trash(self):
		linked_doctypes = ["Team Task", "Team Project Status Update"]
		for doctype in linked_doctypes:
			for d in frappe.db.get_all(doctype, {"project": self.name}):
				frappe.delete_doc(doctype, d.name)

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
	def add_attachment(self, url, title=None):
		if not url.startswith("http"):
			url = "https://" + url

		meta = get_meta_tags(url)
		self.append(
			"attachments", {"url": url, "title": title or meta["title"], "image": meta["image"]}
		)
		self.save()

	@frappe.whitelist()
	def create_section(self, title):
		self.append("sections", {"title": title, "type": "Draft"})
		self.save()

	@frappe.whitelist()
	def delete_section(self, section):
		section_to_remove = None
		for s in self.sections:
			if s.name == section:
				section_to_remove = s
				break

		task_count = frappe.db.count(
			"Team Task", {"project": self.name, "project_section": section_to_remove.name}
		)
		if task_count > 0:
			if task_count == 1:
				frappe.throw(
					f"Section {section_to_remove.title} cannot be deleted because it has 1 task"
				)
			else:
				frappe.throw(
					f"Section {section_to_remove.title} cannot be deleted because it"
					f" has {task_count} tasks"
				)

		self.remove(section_to_remove)

		# recompute idx
		for i, section in enumerate(self.sections):
			section.idx = i + 1

		self.save()

	@frappe.whitelist()
	def update_tasks_order(self, tasks):
		tasks = frappe.parse_json(tasks)
		for task in tasks:
			task = frappe._dict(task)
			frappe.db.set_value(
				"Team Task", task.name, {"idx": task.idx, "project_section": task.project_section}
			)


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
