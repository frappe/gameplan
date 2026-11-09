# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

from datetime import date, datetime, time, timedelta
from urllib.parse import quote

import frappe
from frappe import _
from frappe.query_builder import Order
from frappe.query_builder.functions import Count
from frappe.utils import add_to_date, get_datetime, get_url, getdate, now_datetime, nowdate
from frappe.utils.verified_command import get_signed_params, verify_request

from gameplan.permissions import apply_accessible_project_filter
from gameplan.utils import html_to_text_preview

# The digest is weekly only while we tune what it shows. It covers the 7 days before the send
# day, so a reader catches up on that week and nothing older.
EMAIL_DIGEST_FREQUENCY = "Weekly"
DIGEST_PERIOD_DAYS = 7
EMAIL_DIGEST_DAYS_OF_WEEK = {
	"Monday": 0,
	"Tuesday": 1,
	"Wednesday": 2,
	"Thursday": 3,
	"Friday": 4,
	"Saturday": 5,
	"Sunday": 6,
}
DEFAULT_EMAIL_DIGEST_DAY_OF_WEEK = "Monday"
MAX_DIGEST_ITEMS = 10
# Notifications that ask for the reader's attention; reactions do not
MENTION_NOTIFICATION_TYPES = ("Mention", "Rich Quote")
# A reply takes more effort than a reaction, so it counts as this many reactions when ranking.
REPLY_WEIGHT = 3
# A post needs this many reactions before the digest calls it the most popular of the week.
MIN_HIGHLIGHT_REACTIONS = 3
EMAIL_DIGEST_LINK_EXPIRES_DAYS = 45
DIGEST_PREFERENCES_REDIRECT = "/g/notifications?settings=notifications"
GAMEPLAN_LOGO_PATH = "/assets/gameplan/gameplan_logo_256.png"


def send_due_email_digests():
	today = getdate(nowdate())
	for profile in get_due_profiles(today):
		send_digest_for_profile(profile, today)


def get_due_profiles(today: date | None = None):
	today = today or getdate(nowdate())
	profiles = frappe.qb.get_query(
		"GP User Profile",
		fields=[
			"name",
			"user",
			"full_name",
			"email_digest_frequency",
			"email_digest_day_of_week",
			"email_digest_last_sent_on",
		],
		filters=[
			["enabled", "=", 1],
			["email_digest_frequency", "=", EMAIL_DIGEST_FREQUENCY],
		],
	).run(as_dict=True)
	return [profile for profile in profiles if is_digest_due(profile, today)]


def is_digest_due(profile, today: date | None = None):
	if profile.email_digest_frequency != EMAIL_DIGEST_FREQUENCY:
		return False

	today = today or getdate(nowdate())
	if not is_digest_scheduled_for_today(profile, today):
		return False

	last_sent_on = getdate(profile.email_digest_last_sent_on) if profile.email_digest_last_sent_on else None
	if not last_sent_on:
		return True

	return (today - last_sent_on).days >= DIGEST_PERIOD_DAYS


def is_digest_scheduled_for_today(profile, today: date):
	day_of_week = get_digest_day_of_week(profile)
	return today.weekday() == EMAIL_DIGEST_DAYS_OF_WEEK[day_of_week]


def get_digest_day_of_week(profile):
	day_of_week = profile.get("email_digest_day_of_week")
	if day_of_week in EMAIL_DIGEST_DAYS_OF_WEEK:
		return day_of_week
	return DEFAULT_EMAIL_DIGEST_DAY_OF_WEEK


def get_digest_period_start(today: date) -> datetime:
	"""Start of the week a digest sent on `today` covers.

	It starts at midnight, so a post made on the last send day before the digest went out can
	show up in two digests. Repeating an item is better than missing one."""
	return datetime.combine(today - timedelta(days=DIGEST_PERIOD_DAYS), time.min)


def send_digest_for_profile(profile, today: date | None = None):
	today = today or getdate(nowdate())
	digest = build_digest(profile.user, get_digest_period_start(today))

	if has_digest_items(digest):
		frappe.sendmail(
			recipients=[profile.user],
			subject=get_digest_subject(),
			template="email_digest",
			args=get_digest_email_context(profile, digest),
		)

	frappe.db.set_value(
		"GP User Profile",
		profile.name,
		"email_digest_last_sent_on",
		today,
		update_modified=False,
	)
	return digest


def build_digest(user: str, since: datetime):
	"""What `user` missed since `since`: unread mentions and quotes, the week's most popular post,
	and discussions with new posts they have not read, busiest first."""
	notifications = get_unread_mentions(user, since)
	highlight = get_most_popular_post(user, since)
	# A discussion already in a mention or the highlight is not listed again
	shown = {str(notification.discussion) for notification in notifications if notification.discussion}
	if highlight:
		shown.add(str(highlight.discussion))
	discussions = [
		discussion for discussion in get_active_discussions(user, since) if str(discussion.name) not in shown
	]
	return {
		"notifications": notifications,
		"highlight": highlight,
		"discussions": discussions[:MAX_DIGEST_ITEMS],
	}


def has_digest_items(digest):
	return bool(digest["notifications"] or digest["highlight"] or digest["discussions"])


def get_digest_subject():
	return f"Your {EMAIL_DIGEST_FREQUENCY} Gameplan digest"


def get_digest_email_context(profile, digest):
	avatar_map = get_user_avatar_map(get_digest_item_users(digest))
	highlight = digest["highlight"]
	return {
		"frequency": EMAIL_DIGEST_FREQUENCY,
		"logo_url": get_url(GAMEPLAN_LOGO_PATH),
		"site_url": get_url(),
		"open_gameplan_url": get_signed_digest_url(profile.user, "/g"),
		"preferences_url": get_digest_preferences_url(profile.user),
		"notifications": format_notification_items(digest["notifications"], avatar_map, profile.user),
		"highlight": format_highlight(highlight, avatar_map, profile.user) if highlight else None,
		"discussions": [
			format_discussion_item(discussion, avatar_map, profile.user)
			for discussion in digest["discussions"]
		],
	}


@frappe.whitelist(allow_guest=True, methods=["GET"])
def open_digest_preferences(
	user: str,
	redirect: str = DIGEST_PREFERENCES_REDIRECT,
	expires: str | None = None,
):
	if not verify_request():
		return

	if not is_valid_digest_login_link(user, expires):
		return

	frappe.local.login_manager.login_as(user)
	frappe.local.response["type"] = "redirect"
	frappe.local.response["location"] = get_safe_digest_redirect(redirect)


def get_unread_mentions(user: str, since: datetime):
	return frappe.qb.get_query(
		"GP Notification",
		fields=[
			"name",
			"type",
			"message",
			"creation",
			"from_user",
			"from_user.full_name as from_user_full_name",
			"discussion",
			"discussion.title as discussion_title",
			"discussion.slug as discussion_slug",
			"task",
			"task.title as task_title",
			"project",
			"project.title as project_title",
			"team",
			"team.title as team_title",
		],
		filters=[
			["to_user", "=", user],
			["read", "=", 0],
			["type", "in", MENTION_NOTIFICATION_TYPES],
			["creation", ">=", since],
		],
		order_by="creation desc",
		limit=MAX_DIGEST_ITEMS,
	).run(as_dict=True)


def get_active_discussions(user: str, since: datetime):
	"""Discussions with a post or reply since `since` that `user` has not read.

	Ranked by everything that happened in them since `since` (the new discussion itself, its
	replies and its reactions, with a reply worth `REPLY_WEIGHT` reactions), so an old thread
	with a big history but a quiet week does not push this week's conversations out."""
	UnreadRecord = frappe.qb.DocType("GP Unread Record")
	Discussion = frappe.qb.DocType("GP Discussion")
	Project = frappe.qb.DocType("GP Project")
	Team = frappe.qb.DocType("GP Team")

	query = (
		frappe.qb.from_(UnreadRecord)
		.join(Discussion)
		.on(UnreadRecord.discussion == Discussion.name)
		.join(Project)
		.on(Discussion.project == Project.name)
		.left_join(Team)
		.on(Project.team == Team.name)
		.select(
			Discussion.name,
			Discussion.owner,
			Discussion.title,
			Discussion.slug,
			Discussion.project,
			Discussion.creation,
			Discussion.last_post_at,
			Project.title.as_("project_title"),
			Project.team,
			Team.title.as_("team_title"),
			# COUNT skips nulls, and only a reply's unread record has a comment
			Count(UnreadRecord.comment).as_("unread_replies_count"),
		)
		.where(
			(UnreadRecord.user == user)
			& (UnreadRecord.is_unread == 1)
			& (UnreadRecord.creation >= since)
			& Project.archived_at.isnull()
		)
		.groupby(Discussion.name)
	)
	query = apply_accessible_project_filter(query, Discussion.project, user)
	discussions = query.run(as_dict=True)

	names = [str(discussion.name) for discussion in discussions]
	replies = get_reply_counts(names, since)
	reactions = get_reaction_counts(names, since)
	for discussion in discussions:
		discussion.is_new = get_datetime(discussion.creation) >= since
		discussion.replies_count = replies.get(str(discussion.name), 0)
		discussion.reactions_count = reactions.get(str(discussion.name), 0)
		discussion.activity_score = (
			int(discussion.is_new) + REPLY_WEIGHT * discussion.replies_count + discussion.reactions_count
		)

	return sorted(discussions, key=discussion_sort_key, reverse=True)


def discussion_sort_key(discussion):
	return (discussion.activity_score, str(discussion.last_post_at or ""), str(discussion.name))


def get_reply_counts(discussion_names, since: datetime):
	if not discussion_names:
		return {}

	Comment = frappe.qb.DocType("GP Comment")
	rows = (
		frappe.qb.from_(Comment)
		.select(Comment.reference_name, Count(Comment.name).as_("count"))
		.where(
			(Comment.reference_doctype == "GP Discussion")
			& Comment.reference_name.isin(discussion_names)
			& (Comment.creation >= since)
			& Comment.deleted_at.isnull()
		)
		.groupby(Comment.reference_name)
	).run(as_dict=True)
	return {str(row.reference_name): row.count for row in rows}


def get_reaction_counts(discussion_names, since: datetime):
	"""Reactions added since `since` to each discussion's post and to its replies."""
	if not discussion_names:
		return {}

	Reaction = frappe.qb.DocType("GP Reaction")
	Comment = frappe.qb.DocType("GP Comment")
	post_rows = (
		frappe.qb.from_(Reaction)
		.select(Reaction.reference_name.as_("discussion"), Count(Reaction.name).as_("count"))
		.where(
			(Reaction.reference_doctype == "GP Discussion")
			& Reaction.reference_name.isin(discussion_names)
			& (Reaction.creation >= since)
		)
		.groupby(Reaction.reference_name)
	).run(as_dict=True)
	reply_rows = (
		frappe.qb.from_(Reaction)
		.join(Comment)
		.on(Reaction.reference_name == Comment.name)
		.select(Comment.reference_name.as_("discussion"), Count(Reaction.name).as_("count"))
		.where(
			(Reaction.reference_doctype == "GP Comment")
			& (Comment.reference_doctype == "GP Discussion")
			& Comment.reference_name.isin(discussion_names)
			& Comment.deleted_at.isnull()
			& (Reaction.creation >= since)
		)
		.groupby(Comment.reference_name)
	).run(as_dict=True)

	counts = {}
	for row in [*post_rows, *reply_rows]:
		counts[str(row.discussion)] = counts.get(str(row.discussion), 0) + row.count
	return counts


def get_most_popular_post(user: str, since: datetime):
	"""The discussion post or reply made since `since` with the most reactions, from a Space
	`user` can see. Their own posts are left out, since the digest is about what they missed."""
	candidates = [
		row
		for row in [get_most_reacted_discussion(user, since), get_most_reacted_reply(user, since)]
		if row and row.reactions_count >= MIN_HIGHLIGHT_REACTIONS
	]
	if not candidates:
		return None
	return max(candidates, key=lambda row: (row.reactions_count, str(row.creation)))


def get_most_reacted_discussion(user: str, since: datetime):
	Discussion = frappe.qb.DocType("GP Discussion")
	query = popular_post_query(user, since, Discussion, Discussion, "GP Discussion").select(
		Discussion.name.as_("discussion"),
		Discussion.owner,
		Discussion.content,
		Discussion.creation,
	)
	return first_row(query)


def get_most_reacted_reply(user: str, since: datetime):
	Comment = frappe.qb.DocType("GP Comment")
	Discussion = frappe.qb.DocType("GP Discussion")
	query = (
		popular_post_query(user, since, Comment, Discussion, "GP Comment")
		.where((Comment.reference_doctype == "GP Discussion") & Comment.deleted_at.isnull())
		.select(
			Comment.reference_name.as_("discussion"),
			Comment.name.as_("comment"),
			Comment.owner,
			Comment.content,
			Comment.creation,
		)
	)
	return first_row(query)


def popular_post_query(user: str, since: datetime, Post, Discussion, post_doctype: str):
	"""Posts of `post_doctype` made since `since` by someone other than `user`, in Spaces `user`
	can see, with their reaction counts, most reacted first. `Post` is the discussion itself or
	one of its replies."""
	Reaction = frappe.qb.DocType("GP Reaction")
	Project = frappe.qb.DocType("GP Project")
	Team = frappe.qb.DocType("GP Team")

	query = frappe.qb.from_(Reaction).join(Post).on(Reaction.reference_name == Post.name)
	if Post is not Discussion:
		query = query.join(Discussion).on(Post.reference_name == Discussion.name)
	reactions_count = Count(Reaction.name)
	query = (
		query.join(Project)
		.on(Discussion.project == Project.name)
		.left_join(Team)
		.on(Project.team == Team.name)
		.select(
			Discussion.title,
			Discussion.slug,
			Discussion.project,
			Project.title.as_("project_title"),
			Project.team,
			Team.title.as_("team_title"),
			reactions_count.as_("reactions_count"),
		)
		.where(
			(Reaction.reference_doctype == post_doctype)
			& (Post.creation >= since)
			& (Post.owner != user)
			& Project.archived_at.isnull()
		)
		.groupby(Post.name)
		.orderby(reactions_count, order=Order.desc)
		.orderby(Post.creation, order=Order.desc)
		.limit(1)
	)
	return apply_accessible_project_filter(query, Discussion.project, user)


def first_row(query):
	rows = query.run(as_dict=True)
	return rows[0] if rows else None


def format_notification_items(notifications, avatar_map, user: str):
	grouped_notifications = {}
	for notification in notifications:
		group_key = notification_group_key(notification)
		grouped_notifications.setdefault(group_key, []).append(notification)

	items = [
		format_notification_group(group, avatar_map, user)
		for group in sorted(
			grouped_notifications.values(),
			key=lambda group: str(group[0].creation or ""),
			reverse=True,
		)
	]
	return items[:MAX_DIGEST_ITEMS]


def format_notification_group(notifications, avatar_map, user: str):
	notification = notifications[0]
	item = format_notification_item(notification, avatar_map, user)
	if len(notifications) == 1:
		return item

	actor_labels = [
		avatar_context(row.from_user, row.from_user_full_name, avatar_map)["label"]
		for row in notifications
		if row.from_user or row.from_user_full_name
	]
	actor_summary = summarized_names(actor_labels) or "Someone"
	item["description"] = f"{actor_summary} sent {len(notifications)} updates. Latest: {item['description']}"
	return item


def format_notification_item(notification, avatar_map, user: str):
	title = notification.discussion_title or notification.task_title or notification.type
	description = html_to_text_preview(notification.message, 160) or notification.type
	metadata = location_text(notification.team_title, notification.project_title)
	return {
		"title": title or "Untitled",
		"description": description or "",
		"metadata": metadata,
		"url": get_signed_digest_url(user, notification_path(notification)),
		"avatar": avatar_context(notification.from_user, notification.from_user_full_name, avatar_map),
	}


def format_discussion_item(discussion, avatar_map, user: str):
	return {
		"title": discussion.title or "Untitled",
		"description": "",
		"metadata": activity_text(
			location_text(discussion.team_title, discussion.project_title),
			discussion.replies_count,
			discussion.reactions_count,
		),
		"unread_label": "New"
		if discussion.is_new
		else pluralize(discussion.unread_replies_count, "new reply", "new replies"),
		"url": get_signed_digest_url(user, discussion_path(discussion)),
		"avatar": avatar_context(discussion.owner, None, avatar_map),
	}


def format_highlight(post, avatar_map, user: str):
	author = avatar_context(post.owner, None, avatar_map)
	path = content_path(post.team, post.project, "discussion", post.discussion, post.slug)
	if path and post.get("comment"):
		path = f"{path}?comment={quote(str(post.comment))}"
	return {
		"title": post.title or "Untitled",
		"description": html_to_text_preview(post.content, 200) or "",
		"metadata": join_metadata(
			author["label"],
			location_text(post.team_title, post.project_title),
			pluralize(post.reactions_count, "reaction"),
		),
		"url": get_signed_digest_url(user, path),
		"avatar": author,
	}


def notification_group_key(notification):
	return (
		notification_path(notification),
		notification.discussion or notification.task or notification.name,
		notification.type,
	)


def notification_path(notification):
	if notification.discussion:
		return content_path(
			notification.team,
			notification.project,
			"discussion",
			notification.discussion,
			notification.discussion_slug,
		)
	if notification.task:
		return content_path(notification.team, notification.project, "tasks", notification.task)
	return "/g/notifications"


def discussion_path(discussion):
	return content_path(discussion.team, discussion.project, "discussion", discussion.name, discussion.slug)


def content_path(
	team: str | None, project: str | None, content_type: str, name: str, slug: str | None = None
):
	if not team or not project:
		return None

	segments = ["", "g", "community", team, "space", project]
	if content_type == "discussion":
		segments.extend(["discussion", name])
		if slug:
			segments.append(slug)
	else:
		segments.extend([content_type, name])
	return "/".join(quote(str(segment), safe="") for segment in segments)


def location_text(team_title: str | None, project_title: str | None):
	return " / ".join(part for part in [team_title, project_title] if part)


def activity_text(location: str, replies_count: int, reactions_count: int):
	return join_metadata(
		location,
		pluralize(replies_count, "reply", "replies") if replies_count else None,
		pluralize(reactions_count, "reaction") if reactions_count else None,
	)


def join_metadata(*parts: str | None):
	return " · ".join(part for part in parts if part)


def pluralize(count: int, singular: str, plural: str | None = None):
	label = singular if count == 1 else plural or f"{singular}s"
	return f"{count} {label}"


def summarized_names(names):
	unique_names = list(dict.fromkeys(name for name in names if name))
	if not unique_names:
		return ""
	if len(unique_names) == 1:
		return unique_names[0]
	if len(unique_names) == 2:
		return f"{unique_names[0]} and {unique_names[1]}"
	return f"{unique_names[0]} and {len(unique_names) - 1} others"


def get_digest_preferences_url(user: str):
	return get_signed_digest_url(user, DIGEST_PREFERENCES_REDIRECT)


def get_signed_digest_url(user: str, redirect: str | None):
	if not redirect:
		return None

	params = {
		"user": user,
		"redirect": redirect,
		"expires": add_to_date(now_datetime(), days=EMAIL_DIGEST_LINK_EXPIRES_DAYS).strftime(
			"%Y-%m-%d %H:%M:%S"
		),
	}
	return get_url(f"/api/method/gameplan.email_digest.open_digest_preferences?{get_signed_params(params)}")


def is_valid_digest_login_link(user: str, expires: str | None):
	if not user or not expires:
		show_invalid_digest_link()
		return False

	if get_datetime(expires) < now_datetime():
		show_invalid_digest_link()
		return False

	if not frappe.db.exists("User", {"name": user, "enabled": 1}):
		show_invalid_digest_link()
		return False

	return True


def show_invalid_digest_link():
	frappe.respond_as_web_page(
		_("Invalid Link"),
		_("This digest link is invalid or expired."),
	)


def get_safe_digest_redirect(redirect: str):
	if redirect.startswith("/g") and not redirect.startswith("//") and "\\" not in redirect:
		return redirect
	return DIGEST_PREFERENCES_REDIRECT


def get_digest_item_users(digest):
	users = {notification.from_user for notification in digest["notifications"] if notification.from_user}
	users.update(discussion.owner for discussion in digest["discussions"] if discussion.owner)
	if digest["highlight"]:
		users.add(digest["highlight"].owner)
	return users


def get_user_avatar_map(users):
	users = list({user for user in users if user})
	if not users:
		return {}

	avatar_map = {}
	user_rows = frappe.qb.get_query(
		"User",
		fields=["name", "full_name", "user_image"],
		filters=[["name", "in", users]],
	).run(as_dict=True)
	for row in user_rows:
		avatar_map[row.name] = {
			"label": row.full_name or row.name,
			"image": row.user_image,
		}

	profile_rows = frappe.qb.get_query(
		"GP User Profile",
		fields=["user", "full_name", "image"],
		filters=[["user", "in", users]],
	).run(as_dict=True)
	for row in profile_rows:
		avatar_map[row.user] = {
			"label": row.full_name or avatar_map.get(row.user, {}).get("label") or row.user,
			"image": row.image or avatar_map.get(row.user, {}).get("image"),
		}
	return avatar_map


def avatar_context(user, fallback_label, avatar_map):
	avatar = avatar_map.get(user, {}) if user else {}
	label = avatar.get("label") or fallback_label or user or "User"
	return {
		"label": label,
		"initials": initials_for(label),
		"url": absolute_image_url(avatar.get("image")),
	}


def absolute_image_url(image):
	if not image:
		return None
	if image.startswith(("http://", "https://", "data:")):
		return image

	path = image if image.startswith("/") else f"/{image}"
	# A mail client fetches images without a session, so a private file answers 403 and the
	# reader sees a broken image. The digest templates only fall back to initials when the URL
	# is missing, so drop the URL and let that fallback run.
	if path.startswith("/private/"):
		return None
	return get_url(path)


def initials_for(label):
	parts = [part for part in label.replace("@", " ").replace(".", " ").split() if part]
	return "".join(part[0].upper() for part in parts[:2]) or "U"
