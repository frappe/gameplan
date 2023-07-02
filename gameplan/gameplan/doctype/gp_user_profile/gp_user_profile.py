# Copyright (c) 2022, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
import gameplan
from frappe.model.document import Document
from frappe.model.naming import append_number_if_name_exists
from frappe.website.utils import cleanup_page_name
from gameplan.extends.client import check_permissions
from frappe.query_builder.functions import Count
from rq.job import JobStatus
from time import sleep


class GPUserProfile(Document):
	def autoname(self):
		self.name = self.generate_name()

	def generate_name(self):
		full_name = frappe.db.get_value("User", self.user, "full_name")
		return append_number_if_name_exists(self.doctype, cleanup_page_name(full_name))

	@frappe.whitelist()
	def set_image(self, image):
		self.image = image
		self.is_image_background_removed = False
		self.image_background_color = None
		self.original_image = None
		self.save()
		gameplan.refetch_resource("Users")

	@frappe.whitelist()
	def remove_image_background(self, default_color=None):
		if not self.image:
			frappe.throw("Profile image not found")

		job_id = f"remove-img-bg-{self.name}"
		job = frappe.enqueue(
			remove_imgbg_in_background, profile_name=self.name, default_color=default_color, at_front=True, job_id=job_id
		)
		while True:
			status = job.get_status()
			if status in (JobStatus.QUEUED, JobStatus.STARTED, JobStatus.SCHEDULED):
				print("Waiting for job to complete:", job_id, status)
				sleep(1)
			elif status in (JobStatus.FINISHED, JobStatus.FAILED, JobStatus.CANCELED):
				print("Job status:", job_id, status)
				self.reload()
				break

	@frappe.whitelist()
	def revert_image_background(self):
		if self.original_image:
			self.image = self.original_image
			self.original_image = None
			self.is_image_background_removed = False
			self.image_background_color = None
			self.save()
			gameplan.refetch_resource("Users")


def create_user_profile(doc, method=None):
	if not frappe.db.exists("GP User Profile", {"user": doc.name}):
		frappe.get_doc(doctype="GP User Profile", user=doc.name).insert(ignore_permissions=True)
		frappe.db.commit()


def delete_user_profile(doc, method=None):
	exists = frappe.db.exists("GP User Profile", {"user": doc.name})
	if exists:
		return frappe.get_doc("GP User Profile", {"user": doc.name}).delete()


def on_user_update(doc, method=None):
	create_user_profile(doc)
	if any(doc.has_value_changed(field) for field in ["full_name", "enabled"]):
		profile = frappe.get_doc("GP User Profile", {"user": doc.name})
		profile.enabled = doc.enabled
		profile.full_name = doc.full_name
		profile.save(ignore_permissions=True)


@frappe.whitelist()
def get_list(
	fields=None, filters: dict | None = None, order_by=None, start=0, limit=20, group_by=None, parent=None, debug=False
):
	doctype = "GP User Profile"
	check_permissions(doctype, parent)
	query = frappe.qb.get_query(
		table=doctype,
		fields=fields,
		filters=filters,
		order_by=order_by,
		offset=start,
		limit=limit,
		group_by=group_by,
	)
	data = query.run(as_dict=True, debug=debug)
	users = [d.user for d in data]

	Discussion = frappe.qb.DocType("GP Discussion")
	discussions_count = (
		frappe.qb.from_(Discussion)
		.select(Count(Discussion.name).as_("count"), Discussion.owner)
		.where(Discussion.owner.isin(users))
		.groupby(Discussion.owner)
	).run(as_dict=True)
	discussions_by_user = {d.owner: d.count for d in discussions_count}

	Comment = frappe.qb.DocType("GP Comment")
	comments_count = (
		frappe.qb.from_(Comment)
		.select(Count(Comment.name).as_("count"), Comment.owner)
		.where(Comment.owner.isin(users) & Comment.deleted_at.isnull())
		.groupby(Comment.owner)
	).run(as_dict=True)
	comments_by_user = {d.owner: d.count for d in comments_count}

	for user in data:
		user.discussions_count = discussions_by_user.get(user.user, 0)
		user.comments_count = comments_by_user.get(user.user, 0)

	return data


def remove_imgbg_in_background(profile_name, default_color=None):
	from gameplan.gameplan.doctype.gp_user_profile.profile_photo import remove_background

	profile = frappe.get_doc("GP User Profile", profile_name)
	file = frappe.get_doc("File", {"file_url": profile.image})
	profile.original_image = file.file_url
	image_content = remove_background(file)
	filename, extn = file.get_extension()
	output_filename = f"{filename}_no_bg.png"
	new_file = frappe.get_doc(
		doctype="File",
		file_name=output_filename,
		content=image_content,
		is_private=0,
		attached_to_doctype=profile.doctype,
		attached_to_name=profile.name,
	).insert()
	profile.image = new_file.file_url
	profile.is_image_background_removed = True
	profile.image_background_color = default_color
	profile.save()
	gameplan.refetch_resource("Users", user=profile.user)
