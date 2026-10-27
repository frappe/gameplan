import threading

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_to_date, now_datetime

from gameplan.approval_policy import set_policy
from gameplan.approvals import submit
from gameplan.slow_mode import set_mode
from gameplan.tests.fixtures import create_community, create_discussion, create_member, create_space
from gameplan.tests.search_isolation import guard_real_index


class TestSlowModeConcurrency(FrappeTestCase):
	def test_concurrent_submissions_cannot_bypass_the_cooldown(self):
		if frappe.db.db_type != "mariadb":
			self.skipTest("Tests MariaDB row locks")
		frappe.set_user("Administrator")
		guard_real_index(self)
		user = create_member(f"slow_{frappe.generate_hash()}@example.com", "Slow mode author")
		community = create_community("Slow mode race", members=[user])
		discussion = create_discussion("Slow mode race", create_space("Slow mode race", community))
		set_policy(community.name, 100)
		set_mode(str(discussion.name), 30, "Concurrency test", 0)
		frappe.db.commit()

		def cleanup():
			frappe.set_user("Administrator")
			frappe.db.rollback()
			frappe.db.delete("GP Submission", {"owner": user.name})
			frappe.delete_doc("GP Team", community.name, ignore_permissions=True, force=True)
			frappe.delete_doc("User", user.name, ignore_permissions=True, force=True)
			frappe.db.commit()

		self.addCleanup(cleanup)
		site, sites_path = frappe.local.site, frappe.local.sites_path
		barrier, successes, errors = threading.Barrier(2), [], []

		def action(index):
			return submit("GP Comment", str(index), "Concurrent reply", discussion=str(discussion.name))

		def run(index):
			frappe.init(site, sites_path=sites_path)
			try:
				frappe.connect()
				frappe.set_user(user.name)
				# Establish a snapshot before the other connection can create the cooldown row.
				frappe.get_doc("GP Discussion", discussion.name)
				barrier.wait(timeout=20)
				result = action(index)
				frappe.db.commit()
				successes.append(result)
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
		self.assertEqual(len(successes), 1)
		self.assertEqual(len(errors), 1)
		self.assertIsInstance(errors[0], frappe.RateLimitExceededError)
		self.assertEqual(frappe.db.count("GP Submission", {"discussion": str(discussion.name)}), 1)

		# Deleting a legacy reply must retain its clock, whichever request wins the account lock.
		set_policy(community.name, 0)
		set_mode(str(discussion.name), 0, "Prepare legacy fixture", 30)
		frappe.set_user(user.name)
		legacy = frappe.get_doc(
			doctype="GP Comment",
			reference_doctype="GP Discussion",
			reference_name=str(discussion.name),
			content="Legacy reply",
		).insert()
		frappe.set_user("Administrator")
		frappe.db.set_value("GP Comment", legacy.name, "creation", add_to_date(now_datetime(), seconds=-5))
		frappe.db.delete("GP Submission", {"owner": user.name})
		frappe.db.delete("GP Slow Mode State", {"discussion": str(discussion.name)})
		set_mode(str(discussion.name), 30, "Protect existing replies", 0)
		frappe.db.commit()
		barrier, successes, errors = threading.Barrier(2), [], []

		def action(index):
			if index == 0:
				return submit("GP Comment", "legacy-race", "Must wait", discussion=str(discussion.name))
			frappe.delete_doc("GP Comment", legacy.name)
			return "deleted"

		threads = [threading.Thread(target=run, args=(index,)) for index in range(2)]
		for thread in threads:
			thread.start()
		for thread in threads:
			thread.join(timeout=40)
		self.assertFalse(any(thread.is_alive() for thread in threads))
		frappe.db.rollback()
		self.assertEqual(successes, ["deleted"])
		self.assertEqual(len(errors), 1)
		self.assertIsInstance(errors[0], frappe.RateLimitExceededError)
		self.assertEqual(frappe.db.count("GP Slow Mode State", {"discussion": str(discussion.name)}), 1)
