# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""Public payloads hide identities and member lists, including through REST and realtime."""

import json
from unittest.mock import patch

import frappe
import frappe.api.v2
from werkzeug.test import EnvironBuilder
from werkzeug.wrappers import Request

from gameplan import public_lists
from gameplan.api import get_public_user_info
from gameplan.extends.client import get_list as get_client_list
from gameplan.gameplan.doctype.gp_discussion.api import get_discussions
from gameplan.public_access import (
	VISIBILITY_ANONYMOUS,
	VISIBILITY_MEMBER_ACCESS,
	realtime_has_permission,
	refuse_generic_routes_for_anonymous,
)
from gameplan.public_payload import (
	AUTHOR_FIELDS,
	PRIVATE_FIELDS,
	PUBLIC_CHILD_FIELDS,
	PUBLIC_FIELDS,
	STANDARD_PUBLIC_FIELDS,
	TABLE_FIELDS,
	handles_for,
	public_authors,
	replace_user_ids_in_html,
)
from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import (
	create_comment,
	create_community,
	create_discussion,
	create_poll,
	create_space,
)
from gameplan.tests.fixtures import public_access as switched_on
from gameplan.tests.permissions.test_anonymous_access import ANONYMOUS_READABLE_DOCTYPES

ANONYMOUS = "Guest"
LAYOUT_FIELDTYPES = {"Section Break", "Column Break", "Tab Break"}
# Columns frappe adds to every table that are not in the doctype's field list.
STANDARD_COLUMNS = {"name", "owner", "creation", "modified", "modified_by", "docstatus", "idx"}


def strings_in(value):
	"""Every string anywhere inside `value`, however deeply nested."""
	if isinstance(value, str):
		yield value
	elif isinstance(value, dict):
		for key, item in value.items():
			yield str(key)
			yield from strings_in(item)
	elif isinstance(value, list | tuple):
		for item in value:
			yield from strings_in(item)


class PublicContentTestCase(GameplanTestCase):
	def setUp(self):
		super().setUp()
		self.community = create_community(
			"Payload Community", visibility=VISIBILITY_ANONYMOUS, members=[self.member, self.second_member]
		)
		self.space = create_space(
			"Payload Space", self.community, visibility=VISIBILITY_ANONYMOUS, members=[self.member]
		)
		self.general_space = create_space("Payload General Space", self.community)
		self.member_handle = handles_for([self.member.name])[self.member.name]
		self.second_handle = handles_for([self.second_member.name])[self.second_member.name]
		content = (
			"<p>Hi "
			f'<span data-type="mention" data-id="{self.second_member.name}" data-label="Second Member">'
			"@Second Member</span>, write to me at mira@typed.test.</p>"
			f'<blockquote data-rich-quote-id="1" data-author="{self.second_member.name}"><p>quoted</p>'
			"</blockquote>"
			'<p><span data-type="mention" data-id="nobody@elsewhere.test">@Nobody</span></p>'
		)
		self.discussion = create_discussion(
			"Payload Discussion", self.space, content=content, owner=self.member
		)
		self.comment = create_comment(self.discussion, content=content, owner=self.second_member)
		self.poll = create_poll("Payload Poll", self.discussion, owner=self.member)
		for doc in (self.discussion, self.comment, self.poll):
			doc.reload()
			doc.append("reactions", {"user": self.member.name, "emoji": "👍"})
			doc.append("reactions", {"user": self.second_member.name, "emoji": "👍"})
			doc.save(ignore_permissions=True)
		with self.as_user(self.second_member.name):
			frappe.get_doc("GP Poll", self.poll.name).submit_vote(self.poll.options[0].title)
		self.hidden_discussion = create_discussion(
			"Payload Hidden Discussion", self.general_space, owner=self.outsider
		)
		self.emails = {
			self.member.name,
			self.second_member.name,
			self.outsider.name,
			self.admin.name,
			self.guest.name,
		}

	def assert_carries_no_user_ids(self, payload, label):
		for string in strings_in(payload):
			self.assertNotIn("@example.com", string, label)
			self.assertNotIn("nobody@elsewhere.test", string, label)
			self.assertNotEqual(string, "Administrator", label)


class TestPublicPayloadClassification(GameplanTestCase):
	"""Every field of every anonymously readable doctype has been decided on."""

	def test_the_payload_covers_exactly_the_doctypes_the_guest_role_reads(self):
		self.assertEqual(set(PUBLIC_FIELDS), set(ANONYMOUS_READABLE_DOCTYPES))

	def test_every_field_is_classified_exactly_once(self):
		for doctype in PUBLIC_FIELDS:
			meta = frappe.get_meta(doctype)
			columns = {df.fieldname for df in meta.fields if df.fieldtype not in LAYOUT_FIELDTYPES}
			columns |= STANDARD_COLUMNS
			groups = {
				"standard": STANDARD_PUBLIC_FIELDS & columns,
				"public": PUBLIC_FIELDS[doctype],
				"author": AUTHOR_FIELDS[doctype],
				"table": set(TABLE_FIELDS[doctype]),
				"private": set(PRIVATE_FIELDS[doctype]),
			}
			for fieldname in columns:
				with self.subTest(doctype=doctype, field=fieldname):
					found_in = [group for group, names in groups.items() if fieldname in names]
					self.assertEqual(
						len(found_in),
						1,
						f"{doctype}.{fieldname} must be classified in gameplan/public_payload.py exactly"
						f" once, found in {found_in or 'none'}",
					)
			for group, names in groups.items():
				with self.subTest(doctype=doctype, group=group):
					self.assertLessEqual(names, columns, f"{group} names fields {doctype} does not have")

	def test_no_user_link_is_shown_as_it_is(self):
		for doctype in PUBLIC_FIELDS:
			for df in frappe.get_meta(doctype).fields:
				if df.fieldtype == "Link" and df.options == "User":
					with self.subTest(doctype=doctype, field=df.fieldname):
						self.assertNotIn(df.fieldname, PUBLIC_FIELDS[doctype])

	def test_child_tables_say_nothing_about_who(self):
		for doctype, tables in TABLE_FIELDS.items():
			for table, child_doctype in tables.items():
				with self.subTest(doctype=doctype, table=table):
					self.assertEqual(frappe.get_meta(doctype).get_field(table).options, child_doctype)
					meta = frappe.get_meta(child_doctype)
					for fieldname in PUBLIC_CHILD_FIELDS.get(child_doctype, ()):
						df = meta.get_field(fieldname)
						self.assertFalse(df and df.fieldtype == "Link" and df.options == "User")
						self.assertNotIn(fieldname, {"user", "owner", "modified_by"})
		self.assertNotIn("GP Member", PUBLIC_CHILD_FIELDS)
		self.assertNotIn("GP Poll Vote", PUBLIC_CHILD_FIELDS)


class TestPublicDocuments(PublicContentTestCase):
	def public_docs(self):
		return [self.community, self.space, self.discussion, self.comment, self.poll]

	def test_documents_carry_no_email_and_no_member_list(self):
		with switched_on(), self.as_user(ANONYMOUS):
			for doc in self.public_docs():
				for label, payload in {
					"as_dict": frappe.get_doc(doc.doctype, doc.name).as_dict(),
					"as_dict(no_nulls)": frappe.get_doc(doc.doctype, doc.name).as_dict(no_nulls=True),
					"api/v2 read_doc": frappe.api.v2.read_doc(doc.doctype, doc.name),
				}.items():
					with self.subTest(doctype=doc.doctype, path=label):
						self.assert_carries_no_user_ids(payload, f"{doc.doctype} via {label}")
						self.assertNotIn("modified_by", payload)
						self.assertFalse(payload.get("members"))

	def test_authors_are_profile_handles(self):
		with switched_on(), self.as_user(ANONYMOUS):
			discussion = frappe.get_doc("GP Discussion", self.discussion.name).as_dict()
			comment = frappe.get_doc("GP Comment", self.comment.name).as_dict()
		self.assertEqual(discussion.owner, self.member_handle)
		self.assertEqual(comment.owner, self.second_handle)
		self.assertIn(f'data-id="{self.second_handle}"', discussion.content)
		self.assertIn(f'data-author="{self.second_handle}"', discussion.content)
		self.assertIn('data-id=""', discussion.content)
		self.assertIn("mira@typed.test.", discussion.content, "text the author wrote stays")

	def test_reactions_and_votes_are_totals_only(self):
		with switched_on(), self.as_user(ANONYMOUS):
			discussion = frappe.get_doc("GP Discussion", self.discussion.name).as_dict()
			poll = frappe.get_doc("GP Poll", self.poll.name).as_dict()
		self.assertEqual([reaction.emoji for reaction in discussion.reactions], ["👍", "👍"])
		for reaction in discussion.reactions:
			self.assertEqual(set(reaction), {"name", "emoji"})
		self.assertEqual(poll.votes, [])
		self.assertEqual(poll.total_votes, 1)
		self.assertEqual(sum(option.votes for option in poll.options), 1)

	def test_signed_in_users_see_documents_as_before(self):
		with switched_on(), self.as_user(self.member.name):
			discussion = frappe.get_doc("GP Discussion", self.discussion.name).as_dict()
			space = frappe.get_doc("GP Project", self.space.name).as_dict()
			poll = frappe.get_doc("GP Poll", self.poll.name).as_dict()
		self.assertEqual(discussion.owner, self.member.name)
		self.assertIn(f'data-id="{self.second_member.name}"', discussion.content)
		self.assertEqual(
			{reaction.user for reaction in discussion.reactions}, {self.member.name, self.second_member.name}
		)
		self.assertIn(self.member.name, [m.user for m in space.members])
		self.assertEqual([vote.user for vote in poll.votes], [self.second_member.name])
		self.assertIn("modified_by", discussion)

	def test_a_deleted_comment_keeps_no_content(self):
		frappe.db.set_value("GP Comment", self.comment.name, "deleted_at", frappe.utils.now())
		with switched_on(), self.as_user(ANONYMOUS):
			self.assertIsNone(frappe.get_doc("GP Comment", self.comment.name).as_dict().content)


class TestPublicLists(PublicContentTestCase):
	def test_direct_public_lists_clamp_page_size_and_offset(self):
		for requested, expected in ((-1, 1), (1000000, public_lists.MAX_ROWS)):
			with switched_on(), self.as_user(ANONYMOUS):
				with patch("frappe.qb.get_query", wraps=frappe.qb.get_query) as query:
					get_client_list(doctype="GP Comment", fields=["name"], start=-1, limit=requested)
				calls = [call for call in query.call_args_list if call.kwargs.get("table") == "GP Comment"]
			self.assertEqual(calls[0].kwargs["limit"], expected)
			self.assertEqual(calls[0].kwargs["offset"], 0)

	def client_list(self, doctype, **kwargs):
		with switched_on(), self.as_user(ANONYMOUS):
			return get_client_list(doctype=doctype, limit=100, **kwargs)

	def test_the_spa_queries_carry_no_email(self):
		# The field lists CommentsArea.vue and Poll.vue ask for, plus `*`.
		queries = {
			"GP Comment": [
				"name",
				"content",
				"owner",
				"creation",
				"modified",
				"edited_at",
				"deleted_at",
				{"reactions": ["name", "user", "emoji"]},
			],
			"GP Poll": [
				"name",
				"title",
				"owner",
				{"options": ["name", "title", "idx", "percentage"]},
				{"votes": ["user", "option"]},
				{"reactions": ["name", "user", "emoji"]},
			],
		}
		for doctype in PUBLIC_FIELDS:
			queries.setdefault(doctype, ["*"])
		for doctype, fields in queries.items():
			with self.subTest(doctype=doctype):
				rows = self.client_list(doctype, fields=fields)
				self.assertTrue(rows, f"{doctype} lists nothing")
				self.assert_carries_no_user_ids(rows, doctype)
		ours = {"reference_name": self.discussion.name}
		comment = self.client_list("GP Comment", fields=queries["GP Comment"], filters=ours)[0]
		self.assertEqual(comment.owner, self.second_handle)
		self.assertEqual([reaction.emoji for reaction in comment.reactions], ["👍", "👍"])
		poll = self.client_list(
			"GP Poll", fields=queries["GP Poll"], filters={"discussion": self.discussion.name}
		)
		self.assertEqual(poll[0].votes, [])

	def test_columns_outside_the_allowlist_are_refused(self):
		for fields in (
			["modified_by"],
			["owner as author"],
			["`tabGP Comment`.owner"],
			["_comments"],
			["count(owner)"],
			[{"reactions": ["user as who"]}],
			[{"members": ["user"], "votes": ["user"]}],
		):
			with self.subTest(fields=fields), self.assertRaises(frappe.PermissionError):
				self.client_list("GP Comment", fields=fields)

	def test_filtering_or_sorting_by_a_person_is_refused(self):
		refused = [
			{"filters": {"owner": self.member.name}},
			{"filters": [["owner", "=", self.member.name]]},
			{"filters": [["GP Comment", "modified_by", "=", self.member.name]]},
			{"filters": {"reactions.user": self.member.name}},
			{"order_by": "owner asc"},
			{"order_by": "creation asc, modified_by desc"},
			{"group_by": "owner"},
			{"parent": "GP Discussion"},
		]
		for kwargs in refused:
			with self.subTest(**kwargs), self.assertRaises(frappe.PermissionError):
				self.client_list("GP Comment", fields=["name"], **kwargs)
		self.assertTrue(
			self.client_list(
				"GP Comment",
				fields=["name"],
				filters={"reference_doctype": "GP Discussion", "reference_name": self.discussion.name},
				order_by="creation asc",
			)
		)

	def test_the_feed_carries_no_email(self):
		with switched_on(), self.as_user(ANONYMOUS):
			feed = get_discussions(limit=100)
		self.assertIn(str(self.discussion.name), {str(row.name) for row in feed})
		self.assert_carries_no_user_ids(feed, "feed")
		row = next(row for row in feed if str(row.name) == str(self.discussion.name))
		self.assertEqual(row.owner, self.member_handle)
		self.assertTrue(row.ongoing_polls)

	def test_the_feed_refuses_to_look_up_a_person(self):
		with switched_on(), self.as_user(ANONYMOUS):
			for filters in ({"participator": self.member.name}, {"owner": self.member.name}):
				with self.subTest(filters=filters), self.assertRaises(frappe.PermissionError):
					get_discussions(filters=filters, limit=100)

	def test_signed_in_lists_are_unchanged(self):
		with switched_on(), self.as_user(self.member.name):
			comment = get_client_list(
				doctype="GP Comment",
				fields=["name", "owner", "modified_by", {"reactions": ["user", "emoji"]}],
				filters={"owner": self.second_member.name},
				order_by="owner asc",
			)[0]
			feed = get_discussions(limit=100)
		self.assertEqual(comment.owner, self.second_member.name)
		self.assertEqual({r.user for r in comment.reactions}, {self.member.name, self.second_member.name})
		self.assertIn(self.member.name, {row.owner for row in feed})


class TestPublicListEndpoints(PublicContentTestCase):
	"""The lists the public view reads, called the way frappe-ui calls them: JSON strings."""

	def call(self, endpoint, **kwargs):
		with switched_on(), self.as_user(ANONYMOUS):
			return getattr(public_lists, endpoint)(**kwargs)

	def test_each_lists_its_doctype_cleaned(self):
		for endpoint, doctype, filters in (
			("communities", "GP Team", {"name": self.community.name}),
			("spaces", "GP Project", {"name": self.space.name}),
			("comments", "GP Comment", {"reference_name": self.discussion.name}),
			("polls", "GP Poll", {"discussion": self.discussion.name}),
		):
			with self.subTest(endpoint=endpoint):
				rows = self.call(
					endpoint,
					fields=json.dumps(["*", *({table: ["name"]} for table in TABLE_FIELDS[doctype])]),
					filters=json.dumps(filters),
				)
				self.assertEqual(len(rows), 1)
				self.assert_carries_no_user_ids(rows, endpoint)

	def test_they_refuse_what_get_list_refuses(self):
		with self.assertRaises(frappe.PermissionError):
			self.call("comments", fields=json.dumps(["modified_by"]))
		with self.assertRaises(frappe.PermissionError):
			by_owner = json.dumps({"owner": self.member.name})
			self.call("comments", fields=json.dumps(["name"]), filters=by_owner)

	def test_a_page_has_a_ceiling(self):
		with patch("gameplan.public_lists.get_list") as get_list:
			self.call("comments", limit="1000000")
		self.assertEqual(get_list.call_args.kwargs["limit"], public_lists.MAX_ROWS)

	def test_a_negative_page_size_is_bounded(self):
		with patch("gameplan.public_lists.get_list") as get_list:
			self.call("comments", limit="-1")
		self.assertEqual(get_list.call_args.kwargs["limit"], 1)

	def test_pagination_reports_when_another_request_is_needed(self):
		with patch("gameplan.public_lists.get_list", return_value=[frappe._dict(name="comment")]):
			self.call("comments", limit=1)
			self.assertTrue(frappe.response["has_next_page"])
			self.call("comments", limit=2)
			self.assertFalse(frappe.response["has_next_page"])


class TestPublicProfiles(PublicContentTestCase):
	def profiles(self, handles, user=ANONYMOUS, on=True):
		with switched_on(on), self.as_user(user):
			return get_public_user_info(handles)

	def test_authors_of_public_content_have_a_name_and_an_avatar(self):
		profiles = self.profiles([self.member_handle, self.second_handle])
		self.assertEqual({p["handle"] for p in profiles}, {self.member_handle, self.second_handle})
		for profile in profiles:
			self.assertEqual(
				set(profile),
				{"handle", "full_name", "image", "image_background_color", "is_image_background_removed"},
			)
		self.assert_carries_no_user_ids(profiles, "profiles")

	def test_anyone_else_answers_nothing(self):
		outsider_handle = handles_for([self.outsider.name])[self.outsider.name]
		admin_handle = handles_for([self.admin.name])[self.admin.name]
		self.assertEqual(self.profiles([outsider_handle, admin_handle]), [])

	def test_discussion_actors_are_resolved_with_three_batched_queries(self):
		actors = (self.member.name, self.second_member.name, self.outsider.name, self.admin.name)
		frappe.db.set_value(
			"GP Discussion",
			self.discussion.name,
			dict(zip(("owner", "last_post_by", "closed_by", "pinned_by"), actors, strict=True)),
		)
		with patch.object(frappe.db, "sql", wraps=frappe.db.sql) as sql:
			self.assertEqual(public_authors(actors), set(actors))
		self.assertEqual(sql.call_count, 3)

	def test_nothing_while_switched_off(self):
		self.assertEqual(self.profiles([self.member_handle], on=False), [])

	def test_a_space_leaving_anonymous_takes_its_authors_with_it(self):
		self.space.reload()
		self.space.set_visibility(VISIBILITY_MEMBER_ACCESS)
		self.assertEqual(self.profiles([self.member_handle]), [])


class TestDoorsAroundTheCleaning(PublicContentTestCase):
	def route(self, path, method="GET", user=ANONYMOUS):
		request = Request(EnvironBuilder(path=path, method=method).get_environ())
		with patch.object(frappe.local, "request", request, create=True), switched_on(), self.as_user(user):
			refuse_generic_routes_for_anonymous()

	def test_the_guard_is_registered(self):
		self.assertIn(
			"gameplan.public_access.refuse_generic_routes_for_anonymous", frappe.get_hooks("before_request")
		)

	def test_generic_list_and_bulk_routes_are_refused(self):
		name = self.discussion.name
		for method, path in (
			("GET", "/api/resource/GP Discussion"),
			("GET", f"/api/resource/GP Discussion/{name}"),
			("GET", "/api/v1/resource/GP Comment"),
			("GET", "/api/v2/document/GP Discussion"),
			("GET", "/api/v2/document/GP%20Discussion"),
			("GET", f"/api/v2/document/GP Discussion/{name}/copy"),
			("GET", "/api/v2/doctype/GP Comment/count"),
			("POST", "/api/v2/document/GP Poll"),
		):
			with self.subTest(path=path), self.assertRaises(frappe.PermissionError):
				self.route(path, method)

	def test_reading_one_document_and_calling_its_methods_still_route(self):
		name = self.discussion.name
		for method, path in (
			("GET", f"/api/v2/document/GP Discussion/{name}"),
			("POST", f"/api/v2/document/GP Discussion/{name}/method/react"),
			("GET", "/api/v2/method/gameplan.extends.client.get_list"),
			("GET", "/api/resource/Blog Post"),
			("GET", "/login"),
		):
			with self.subTest(path=path):
				self.route(path, method)

	def test_signed_in_users_are_not_affected(self):
		self.route("/api/resource/GP Discussion", user=self.member.name)

	def test_realtime_override_is_registered(self):
		self.assertEqual(
			frappe.override_whitelisted_method("frappe.realtime.has_permission"),
			"gameplan.public_access.realtime_has_permission",
		)

	def test_anonymous_sockets_cannot_join_doctype_or_document_presence_rooms(self):
		with switched_on(), self.as_user(ANONYMOUS):
			for doctype in PUBLIC_FIELDS:
				with self.subTest(doctype=doctype), self.assertRaises(frappe.PermissionError):
					realtime_has_permission(doctype, "")
			for name in (self.discussion.name, self.hidden_discussion.name):
				with self.subTest(name=name), self.assertRaises(frappe.PermissionError):
					realtime_has_permission("GP Discussion", str(name))

	def test_signed_in_sockets_still_join_a_doctype(self):
		with switched_on(), self.as_user(self.member.name):
			self.assertTrue(realtime_has_permission("GP Comment", ""))
			self.assertTrue(realtime_has_permission("GP Discussion", str(self.discussion.name)))


class TestReplaceUserIdsInHtml(GameplanTestCase):
	def test_only_attribute_values_that_are_user_ids_change(self):
		html = (
			'<a href="mailto:x@y.test" data-id="a@b.test" title=\'Administrator\'>a@b.test</a>'
			'<img src="/files/a@2x.png">'
		)
		self.assertEqual(
			replace_user_ids_in_html(html, {"a@b.test": "ann"}),
			'<a href="mailto:x@y.test" data-id="ann" title=\'\'>a@b.test</a><img src="/files/a@2x.png">',
		)
