import threading

import frappe
from frappe.tests.utils import FrappeTestCase

from gameplan.approval_policy import set_policy
from gameplan.approvals import decide, detail, submit
from gameplan.tests.fixtures import create_community, create_member, create_space
from gameplan.tests.search_isolation import guard_real_index


class TestApprovalConcurrency(FrappeTestCase):
	def setUp(self):
		if frappe.db.db_type != "mariadb":
			self.skipTest("Tests MariaDB row locks")
		frappe.set_user("Administrator")
		guard_real_index(self)
		self.author = create_member(f"approval_{frappe.generate_hash()}@example.com", "Approval author")
		self.community = create_community(f"Approval race {frappe.generate_hash()}", members=[self.author])
		self.space = create_space("Approval race", self.community)
		set_policy(self.community.name, 3)
		frappe.db.commit()
		self.addCleanup(self.cleanup)

	def cleanup(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()
		frappe.db.delete("GP Submission", {"owner": self.author.name})
		frappe.db.delete("GP Approval Counter", {"user": self.author.name})
		frappe.delete_doc("GP Team", self.community.name, ignore_permissions=True, force=True)
		frappe.delete_doc("User", self.author.name, ignore_permissions=True, force=True)
		frappe.db.commit()

	def submit(self, key):
		return submit(
			"GP Discussion",
			key,
			"Concurrent submission",
			project=str(self.space.name),
			title="Concurrent approval",
		)

	def concurrently(self, user, action):
		site, sites_path = frappe.local.site, frappe.local.sites_path
		barrier, results, errors = threading.Barrier(2), [], []

		def run(index):
			frappe.init(site, sites_path=sites_path)
			try:
				frappe.connect()
				frappe.set_user(user)
				frappe.get_doc("GP Project", self.space.name)
				barrier.wait(timeout=20)
				result = action(index)
				frappe.db.commit()
				results.append(result)
			except Exception as error:
				errors.append(error)
				frappe.db.rollback()
			finally:
				frappe.destroy()

		threads = [threading.Thread(target=run, args=(index,)) for index in range(2)]
		for thread in threads:
			thread.start()
		for thread in threads:
			thread.join(timeout=40)
		self.assertFalse(any(thread.is_alive() for thread in threads))
		frappe.db.rollback()
		return results, errors

	def test_duplicate_submissions_and_counter_initialization_are_serialized(self):
		results, errors = self.concurrently(self.author.name, lambda _: self.submit("same-intent"))
		self.assertEqual(errors, [])
		self.assertEqual(results[0], results[1])
		self.assertEqual(frappe.db.count("GP Submission", {"owner": self.author.name}), 1)
		self.assertEqual(frappe.db.count("GP Approval Counter", {"user": self.author.name}), 1)

	def test_pending_capacity_cannot_be_exceeded_concurrently(self):
		frappe.set_user(self.author.name)
		for index in range(4):
			self.submit(str(index))
		frappe.db.commit()
		results, errors = self.concurrently(self.author.name, lambda index: self.submit(f"last-{index}"))
		self.assertEqual(len(results), 1)
		self.assertEqual(len(errors), 1)
		self.assertIsInstance(errors[0], frappe.RateLimitExceededError)
		self.assertEqual(frappe.db.count("GP Submission", {"owner": self.author.name}), 5)

	def test_concurrent_approval_publishes_and_counts_once(self):
		frappe.set_user(self.author.name)
		item = self.submit("approve-once")
		frappe.set_user("Administrator")
		version = str(detail(item["name"]).modified)
		frappe.db.commit()
		results, errors = self.concurrently(
			"Administrator", lambda _: decide(item["name"], "Approve", version)
		)
		self.assertEqual(errors, [])
		self.assertEqual(results[0], results[1])
		self.assertEqual(frappe.db.count("GP Discussion", {"owner": self.author.name}), 1)
		self.assertEqual(
			frappe.db.get_value("GP Approval Counter", {"user": self.author.name}, "accepted"), 1
		)
