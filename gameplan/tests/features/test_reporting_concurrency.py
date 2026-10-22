import threading

import frappe
from frappe.tests.utils import FrappeTestCase

from gameplan.reporting import detail, resolve, submit
from gameplan.tests.fixtures import create_community, create_discussion, create_member, create_space
from gameplan.tests.search_isolation import guard_real_index


class TestReportingConcurrency(FrappeTestCase):
	def setUp(self):
		if frappe.db.db_type != "mariadb":
			self.skipTest("Tests MariaDB row locks")
		frappe.set_user("Administrator")
		guard_real_index(self)
		suffix = frappe.generate_hash(length=8)
		self.owner = create_member(f"report_owner_{suffix}@example.com", "Owner")
		self.reporter = create_member(f"reporter_{suffix}@example.com", "Reporter")
		self.other_reporter = create_member(f"reporter2_{suffix}@example.com", "Other Reporter")
		self.community = create_community(
			f"Concurrent reports {suffix}", members=[self.owner, self.reporter, self.other_reporter]
		)
		self.discussion = create_discussion(
			"Concurrent reports", create_space("Reports", self.community), owner=self.owner
		)
		frappe.db.commit()
		self.targets = [str(self.discussion.name)]
		self.addCleanup(self.cleanup_fixtures)

	def cleanup_fixtures(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()
		doc = frappe.get_doc("GP Discussion", self.discussion.name)
		if doc.hidden_at or doc.spam_removed_at:
			doc.restore()
		reviews = frappe.get_all(
			"GP Review",
			filters={"reference_doctype": "GP Discussion", "reference_name": ["in", self.targets]},
			pluck="name",
		)
		for dt, filters in (
			("GP Report", {"review": ["in", reviews]}),
			("GP Review", {"reference_doctype": "GP Discussion", "reference_name": ["in", self.targets]}),
			("GP Moderation Log", {"discussion": ["in", self.targets]}),
		):
			frappe.db.delete(dt, filters)
		frappe.delete_doc("GP Team", self.community.name, ignore_permissions=True, force=True)
		for user in (self.owner, self.reporter, self.other_reporter):
			frappe.delete_doc("User", user.name, ignore_permissions=True, force=True)
		frappe.db.commit()

	def concurrently(self, user, action):
		site, sites_path = frappe.local.site, frappe.local.sites_path
		barrier, results, errors = threading.Barrier(2), [], []

		def run(index):
			frappe.init(site, sites_path=sites_path)
			try:
				frappe.connect()
				frappe.set_user(user[index] if isinstance(user, list) else user)
				frappe.get_doc("GP Discussion", self.discussion.name)
				barrier.wait(timeout=20)
				results.append(action(index))
				frappe.db.commit()
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

	def test_simultaneous_duplicate_reports_create_one_report_and_review(self):
		results, errors = self.concurrently(
			self.reporter.name, lambda _index: submit("GP Discussion", str(self.discussion.name), "Spam")
		)
		self.assertEqual(errors, [])
		self.assertEqual(results[0], results[1])
		self.assertEqual(frappe.db.count("GP Report", {"owner": self.reporter.name}), 1)
		self.assertEqual(
			frappe.db.count(
				"GP Review",
				{"reference_doctype": "GP Discussion", "reference_name": str(self.discussion.name)},
			),
			1,
		)

	def test_simultaneous_decisions_make_one_content_action(self):
		frappe.set_user(self.reporter.name)
		report = submit("GP Discussion", str(self.discussion.name), "Spam")["name"]
		review = frappe.db.get_value("GP Report", report, "review")
		frappe.set_user("Administrator")
		version = detail(self.community.name, review)["current"]["version"]
		frappe.db.commit()
		results, errors = self.concurrently(
			"Administrator", lambda _index: resolve(self.community.name, review, "Hide", "Reviewed", version)
		)
		self.assertEqual(len(results), 1)
		self.assertEqual(len(errors), 1)
		self.assertIsInstance(errors[0], frappe.TimestampMismatchError)
		self.assertEqual(
			frappe.db.count("GP Moderation Log", {"discussion": str(self.discussion.name), "action": "Hide"}),
			1,
		)

	def test_simultaneous_reports_on_different_targets_cannot_exceed_the_quota(self):
		other = create_discussion("Other target", self.discussion.project, owner=self.owner)
		self.targets.append(str(other.name))
		for _ in range(9):
			review = frappe.get_doc(
				doctype="GP Review",
				reference_doctype="GP Discussion",
				reference_name=str(self.discussion.name),
				status="Resolved",
			).insert(ignore_permissions=True)
			frappe.get_doc(
				doctype="GP Report", review=review.name, reason="Spam", owner=self.reporter.name
			).insert(ignore_permissions=True)
		frappe.db.commit()
		results, errors = self.concurrently(
			self.reporter.name, lambda index: submit("GP Discussion", self.targets[index], "Spam")
		)
		self.assertEqual(len(results), 1)
		self.assertEqual(len(errors), 1)
		self.assertIsInstance(errors[0], frappe.RateLimitExceededError)
		self.assertEqual(frappe.db.count("GP Report", {"owner": self.reporter.name}), 10)

	def test_simultaneous_different_reporters_share_one_review(self):
		results, errors = self.concurrently(
			[self.reporter.name, self.other_reporter.name],
			lambda _index: submit("GP Discussion", str(self.discussion.name), "Spam"),
		)
		self.assertEqual(errors, [])
		self.assertNotEqual(results[0], results[1])
		self.assertEqual(
			frappe.db.get_value("GP Report", results[0]["name"], "review"),
			frappe.db.get_value("GP Report", results[1]["name"], "review"),
		)
