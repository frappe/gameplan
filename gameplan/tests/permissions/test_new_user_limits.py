# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""Discourse-style limits on Gameplan Guests posting in a space only because it is public."""

from datetime import timedelta
from unittest.mock import patch

import frappe
from frappe.utils import now_datetime

from gameplan.new_user_limits import (
	MAX_DISCUSSIONS_IN_FIRST_DAY,
	MAX_REPLIES_IN_FIRST_DAY,
	POST_FIELDS,
	NewUserLimitError,
)
from gameplan.permissions import GUEST_CREATABLE_DOCTYPES
from gameplan.public_access import PUBLIC_ACCESS_CONFIG_KEY, VISIBILITY_ANONYMOUS
from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import (
	create_comment,
	create_community,
	create_discussion,
	create_space,
	grant_guest_access,
)

IMAGE = '<img src="/files/a.png">'
EMOJI = '<img data-emoji="" src="/files/party.png" alt="party">'
LINK = '<a href="https://example.org/{n}">link</a>'
FILE = '<a href="/private/files/report.pdf">report.pdf</a>'
MENTION = '<span data-type="mention" data-id="m{n}@example.com" data-label="M{n}">@M{n}</span>'
EVERYONE = '<span data-type="mention" data-id="_everyone_" data-label="everyone">@everyone</span>'


class NewUserLimitsTestCase(GameplanTestCase):
	def setUp(self):
		super().setUp()
		self.enterContext(patch.dict(frappe.conf, {PUBLIC_ACCESS_CONFIG_KEY: 1}))
		community = create_community("Limits Community", visibility=VISIBILITY_ANONYMOUS)
		self.public_space = create_space("Limits Public", community, visibility=VISIBILITY_ANONYMOUS)
		self.invited_space = create_space("Limits Invited", community, visibility=VISIBILITY_ANONYMOUS)
		grant_guest_access(self.guest, self.invited_space)
		self.thread = create_discussion("Limits Thread", self.public_space, owner=self.member)
		self.account_age(hours=1)

	def account_age(self, hours):
		created = now_datetime() - timedelta(hours=hours)
		frappe.db.set_value("User", self.guest.name, "creation", created, update_modified=False)

	def post(self, content="<p>Hello</p>", *, space=None, user=None):
		with self.as_user(user or self.guest.name):
			return frappe.get_doc(
				doctype="GP Discussion",
				title="A post",
				project=(space or self.public_space).name,
				content=content,
			).insert()

	def reply(self, content="<p>Hi</p>", *, user=None):
		with self.as_user(user or self.guest.name):
			return frappe.get_doc(
				doctype="GP Comment",
				reference_doctype="GP Discussion",
				reference_name=self.thread.name,
				content=content,
			).insert()

	def poll(self):
		with self.as_user(self.guest.name):
			return frappe.get_doc(
				doctype="GP Poll",
				title="A poll",
				discussion=self.thread.name,
				options=[{"title": "Yes"}, {"title": "No"}],
			).insert()


class TestFirstDay(NewUserLimitsTestCase):
	def test_posting_counters_cannot_be_reset_by_deleting_the_profile(self):
		self.post()
		profile = frappe.db.get_value("GP User Profile", {"user": self.guest.name}, "name")
		with self.as_user(self.guest.name), self.assertRaises(frappe.PermissionError):
			frappe.delete_doc("GP User Profile", profile)
		self.assertEqual(frappe.db.get_value("GP User Profile", profile, "first_day_discussions"), 1)

	def test_posting_counters_cannot_be_reset_through_profile_edits(self):
		self.post()
		profile = frappe.get_doc("GP User Profile", {"user": self.guest.name})
		with self.as_user(self.guest.name), self.assertRaises(frappe.PermissionError):
			profile.first_day_discussions = 0
			profile.save()
		self.assertEqual(frappe.db.get_value("GP User Profile", profile.name, "first_day_discussions"), 1)

	def test_migration_backfills_existing_posts_and_never_lowers_a_counter(self):
		from gameplan.gameplan.doctype.gp_user_profile.patches.backfill_first_day_post_counts import execute

		post = self.post()
		self.post()
		self.reply()
		self.poll()
		profile = frappe.db.get_value("GP User Profile", {"user": self.guest.name}, "name")
		frappe.db.set_value("GP User Profile", profile, {"first_day_discussions": 0, "first_day_replies": 0})
		execute()
		with self.as_user(self.guest.name):
			frappe.delete_doc(post.doctype, post.name)
		execute()
		counts = frappe.db.get_value(
			"GP User Profile", profile, ["first_day_discussions", "first_day_replies"]
		)
		self.assertEqual(tuple(counts), (2, 2))

	def test_deleting_discussions_does_not_reset_the_cap(self):
		for _ in range(MAX_DISCUSSIONS_IN_FIRST_DAY):
			post = self.post()
			with self.as_user(self.guest.name):
				frappe.delete_doc(post.doctype, post.name)
		with self.assertRaises(NewUserLimitError):
			self.post()

	def test_deleting_replies_and_polls_does_not_reset_the_shared_cap(self):
		for index in range(MAX_REPLIES_IN_FIRST_DAY):
			post = self.reply() if index % 2 else self.poll()
			with self.as_user(self.guest.name):
				frappe.delete_doc(post.doctype, post.name)
		with self.assertRaises(NewUserLimitError):
			self.reply()
		with self.assertRaises(NewUserLimitError):
			self.poll()

	def test_a_refused_post_does_not_use_the_posting_allowance(self):
		with self.assertRaises(NewUserLimitError):
			self.post(IMAGE * 2)
		for _ in range(MAX_DISCUSSIONS_IN_FIRST_DAY):
			self.post()

	def test_three_discussions_on_the_first_day(self):
		for _ in range(MAX_DISCUSSIONS_IN_FIRST_DAY):
			self.post()
		with self.assertRaises(NewUserLimitError):
			self.post()

	def test_ten_replies_on_the_first_day_polls_included(self):
		for _ in range(MAX_REPLIES_IN_FIRST_DAY - 1):
			self.reply()
		self.poll()
		with self.assertRaises(NewUserLimitError):
			self.reply()
		with self.assertRaises(NewUserLimitError):
			self.poll()

	def test_no_daily_cap_once_the_account_is_a_day_old(self):
		self.account_age(hours=25)
		for _ in range(MAX_DISCUSSIONS_IN_FIRST_DAY + 1):
			self.post()


class TestPerPost(NewUserLimitsTestCase):
	def assert_refused(self, content):
		with self.assertRaises(NewUserLimitError):
			self.reply(content)

	def test_one_image_custom_emoji_aside(self):
		self.reply(IMAGE + EMOJI + EMOJI)
		self.assert_refused(IMAGE * 2)

	def test_two_links_embeds_included(self):
		self.reply(LINK.format(n=1) + LINK.format(n=2))
		self.assert_refused(LINK.format(n=1) + LINK.format(n=2) + LINK.format(n=3))
		self.assert_refused(
			LINK.format(n=1) + LINK.format(n=2) + '<iframe src="https://www.youtube.com/embed/x"></iframe>'
		)

	def test_no_attachments(self):
		self.assert_refused(FILE)
		self.assert_refused('<video src="/files/clip.mp4"></video>')

	def test_two_mentions_and_never_everyone(self):
		self.reply(MENTION.format(n=1) + MENTION.format(n=2))
		self.assert_refused(MENTION.format(n=1) + MENTION.format(n=2) + MENTION.format(n=3))
		self.assert_refused(EVERYONE)

	def test_a_discussion_body_is_checked_too(self):
		with self.assertRaises(NewUserLimitError):
			self.post(IMAGE * 2)

	def test_an_edit_is_checked_too(self):
		comment = self.reply()
		with self.as_user(self.guest.name), self.assertRaises(NewUserLimitError):
			comment.content = IMAGE * 2
			comment.save()


class TestEditWindow(NewUserLimitsTestCase):
	def test_old_poll_option_text_cannot_be_changed_but_votes_can(self):
		poll = self.age(self.poll(), hours=25)
		with self.as_user(self.guest.name), self.assertRaises(NewUserLimitError):
			poll.options[0].title = "Changed answer"
			poll.save()
		with self.as_user(self.guest.name):
			poll = frappe.get_doc("GP Poll", poll.name)
			poll.submit_vote("Yes")
			poll.submit_vote("No")
			poll.retract_vote()

	def age(self, doc, hours):
		created = now_datetime() - timedelta(hours=hours)
		frappe.db.set_value(doc.doctype, doc.name, "creation", created, update_modified=False)
		return frappe.get_doc(doc.doctype, doc.name)

	def test_own_posts_are_editable_for_a_day(self):
		comment = self.age(self.reply(), hours=23)
		with self.as_user(self.guest.name):
			comment.content = "<p>Fixed a typo</p>"
			comment.save()
		comment = self.age(comment, hours=25)
		with self.as_user(self.guest.name), self.assertRaises(NewUserLimitError):
			comment.content = "<p>Too late</p>"
			comment.save()

	def test_reacting_is_not_editing(self):
		own = self.age(self.reply(), hours=48)
		with self.as_user(self.guest.name):
			own.append("reactions", {"user": self.guest.name, "emoji": "👍"})
			own.save()

	def test_others_editing_an_old_guest_post_are_not_limited(self):
		comment = self.age(self.reply(), hours=48)
		with self.as_user(self.member.name):
			comment.content = "<p>Edited by a member</p>" + IMAGE * 3
			comment.save()


class TestWhoIsLimited(NewUserLimitsTestCase):
	def test_not_in_a_space_the_guest_was_invited_to(self):
		for _ in range(MAX_DISCUSSIONS_IN_FIRST_DAY + 1):
			self.post(IMAGE * 3, space=self.invited_space)

	def test_not_members(self):
		for _ in range(MAX_DISCUSSIONS_IN_FIRST_DAY + 1):
			self.post(IMAGE * 3 + EVERYONE, user=self.member.name)

	def test_not_existing_content_saved_by_the_system(self):
		comment = create_comment(self.thread, content=IMAGE * 3, owner=self.guest)
		self.assertTrue(comment.name)


class TestCoverage(GameplanTestCase):
	def test_every_doctype_a_guest_may_create_is_limited(self):
		self.assertEqual(set(POST_FIELDS), GUEST_CREATABLE_DOCTYPES)
		for doctype in GUEST_CREATABLE_DOCTYPES:
			with self.subTest(doctype=doctype):
				hooks = frappe.get_hooks("doc_events").get(doctype, {}).get("validate", [])
				self.assertIn("gameplan.new_user_limits.check_new_user_limits", hooks)
