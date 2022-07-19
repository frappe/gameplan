# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from __future__ import unicode_literals
import frappe


@frappe.whitelist()
def create_team(name):
	return frappe.get_doc(doctype="Team", title=name).insert()


@frappe.whitelist()
def get_team(name):
	return frappe.get_doc("Team", name)


@frappe.whitelist()
def get_documents(team):
	return frappe.db.get_all(
		"Team Document",
		fields=["name", "title", "modified", "creation"],
		filters={"team": team},
		order_by="creation desc",
	)


@frappe.whitelist()
def new_document(team):
	return frappe.get_doc(doctype="Team Document", team=team).insert()


@frappe.whitelist()
def get_document(name):
	return frappe.get_doc("Team Document", name)


@frappe.whitelist()
def update_document(name, title, content):
	doc = frappe.get_doc("Team Document", name)
	doc.title = title
	doc.content = content
	doc.save()


@frappe.whitelist()
def get_user_info():
	users = frappe.db.get_all(
		"User",
		filters=[["Has Role", "role", "=", "Teams User"]],
		fields=["name", "email", "user_image", "full_name", "user_type"],
	)
	out = {}
	for user in users:
		if frappe.session.user == user.name:
			user.session_user = True
		out[user.name] = user
	return out


@frappe.whitelist()
def invite_member(email, team):
	team = frappe.get_doc("Team", team)
	team.send_invitation(email)


@frappe.whitelist(allow_guest=True)
def accept_invitation(key=None):
	if not key:
		frappe.throw("Invalid or expired key")

	result = frappe.db.get_all(
		"Team Member", filters={"key": key}, fields=["email", "parent", "parenttype"]
	)
	if not result:
		frappe.throw("Invalid or expired key")

	# valid key, now set the user as Administrator
	frappe.set_user("Administrator")
	doctype = result[0].parenttype
	doc = frappe.get_doc(doctype, result[0].parent)
	user = doc.accept_invitation(key)

	if doctype == "Team":
		redirect_location = f"/teams/{doc.name}"
	elif doctype == "Team Project":
		redirect_location = f"/teams/{doc.team}/projects/{doc.name}"
	else:
		redirect_location = "/teams"

	if user:
		frappe.local.login_manager.login_as(user.name)
		frappe.local.response["type"] = "redirect"
		frappe.local.response["location"] = redirect_location


@frappe.whitelist()
def get_unsplash_photos(keyword=None):
	from gameplan.unsplash import get_list, get_by_keyword

	if keyword:
		return get_by_keyword(keyword)

	return frappe.cache().get_value("unsplash_photos", generator=get_list)


@frappe.whitelist()
def assign_task(task, user):
	from frappe.desk.form.assign_to import add, clear

	clear("Team Task", task)
	add({"assign_to": [user], "doctype": "Team Task", "name": task})


@frappe.whitelist()
def project_tasks(project):
	project = frappe.get_doc("Team Project", project)
	tasks_by_status = []
	for state in project.task_states:
		tasks_by_status.append(
			{
				"status": state.status,
				"tasks": frappe.db.get_all(
					"Team Task",
					filters={"project": project.name, "status": state.status},
					fields=["*"],
					order_by="idx asc, creation asc",
				),
			}
		)
	return tasks_by_status


@frappe.whitelist()
def delete_group(project, group):
	project = frappe.get_doc("Team Project", project)
	project.delete_group(group)
	return project


@frappe.whitelist()
def get_system_users():
	return frappe.db.get_all(
		"User",
		fields=["name", "email", "full_name", "first_name", "last_name", "user_image"],
		filters={"user_type": "System User", "enabled": 1},
	)


@frappe.whitelist()
def session_user():
	out = frappe.get_doc("User", frappe.session.user).as_dict()
	return out


@frappe.whitelist()
def daily_note(date=None):
	if not date:
		date = frappe.utils.today()

	note_name = frappe.db.get_value(
		"Team Note", filters={"date": date, "owner": frappe.session.user}
	)
	if not note_name:
		note = frappe.get_doc(doctype="Team Note", date=date, content="").insert()
	else:
		note = frappe.get_doc("Team Note", note_name)

	return note


@frappe.whitelist()
def update_daily_note(content, date=None):
	if not date:
		date = frappe.utils.today()

	note = frappe.get_doc("Team Note", {"date": date, "owner": frappe.session.user})
	note.content = content
	note.save()
	return note


@frappe.whitelist()
def tasks_for_day(date):
	Task = frappe.qb.DocType("Team Task")
	Project = frappe.qb.DocType("Team Project")
	overdue_condition = date == frappe.utils.today()
	query = (
		frappe.qb.from_(Task)
		.select(Task.star)
		.left_join(Project)
		.on(Task.project == Project.name)
		.where(Task.owner == frappe.session.user)
		.orderby(Task.idx, order=frappe._dict(value="desc"))
	)
	if date == frappe.utils.today():
		# fetch overdues only for today
		query = query.where(
			((Task.due_date == date) | ((Task.due_date < date) & (Task.is_completed == 0)))
		)
	else:
		query = query.where(Task.due_date == date)

	return query.run(as_dict=1)
