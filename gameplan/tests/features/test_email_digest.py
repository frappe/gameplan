# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# See license.txt

from contextlib import contextmanager
from datetime import date
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlparse

import frappe
from frappe.email.email_body import get_formatted_html
from frappe.utils import add_to_date, get_url, getdate, now_datetime
from frappe.utils.jinja import get_email_from_template

from gameplan.email_digest import (
	DIGEST_PREFERENCES_REDIRECT,
	absolute_image_url,
	build_digest,
	get_digest_period_start,
	get_due_profiles,
	get_safe_digest_redirect,
	is_digest_due,
	is_valid_digest_login_link,
	open_digest_preferences,
	send_digest_for_profile,
)
from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import (
	create_comment,
	create_community,
	create_discussion,
	create_member,
	create_space,
	set_owner,
)

LONG_AGO = "2022-10-27 12:00:00"


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
		self.today = getdate()

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

	def test_old_popular_discussions_with_no_new_activity_are_left_out(self):
		"""The report that started this: a weekly digest led with unread review threads from
		2022 that had hundreds of reactions and no post in years."""
		project = self.create_project("Digest Reviews")
		old = self.create_unread_discussion(project, "Reflections for Q2 22", created=LONG_AGO)
		self.add_reactions("GP Discussion", old.name, 20, created=LONG_AGO)
		for _index in range(5):
			self.add_reply(old, created=LONG_AGO)
		self.create_unread_discussion(project, "Planning this week")

		digest = self.build_digest()

		self.assertEqual([discussion.title for discussion in digest["discussions"]], ["Planning this week"])
		self.assertIsNone(digest["highlight"])

	def test_discussions_are_ranked_by_this_weeks_activity(self):
		"""All-time totals do not count. An old thread with a long history and two new replies
		ranks below a new thread that got three replies this week. A reply counts for more than
		a reaction, so those two replies also beat a new thread with two reactions."""
		project = self.create_project("Digest Ranking")
		revived = self.create_unread_discussion(project, "Old thread with new replies", created=LONG_AGO)
		self.add_reactions("GP Discussion", revived.name, 30, created=LONG_AGO)
		self.add_reply(revived)
		self.add_reply(revived)
		busy = self.create_unread_discussion(project, "Busy new thread")
		for _index in range(3):
			self.add_reply(busy)
		liked = self.create_unread_discussion(project, "Liked new thread")
		self.add_reactions("GP Discussion", liked.name, 2)
		self.create_unread_discussion(project, "Quiet new thread")

		context = self.render_context()

		self.assertEqual(
			[(item["title"], item["unread_label"]) for item in context["discussions"]],
			[
				("Busy new thread", "New"),
				("Old thread with new replies", "2 new replies"),
				("Liked new thread", "New"),
				("Quiet new thread", "New"),
			],
		)
		self.assertEqual(
			context["discussions"][0]["metadata"], "Digest Ranking Team / Digest Ranking · 3 replies"
		)
		self.assertEqual(
			context["discussions"][1]["metadata"], "Digest Ranking Team / Digest Ranking · 2 replies"
		)

	def test_most_popular_post_of_the_week_leads_the_digest(self):
		"""The highlight is the post or reply with the most reactions this week. The reader's
		own posts are left out, and so is a post with too few reactions to call it popular."""
		project = self.create_project("Digest Highlight")
		author = create_member(
			f"digest-author-{frappe.generate_hash(length=8)}@example.com", "Popular Author"
		)
		discussion = self.create_unread_discussion(project, "Launch plan")
		self.add_reactions("GP Discussion", discussion.name, 3)
		reply = self.add_reply(discussion, content="<p>We ship on Friday.</p>", owner=author)
		self.add_reactions("GP Comment", reply.name, 5)
		own_post = self.create_unread_discussion(project, "My own post")
		set_owner(own_post, self.user.name)
		frappe.db.delete("GP Unread Record", {"user": self.user.name, "discussion": own_post.name})
		self.add_reactions("GP Discussion", own_post.name, 9)
		barely = self.create_unread_discussion(project, "Barely noticed")
		self.add_reactions("GP Discussion", barely.name, 2)

		context = self.render_context()

		highlight = context["highlight"]
		self.assertEqual(highlight["title"], "Launch plan")
		self.assertEqual(highlight["description"], "We ship on Friday.")
		self.assertEqual(
			highlight["metadata"], "Popular Author · Digest Highlight Team / Digest Highlight · 5 reactions"
		)
		self.assert_signed_digest_url(
			highlight["url"],
			f"/g/community/{project.team}/space/{project.name}/discussion/{discussion.name}/{discussion.slug}"
			f"?comment={reply.name}",
		)
		# The highlight's discussion is not repeated in the list below it.
		self.assertNotIn("Launch plan", [item["title"] for item in context["discussions"]])

	def test_only_this_weeks_mentions_and_quotes_are_included(self):
		project = self.create_project("Digest Notifications")
		discussion = create_discussion("Digest Notification Discussion", project.name)
		old = self.add_notification(discussion, project, "An old mention.")
		self.backdate("GP Notification", old.name, LONG_AGO)
		self.add_notification(discussion, project, "A mention this week.")
		self.add_notification(discussion, project, "A quote this week.", type="Rich Quote")
		self.add_notification(discussion, project, "A reaction this week.", type="Reaction")

		digest = self.build_digest()

		self.assertEqual(
			sorted(row.message for row in digest["notifications"]),
			["A mention this week.", "A quote this week."],
		)
		# The mention already points at the discussion, so the list does not repeat it.
		self.assertNotIn(discussion.name, [row.name for row in digest["discussions"]])

	def test_send_digest_skips_email_when_nothing_is_new_this_week(self):
		project = self.create_project("Digest Quiet")
		self.create_unread_discussion(project, "Unread but old", created=LONG_AGO)

		with patch("frappe.sendmail") as sendmail:
			send_digest_for_profile(self.profile, self.today)

		sendmail.assert_not_called()
		self.assertEqual(
			frappe.db.get_value("GP User Profile", self.profile.name, "email_digest_last_sent_on"),
			self.today,
		)

	def test_send_digest_emails_this_weeks_items_and_updates_last_sent_on(self):
		author = create_member(f"digest-author-{frappe.generate_hash(length=8)}@example.com", "Digest Author")
		frappe.db.set_value("GP User Profile", {"user": author.name}, "image", "/files/digest-author.png")
		project = self.create_project("Digest Space")
		discussion = self.create_unread_discussion(project, "Digest Discussion")
		set_owner(discussion, author)
		self.add_reply(discussion)
		self.add_reactions("GP Discussion", discussion.name, 2)
		mentioned_in = create_discussion("Digest Mention Discussion", project.name)
		self.add_notification(mentioned_in, project, "You were mentioned in the digest thread.", author)
		self.add_notification(mentioned_in, project, "You were mentioned again in the digest thread.", author)

		with patch("frappe.sendmail") as sendmail:
			send_digest_for_profile(self.profile, self.today)

		sendmail.assert_called_once()
		email = sendmail.call_args.kwargs
		self.assertEqual(email["recipients"], [self.user.name])
		self.assertEqual(email["subject"], "Your Weekly Gameplan digest")
		self.assertEqual(email["template"], "email_digest")
		self.assertEqual(len(email["args"]["notifications"]), 1)
		self.assertEqual(email["args"]["notifications"][0]["description"].count("sent 2 updates"), 1)

		message, text_content = get_email_from_template(email["template"], email["args"])
		discussions_markup = message.split("New this week", 1)[1]
		self.assertIn("Your weekly digest", message)
		self.assertIn("Your weekly digest", text_content)
		self.assertIn("/assets/gameplan/gameplan_logo_256.png", message)
		self.assertIn(get_url(), message)
		self.assertIn("Mentions and quotes</h3>", message)
		self.assertIn("You were mentioned", message)
		self.assertIn("Digest Discussion", discussions_markup)
		self.assertIn("gp-email-digest__unread-label", discussions_markup)
		self.assertIn("Digest Space Team / Digest Space · 1 reply · 2 reactions", discussions_markup)
		self.assertIn(get_url("/files/digest-author.png"), discussions_markup)
		self.assertNotIn("Most popular this week", message)
		self.assertIn("Open Gameplan", message)
		self.assertIn("Manage preferences", message)
		self.assertIn("Digest Discussion", text_content)
		self.assertIn("New this week", text_content)
		self.assertNotIn("style=", message)
		formatted = get_formatted_html(email["subject"], message)
		self.assertIn("font-family:Inter", formatted)
		self.assertIn("float:right", formatted)
		self.assertIn("width:48px", formatted)
		self.assert_signed_digest_url(email["args"]["open_gameplan_url"], "/g")
		self.assert_signed_digest_url(
			email["args"]["discussions"][0]["url"],
			f"/g/community/{project.team}/space/{project.name}/discussion/{discussion.name}/{discussion.slug}",
		)
		self.assert_signed_digest_url(email["args"]["preferences_url"], DIGEST_PREFERENCES_REDIRECT)
		self.assertEqual(
			frappe.db.get_value("GP User Profile", self.profile.name, "email_digest_last_sent_on"),
			self.today,
		)

	def test_private_images_are_dropped_so_the_digest_shows_initials(self):
		"""A mail client fetches images with no session, so a private file answers 403. Without
		a URL the templates take their initials branch instead of rendering a broken image."""
		message = self.render_digest_with_author_image("/private/files/digest-author.png")

		self.assertNotIn("/private/files/", message)
		self.assertNotIn("gp-email-digest__avatar-image", message)
		self.assertIn("gp-email-digest__avatar-fallback", message)

	def test_public_images_are_still_rendered_in_the_digest(self):
		message = self.render_digest_with_author_image("/files/digest-author.png")

		self.assertIn(get_url("/files/digest-author.png"), message)
		self.assertNotIn("gp-email-digest__avatar-fallback", message)

	def test_absolute_image_url_keeps_public_paths_and_drops_private_ones(self):
		self.assertEqual(absolute_image_url("/files/avatar.png"), get_url("/files/avatar.png"))
		self.assertEqual(absolute_image_url("files/avatar.png"), get_url("/files/avatar.png"))
		self.assertIsNone(absolute_image_url("/private/files/avatar.png"))
		self.assertIsNone(absolute_image_url("private/files/avatar.png"))
		self.assertIsNone(absolute_image_url(None))

	def build_digest(self):
		return build_digest(self.user.name, get_digest_period_start(self.today))

	def render_context(self):
		with patch("frappe.sendmail") as sendmail:
			send_digest_for_profile(self.profile, self.today)
		sendmail.assert_called_once()
		return sendmail.call_args.kwargs["args"]

	def render_digest_with_author_image(self, image):
		author = create_member(f"digest-author-{frappe.generate_hash(length=8)}@example.com", "Digest Author")
		frappe.db.set_value("GP User Profile", {"user": author.name}, "image", image)
		project = self.create_project("Digest Image")
		discussion = self.create_unread_discussion(project, "Digest Image Discussion")
		set_owner(discussion, author)
		message, _text = get_email_from_template("email_digest", self.render_context())
		return message

	def create_project(self, title):
		team = create_community(f"{title} Team")
		return create_space(title, team.name)

	def create_unread_discussion(self, project, title, created=None):
		"""A discussion by someone else, posted at `created` (now by default). Posting in a
		public Space gives every member, the reader included, an unread record for it."""
		discussion = create_discussion(title, project.name)
		if created:
			self.backdate("GP Discussion", discussion.name, created)
			self.backdate_unread_record(discussion.name, None, created)
		return discussion

	def add_reply(self, discussion, created=None, content="Reply", owner=None):
		"""A reply the reader has not read, posted at `created` (now by default)."""
		comment = create_comment(discussion.name, content=content, owner=owner)
		if created:
			self.backdate("GP Comment", comment.name, created)
			self.backdate_unread_record(discussion.name, comment.name, created)
		return comment

	def backdate_unread_record(self, discussion, comment, created):
		record = frappe.db.get_value(
			"GP Unread Record", {"user": self.user.name, "discussion": discussion, "comment": comment}
		)
		self.assertTrue(record, "posting should give the reader an unread record")
		self.backdate("GP Unread Record", record, created)

	def add_reactions(self, doctype, name, count, created=None):
		for index in range(count):
			reaction = frappe.get_doc(
				doctype="GP Reaction",
				reference_doctype=doctype,
				reference_name=name,
				emoji=":thumbsup:",
				user=f"digest-reaction-{index}-{frappe.generate_hash(length=8)}@example.com",
			).insert(ignore_permissions=True)
			if created:
				self.backdate("GP Reaction", reaction.name, created)

	def add_notification(self, discussion, project, message, from_user=None, type="Mention"):
		return frappe.get_doc(
			{
				"doctype": "GP Notification",
				"to_user": self.user.name,
				"type": type,
				"message": message,
				"discussion": discussion.name,
				"project": project.name,
				"team": project.team,
				"from_user": from_user and from_user.name,
			}
		).insert(ignore_permissions=True)

	def backdate(self, doctype, name, created):
		frappe.db.set_value(doctype, name, "creation", created, update_modified=False)

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
