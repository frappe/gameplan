from unittest.mock import patch

import frappe
from frappe.api.v2 import update_doc

from gameplan.gameplan.doctype.gp_team.gp_team import update_joined_teams
from gameplan.gameplan.doctype.gp_user_profile.gp_user_profile import save_my_bento_cards
from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import create_community, create_discussion, create_poll, create_space


class TestParentManagedRows(GameplanTestCase):
	def setUp(self):
		super().setUp()
		self.community = create_community("Row Community", admins=[self.member])
		self.space = create_space("Row Space", self.community, members=[self.member])
		self.discussion = create_discussion("Row Discussion", self.space, owner=self.member)
		self.poll = create_poll("Row Poll", self.discussion, owner=self.member)

	def test_rows_are_updated_through_their_parents(self):
		other_poll = create_poll("Other Row Poll", self.discussion, owner=self.member)
		tag = frappe.get_doc(doctype="GP Tag", label="First").insert(ignore_permissions=True)
		other_tag = frappe.get_doc(doctype="GP Tag", label="Second").insert(ignore_permissions=True)
		self.discussion.reload()
		self.discussion.append("tags", {"tag": tag.name})
		self.discussion.save(ignore_permissions=True)
		with self.as_user(self.member):
			self.poll.submit_vote("Yes")
			save_my_bento_cards(
				[{"id": "intro", "type": "Card", "size": "1x1", "title": "Intro", "text": "Hello"}]
			)
		profile = frappe.get_doc("GP User Profile", {"user": self.member.name})
		rows = [
			(
				self.poll.votes[0],
				{"user": self.second_member.name, "option": "No", "parent": other_poll.name},
			),
			(self.poll.options[0], {"title": "Another", "votes": 5, "parent": other_poll.name}),
			(self.discussion.tags[0], {"tag": other_tag.name}),
			(self.community.get_member(self.member.name), {"user": self.second_member.name, "is_admin": 0}),
			(profile.bento_cards[0], {"text": "Updated"}),
		]
		for row, changes in rows:
			user = self.second_member if row.parenttype == "GP Poll" else self.member
			with self.subTest(doctype=row.doctype), self.as_user(user):
				before = frappe.get_doc(row.doctype, row.name).as_dict()
				with patch.object(frappe.local, "form_dict", frappe._dict(changes)):
					with self.assertRaises(frappe.PermissionError):
						update_doc(row.doctype, row.name)
				stored = frappe.get_doc(row.doctype, row.name)
				for field in changes:
					self.assertEqual(stored.get(field), before[field])
			with self.as_user(self.member), self.assertRaises(frappe.PermissionError):
				frappe.delete_doc(row.doctype, row.name)

		with self.as_user(self.member):
			self.poll.retract_vote()
			poll = frappe.get_doc("GP Poll", self.poll.name)
			poll.options[0].title = "Updated"
			poll.save()
			discussion = frappe.get_doc("GP Discussion", self.discussion.name)
			discussion.tags[0].tag = other_tag.name
			discussion.save()
			self.community.add_members([self.second_member.name])
			save_my_bento_cards(
				[{"id": "intro", "type": "Card", "size": "1x1", "title": "Intro", "text": "Updated"}]
			)
		self.assertEqual(frappe.get_doc("GP Poll", self.poll.name).total_votes, 0)
		self.assertEqual(frappe.get_doc("GP Poll", self.poll.name).options[0].title, "Updated")
		self.assertEqual(frappe.get_doc("GP Discussion", self.discussion.name).tags[0].tag, other_tag.name)
		self.assertIsNotNone(self.community.get_member(self.second_member.name))
		self.assertEqual(profile.reload().bento_cards[0].text, "Updated")

	def test_new_polls_start_with_empty_results(self):
		for anonymous in (0, 1):
			with self.subTest(anonymous=anonymous), self.as_user(self.member):
				poll = frappe.get_doc(
					doctype="GP Poll",
					title="Fresh Poll",
					discussion=self.discussion.name,
					anonymous=anonymous,
					options=[{"title": "Yes", "votes": 8, "percentage": 100}, {"title": "No"}],
					votes=[{"user": self.second_member.name, "option": "Yes"}],
					total_votes=8,
				).insert()
				poll.reload()
				self.assertEqual(poll.votes, [])
				self.assertEqual(poll.total_votes, 0)
				self.assertTrue(all(option.votes == 0 and option.percentage == 0 for option in poll.options))
				poll.submit_vote("Yes")
				self.assertEqual(poll.total_votes, 1)
				self.assertEqual(poll.options[0].votes, 1)

				edits = {
					"votes": lambda p: p.append("votes", {"user": self.second_member.name, "option": "No"}),
					"counts": lambda p: p.options[1].update({"votes": 5, "percentage": 50}),
				}
				for name, edit in edits.items():
					with self.subTest(edit=name):
						edited = frappe.get_doc("GP Poll", poll.name)
						edit(edited)
						with self.assertRaises(frappe.PermissionError):
							edited.save()
						stored = frappe.get_doc("GP Poll", poll.name)
						self.assertEqual([d.user for d in stored.votes], [self.member.name])
						self.assertEqual([d.votes for d in stored.options], [1, 0])
						self.assertEqual(stored.total_votes, 1)


class TestSpaceCommunityValidation(GameplanTestCase):
	def test_space_creation_uses_visible_communities_and_creator_membership(self):
		hidden = create_community("Other Community", is_private=1, members=[self.second_member])
		joined = create_community("Joined Community", is_private=1, members=[self.member])
		public = create_community("Visible Community")
		with self.as_user(self.member):
			with self.assertRaises(frappe.PermissionError):
				frappe.get_doc(doctype="GP Project", title="New Space", team=hidden.name).insert()
			for team in (joined.name, public.name, None):
				with self.subTest(team=team):
					space = frappe.get_doc(
						doctype="GP Project",
						title="New Space",
						team=team,
						is_private=1,
						members=[
							{"user": self.second_member.name},
							{"user": self.member.name, "is_admin": 1},
						],
					).insert()
					self.assertEqual(
						[(row.user, row.is_admin) for row in space.reload().members], [(self.member.name, 0)]
					)

	def test_space_saves_apply_community_move_rules(self):
		origin = create_community("Source Community", admins=[self.member])
		destination = create_community("Destination Community", members=[self.member])
		hidden = create_community("Other Destination", is_private=1, members=[self.second_member])
		space = create_space("Moving Space", origin, is_private=1, members=[self.member])
		discussion = create_discussion("Moving Discussion", space)
		with self.as_user(self.member):
			with patch.object(frappe.local, "form_dict", frappe._dict(team=hidden.name)):
				with self.assertRaises(frappe.PermissionError):
					update_doc("GP Project", space.name)
			self.assertEqual(space.reload().team, origin.name)
			with patch.object(frappe.local, "form_dict", frappe._dict(team=destination.name)):
				update_doc("GP Project", space.name)
		self.assertEqual(space.reload().team, destination.name)
		self.assertEqual(discussion.reload().team, destination.name)
		with self.as_user(self.outsider):
			with patch.object(frappe.local, "form_dict", frappe._dict(team=origin.name, is_private=1)):
				with self.assertRaises(frappe.PermissionError):
					update_doc("GP Project", space.name)


class TestJoinedCommunityValidation(GameplanTestCase):
	def test_bulk_leave_keeps_an_admin_until_another_is_assigned(self):
		community = create_community("Managed Community", admins=[self.member])
		other = create_community("Retained Community", members=[self.member])
		for row in list(community.members):
			if row.user != self.member.name:
				community.remove(row)
		community.save(ignore_permissions=True)
		with self.as_user(self.member):
			with self.assertRaises(frappe.ValidationError):
				update_joined_teams([other.name])
		self.assertIsNotNone(community.reload().get_member(self.member.name))
		community.add_member(self.second_member.name, is_admin=1)
		community.save(ignore_permissions=True)
		with self.as_user(self.member):
			self.assertEqual(update_joined_teams([other.name]), [other.name])
		self.assertIsNone(community.reload().get_member(self.member.name))
		self.assertEqual(community.count_admins(), 1)
