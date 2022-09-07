# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe


@frappe.whitelist()
def search(query=None):
	from bs4 import BeautifulSoup

	query = query.lower() if query else ''
	if not query:
		return []

	results = frappe.db.sql('''
		SELECT name, title, content, owner, team, project, modified FROM `tabTeam Discussion`
		WHERE MATCH (title,content,owner)
		AGAINST (%(query)s IN NATURAL LANGUAGE MODE)
		ORDER BY modified DESC
		LIMIT 5
	''', values={'query': query}, as_dict=1)

	keywords = remove_falsy_values(query.split(' '))
	out = []
	for r in results:
		soup = BeautifulSoup(r.content)
		content_text = soup.get_text()
		r.content = highlight_matched_words(content_text, keywords, strip_content=True)
		r.title = highlight_matched_words(r.title, keywords)
		out.append(r)

	return out


@frappe.whitelist()
def get_discussions(filters=None, limit_start=None):
	filters = frappe.parse_json(filters) if filters else None
	Discussion = frappe.qb.DocType('Team Discussion')
	Visit = frappe.qb.DocType('Team Discussion Visit')
	Project = frappe.qb.DocType('Team Project')
	Team = frappe.qb.DocType('Team')
	query = (
		frappe.qb.from_(Discussion)
		.select(
			Discussion.name, Discussion.owner, Discussion.creation, Discussion.modified,
			Discussion.title, Discussion.status, Discussion.team, Discussion.project,
			Discussion.last_post_at, Discussion.comments_count,
			Visit.last_visit, Project.title.as_('project_title'), Team.title.as_('team_title')
		)
		.left_join(Visit)
		.on((Discussion.name == Visit.discussion) & (Visit.user == frappe.session.user))
		.left_join(Project)
		.on(Discussion.project == Project.name)
		.left_join(Team)
		.on(Discussion.team == Team.name)
		.orderby(Discussion.last_post_at, order=frappe._dict(value="desc"))
		.limit(20)
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
