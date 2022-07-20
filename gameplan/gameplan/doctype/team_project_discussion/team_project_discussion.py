# Copyright (c) 2022, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class TeamProjectDiscussion(Document):
	def on_trash(self):
		for name in frappe.db.get_all('Team Comment', {
			'reference_doctype': self.doctype,
			'reference_name': self.name
		}, pluck='name'):
			frappe.delete_doc('Team Comment', name)

def make_full_text_search_index():
	frappe.db.sql('ALTER TABLE `tabTeam Project Discussion` ADD FULLTEXT (title, content, owner)')

@frappe.whitelist()
def search(query=None):
	from bs4 import BeautifulSoup

	query = query.lower() if query else ''
	if not query:
		return []

	results = frappe.db.sql('''
		SELECT name, title, content, owner, team, project, modified FROM `tabTeam Project Discussion`
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