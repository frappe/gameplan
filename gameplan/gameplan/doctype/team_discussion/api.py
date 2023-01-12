# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe
import gameplan
from pypika.terms import ExistsCriterion


@frappe.whitelist()
def get_discussions(filters=None, limit_start=None, limit_page_length=None):
	if not frappe.has_permission('Team Discussion', 'read'):
		frappe.throw('Insufficient Permission for Team Discussion', frappe.PermissionError)

	filters = frappe.parse_json(filters) if filters else None
	Discussion = frappe.qb.DocType('Team Discussion')
	Visit = frappe.qb.DocType('Team Discussion Visit')
	Project = frappe.qb.DocType('Team Project')
	Team = frappe.qb.DocType('GP Team')
	Member = frappe.qb.DocType('Team Member')
	member_exists = (
		frappe.qb.from_(Member)
			.select(Member.name)
			.where(Member.parenttype == 'GP Team')
			.where(Member.parent == Project.team)
			.where(Member.user == frappe.session.user)
	)
	query = (
		frappe.qb.from_(Discussion)
		.select(
			Discussion.name, Discussion.owner, Discussion.creation, Discussion.modified,
			Discussion.title, Discussion.status, Discussion.team, Discussion.project,
			Discussion.last_post_at, Discussion.last_post_by, Discussion.comments_count,
			Discussion.closed_at, Discussion.closed_by, Discussion.slug,
			Visit.last_visit, Project.title.as_('project_title'), Team.title.as_('team_title')
		)
		.left_join(Visit)
		.on((Discussion.name == Visit.discussion) & (Visit.user == frappe.session.user))
		.left_join(Project)
		.on(Discussion.project == Project.name)
		.left_join(Team)
		.on(Discussion.team == Team.name)
		.where(
			(Project.is_private == 0) | ((Project.is_private == 1) & ExistsCriterion(member_exists))
		)
		.orderby(Discussion.last_post_at, order=frappe._dict(value="desc"))
		.limit(limit_page_length)
		.offset(limit_start or 0)
	)
	if filters:
		for key in filters:
			query = query.where(Discussion[key] == filters[key])

	is_guest = gameplan.is_guest()
	if is_guest:
		GuestAccess = frappe.qb.DocType('GP Guest Access')
		project_list = GuestAccess.select(GuestAccess.project).where(GuestAccess.user == frappe.session.user)
		query = query.where(Discussion.project.isin(project_list))

	return query.run(as_dict=1)



def highlight_matched_words(text, keywords, strip_content=False):
	words = remove_falsy_values(text.split(' '))
	matches = []
	for i, word in enumerate(words):
		if word.lower() in keywords:
			matches.append(i)
			words[i] = f'<mark class="bg-yellow-100">{word}</mark>'

	if matches:
		if strip_content:
			min_match = min(matches)
			max_match = min_match + 8
			left = min_match - 2
			right = max_match + 2
			left = left if left >= 0 else 0
			right = right if right < len(words) else len(words) - 1
			words = words[left:right]
	else:
		if strip_content:
			words = []

	return ' '.join(words)


def remove_falsy_values(items):
	return [item for item in items if item]
