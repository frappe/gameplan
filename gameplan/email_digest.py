# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

from datetime import date
from urllib.parse import quote

import frappe
from frappe import _
from frappe.query_builder.functions import Count
from frappe.utils import add_to_date, get_datetime, get_url, getdate, now_datetime, nowdate
from frappe.utils.verified_command import get_signed_params, verify_request

from gameplan.permissions import apply_accessible_project_filter
from gameplan.utils import html_to_text_preview

EMAIL_DIGEST_FREQUENCY_DAYS = {
	"Weekly": 7,
	"Fortnightly": 14,
	"Monthly": 30,
}
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
DIGEST_DISCUSSIONS_PER_COMMUNITY = 3
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
			["email_digest_frequency", "in", list(EMAIL_DIGEST_FREQUENCY_DAYS)],
		],
	).run(as_dict=True)
	return [profile for profile in profiles if is_digest_due(profile, today)]


def is_digest_due(profile, today: date | None = None):
	frequency = profile.email_digest_frequency
	if frequency not in EMAIL_DIGEST_FREQUENCY_DAYS:
		return False

	today = today or getdate(nowdate())
	if not is_digest_scheduled_for_today(profile, today):
		return False

	last_sent_on = getdate(profile.email_digest_last_sent_on) if profile.email_digest_last_sent_on else None
	if not last_sent_on:
		return True

	return (today - last_sent_on).days >= EMAIL_DIGEST_FREQUENCY_DAYS[frequency]


def is_digest_scheduled_for_today(profile, today: date):
	day_of_week = get_digest_day_of_week(profile)
	return today.weekday() == EMAIL_DIGEST_DAYS_OF_WEEK[day_of_week]


def get_digest_day_of_week(profile):
	day_of_week = profile.get("email_digest_day_of_week")
	if day_of_week in EMAIL_DIGEST_DAYS_OF_WEEK:
		return day_of_week
	return DEFAULT_EMAIL_DIGEST_DAY_OF_WEEK


def send_digest_for_profile(profile, today: date | None = None):
	today = today or getdate(nowdate())
	digest = build_digest(profile.user)

	if has_digest_items(digest):
		frappe.sendmail(
			recipients=[profile.user],
			subject=get_digest_subject(profile),
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


def build_digest(user: str):
	return {
		"notifications": get_unread_notifications(user),
		"discussions": get_unread_discussions(user),
	}


def has_digest_items(digest):
	return bool(digest["notifications"] or digest["discussions"])


def get_digest_subject(profile):
	return f"Your {profile.email_digest_frequency} Gameplan digest"


def get_digest_email_context(profile, digest):
	avatar_map = get_user_avatar_map(get_digest_item_users(digest))
	discussion_groups = format_discussion_groups(digest["discussions"], avatar_map, profile.user)
	return {
		"frequency": profile.email_digest_frequency,
		"logo_url": get_url(GAMEPLAN_LOGO_PATH),
		"site_url": get_url(),
		"open_gameplan_url": get_signed_digest_url(profile.user, "/g"),
		"preferences_url": get_digest_preferences_url(profile.user),
		"notifications": format_notification_items(digest["notifications"], avatar_map, profile.user),
		"discussion_groups": discussion_groups,
		"discussions": [discussion for group in discussion_groups for discussion in group["discussions"]],
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


def get_unread_notifications(user: str):
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
		filters={"to_user": user, "read": 0},
		order_by="creation desc",
		limit=MAX_DIGEST_ITEMS,
	).run(as_dict=True)


def get_unread_discussions(user: str):
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
			Discussion.last_post_at,
			Discussion.last_post_by,
			Discussion.comments_count,
			Project.title.as_("project_title"),
			Project.team,
			Team.title.as_("team_title"),
			Team.image.as_("team_image"),
			Count(UnreadRecord.name).as_("unread_count"),
		)
		.where((UnreadRecord.user == user) & (UnreadRecord.is_unread == 1) & Project.archived_at.isnull())
		.groupby(Discussion.name)
	)
	query = apply_accessible_project_filter(query, Discussion.project, user)
	return get_popular_discussions(query.run(as_dict=True))


def get_popular_discussions(discussions):
	discussion_names = [discussion.name for discussion in discussions]
	discussion_reactions = get_discussion_reaction_counts(discussion_names)
	comment_reactions = get_comment_reaction_counts(discussion_names)

	for discussion in discussions:
		discussion_name = str(discussion.name)
		discussion.comments_count = discussion.comments_count or 0
		discussion.reactions_count = discussion_reactions.get(discussion_name, 0) + comment_reactions.get(
			discussion_name, 0
		)
		discussion.popularity_score = discussion.comments_count + discussion.reactions_count

	return select_balanced_popular_discussions(discussions)


def select_balanced_popular_discussions(discussions):
	groups = get_discussions_by_group(discussions)
	ordered_groups = sorted(groups.values(), key=discussion_group_sort_key, reverse=True)
	for group in ordered_groups:
		group["discussions"].sort(key=discussion_sort_key, reverse=True)

	selected = []
	selected_names = set()
	for group in ordered_groups:
		for discussion in group["discussions"][:DIGEST_DISCUSSIONS_PER_COMMUNITY]:
			add_selected_discussion(selected, selected_names, discussion)
			if len(selected) == MAX_DIGEST_ITEMS:
				return selected

	remaining_discussions = [
		discussion
		for group in ordered_groups
		for discussion in group["discussions"][DIGEST_DISCUSSIONS_PER_COMMUNITY:]
	]
	for discussion in sorted(remaining_discussions, key=discussion_sort_key, reverse=True):
		add_selected_discussion(selected, selected_names, discussion)
		if len(selected) == MAX_DIGEST_ITEMS:
			return selected

	return selected


def get_discussions_by_group(discussions):
	groups = {}
	for discussion in discussions:
		group_key = get_discussion_group_key(discussion)
		group = groups.setdefault(
			group_key,
			{
				"title": discussion.team_title or "",
				"popularity_score": 0,
				"discussions": [],
			},
		)
		group["popularity_score"] += discussion.popularity_score
		group["discussions"].append(discussion)
	return groups


def add_selected_discussion(selected, selected_names, discussion):
	if discussion.name in selected_names:
		return
	selected.append(discussion)
	selected_names.add(discussion.name)


def discussion_group_sort_key(group):
	return (group["popularity_score"], group["title"])


def discussion_sort_key(discussion):
	return (
		discussion.popularity_score,
		str(discussion.last_post_at or ""),
		str(discussion.name),
	)


def get_discussion_reaction_counts(discussion_names):
	if not discussion_names:
		return {}

	Reaction = frappe.qb.DocType("GP Reaction")
	rows = (
		frappe.qb.from_(Reaction)
		.select(Reaction.parent, Count(Reaction.name).as_("count"))
		.where((Reaction.parenttype == "GP Discussion") & Reaction.parent.isin(discussion_names))
		.groupby(Reaction.parent)
	).run(as_dict=True)
	return {str(row.parent): row.count for row in rows}


def get_comment_reaction_counts(discussion_names):
	if not discussion_names:
		return {}

	Reaction = frappe.qb.DocType("GP Reaction")
	Comment = frappe.qb.DocType("GP Comment")
	rows = (
		frappe.qb.from_(Reaction)
		.join(Comment)
		.on(Reaction.parent == Comment.name)
		.select(Comment.reference_name.as_("discussion"), Count(Reaction.name).as_("count"))
		.where(
			(Reaction.parenttype == "GP Comment")
			& (Comment.reference_doctype == "GP Discussion")
			& Comment.reference_name.isin(discussion_names)
			& Comment.deleted_at.isnull()
		)
		.groupby(Comment.reference_name)
	).run(as_dict=True)
	return {str(row.discussion): row.count for row in rows}


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


def format_discussion_groups(discussions, avatar_map, user: str):
	groups = {}
	for discussion in discussions:
		group_key = get_discussion_group_key(discussion)
		group = groups.setdefault(
			group_key,
			{
				"title": discussion.team_title or "Other discussions",
				"image_url": absolute_image_url(discussion.team_image),
				"initials": initials_for(discussion.team_title or "Other discussions"),
				"popularity_score": 0,
				"discussions": [],
			},
		)
		group["popularity_score"] += discussion.popularity_score
		group["discussions"].append(format_discussion_item(discussion, avatar_map, user))

	return sorted(
		groups.values(),
		key=lambda group: (group["popularity_score"], group["title"]),
		reverse=True,
	)


def format_discussion_item(discussion, avatar_map, user: str):
	metadata = activity_text(discussion.project_title, discussion.comments_count, discussion.reactions_count)
	last_post_by = discussion.last_post_by or discussion.owner
	return {
		"title": discussion.title or "Untitled",
		"description": "",
		"metadata": metadata,
		"unread_label": f"{discussion.unread_count} unread",
		"url": get_signed_digest_url(user, discussion_path(discussion)),
		"avatar": avatar_context(last_post_by, None, avatar_map),
	}


def notification_group_key(notification):
	return (
		notification_path(notification),
		notification.discussion or notification.task or notification.name,
		notification.type,
	)


def get_discussion_group_key(discussion):
	return discussion.team or "__no_community__"


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


def activity_text(project_title: str | None, comments_count: int, reactions_count: int):
	parts = [project_title] if project_title else []
	if comments_count:
		parts.append(pluralize(comments_count, "comment"))
	if reactions_count:
		parts.append(pluralize(reactions_count, "reaction"))
	return " · ".join(parts)


def pluralize(count: int, singular: str):
	label = singular if count == 1 else f"{singular}s"
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
	users.update(
		(discussion.last_post_by or discussion.owner)
		for discussion in digest["discussions"]
		if discussion.last_post_by or discussion.owner
	)
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
