# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe
from pypika.terms import ExistsCriterion


@frappe.whitelist()
def get_discussions(filters=None, limit_start=None, limit_page_length=None):
	filters = frappe.parse_json(filters) if filters else None
	Discussion = frappe.qb.DocType('Team Discussion')
	Visit = frappe.qb.DocType('Team Discussion Visit')
	Project = frappe.qb.DocType('Team Project')
	Team = frappe.qb.DocType('Team')
	Member = frappe.qb.DocType('Team Member')
	member_exists = (
		frappe.qb.from_(Member)
			.select(Member.name)
			.where(Member.parenttype == 'Team')
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
