# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# See license.txt

from contextlib import contextmanager
from datetime import date
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlparse

import frappe
from frappe.email.email_body import get_formatted_html
from frappe.utils import add_to_date, get_url, now_datetime
from frappe.utils.jinja import get_email_from_template

from gameplan.email_digest import (
	DIGEST_PREFERENCES_REDIRECT,
	absolute_image_url,
	get_due_profiles,
	get_safe_digest_redirect,
	get_unread_discussions,
	is_digest_due,
	is_valid_digest_login_link,
	open_digest_preferences,
	send_digest_for_profile,
)
from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import create_community, create_discussion, create_member, create_space


class TestEmailDigest(GameplanTestCase):
	"""On GameplanTestCase for its per-test rollback: this class had no tearDown at all,
	so every community, space, discussion and unread record it wrote stayed on the site
	and leaked into the next test method."""

	def setUp(self):
		super().setUp()
		self.user = create_member(f"digest-{frappe.generate_hash(length=8)}@example.com", "Digest Member")
		self.profile = frappe.get_doc("GP User Profile", {"user": self.user.name})
		self.profile.email_digest_frequency = "Weekly"
		self.profile.email_digest_day_of_week = "Monday"
		self.profile.email_digest_last_sent_on = None
		self.profile.save(ignore_permissions=True)

	def test_weekly_digest_is_due_after_seven_days(self):
		profile = frappe._dict(email_digest_frequency="Weekly", email_digest_last_sent_on=date(2026, 6, 1))

		self.assertFalse(is_digest_due(profile, date(2026, 6, 7)))
		self.assertTrue(is_digest_due(profile, date(2026, 6, 8)))

	def test_digest_is_due_only_on_configured_day_of_week(self):
		profile = frappe._dict(
			email_digest_frequency="Weekly",
			email_digest_day_of_week="Friday",
			email_digest_last_sent_on=None,
		)

		self.assertFalse(is_digest_due(profile, date(2026, 7, 2)))
		self.assertTrue(is_digest_due(profile, date(2026, 7, 3)))

	def test_digest_is_not_due_when_frequency_is_off(self):
		profile = frappe._dict(
			email_digest_frequency="Off",
			email_digest_day_of_week="Monday",
			email_digest_last_sent_on=None,
		)

		self.assertFalse(is_digest_due(profile, date(2026, 6, 30)))

	def test_longer_digest_frequencies_use_their_intervals(self):
		fortnightly = frappe._dict(
			email_digest_frequency="Fortnightly", email_digest_last_sent_on=date(2026, 6, 1)
		)
		monthly = frappe._dict(email_digest_frequency="Monthly", email_digest_last_sent_on=date(2026, 6, 1))

		self.assertFalse(is_digest_due(fortnightly, date(2026, 6, 14)))
		self.assertTrue(is_digest_due(fortnightly, date(2026, 6, 15)))
		self.assertFalse(is_digest_due(monthly, date(2026, 6, 30)))
		self.assertFalse(is_digest_due(monthly, date(2026, 7, 1)))
		self.assertTrue(is_digest_due(monthly, date(2026, 7, 6)))

	def test_get_due_profiles_ignores_profiles_scheduled_for_another_weekday(self):
		self.profile.email_digest_day_of_week = "Friday"
		self.profile.save(ignore_permissions=True)

		due_profiles = get_due_profiles(date(2026, 6, 30))

		self.assertNotIn(self.profile.name, [profile.name for profile in due_profiles])

	def test_get_due_profiles_ignores_profiles_sent_recently(self):
		self.profile.email_digest_last_sent_on = date(2026, 6, 25)
		self.profile.save(ignore_permissions=True)

		due_profiles = get_due_profiles(date(2026, 6, 30))

		self.assertNotIn(self.profile.name, [profile.name for profile in due_profiles])

	def test_send_digest_emails_unread_items_and_updates_last_sent_on(self):
		author = create_member(f"digest-author-{frappe.generate_hash(length=8)}@example.com", "Digest Author")
		author_profile = frappe.get_doc("GP User Profile", {"user": author.name})
		author_profile.image = "/files/digest-author.png"
		author_profile.save(ignore_permissions=True)
		team = create_community("Digest Team")
		frappe.db.set_value("GP Team", team.name, "image", "/files/digest-team.png", update_modified=False)
		project = create_space("Digest Space", team.name)
		discussion = create_discussion("Digest Discussion", project.name)
		frappe.db.set_value(
			"GP Discussion",
			discussion.name,
			{"owner": author.name, "last_post_by": author.name, "comments_count": 3},
			update_modified=False,
		)
		self.add_discussion_reactions(discussion, 2)
		frappe.get_doc(
			{
				"doctype": "GP Unread Record",
				"user": self.user.name,
				"discussion": discussion.name,
				"project": project.name,
				"is_unread": 1,
			}
		).insert(ignore_permissions=True)
		other_team = create_community("Digest Other Team")
		other_project = create_space("Digest Other Space", other_team.name)
		other_discussion = create_discussion("Digest Other Discussion", other_project.name)
		frappe.get_doc(
			{
				"doctype": "GP Unread Record",
				"user": self.user.name,
				"discussion": other_discussion.name,
				"project": other_project.name,
				"is_unread": 1,
			}
		).insert(ignore_permissions=True)
		frappe.get_doc(
			{
				"doctype": "GP Notification",
				"to_user": self.user.name,
				"type": "Mention",
				"message": "You were mentioned in the digest thread.",
				"discussion": discussion.name,
				"project": project.name,
				"team": team.name,
				"from_user": author.name,
			}
		).insert(ignore_permissions=True)
		frappe.get_doc(
			{
				"doctype": "GP Notification",
				"to_user": self.user.name,
				"type": "Mention",
				"message": "You were mentioned again in the digest thread.",
				"discussion": discussion.name,
				"project": project.name,
				"team": team.name,
				"from_user": author.name,
			}
		).insert(ignore_permissions=True)

		with patch("frappe.sendmail") as sendmail:
			send_digest_for_profile(self.profile, date(2026, 6, 30))

		sendmail.assert_called_once()
		email = sendmail.call_args.kwargs
		self.assertEqual(email["recipients"], [self.user.name])
		self.assertEqual(email["subject"], "Your Weekly Gameplan digest")
		self.assertEqual(email["template"], "email_digest")
		self.assertEqual(len(email["args"]["notifications"]), 1)
		self.assertEqual(email["args"]["notifications"][0]["description"].count("sent 2 updates"), 1)
		self.assertEqual(email["args"]["discussion_groups"][0]["title"], "Digest Team")

		message, text_content = get_email_from_template(email["template"], email["args"])
		self.assertIn("Digest Discussion", message)
		self.assertIn("You were mentioned", message)
		discussions_markup = message.split("Unread discussions", 1)[1]
		self.assertIn("gp-email-digest__brand", message)
		self.assertIn("gp-email-digest__brand-logo", message)
		self.assertIn("gp-email-digest__brand-name", message)
		self.assertIn("Gameplan", message)
		self.assertIn("/assets/gameplan/gameplan_logo_256.png", message)
		self.assertIn("Your weekly digest", message)
		self.assertIn("Your weekly digest", text_content)
		self.assertNotIn("Your Weekly Gameplan digest", message)
		self.assertIn("gp-email-digest__card", message)
		self.assertIn("gp-email-digest__site-url", message)
		self.assertIn(get_url(), message)
		self.assertIn("gp-email-digest__avatar-image", message)
		self.assertIn("gp-email-digest__avatar-content", message)
		self.assertNotIn("gp-email-digest__avatar-link", message)
		self.assertIn("gp-email-digest__content-link", message)
		self.assertIn(
			'<h3 class="gp-email-digest__section-title gp-email-digest__section-title--muted">'
			"Unread notifications</h3>",
			message,
		)
		self.assertIn("gp-email-digest__section-title--muted", message)
		self.assertIn("gp-email-digest__group-image", discussions_markup)
		self.assertIn("/files/digest-team.png", discussions_markup)
		self.assertIn("gp-email-digest__unread-label", discussions_markup)
		self.assertIn("2 unread", discussions_markup)
		self.assertNotIn("gp-email-digest__description", discussions_markup)
		self.assertNotIn("gp-email-digest__link", message)
		self.assertIn("Digest Space · 3 comments · 2 reactions", discussions_markup)
		self.assertIn("Open Gameplan", message)
		self.assertIn("Manage preferences", message)
		self.assertIn("gameplan.email_digest.open_digest_preferences", message)
		self.assertIn("_signature=", message)
		self.assert_signed_digest_url(email["args"]["open_gameplan_url"], "/g")
		self.assert_signed_digest_url(
			email["args"]["notifications"][0]["url"],
			f"/g/community/{team.name}/space/{project.name}/discussion/{discussion.name}/{discussion.slug}",
		)
		self.assert_signed_digest_url(
			email["args"]["discussion_groups"][0]["discussions"][0]["url"],
			f"/g/community/{team.name}/space/{project.name}/discussion/{discussion.name}/{discussion.slug}",
		)
		self.assertIn("Digest Author", message)
		self.assertIn("/files/digest-author.png", message)
		self.assertIn("Digest Discussion", text_content)
		self.assertIn("You were mentioned", text_content)
		self.assertNotIn("style=", message)
		self.assertIn("font-family:Inter", get_formatted_html(email["subject"], message))
		self.assertIn("text-align:center", get_formatted_html(email["subject"], message))
		self.assertIn("text-align:left", get_formatted_html(email["subject"], message))
		self.assertIn("padding: 0 16px", get_formatted_html(email["subject"], message))
		self.assertIn("margin-bottom:16px", get_formatted_html(email["subject"], message))
		self.assertIn("line-height:24px", get_formatted_html(email["subject"], message))
		self.assertIn("vertical-align:middle", get_formatted_html(email["subject"], message))
		self.assertIn("float:right", get_formatted_html(email["subject"], message))
		self.assertIn("padding:10px 0", get_formatted_html(email["subject"], message))
		self.assertIn("font-size:15px", get_formatted_html(email["subject"], message))
		self.assertIn("width:48px", get_formatted_html(email["subject"], message))
		self.assertIn("height:20px", get_formatted_html(email["subject"], message))
		self.assertIn("width:20px", get_formatted_html(email["subject"], message))
		self.assertIn("width:28px", get_formatted_html(email["subject"], message))
		self.assertIn("border-radius:4px", get_formatted_html(email["subject"], message))
		self.assertIn("margin:0 8px 0 0", get_formatted_html(email["subject"], message))
		self.assertIn("border-bottom:1px solid #e5e7eb", get_formatted_html(email["subject"], message))
		self.assertIn("margin-bottom:8px", get_formatted_html(email["subject"], message))
		self.assertIn("margin-top:40px", get_formatted_html(email["subject"], message))
		self.assert_signed_digest_url(
			email["args"]["preferences_url"], "/g/notifications?settings=notifications"
		)
		self.assertEqual(
			frappe.db.get_value("GP User Profile", self.profile.name, "email_digest_last_sent_on"),
			date(2026, 6, 30),
		)

	def test_private_images_are_dropped_so_the_digest_shows_initials(self):
		"""A mail client fetches images with no session, so a private file answers 403. Without
		a URL the templates take their initials branch instead of rendering a broken image."""
		message, discussions_markup = self.render_digest_with_images(
			"/private/files/digest-author.png", "/private/files/digest-team.png"
		)

		self.assertNotIn("/private/files/", message)
		self.assertNotIn("gp-email-digest__avatar-image", message)
		self.assertNotIn('class="gp-email-digest__group-image"', discussions_markup)
		self.assertIn("gp-email-digest__avatar-fallback", message)
		self.assertIn("gp-email-digest__group-fallback", discussions_markup)

	def test_public_images_are_still_rendered_in_the_digest(self):
		message, discussions_markup = self.render_digest_with_images(
			"/files/digest-author.png", "/files/digest-team.png"
		)

		self.assertIn("gp-email-digest__avatar-image", message)
		self.assertIn(get_url("/files/digest-author.png"), message)
		self.assertIn('class="gp-email-digest__group-image"', discussions_markup)
		self.assertIn(get_url("/files/digest-team.png"), discussions_markup)
		self.assertNotIn("gp-email-digest__avatar-fallback", message)
		self.assertNotIn("gp-email-digest__group-fallback", discussions_markup)

	def test_absolute_image_url_keeps_public_paths_and_drops_private_ones(self):
		self.assertEqual(absolute_image_url("/files/avatar.png"), get_url("/files/avatar.png"))
		self.assertEqual(absolute_image_url("files/avatar.png"), get_url("/files/avatar.png"))
		self.assertIsNone(absolute_image_url("/private/files/avatar.png"))
		self.assertIsNone(absolute_image_url("private/files/avatar.png"))
		self.assertIsNone(absolute_image_url(None))

	def test_unread_discussions_are_sorted_by_popularity(self):
		team = create_community("Digest Popularity Team")
		project = create_space("Digest Popularity Space", team.name)
		self.create_unread_discussion(project.name, "Quiet Recent Discussion", 0, "2026-06-30 10:00:00")
		self.create_unread_discussion(
			project.name,
			"Comment Heavy Discussion",
			7,
			"2026-06-29 10:00:00",
		)
		reaction_heavy = self.create_unread_discussion(
			project.name,
			"Reaction Heavy Discussion",
			1,
			"2026-06-28 10:00:00",
		)
		mixed = self.create_unread_discussion(
			project.name, "Mixed Popular Discussion", 4, "2026-06-27 10:00:00"
		)
		self.add_discussion_reactions(reaction_heavy, 8)
		self.add_discussion_reactions(mixed, 2)
		self.add_comment_reactions(mixed, 4)
		frappe.db.set_value(
			"GP Discussion",
			mixed.name,
			"comments_count",
			4,
			update_modified=False,
		)

		discussions = get_unread_discussions(self.user.name)

		self.assertEqual(
			[discussion.title for discussion in discussions[:4]],
			[
				"Mixed Popular Discussion",
				"Reaction Heavy Discussion",
				"Comment Heavy Discussion",
				"Quiet Recent Discussion",
			],
		)
		self.assertEqual(discussions[0].popularity_score, 10)

	def test_unread_discussions_are_sorted_by_community_popularity(self):
		aggregate_team = create_community("Digest Aggregate Team")
		aggregate_project = create_space("Digest Aggregate Space", aggregate_team.name)
		single_team = create_community("Digest Single Team")
		single_project = create_space("Digest Single Space", single_team.name)
		self.create_unread_discussion(
			aggregate_project.name,
			"Aggregate Popular One",
			7,
			"2026-06-29 10:00:00",
		)
		self.create_unread_discussion(
			aggregate_project.name,
			"Aggregate Popular Two",
			5,
			"2026-06-28 10:00:00",
		)
		self.create_unread_discussion(
			single_project.name,
			"Single Popular Discussion",
			10,
			"2026-06-30 10:00:00",
		)

		discussions = get_unread_discussions(self.user.name)

		self.assertEqual(
			[discussion.title for discussion in discussions[:3]],
			[
				"Aggregate Popular One",
				"Aggregate Popular Two",
				"Single Popular Discussion",
			],
		)

	def test_unread_discussions_are_balanced_across_popular_communities(self):
		dominant_team = create_community("Digest Dominant Team")
		dominant_project = create_space("Digest Dominant Space", dominant_team.name)
		secondary_team = create_community("Digest Secondary Team")
		secondary_project = create_space("Digest Secondary Space", secondary_team.name)
		tertiary_team = create_community("Digest Tertiary Team")
		tertiary_project = create_space("Digest Tertiary Space", tertiary_team.name)
		for index, score in enumerate([100, 90, 80, 70, 60], start=1):
			self.create_unread_discussion(
				dominant_project.name,
				f"Dominant Discussion {index}",
				score,
				f"2026-06-2{index} 10:00:00",
			)
		self.create_unread_discussion(
			secondary_project.name,
			"Secondary Discussion",
			20,
			"2026-06-27 10:00:00",
		)
		self.create_unread_discussion(
			tertiary_project.name,
			"Tertiary Discussion",
			10,
			"2026-06-26 10:00:00",
		)

		discussions = get_unread_discussions(self.user.name)

		self.assertEqual(
			[discussion.title for discussion in discussions[:7]],
			[
				"Dominant Discussion 1",
				"Dominant Discussion 2",
				"Dominant Discussion 3",
				"Secondary Discussion",
				"Tertiary Discussion",
				"Dominant Discussion 4",
				"Dominant Discussion 5",
			],
		)

	def test_send_digest_skips_email_when_there_are_no_unread_items(self):
		with patch("frappe.sendmail") as sendmail:
			send_digest_for_profile(self.profile, date(2026, 6, 30))

		sendmail.assert_not_called()
		self.assertEqual(
			frappe.db.get_value("GP User Profile", self.profile.name, "email_digest_last_sent_on"),
			date(2026, 6, 30),
		)

	def render_digest_with_images(self, avatar, community_image):
		"""Render the digest for a member with one unread notification and one unread discussion,
		both from an author whose avatar is `avatar`, in a community whose image is `community_image`.

		Returns the rendered HTML and the part of it after the "Unread discussions" heading, since
		the community image only appears there.
		"""
		author = create_member(f"digest-author-{frappe.generate_hash(length=8)}@example.com", "Digest Author")
		author_profile = frappe.get_doc("GP User Profile", {"user": author.name})
		author_profile.image = avatar
		author_profile.save(ignore_permissions=True)
		team = create_community("Digest Image Team")
		frappe.db.set_value("GP Team", team.name, "image", community_image, update_modified=False)
		project = create_space("Digest Image Space", team.name)
		discussion = create_discussion("Digest Image Discussion", project.name)
		frappe.db.set_value(
			"GP Discussion",
			discussion.name,
			{"owner": author.name, "last_post_by": author.name},
			update_modified=False,
		)
		frappe.get_doc(
			{
				"doctype": "GP Unread Record",
				"user": self.user.name,
				"discussion": discussion.name,
				"project": project.name,
				"is_unread": 1,
			}
		).insert(ignore_permissions=True)
		frappe.get_doc(
			{
				"doctype": "GP Notification",
				"to_user": self.user.name,
				"type": "Mention",
				"message": "You were mentioned in the digest thread.",
				"discussion": discussion.name,
				"project": project.name,
				"team": team.name,
				"from_user": author.name,
			}
		).insert(ignore_permissions=True)

		with patch("frappe.sendmail") as sendmail:
			send_digest_for_profile(self.profile, date(2026, 6, 30))

		sendmail.assert_called_once()
		email = sendmail.call_args.kwargs
		message, _text_content = get_email_from_template(email["template"], email["args"])
		return message, message.split("Unread discussions", 1)[1]

	def create_unread_discussion(self, project, title, comments_count, last_post_at):
		discussion = create_discussion(title, project)
		frappe.db.set_value(
			"GP Discussion",
			discussion.name,
			{"comments_count": comments_count, "last_post_at": last_post_at},
			update_modified=False,
		)
		frappe.get_doc(
			{
				"doctype": "GP Unread Record",
				"user": self.user.name,
				"discussion": discussion.name,
				"project": project,
				"is_unread": 1,
			}
		).insert(ignore_permissions=True)
		return discussion

	def add_discussion_reactions(self, discussion, count):
		discussion = frappe.get_doc("GP Discussion", discussion.name)
		for index in range(count):
			discussion.append("reactions", self.reaction_row(index))
		discussion.save(ignore_permissions=True)

	def add_comment_reactions(self, discussion, count):
		comment = frappe.get_doc(
			{
				"doctype": "GP Comment",
				"reference_doctype": "GP Discussion",
				"reference_name": discussion.name,
				"content": "Comment with reactions",
			}
		).insert(ignore_permissions=True)
		for index in range(count):
			comment.append("reactions", self.reaction_row(index))
		comment.save(ignore_permissions=True)

	def reaction_row(self, index):
		return {
			"emoji": ":thumbsup:",
			"user": f"digest-reaction-{index}-{frappe.generate_hash(length=8)}@example.com",
		}

	def assert_signed_digest_url(self, url, redirect):
		query = parse_qs(urlparse(url).query)
		self.assertIn("gameplan.email_digest.open_digest_preferences", url)
		self.assertEqual(query["user"], [self.user.name])
		self.assertEqual(query["redirect"], [redirect])
		self.assertIn("expires", query)
		self.assertIn("_signature", query)


def as_expires(moment):
	return moment.strftime("%Y-%m-%d %H:%M:%S")


class TestDigestLoginLink(GameplanTestCase):
	"""Pins the gates behind `open_digest_preferences`, which is `allow_guest` and logs a user in.

	`verify_request`'s HMAC is the primary defense — nobody forges a link without the site
	secret. These cover the layer behind it, so a refactor cannot silently drop the expiry
	check, the `enabled` check or the redirect allowlist. The two regressions they exist to
	catch: an expired digest link working forever, and an offboarded user logging in from an
	old digest email.
	"""

	def setUp(self):
		super().setUp()
		self.link_user = create_member(
			f"digest-link-{frappe.generate_hash(length=8)}@example.com", "Link User"
		)
		self.future = as_expires(add_to_date(now_datetime(), days=1))
		self.past = as_expires(add_to_date(now_datetime(), days=-1))

	@contextmanager
	def isolated_response(self):
		"""Swap in a throwaway `frappe.local.response`.

		Both branches under test write to the shared response — `respond_as_web_page` on
		rejection, the redirect keys on success — and that dict outlives the test.
		"""
		previous = frappe.local.response
		frappe.local.response = frappe._dict()
		try:
			yield frappe.local.response
		finally:
			frappe.local.response = previous

	def test_link_for_an_enabled_user_before_expiry_is_valid(self):
		with self.isolated_response():
			self.assertIs(is_valid_digest_login_link(self.link_user.name, self.future), True)

	def test_link_is_rejected_when_either_user_or_expiry_is_missing(self):
		"""A missing field is rejected outright, before the clock is ever consulted.

		Asserting the clock goes untouched is the point, not incidental strictness. A
		missing `expires` would otherwise reach `get_datetime(None) < now_datetime()`,
		which compares "now" against a "now" sampled microseconds later — it rejects by
		accident, and only because evaluating the left side takes non-zero time.
		"""
		for user, expires in ((None, self.future), (self.link_user.name, None), (None, None)):
			with (
				self.subTest(user=user, expires=expires),
				self.isolated_response(),
				patch("gameplan.email_digest.now_datetime") as clock,
			):
				self.assertIs(is_valid_digest_login_link(user, expires), False)
				clock.assert_not_called()

	def test_expired_link_is_rejected(self):
		with self.isolated_response():
			self.assertIs(is_valid_digest_login_link(self.link_user.name, self.past), False)

	def test_link_is_valid_up_to_and_including_its_expiry_moment(self):
		# Truncated to the second because that is the resolution `get_signed_digest_url`
		# writes; a microsecond of drift would make this an expired-link test by accident.
		frozen = now_datetime().replace(microsecond=0)

		with self.isolated_response(), patch("gameplan.email_digest.now_datetime", return_value=frozen):
			self.assertIs(is_valid_digest_login_link(self.link_user.name, as_expires(frozen)), True)

	def test_link_for_a_disabled_user_is_rejected(self):
		frappe.db.set_value("User", self.link_user.name, "enabled", 0, update_modified=False)

		with self.isolated_response():
			self.assertIs(is_valid_digest_login_link(self.link_user.name, self.future), False)

	def test_link_for_a_deleted_user_is_rejected(self):
		with self.isolated_response():
			self.assertIs(is_valid_digest_login_link("digest-ghost@example.com", self.future), False)

	def test_in_app_redirect_is_preserved(self):
		self.assertEqual(get_safe_digest_redirect("/g/spaces"), "/g/spaces")

	def test_offsite_redirects_fall_back_to_the_preferences_page(self):
		hostile = (
			"//evil.example.com",
			"https://evil.example.com",
			"/g\\evil.example.com",
			"\\\\evil.example.com",
			"/other",
		)

		for redirect in hostile:
			with self.subTest(redirect=redirect):
				self.assertEqual(get_safe_digest_redirect(redirect), DIGEST_PREFERENCES_REDIRECT)

	def test_endpoint_stays_reachable_without_a_session(self):
		# The link is opened from an email client, so losing allow_guest would break every
		# digest link for logged-out readers.
		with self.as_user("Guest"):
			frappe.is_whitelisted(open_digest_preferences)

	def test_signed_valid_link_logs_the_user_in_and_redirects(self):
		response, login_manager = self.open_preferences(
			verified=True, expires=self.future, redirect="/g/spaces"
		)

		login_manager.login_as.assert_called_once_with(self.link_user.name)
		self.assertEqual(response["type"], "redirect")
		self.assertEqual(response["location"], "/g/spaces")

	def test_unsigned_request_does_not_log_the_user_in(self):
		response, login_manager = self.open_preferences(verified=False, expires=self.future)

		login_manager.login_as.assert_not_called()
		self.assertNotIn("location", response)

	def test_invalid_link_does_not_log_the_user_in(self):
		response, login_manager = self.open_preferences(verified=True, expires=self.past)

		login_manager.login_as.assert_not_called()
		self.assertNotIn("location", response)

	def open_preferences(self, verified, expires, redirect=DIGEST_PREFERENCES_REDIRECT):
		"""Call the endpoint with the signature check stubbed and the login manager faked.

		Returns `(response, login_manager)` to assert on.
		"""
		login_manager = MagicMock()
		with (
			self.isolated_response() as response,
			patch("gameplan.email_digest.verify_request", return_value=verified),
			patch.object(frappe.local, "login_manager", login_manager, create=True),
		):
			open_digest_preferences(user=self.link_user.name, redirect=redirect, expires=expires)

		return response, login_manager
