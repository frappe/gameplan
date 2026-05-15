from __future__ import annotations

import time
from random import randint
from html import escape

import frappe
from frappe.utils import add_days, get_url, now_datetime, strip_html_tags


INACTIVE_DAYS = 7
DIGEST_WINDOW_DAYS = 7
DIGEST_LIMIT = 10


def send_inactivity_digest_weekly():
	"""Send a weekly catch-up digest to opted-in users inactive for 7 days."""
	try:
		users = get_inactive_digest_users()
		for user in users:
			digest = build_user_digest(user.name)
			if not has_digest_items(digest):
				frappe.log_error("No digest items found", "Gameplan Digest")
				print(f"No digest items found for {user.email}, skipping email")
				continue

			try:
				frappe.sendmail(
					recipients=user.email,
					subject="Your Gameplan catch-up digest",
					message=render_digest_email(user, digest),
					now=True,
				)
			except frappe.OutgoingEmailError as e:
				# If outgoing Email Account isn't configured, don't fail the whole job.
				frappe.log_error(
					f"Error sending inactivity digest to {user.email}: {str(e)}",
					"Gameplan Digest",
				)
				print(f"Skipping email for {user.email}: {str(e)}")
				continue
			except Exception as e:
				frappe.log_error(f"Error sending inactivity digest: {str(e)}", "Gameplan Digest")
				print(f"Error sending inactivity digest: {str(e)}")
	except Exception as e:
		frappe.log_error(f"Error sending inactivity digest: {str(e)}", "Gameplan Digest")
		print(f"Error sending inactivity digest: {str(e)}")
		
	


def get_inactive_digest_users(inactive_days: int = INACTIVE_DAYS):
	"""Return opted-in users whose last activity is older than the inactivity threshold.

	Seven days is long enough to avoid nudging people who only missed a day or two,
	and short enough that active project discussions are still fresh.
	"""
	cutoff = add_days(now_datetime(), -inactive_days)
	return frappe.db.sql(
		"""
		select u.name, u.email, u.full_name, u.last_active
		from `tabUser` u
		where u.enabled = 1
			and u.user_type = 'Website User'
			and u.weekly_digest = 1
			and (
				u.last_active <= %(cutoff)s
				or (u.last_active is null and u.creation <= %(cutoff)s)
			)
			and exists (
				select 1
				from `tabHas Role` role
				where role.parenttype = 'User'
					and role.parent = u.name
					and role.role like 'Gameplan %%'
			)
		order by u.last_active asc
		""",
		{"cutoff": cutoff},
		as_dict=True,
	)


def build_user_digest(user: str, window_days: int = DIGEST_WINDOW_DAYS):
	window_start = add_days(now_datetime(), -window_days)
	digest = {
		"new_discussions": get_new_discussions_in_user_spaces(user, window_start),
		"thread_replies": get_replies_in_user_threads(user, window_start),
		"notifications": get_unread_notifications(user, window_start),
	}
	log_message = f"Built digest for {user}: {len(digest['new_discussions'])} new discussions, {len(digest['thread_replies'])} thread replies, {len(digest['notifications'])} notifications"
	frappe.log_error(log_message, "Gameplan Digest")
	print(log_message)
	return digest


def get_new_discussions_in_user_spaces(user: str, window_start):
	return frappe.db.sql(
		"""
		select
			discussion.name,
			discussion.title,
			discussion.slug,
			discussion.project,
			project.title as project_title,
			discussion.owner,
			discussion.creation
		from `tabGP Discussion` discussion
		inner join `tabGP Project` project on project.name = discussion.project
		where discussion.creation >= %(window_start)s
			and discussion.owner != %(user)s
			and project.archived_at is null
			and exists (
				select 1
				from `tabGP Member` member
				where member.parenttype = 'GP Project'
					and member.parent = discussion.project
					and member.user = %(user)s
			)
		order by discussion.creation desc
		limit %(limit)s
		""",
		{"user": user, "window_start": window_start, "limit": DIGEST_LIMIT},
		as_dict=True,
	)


def get_replies_in_user_threads(user: str, window_start):
	return frappe.db.sql(
		"""
		select
			comment.name,
			comment.owner,
			comment.creation,
			discussion.name as discussion,
			discussion.title,
			discussion.slug,
			discussion.project,
			project.title as project_title
		from `tabGP Comment` comment
		inner join `tabGP Discussion` discussion on discussion.name = comment.reference_name
		inner join `tabGP Project` project on project.name = discussion.project
		where comment.reference_doctype = 'GP Discussion'
			and comment.creation >= %(window_start)s
			and comment.owner != %(user)s
			and comment.deleted_at is null
			and (
				discussion.owner = %(user)s
				or exists (
					select 1
					from `tabGP Comment` user_comment
					where user_comment.reference_doctype = 'GP Discussion'
						and user_comment.reference_name = discussion.name
						and user_comment.owner = %(user)s
						and user_comment.deleted_at is null
				)
			)
		order by comment.creation desc
		limit %(limit)s
		""",
		{"user": user, "window_start": window_start, "limit": DIGEST_LIMIT},
		as_dict=True,
	)


def get_unread_notifications(user: str, window_start):
	return frappe.get_all(
		"GP Notification",
		filters={
			"to_user": user,
			"read": 0,
			"creation": [">=", window_start],
		},
		fields=["name", "type", "message", "discussion", "project", "creation", "from_user"],
		order_by="creation desc",
		limit=DIGEST_LIMIT,
	)


def has_digest_items(digest: dict) -> bool:
	return any(digest.get(key) for key in ("new_discussions", "thread_replies", "notifications"))


# def render_digest_email(user, digest: dict) -> str:
# 	name = escape(user.full_name or user.name)
# 	return f"""
# 		<p>Hi {name},</p>
# 		<p>You have been away from Gameplan for at least {INACTIVE_DAYS} days. Here is what changed in the last {DIGEST_WINDOW_DAYS} days.</p>
# 		{render_discussion_list("New discussions in your spaces", digest["new_discussions"])}
# 		{render_reply_list("Replies on threads you are in", digest["thread_replies"])}
# 		{render_notification_list("Unread mentions and direct notifications", digest["notifications"])}
# 		<p><a href="{get_url('/g')}">Open Gameplan</a></p>
# 	"""


```python
def render_digest_email(user, digest: dict) -> str:
	name = escape(user.full_name or user.name)

	new_discussions = digest.get("new_discussions", [])
	thread_replies = digest.get("thread_replies", [])
	notifications = digest.get("notifications", [])

	return f"""
	<html>
	<body style="
		margin:0;
		padding:0;
		background:#f4f5f7;
		font-family:Inter, Arial, sans-serif;
		color:#1f2937;
	">
		<div style="
			max-width:720px;
			margin:40px auto;
			padding:0 16px;
		">

			<!-- Preview Text -->
			<div style="
				display:none;
				max-height:0;
				overflow:hidden;
				opacity:0;
			">
				{len(new_discussions)} new discussions,
				{len(thread_replies)} replies,
				and {len(notifications)} notifications waiting for you.
			</div>

			<!-- Main Card -->
			<div style="
				background:#ffffff;
				border-radius:16px;
				padding:32px;
				box-shadow:0 2px 10px rgba(0,0,0,0.06);
			">

				<!-- Header -->
				<div style="margin-bottom:28px;">
					<h1 style="
						margin:0;
						font-size:28px;
						font-weight:700;
						color:#111827;
					">
						Gameplan Digest
					</h1>

					<p style="
						margin-top:12px;
						font-size:16px;
						line-height:1.6;
						color:#4b5563;
					">
						Hi <strong>{name}</strong>,
						<br /><br />
						Here’s what changed in the last
						<strong>{DIGEST_WINDOW_DAYS} days</strong>.
					</p>
				</div>

				<!-- Stats -->
				<div style="
					display:flex;
					gap:12px;
					margin-bottom:32px;
					flex-wrap:wrap;
				">
					{render_stat_card('🆕 Discussions', len(new_discussions))}
					{render_stat_card('💬 Replies', len(thread_replies))}
					{render_stat_card('🔔 Notifications', len(notifications))}
				</div>

				<!-- Empty State -->
				{
					render_empty_digest()
					if not new_discussions
					and not thread_replies
					and not notifications
					else ""
				}

				<!-- Sections -->
				{
					render_discussion_list(
						"🆕 New discussions in your spaces",
						new_discussions,
					)
					if new_discussions
					else ""
				}

				{
					render_reply_list(
						"💬 Replies on threads you are in",
						thread_replies,
					)
					if thread_replies
					else ""
				}

				{
					render_notification_list(
						"🔔 Unread mentions and notifications",
						notifications,
					)
					if notifications
					else ""
				}

				<!-- CTA -->
				<div style="
					margin-top:36px;
					text-align:center;
				">
					<a
						href="{get_url('/g')}"
						style="
							display:inline-block;
							background:#2563eb;
							color:white;
							text-decoration:none;
							padding:14px 24px;
							border-radius:10px;
							font-weight:600;
							font-size:15px;
						"
					>
						Open Gameplan
					</a>
				</div>

			</div>

			<!-- Footer -->
			<p style="
				text-align:center;
				font-size:12px;
				color:#9ca3af;
				margin-top:16px;
			">
				You’re receiving this digest because you were inactive recently.
			</p>

		</div>
	</body>
	</html>
	"""


def render_empty_digest():
	return """
	<div style="
		text-align:center;
		padding:48px 24px;
		background:#f9fafb;
		border:1px dashed #d1d5db;
		border-radius:14px;
		margin-bottom:24px;
	">
		<div style="
			font-size:42px;
			margin-bottom:12px;
		">
			✨
		</div>

		<h2 style="
			margin:0 0 10px 0;
			font-size:20px;
			color:#111827;
		">
			You’re all caught up
		</h2>

		<p style="
			margin:0;
			font-size:14px;
			line-height:1.6;
			color:#6b7280;
		">
			No new discussions, replies, or notifications
			were found for this digest period.
		</p>
	</div>
	"""
```


def render_discussion_list(title: str, rows: list) -> str:
	if not rows:
		return ""
	items = "\n".join(
		f'<li><a href="{discussion_url(row)}">{escape(row.title)}</a> <span style="color: #667085;">in {escape(row.project_title or "a space")}</span></li>'
		for row in rows
	)
	return f"<h3>{escape(title)}</h3><ul>{items}</ul>"


def render_reply_list(title: str, rows: list) -> str:
	if not rows:
		return ""
	items = "\n".join(
		f'<li><a href="{discussion_url(row)}">{escape(row.title)}</a> <span style="color: #667085;">in {escape(row.project_title or "a space")}</span></li>'
		for row in rows
	)
	return f"<h3>{escape(title)}</h3><ul>{items}</ul>"


def render_notification_list(title: str, rows: list) -> str:
	if not rows:
		return ""
	items = "\n".join(
		f'<li><a href="{notification_url(row)}">{escape(row.type)}</a>: {escape(strip_html_tags(row.message or ""))}</li>'
		for row in rows
	)
	return f"<h3>{escape(title)}</h3><ul>{items}</ul>"


def discussion_url(row) -> str:
	slug = f"/{row.slug}" if row.get("slug") else ""
	return get_url(f"/g/space/{row.project}/discussion/{row.get('discussion') or row.name}{slug}")


def notification_url(row) -> str:
	if row.get("discussion") and row.get("project"):
		return get_url(f"/g/space/{row.project}/discussion/{row.discussion}")
	return get_url("/g/notifications")


def log_inactive_digest_users(inactive_days: int = INACTIVE_DAYS):
	users = get_inactive_digest_users(inactive_days)
	usernames = [user.name for user in users]
	message = f"Inactive digest users ({inactive_days}+ days): {', '.join(usernames) if usernames else 'none'}"
	frappe.logger("gameplan.digest").info(message)
	print(message)
	return users


def run_inactivity_digest_dev_loop(interval_seconds: int = 5, max_runs: int = 0):
	"""Print inactive digest users every 5 seconds for local development.

	Frappe scheduler cron is minute-granularity, so this helper gives a true 5-second loop
	without changing production scheduler behavior. Set max_runs=0 to run until interrupted.
	"""
	run_count = 0
	while True:
		log_inactive_digest_users()
		run_count += 1
		if max_runs and run_count >= max_runs:
			break
		time.sleep(interval_seconds)


def backdate_user_login_for_tests(users: list[str], update_last_active: bool = True):
	"""Move users' login timestamps 8 days back for local digest testing."""
	days_back = 8
	login_at = add_days(now_datetime(), -days_back)
	results = []

	for user in users:
		fields = {"last_login": login_at}

		if update_last_active and frappe.get_meta("User").has_field("last_active"):
			fields["last_active"] = login_at

		frappe.db.set_value("User", user, fields, update_modified=False)

		print(f"Updated {user}: {', '.join(fields)} = {login_at} ({days_back} days back)")
		results.append({"user": user, "days_back": days_back, "updated_fields": fields})

	frappe.db.commit()
	return results
