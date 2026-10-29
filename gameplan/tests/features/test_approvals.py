from html import escape

import frappe

from gameplan.approval_policy import set_policy
from gameplan.approvals import decide, detail, queue, submit
from gameplan.community_bans import set_ban
from gameplan.gameplan.doctype.gp_draft.gp_draft import publish_draft, publish_due_drafts
from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import create_community, create_discussion, create_member, create_space


class TestApprovals(GameplanTestCase):
	def setUp(self):
		super().setUp()
		self.community = create_community(
			"Approval policy", members=[self.member, self.second_member, self.outsider]
		)
		self.community.set_member_moderator(self.second_member.name, 1)
		self.space = create_space("Approval Space", self.community)
		self.parent = create_discussion("Parent", self.space, owner=self.outsider)
		set_policy(self.community.name, 3)

	def submit(self, *, reply=False, key=None, content="<p>Review these words</p>"):
		with self.as_user(self.member):
			return submit(
				"GP Comment" if reply else "GP Discussion",
				key or frappe.generate_hash(),
				content,
				project=str(self.space.name),
				discussion=str(self.parent.name) if reply else "",
				title="A held discussion" if not reply else "",
			)

	def decide(self, result, decision="Approve", note=""):
		with self.as_user(self.second_member):
			row = detail(result["name"])
			return decide(result["name"], decision, str(row.modified), note)

	def test_first_n_approvals_publish_once_as_author_then_allow_direct_posting(self):
		for index in range(3):
			result = self.submit(reply=bool(index % 2))
			self.assertEqual(result["status"], "Pending")
			approved = self.decide(result)
			doc = frappe.get_doc(approved["published_doctype"], approved["published_name"])
			self.assertEqual(doc.owner, self.member.name)
			self.assertEqual(
				frappe.db.get_value("GP Submission", result["name"], "decided_by"), self.second_member.name
			)
			self.assertEqual(self.decide(result), approved)
		result = self.submit()
		self.assertEqual(result["doctype"], "GP Discussion")
		self.assertEqual(len(queue(self.community.name, status="Approved")["items"]), 3)
		self.assertEqual(
			frappe.db.get_value(
				"GP Approval Counter",
				{"user": self.member.name, "community": self.community.name},
				"accepted",
			),
			4,
		)

	def test_reject_withdraw_and_retry_do_not_publish_or_earn_credit(self):
		result = self.submit(key="same-intent")
		self.assertEqual(self.submit(key="same-intent"), result)
		with self.assertRaises(frappe.ValidationError):
			self.submit(key="same-intent", content="Changed intent")
		with self.assertRaises(frappe.ValidationError):
			self.decide(result, "Reject")
		self.decide(result, "Reject", "Please explain the problem you are solving")
		with self.as_user(self.member):
			row = detail(result["name"])
			self.assertIn("Please explain", row.decision_note)
			with self.assertRaises(frappe.TimestampMismatchError):
				decide(row.name, "Withdraw", str(row.modified))
		other = self.submit()
		with self.as_user(self.member):
			row = detail(other["name"])
			decide(row.name, "Withdraw", str(row.modified))
		self.assertEqual(
			frappe.db.get_value(
				"GP Approval Counter",
				{"user": self.member.name, "community": self.community.name},
				"accepted",
			),
			0,
		)
		self.assertEqual(
			frappe.db.count("GP Discussion", {"owner": self.member.name, "project": self.space.name}), 0
		)

	def test_policy_changes_never_publish_or_duplicate_existing_queue_items(self):
		result = self.submit(key="pending-before-disable")
		set_policy(self.community.name, 0)
		self.assertEqual(self.submit(key="pending-before-disable"), result)
		self.assertEqual(self.submit()["doctype"], "GP Discussion")
		self.assertEqual(frappe.db.get_value("GP Submission", result["name"], "status"), "Pending")
		self.decide(result)

	def test_existing_contributors_and_staff_are_exempt_and_earned_counts_do_not_shrink(self):
		docs = [create_discussion(f"Existing {i}", self.space, owner=self.member) for i in range(3)]
		self.assertEqual(self.submit()["doctype"], "GP Discussion")
		for doc in docs:
			doc.hide("Later moderation")
		self.assertEqual(self.submit()["doctype"], "GP Discussion")
		with self.as_user(self.second_member):
			result = submit(
				"GP Discussion", "staff", "Staff content", project=str(self.space.name), title="Staff post"
			)
		self.assertEqual(result["doctype"], "GP Discussion")
		elsewhere = create_community("Separate progress", members=[self.member])
		space = create_space("Elsewhere", elsewhere)
		set_policy(elsewhere.name, 3)
		with self.as_user(self.member):
			result = submit(
				"GP Discussion", "elsewhere", "New Community", project=str(space.name), title="New start"
			)
		self.assertEqual(result["status"], "Pending")

	def test_capacity_and_raw_document_apis_cannot_bypass_approval(self):
		for _ in range(5):
			self.submit()
		with self.assertRaises(frappe.RateLimitExceededError):
			self.submit()
		with self.as_user(self.member):
			for doctype, values in (
				("GP Discussion", {"project": self.space.name, "title": "Bypass"}),
				("GP Comment", {"reference_doctype": "GP Discussion", "reference_name": self.parent.name}),
			):
				with self.subTest(doctype=doctype), self.assertRaises(frappe.PermissionError):
					doc = frappe.get_doc(doctype=doctype, content="Bypass", **values)
					doc.flags.approved_submission = True
					doc.insert(ignore_permissions=True)
			with self.assertRaises(frappe.PermissionError):
				set_policy(self.community.name, 0)

	def test_approval_rechecks_bans_closed_parent_and_disabled_account(self):
		result = self.submit(reply=True)
		set_ban(self.community.name, self.member.name, 1, "No participation")
		with self.assertRaises(frappe.PermissionError):
			self.decide(result)
		set_ban(self.community.name, self.member.name, 0)
		self.parent.close_discussion()
		with self.assertRaises(frappe.ValidationError):
			self.decide(result)
		self.parent.reopen_discussion()
		frappe.db.set_value("User", self.member.name, "enabled", 0)
		with self.assertRaises(frappe.PermissionError):
			self.decide(result)
		self.assertEqual(frappe.db.get_value("GP Submission", result["name"], "status"), "Pending")

	def test_private_queue_and_decisions_require_current_authority(self):
		result = self.submit()
		with self.as_user(self.outsider):
			with self.assertRaises(frappe.PermissionError):
				detail(result["name"])
			with self.assertRaises(frappe.PermissionError):
				queue(self.community.name)
		self.community.set_member_moderator(self.second_member.name, 0)
		with self.assertRaises(frappe.PermissionError):
			self.decide(result)

	def test_embedded_poll_is_created_only_after_approval(self):
		payload = escape(
			frappe.as_json({"title": "Held question", "options": [{"title": "Yes"}, {"title": "No"}]}),
			quote=True,
		)
		result = self.submit(
			reply=True, content=f'<p>Question</p><div data-type="poll" data-poll-draft="{payload}"></div>'
		)
		self.assertFalse(frappe.db.exists("GP Poll", {"title": "Held question"}))
		self.decide(result)
		self.assertTrue(frappe.db.exists("GP Poll", {"title": "Held question"}))

	def test_draft_and_scheduled_publication_enter_the_queue(self):
		for scheduled in (False, True):
			with self.as_user(self.member):
				draft = frappe.get_doc(
					doctype="GP Draft",
					type="Discussion",
					mode="New",
					project=str(self.space.name),
					title="Draft approval",
					content="Queued draft",
				).insert()
				if scheduled:
					draft.db_set(
						"scheduled_at", frappe.utils.add_to_date(frappe.utils.now_datetime(), minutes=-1)
					)
					publish_due_drafts()
				else:
					self.assertEqual(draft.publish()["status"], "Pending")
				self.assertFalse(frappe.db.exists("GP Draft", draft.name))
		self.assertEqual(
			frappe.db.count("GP Submission", {"owner": self.member.name, "project": self.space.name}), 2
		)

	def test_approved_attachment_removes_draft_file_identity_and_becomes_readable(self):
		with self.as_user(self.member):
			file = frappe.get_doc(
				doctype="File", file_name="approved.txt", content=b"Approved bytes", is_private=1
			).save(ignore_permissions=True)
		result = self.submit(content=f'<a href="{file.file_url}?fid={file.name}">Attachment</a>')
		approved = self.decide(result)
		doc = frappe.get_doc(approved["published_doctype"], approved["published_name"])
		self.assertNotIn("?fid=", doc.content)
		published_file = frappe.db.get_value(
			"File",
			{"file_url": file.file_url, "attached_to_doctype": doc.doctype, "attached_to_name": doc.name},
		)
		self.assertTrue(published_file)
		with self.as_user(self.outsider):
			self.assertEqual(frappe.get_doc("File", published_file).get_content(), "Approved bytes")

	def test_publication_preserves_the_reviewers_session_and_request(self):
		result = self.submit()
		with self.as_user(self.second_member):
			row = detail(result["name"])
			frappe.session.sid = "reviewer-session"
			frappe.session.data = frappe._dict(user=self.second_member.name, preserved="session data")
			frappe.local.form_dict = frappe._dict(cmd="gameplan.approvals.decide")
			decide(row.name, "Approve", str(row.modified))
			self.assertEqual(frappe.session.user, self.second_member.name)
			self.assertEqual(frappe.session.sid, "reviewer-session")
			self.assertEqual(frappe.session.data.preserved, "session data")
			self.assertEqual(frappe.local.form_dict.cmd, "gameplan.approvals.decide")

	def test_held_submission_retries_survive_source_draft_cleanup(self):
		with self.as_user(self.member):
			draft = frappe.get_doc(
				doctype="GP Draft",
				type="Discussion",
				mode="New",
				project=self.space.name,
				title="Retry draft",
				content="Preserve retry",
			).insert()
			first = publish_draft(draft.name)
			self.assertEqual(publish_draft(draft.name), first)
			draft = frappe.get_doc(
				doctype="GP Draft",
				type="Comment",
				mode="New",
				reference_doctype="GP Discussion",
				reference_name=self.parent.name,
				content="Retry reply",
			).insert()
			values = dict(
				doctype="GP Comment",
				request_key=f"draft:{draft.name}",
				discussion=str(self.parent.name),
				content="Retry reply",
				draft=draft.name,
			)
			first = submit(**values)
			self.assertEqual(submit(**values), first)

	def test_community_deletion_discards_progress_and_preserves_restricted_submissions(self):
		other = create_community("Deleted approval Community", members=[self.member])
		space = create_space("Deleted approval Space", other)
		set_policy(other.name, 3)
		with self.as_user(self.member):
			result = submit(
				"GP Discussion",
				"delete-community",
				"Kept evidence",
				project=str(space.name),
				title="Retained submission",
			)
		frappe.delete_doc("GP Team", other.name, ignore_permissions=True, force=True)
		self.assertFalse(frappe.db.exists("GP Approval Counter", {"community": other.name}))
		self.assertTrue(frappe.db.exists("GP Submission", result["name"]))

	def test_archived_community_prevents_approval(self):
		result = self.submit()
		self.community.archive()
		with self.assertRaises(frappe.ValidationError):
			self.decide(result)
		self.assertEqual(frappe.db.get_value("GP Submission", result["name"], "status"), "Pending")

	def test_account_deletion_clears_approval_progress_without_deleting_evidence(self):
		user = create_member(f"approval_delete_{frappe.generate_hash()}@example.com", "Removed author")
		self.community.add_members([user.name])
		with self.as_user(user):
			result = submit(
				"GP Discussion",
				"delete-account",
				"Retained words",
				project=str(self.space.name),
				title="Retained author",
			)
		self.community.remove_member(user.name)
		frappe.delete_doc("User", user.name, ignore_permissions=True, force=True)
		self.assertFalse(frappe.db.exists("GP Approval Counter", {"user": user.name}))
		self.assertTrue(frappe.db.exists("GP Submission", result["name"]))
