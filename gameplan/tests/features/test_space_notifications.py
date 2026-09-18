# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""What a space subscription, a move, a poll vote and being added put in the bell.

A `GP Space Subscription` row is the one thing that makes a *new* discussion news: its
subscribers hear when one starts in the space, or moves in or out of it, and nobody else
does. A comment never reaches them through it — that is the discussion bell's business
(`test_notification_preferences.py`). Being added to a space or community and someone
voting on your poll are the two remaining events, and losing a space forgets every
choice the user made about it.
"""

import frappe

from gameplan.gameplan.doctype.gp_discussion.gp_discussion import move_discussion
from gameplan.gameplan.doctype.gp_team.gp_team import join_team
from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import (
	_name,
	create_comment,
	create_community,
	create_discussion,
	create_poll,
	create_space,
	grant_guest_access,
)


class SpaceNotificationTestCase(GameplanTestCase):
	def setUp(self):
		super().setUp()
		self.notifications_before = set(frappe.get_all("GP Notification", pluck="name"))
		self.community = create_community(
			"Acme", members=[self.member, self.second_member], admins=[self.admin]
		)
		self.space = create_space("Engineering", self.community)
		self.other_space = create_space("Design", self.community)

	def subscribe(self, user, space):
		return frappe.get_doc(doctype="GP Space Subscription", user=_name(user), project=_name(space)).insert(
			ignore_permissions=True
		)

	def subscriptions_for(self, user, space=None):
		filters = {"user": _name(user)}
		if space:
			filters["project"] = str(_name(space))
		return frappe.get_all("GP Space Subscription", filters=filters, pluck="name")

	def discussion_subscriptions_for(self, user):
		return frappe.get_all("GP Discussion Subscription", filters={"user": _name(user)}, pluck="name")

	def notifications_for(self, user, **filters):
		rows = frappe.get_all(
			"GP Notification",
			filters={"to_user": _name(user), **filters},
			fields=[
				"name",
				"type",
				"message",
				"from_user",
				"discussion",
				"project",
				"team",
				"read",
				"event_count",
			],
			order_by="creation asc",
		)
		return [row for row in rows if row.name not in self.notifications_before]

	def forget_notifications_so_far(self):
		self.notifications_before.update(frappe.get_all("GP Notification", pluck="name"))

	def start_discussion(self, author, space=None, title="A new thread"):
		with self.as_user(author):
			return create_discussion(title, space or self.space)


class TestNewDiscussion(SpaceNotificationTestCase):
	def test_a_subscriber_hears_about_a_new_discussion(self):
		self.subscribe(self.second_member, self.space)

		discussion = self.start_discussion(self.member, title="Roadmap")

		rows = self.notifications_for(self.second_member)
		self.assertEqual([r.type for r in rows], ["New Discussion"])
		self.assertEqual(rows[0].message, "Member started a discussion in Engineering")
		self.assertEqual(rows[0].from_user, self.member.name)
		self.assertEqual(str(rows[0].discussion), str(discussion.name))
		self.assertEqual(str(rows[0].project), str(self.space.name))
		self.assertEqual(rows[0].team, self.community.name)

	def test_each_discussion_is_its_own_row(self):
		self.subscribe(self.second_member, self.space)

		self.start_discussion(self.member, title="One")
		self.start_discussion(self.member, title="Two")

		self.assertEqual(len(self.notifications_for(self.second_member)), 2)

	def test_the_author_is_never_told_about_their_own_discussion(self):
		self.subscribe(self.member, self.space)

		self.start_discussion(self.member)

		self.assertEqual(self.notifications_for(self.member, type="New Discussion"), [])

	def test_a_non_subscriber_hears_nothing(self):
		self.start_discussion(self.member)

		self.assertEqual(self.notifications_for(self.second_member), [])

	def test_a_subscription_to_another_space_does_not_count(self):
		self.subscribe(self.second_member, self.other_space)

		self.start_discussion(self.member, space=self.space)

		self.assertEqual(self.notifications_for(self.second_member), [])

	def test_a_comment_does_not_reach_space_subscribers(self):
		self.subscribe(self.second_member, self.space)
		discussion = self.start_discussion(self.member)
		self.forget_notifications_so_far()

		with self.as_user(self.member):
			create_comment(discussion, content="<p>A reply</p>")

		self.assertEqual(self.notifications_for(self.second_member), [])

	def test_a_subscriber_who_cannot_open_the_space_hears_nothing(self):
		private = create_space("Secret", self.community, is_private=1, members=[self.member])
		self.subscribe(self.second_member, private)

		self.start_discussion(self.member, space=private)

		self.assertEqual(self.notifications_for(self.second_member), [])


class TestMoved(SpaceNotificationTestCase):
	def setUp(self):
		super().setUp()
		self.discussion = self.start_discussion(self.member, title="Roadmap")
		self.forget_notifications_so_far()

	def move(self, actor, to=None):
		with self.as_user(actor):
			doc = frappe.get_doc("GP Discussion", self.discussion.name)
			move_discussion(doc, str(_name(to or self.other_space)))

	def test_subscribers_of_the_old_space_are_told_where_it_went(self):
		self.subscribe(self.second_member, self.space)

		self.move(self.admin)

		rows = self.notifications_for(self.second_member)
		self.assertEqual([r.type for r in rows], ["Moved"])
		self.assertEqual(rows[0].message, "Admin moved Roadmap to Design")
		self.assertEqual(str(rows[0].discussion), str(self.discussion.name))
		self.assertEqual(str(rows[0].project), str(self.other_space.name))

	def test_subscribers_of_the_new_space_are_told_what_arrived(self):
		self.subscribe(self.second_member, self.other_space)

		self.move(self.admin)

		self.assertEqual([r.type for r in self.notifications_for(self.second_member)], ["Moved"])

	def test_a_subscriber_of_both_spaces_is_told_once(self):
		self.subscribe(self.second_member, self.space)
		self.subscribe(self.second_member, self.other_space)

		self.move(self.admin)

		self.assertEqual(len(self.notifications_for(self.second_member)), 1)

	def test_a_move_is_not_a_new_discussion(self):
		self.subscribe(self.second_member, self.other_space)

		self.move(self.admin)

		self.assertEqual(self.notifications_for(self.second_member, type="New Discussion"), [])

	def test_the_mover_is_not_told(self):
		self.subscribe(self.admin, self.space)

		self.move(self.admin)

		self.assertEqual(self.notifications_for(self.admin), [])

	def test_a_non_subscriber_is_not_told(self):
		self.move(self.admin)

		self.assertEqual(self.notifications_for(self.second_member), [])

	def test_a_mute_on_the_discussion_wins(self):
		self.subscribe(self.second_member, self.space)
		frappe.get_doc(
			doctype="GP Discussion Subscription",
			user=self.second_member.name,
			discussion=self.discussion.name,
			state="Mute",
		).insert(ignore_permissions=True)

		self.move(self.admin)

		self.assertEqual(self.notifications_for(self.second_member), [])

	def test_a_subscriber_who_cannot_open_the_destination_is_not_told(self):
		private = create_space("Secret", self.community, is_private=1, members=[self.admin])
		self.subscribe(self.second_member, self.space)

		self.move(self.admin, to=private)

		self.assertEqual(self.notifications_for(self.second_member), [])

	def test_moving_a_space_tells_its_subscribers(self):
		other_community = create_community("Globex", members=[self.second_member], admins=[self.admin])
		self.subscribe(self.second_member, self.space)

		with self.as_user(self.admin):
			frappe.get_doc("GP Project", self.space.name).move_to_team(other_community.name)

		rows = self.notifications_for(self.second_member)
		self.assertEqual([r.type for r in rows], ["Moved"])
		self.assertEqual(rows[0].message, "Admin moved Engineering to Globex")
		self.assertIsNone(rows[0].discussion)
		self.assertEqual(str(rows[0].project), str(self.space.name))
		self.assertEqual(rows[0].team, other_community.name)

	def test_moving_a_space_carries_its_subscriptions_to_the_new_community(self):
		other_community = create_community("Globex", members=[self.second_member], admins=[self.admin])
		row = self.subscribe(self.second_member, self.space)

		with self.as_user(self.admin):
			frappe.get_doc("GP Project", self.space.name).move_to_team(other_community.name)

		self.assertEqual(frappe.db.get_value("GP Space Subscription", row.name, "team"), other_community.name)


class TestAdded(SpaceNotificationTestCase):
	def test_being_added_to_a_space_is_news(self):
		private = create_space("Secret", self.community, is_private=1, members=[self.admin])

		with self.as_user(self.admin):
			frappe.get_doc("GP Project", private.name).add_member(self.second_member.name)

		rows = self.notifications_for(self.second_member)
		self.assertEqual([r.type for r in rows], ["Added"])
		self.assertEqual(rows[0].message, "Admin added you to Secret")
		self.assertEqual(rows[0].from_user, self.admin.name)
		self.assertEqual(str(rows[0].project), str(private.name))
		self.assertEqual(rows[0].team, self.community.name)
		self.assertIsNone(rows[0].discussion)

	def test_adding_someone_who_is_already_a_member_is_not_news(self):
		with self.as_user(self.admin):
			frappe.get_doc("GP Project", self.space.name).add_member(self.second_member.name)
		self.forget_notifications_so_far()

		with self.as_user(self.admin):
			frappe.get_doc("GP Project", self.space.name).add_member(self.second_member.name)

		self.assertEqual(self.notifications_for(self.second_member), [])

	def test_joining_a_space_yourself_is_not_news(self):
		with self.as_user(self.second_member):
			frappe.get_doc("GP Project", self.other_space.name).join()

		self.assertEqual(self.notifications_for(self.second_member), [])

	def test_being_added_to_a_community_is_news(self):
		with self.as_user(self.admin):
			frappe.get_doc("GP Team", self.community.name).add_members([self.outsider.name])

		rows = self.notifications_for(self.outsider)
		self.assertEqual([r.type for r in rows], ["Added"])
		self.assertEqual(rows[0].message, "Admin added you to Acme")
		self.assertIsNone(rows[0].project)
		self.assertEqual(rows[0].team, self.community.name)

	def test_joining_a_community_yourself_is_not_news(self):
		with self.as_user(self.outsider):
			join_team(self.community.name)

		self.assertEqual(self.notifications_for(self.outsider), [])

	def test_a_guest_is_told_about_the_space_they_were_given(self):
		with self.as_user(self.admin):
			grant_guest_access(self.guest, self.space)

		rows = self.notifications_for(self.guest)
		self.assertEqual([r.type for r in rows], ["Added"])
		self.assertEqual(rows[0].message, "Admin added you to Engineering")
		self.assertEqual(str(rows[0].project), str(self.space.name))

	def test_a_grant_with_nobody_behind_it_is_worded_without_a_name(self):
		with self.as_user("Guest"):
			grant_guest_access(self.guest, self.space)

		rows = self.notifications_for(self.guest)
		self.assertEqual(rows[0].message, "You were added to Engineering")
		self.assertIsNone(rows[0].from_user)


class TestPollVote(SpaceNotificationTestCase):
	def setUp(self):
		super().setUp()
		self.discussion = self.start_discussion(self.member, title="Roadmap")
		with self.as_user(self.member):
			self.poll = create_poll("Ship on Friday?", self.discussion)
		self.forget_notifications_so_far()

	def vote(self, user, option="Yes", poll=None):
		with self.as_user(user):
			frappe.get_doc("GP Poll", _name(poll or self.poll)).submit_vote(option)

	def retract(self, user, option=None):
		with self.as_user(user):
			frappe.get_doc("GP Poll", self.poll.name).retract_vote(option)

	def set_prefs(self, user, **fields):
		profile = frappe.db.get_value("GP User Profile", {"user": _name(user)}, "name")
		frappe.db.set_value("GP User Profile", profile, fields)

	def test_the_author_hears_about_a_vote(self):
		self.vote(self.second_member)

		rows = self.notifications_for(self.member)
		self.assertEqual([r.type for r in rows], ["Poll Vote"])
		self.assertEqual(rows[0].message, "Second Member voted on your poll")
		self.assertEqual(rows[0].from_user, self.second_member.name)
		self.assertEqual(str(rows[0].discussion), str(self.discussion.name))

	def test_votes_fold_into_one_row(self):
		self.vote(self.second_member)
		self.vote(self.admin, "No")

		rows = self.notifications_for(self.member)
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0].event_count, 2)
		self.assertEqual(rows[0].message, "2 people voted on your poll")
		self.assertIsNone(rows[0].from_user)

	def test_changing_a_vote_is_not_another_person_voting(self):
		self.vote(self.second_member, "Yes")
		self.vote(self.second_member, "No")

		self.assertEqual(self.notifications_for(self.member)[0].event_count, 1)

	def test_the_author_voting_on_their_own_poll_is_not_news(self):
		self.vote(self.member)

		self.assertEqual(self.notifications_for(self.member), [])

	def test_retracting_a_vote_is_not_news(self):
		self.vote(self.second_member)
		self.forget_notifications_so_far()

		self.retract(self.second_member)

		self.assertEqual(self.notifications_for(self.member), [])

	def test_an_anonymous_poll_names_nobody(self):
		with self.as_user(self.member):
			poll = create_poll("Secret ballot", self.discussion, anonymous=1)
		self.forget_notifications_so_far()

		self.vote(self.second_member, poll=poll)

		rows = self.notifications_for(self.member)
		self.assertEqual(rows[0].message, "1 person voted on your poll")
		self.assertIsNone(rows[0].from_user)

	def test_the_toggle_turns_it_off(self):
		self.set_prefs(self.member, notify_poll_votes=0)

		self.vote(self.second_member)

		self.assertEqual(self.notifications_for(self.member), [])

	def test_opening_the_discussion_clears_it(self):
		self.vote(self.second_member)

		with self.as_user(self.member):
			frappe.get_doc("GP Discussion", self.discussion.name).track_visit()

		self.assertEqual(self.notifications_for(self.member, read=0), [])


class TestAccessLoss(SpaceNotificationTestCase):
	def setUp(self):
		super().setUp()
		self.private = create_space(
			"Secret", self.community, is_private=1, members=[self.admin, self.second_member]
		)
		self.discussion = self.start_discussion(self.admin, space=self.private)
		self.subscribe(self.second_member, self.private)
		frappe.get_doc(
			doctype="GP Discussion Subscription",
			user=self.second_member.name,
			discussion=self.discussion.name,
			state="Watch",
		).insert(ignore_permissions=True)

	def assert_forgotten(self, user=None):
		user = user or self.second_member
		self.assertEqual(self.subscriptions_for(user, self.private), [])
		self.assertEqual(self.discussion_subscriptions_for(user), [])

	def test_leaving_a_space_forgets_every_choice_about_it(self):
		with self.as_user(self.second_member):
			frappe.get_doc("GP Project", self.private.name).leave()

		self.assert_forgotten()

	def test_being_removed_from_a_space_forgets_every_choice_about_it(self):
		with self.as_user(self.admin):
			frappe.get_doc("GP Project", self.private.name).remove_member(self.second_member.name)

		self.assert_forgotten()

	def test_a_choice_about_another_space_survives(self):
		self.subscribe(self.second_member, self.space)

		with self.as_user(self.second_member):
			frappe.get_doc("GP Project", self.private.name).leave()

		self.assertEqual(len(self.subscriptions_for(self.second_member, self.space)), 1)

	def test_a_removed_guest_is_forgotten(self):
		grant_guest_access(self.guest, self.private)
		self.subscribe(self.guest, self.private)

		with self.as_user(self.admin):
			frappe.get_doc("GP Project", self.private.name).remove_guest(self.guest.name)

		self.assert_forgotten(self.guest)

	def test_being_removed_from_a_community_forgets_its_private_spaces(self):
		self.subscribe(self.second_member, self.space)

		with self.as_user(self.admin):
			frappe.get_doc("GP Team", self.community.name).remove_member(self.second_member.name)

		self.assert_forgotten()
		# The public space stays readable, so the choice about it stays too.
		self.assertEqual(len(self.subscriptions_for(self.second_member, self.space)), 1)

	def test_being_removed_from_a_private_community_forgets_every_space(self):
		closed = create_community("Closed", is_private=1, members=[self.second_member], admins=[self.admin])
		closed_space = create_space("Lobby", closed)
		self.subscribe(self.second_member, closed_space)

		with self.as_user(self.admin):
			frappe.get_doc("GP Team", closed.name).remove_member(self.second_member.name)

		self.assertEqual(self.subscriptions_for(self.second_member, closed_space), [])

	def test_rejoining_starts_clean(self):
		with self.as_user(self.second_member):
			frappe.get_doc("GP Project", self.private.name).leave()
		with self.as_user(self.admin):
			frappe.get_doc("GP Project", self.private.name).add_member(self.second_member.name)

		self.assert_forgotten()
