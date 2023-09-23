# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
from posixpath import splitext
import frappe
import psycopg2
from psycopg2.extras import DictCursor
from frappe.utils import update_progress_bar
from bs4 import BeautifulSoup
from .emojis import get_emoji

CONNECTION_STRING = "host='localhost' dbname='discourse_db' user='postgres' password='qwe' port=5432"
UPLOADS_FOLDER = "/path/to/discourse-backup/uploads"

def execute():
	frappe.flags.in_import = True
	clear_data([
		# 'GP Project',
		# 'GP Team',
		# 'GP Discussion'
		# 'User'
	])
	# migrate_categories()
	# migrate_users()
	migrate_posts()


def migrate_posts():
	topics = run_query('''
		select topics.id, topics.title, topics.user_id, topics.category_id,
			posts.created_at as creation, posts.updated_at as modified,
			posts.cooked as content, posts.id as post_id, topics.last_posted_at as last_post_at
		from topics
		left join posts on posts.topic_id = topics.id
		where posts.user_id > 0 and posts.post_number = 1
		order by topics.id asc
	''')

	for i, topic in enumerate(topics):
		if frappe.db.exists('Discourse ID Map', {'discourse_table': 'topics', 'discourse_id': topic.id}):
			continue

		update_progress_bar('Creating Posts', i, len(topics), absolute=True)
		savepoint = f'inserting_topic_{topic.id}'
		try:
			frappe.db.savepoint(savepoint)
			user = get_user(topic.user_id)
			project = get_project(topic.category_id)
			# likes - reactions
			reactions = get_reactions(topic.post_id)

			doc = frappe.get_doc(
				doctype='GP Discussion',
				title=topic.title,
				content=topic.content,
				project=project,
				team=frappe.db.get_value('GP Project', project, 'team'),
				last_post_at=topic.last_post_at,
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
					doctype='GP Comment',
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

			# visits
			visits_data = run_query(f'''
				select topic_id, first_visited_at as creation, last_visited_at as last_visit, user_id
				from topic_users where topic_id = '{topic.id}'
			''')
			visits = []
			for d in visits_data:
				name = frappe.db.get_next_sequence_val('GP Discussion Visit')
				user = get_user(d.user_id)
				#        ["name", "user", "discussion", 'last_visit', 'creation', 'modified', 'modified_by', 'owner'],
				visits.append([name, user, doc.name, d.last_visit, d.creation, d.last_visit, user, user])

			if visits:
				frappe.db.bulk_insert(
					"GP Discussion Visit",
					["name", "user", "discussion", "last_visit", "creation", "modified", "modified_by", "owner"],
					visits
				)

			log_discourse_map(doc, "topics", topic.id)
		except Exception:
			frappe.db.rollback(save_point=savepoint)
			print(frappe.get_traceback())
			break
		else:
			frappe.db.release_savepoint(savepoint)


def process_images_in_html(doc, fieldname):
	html = doc.get(fieldname)
	touched = False
	soup = BeautifulSoup(html, 'html.parser')
	for img in soup.find_all('img', attrs={'class': 'emoji'}):
		emoji_name = img.get('title', '::')[1:-1]
		if emoji_name:
			emoji = get_emoji(emoji_name)
			if emoji:
				img.replace_with(f' {emoji} ')
				touched = True

	for img in soup.findAll('img'):
		src = img.get('src')
		filename = img.get('alt')
		if src and not src.startswith('https://mail.google.com'):
			file = save_image(src, filename, doc)
			if file:
				img['src'] = file.file_url
				touched = True

	if touched:
		doc.db_set(fieldname, str(soup), update_modified=False)


def save_image(src, filename=None, doc=None):
	parts = src.split('/uploads/', 1)
	if len(parts) == 2:
		file_path = parts[1]
		full_path = f'{UPLOADS_FOLDER}/{file_path}'
		file_content = None
		try:
			with open(full_path, 'rb') as f:
				file_content = f.read()
		except FileNotFoundError:
			return

		_, extn = splitext(full_path)
		hash = frappe.generate_hash(length=5)
		filename = f'{filename or ""}-{hash}{extn}'.replace(' ', '-').replace('%20', '-')
		filename = filename.split('?', 1)[0]
		return frappe.get_doc(
			doctype='File',
			content=file_content,
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
		'reference_doctype': 'GP Project',
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
			'user': get_user(d.user_id),
			'emoji': '💖'
		})
	return reactions

def get_avatar_url(user_id):
	result = run_query(f'''
		select users.id, url from users
		left join user_avatars on user_avatars.user_id = users.id
		left join uploads on uploads.id = user_avatars.custom_upload_id
		where users.id = {user_id} limit 1;
	''')
	user = result[0] if result else None
	if user:
		return user['url']


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
		update_progress_bar("Creating users", i, len(users), absolute=True)

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
			roles=[{"role": "Gameplan Member"}]
		).insert(ignore_if_duplicate=True)

		if doc:
			avatar_url = get_avatar_url(user.id)
			if avatar_url:
				filename = f'{user.username}'.replace(' ', '-').replace('%20', '-')
				file = save_image(avatar_url, filename, doc)
				if file:
					doc.db_set('user_image', file.file_url)
			log_discourse_map(doc, "users", user.id)



def migrate_categories():
	# create one team under which all categories will be created as projects
	team = 'General'
	if not frappe.db.exists('GP Team', {'title': team}):
		team_doc = frappe.get_doc(doctype='GP Team', title=team).insert()
	else:
		team_doc = frappe.get_doc('GP Team', {'title': team})

	categories = run_query('''
		select categories.id, categories.name as project
		from categories
	''')

	for i, d in enumerate(categories):
		update_progress_bar('Creating projects', i, len(categories), absolute=True)
		id = d['id']
		project = d['project']
		project_doc = frappe.get_doc(doctype='GP Project', title=project, team=team_doc.name).insert()
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
		conn = psycopg2.connect(CONNECTION_STRING)
		cursor = conn.cursor(cursor_factory=DictCursor)

	cursor.execute(query, values)
	result = cursor.fetchall()
	return [frappe._dict(row) for row in result]
