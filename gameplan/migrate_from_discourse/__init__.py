# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
from abc import abstractstaticmethod
from posixpath import splitext
from urllib.parse import urljoin
import frappe
import psycopg2
from psycopg2.extras import DictCursor
from frappe.database.database import savepoint
from frappe.utils import update_progress_bar
from bs4 import BeautifulSoup
from .emojis import get_emoji
import requests

def execute():
	frappe.flags.in_import = True
	# clear_data([
	# 	# 'Team Project',
	# 	# 'Team',
	# 	'Team Project Discussion'
	# ])
	# migrate_users()
	# migrate_categories()
	migrate_posts()


def migrate_posts():
	topics = run_query('''
		select topics.id, topics.title, topics.user_id, topics.category_id,
			posts.created_at as creation, posts.updated_at as modified,
			posts.cooked as content, posts.id as post_id
		from topics
		left join posts on posts.topic_id = topics.id
		where posts.user_id > 0 and posts.post_number = 1
	''')

	for i, topic in enumerate(topics):
		if frappe.db.exists('Discourse ID Map', {'discourse_table': 'topics', 'discourse_id': topic.id}):
			continue

		update_progress_bar('Creating Posts', i, len(topics), absolute=True)

		with savepoint():
			user = get_user(topic.user_id)
			project = get_project(topic.category_id)
			# likes - reactions
			reactions = get_reactions(topic.post_id)

			doc = frappe.get_doc(
				doctype='Team Project Discussion',
				title=topic.title,
				content=topic.content,
				project=project,
				team=frappe.db.get_value('Team Project', project, 'team'),
				creation=topic.creation,
				modified=topic.modified,
				owner=user,
				modified_by=user,
				reactions=reactions
			)
			doc.db_insert()
			for d in doc.get_all_children():
				d.parent = doc.name
				d.db_insert()

			# images
			process_images_in_html(doc, 'content')

			# comments
			comments = run_query(f'''
				select posts.id, posts.created_at as creation, posts.updated_at as modified, posts.user_id,
				posts.cooked as content, posts.topic_id
				from posts
				where posts.topic_id = {topic.id} and posts.user_id > 0 and posts.post_number > 1
			''')

			for comment in comments:
				user = get_user(comment.user_id)
				reactions = get_reactions(comment.id)
				comment_doc = frappe.get_doc(
					doctype='Team Comment',
					reference_doctype=doc.doctype,
					reference_name=doc.name,
					content=comment.content,
					creation=comment.creation,
					modified=comment.modified,
					owner=user,
					modified_by=user,
					reactions=reactions
				)
				comment_doc.db_insert()
				for d in comment_doc.get_all_children():
					d.parent = comment_doc.name
					d.db_insert()
				process_images_in_html(comment_doc, 'content')

			log_discourse_map(doc, 'topics', topic.id)


def process_images_in_html(doc, fieldname):
	html = doc.get(fieldname)
	soup = BeautifulSoup(html, 'html.parser')
	for img in soup.find_all('img', attrs={'class': 'emoji'}):
		emoji_name = img.get('title', '::')[1:-1]
		if emoji_name:
			emoji = get_emoji(emoji_name)
			if emoji:
				img.replace_with(f' {emoji} ')

	for img in soup.findAll('img'):
		src = img.get('src')
		filename = img.get('alt')
		if src:
			file = save_image(src, filename, doc)
			if file:
				img['src'] = file.file_url

	doc.db_set(fieldname, str(soup), update_modified=False)


def save_image(src, filename=None, doc=None):
	if not src.startswith('http'):
		src = urljoin('https://gameplan.frappe.io', src)

	res = requests.get(src)
	if res.ok:
		_, extn = splitext(src)
		hash = frappe.generate_hash(length=5)
		filename = f'{filename}-{hash}{extn}'.replace(' ', '-').replace('%20', '-')
		return frappe.get_doc(
			doctype='File',
			content=res.content,
			file_name=filename,
			is_private=0,
			attached_to_doctype=doc.doctype,
			attached_to_name=doc.name
		).insert()

def get_user(user_id):
	return frappe.db.get_value('Discourse ID Map', {
		'discourse_table': 'users',
		'discourse_id': user_id
	}, 'reference_name')

def get_project(category_id):
	return frappe.db.get_value('Discourse ID Map', {
		'reference_doctype': 'Team Project',
		'discourse_table': 'categories',
		'discourse_id': category_id
	}, 'reference_name')

def get_reactions(post_id):
	likes = run_query(f'''
		select user_id from post_actions where post_action_type_id = 2 and user_id > 0 and post_id = {post_id};
	''')
	reactions = []
	for d in likes:
		reactions.append({
			'owner': get_user(d.user_id),
			'emoji': '💖'
		})
	return reactions

def get_avatar_url(user_id):
	result = run_query(f'''
		select users.id, users.username, user_avatars.custom_upload_id from users
		left join user_avatars on user_avatars.user_id = users.id
		where user_id = {user_id} limit 1;
	''')
	user = result[0] if result else None
	if user:
		return f'https://gameplan.frappe.io/user_avatar/gameplan.frappe.io/{user.username}/240/{user.custom_upload_id}.png'


def clear_data(doctypes=None):
	to_delete = []
	for dt in doctypes:
		for row in frappe.db.get_all('Discourse ID Map', {'reference_doctype': dt}, ['reference_name', 'name']):
			to_delete.append((dt, row.reference_name))
			to_delete.append(('Discourse ID Map', row.name))


	for i, d in enumerate(to_delete):
		update_progress_bar('Deleting', i, len(to_delete))
		frappe.delete_doc(d[0], d[1])


def migrate_users():
	users = run_query('''
		select users.id, username, active, name as full_name, user_emails.email as email
		from users
		left join user_emails on user_emails.user_id = users.id
		where users.id > 1 order by id asc;
	''')

	for i, user in enumerate(users):
		update_progress_bar("Creating users", i, len(users))

		full_name = f'{user.full_name or user.username} '
		first_name, last_name = full_name.split(' ', 1)
		doc = frappe.get_doc(
			doctype="User",
			send_welcome_email=0,
			email=user.email,
			enabled=user.active,
			first_name=first_name,
			last_name=last_name,
			username=user.username,
			roles=[{"role": "Teams User"}]
		).insert(ignore_if_duplicate=True)

		if doc:
			avatar_url = get_avatar_url(user.id)
			if avatar_url:
				filename = f'{user.username}.png'.replace(' ', '-').replace('%20', '-')
				file = save_image(avatar_url, filename, doc)
				if file:
					doc.db_set('user_image', file.file_url)
			log_discourse_map(doc, "users", user.id)



def migrate_categories():
	categories = [{
		'id': 46,
		'project': "Business / Strategy",
		'team': 'Company'
	},
	{
		'id': 1,
		'project': "Uncategorized",
		'team': 'Company'
	},
	{
		'id': 51,
		'project': "Documentation",
		'team': 'Engineering'
	},
	{
		'id': 11,
		'project': "General",
		'team': 'HR'
	},
	{
		'id': 19,
		'project': "Friday Forum",
		'team': 'Company'
	},
	{
		'id': 34,
		'project': "Conference",
		'team': 'Marketing'
	},
	{
		'id': 33,
		'project': "General",
		'team': 'Framework'
	},
	{
		'id': 49,
		'project': "General",
		'team': 'Company'
	},
	{
		'id': 20,
		'project': "General",
		'team': 'Support'
	},
	{
		'id': 48,
		'project': "Systems",
		'team': 'Quality'
	},
	{
		'id': 41,
		'project': "CSR",
		'team': 'Company'
	},
	{
		'id': 42,
		'project': "Contributor of the Month",
		'team': 'HR'
	},
	{
		'id': 28,
		'project': "Monthly Update",
		'team': 'Company'
	},
	{
		'id': 55,
		'project': "ISO",
		'team': "Quality"
	},
	{
		'id': 56,
		'project': "SAAS",
		'team': 'Engineering'
	},
	{
		'id': 47,
		'project': "Culture / Leadership",
		'team': 'Company'
	},
	{
		'id': 23,
		'project': "General",
		'team': 'Frappe Cloud'
	},
	{
		'id': 54,
		'project': "Solutions",
		'team': 'Delivery Team'
	},
	{
		'id': 36,
		'project': "Grievance",
		'team': "HR"
	},
	{
		'id': 17,
		'project': "Product Management",
		'team': 'Company'
	},
	{
		'id': 50,
		'project': "General",
		'team': 'Frappe School'
	},
	{
		'id': 27,
		'project': "Approved",
		'team': "OpenFLC"
	},
	{
		'id': 6,
		'project': "SRE",
		'team': 'DevOps'
	},
	{
		'id': 30,
		'project': "Delivery / Projects",
		'team': 'Delivery Team'
	},
	{
		'id': 13,
		'project': "General",
		'team': 'Sales'
	},
	{
		'id': 9,
		'project': "Training",
		'team': "HR"
	},
	{
		'id': 52,
		'project': "Release",
		'team': 'Engineering'
	},
	{
		'id': 22,
		'project': "General",
		'team': 'Operations'
	},
	{
		'id': 38,
		'project': "General",
		'team': 'Engineering'
	},
	{
		'id': 53,
		'project': "Team",
		'team': 'Company'
	},
	{
		'id': 43,
		'project': "Goals & Reflections",
		'team': 'HR'
	},
	{
		'id': 45,
		'project': "Legal",
		'team': 'Company'
	},
	{
		'id': 8,
		'project': "General",
		'team': 'Quality'
	},
	{
		'id': 5,
		'project': "Meta",
		'team': 'Company'
	},
	{
		'id': 25,
		'project': "General",
		'team': 'Design'
	},
	{
		'id': 21,
		'project': "Testing",
		'team': "Quality"
	},
	{
		'id': 10,
		'project': "General",
		'team': 'Marketing'
	},
	{
		'id': 26,
		'project': "General",
		'team': 'OpenFLC'
	},
	{
		'id': 7,
		'project': "Accounts",
		'team': 'Company'
	},
	{
		'id': 16,
		'project': "Wiki",
		'team': 'Engineering'
	},
	{
		'id': 12,
		'project': "Fun Points",
		'team': 'Company'
	},
	{
		'id': 18,
		'project': "General",
		'team': 'Partner Team'
	}]

	for i, d in enumerate(categories):
		update_progress_bar('Creating projects', i, len(categories))
		id = d['id']
		team = d['team']
		project = d['project']

		if not frappe.db.exists('Team', {'title': team}):
			team_doc = frappe.get_doc(doctype='Team', title=team).insert()
			log_discourse_map(team_doc, 'categories', id)
		else:
			team_doc = frappe.get_doc('Team', {'title': team})

		project_doc = frappe.get_doc(doctype='Team Project', title=project, team=team_doc.name).insert()
		log_discourse_map(project_doc, 'categories', id)



def log_discourse_map(doc, table, id):
    frappe.get_doc(
		doctype='Discourse ID Map',
		reference_doctype=doc.doctype,
		reference_name=doc.name,
		discourse_table=table,
		discourse_id=id
	).insert()


conn = None
cursor = None
def run_query(query, values=None):
	global conn, cursor

	if not conn:
		conn = psycopg2.connect(
			"host='localhost' dbname='gameplandb' user='postgres' password='qwe' port=5432"
		)
		cursor = conn.cursor(cursor_factory=DictCursor)

	cursor.execute(query, values)
	result = cursor.fetchall()
	return [frappe._dict(row) for row in result]
