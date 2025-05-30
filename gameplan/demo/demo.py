# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and Contributors

import frappe

from gameplan.demo.discussions_comments import generate_discussions_and_comments
from gameplan.demo.team_projects import generate_teams_and_projects
from gameplan.demo.user import generate_users


def generate(ignore_real_data=False):
	"""Generate demo data for Gameplan including 35 users for Techflow Inc."""

	if not ignore_real_data:
		# Check for existing real data and warn user
		warnings, _ = check_for_real_data()
		if not confirm_operation("generate", warnings):
			print("❌ Demo data generation cancelled by user")
			return

	frappe.conf.disable_gameplan_search = True

	print("🚀 Generating demo data for gameplan...")

	generate_users()
	generate_teams_and_projects()
	generate_discussions_and_comments()

	print("\n🎉 Demo data generation completed!")


def clear(ignore_real_data=False):
	"""Clear all demo data by directly deleting from database tables."""

	if not ignore_real_data:
		# Check for existing real data and warn user
		warnings, real_users_count = check_for_real_data()
		if real_users_count > 0 and not confirm_operation("clear", warnings):
			print("❌ Demo data clearing cancelled by user")
			return

	print("🧹 Clearing all demo data...")

	gameplan_doctypes = [
		# Child/dependent tables first
		"GP Reaction",
		"GP Member",
		"GP Activity",
		"GP Poll Vote",
		"GP Poll Option",
		"GP Comment",
		"GP Discussion Visit",
		"GP Project Visit",
		"GP Pinned Project",
		"GP Followed Project",
		"GP Bookmark",
		"GP Guest Access",
		"GP Invitation",
		"GP Draft",
		"GP Notification",
		# Main content tables
		"GP Discussion",
		"GP Task",
		"GP Page",
		"GP Poll",
		# Project and team tables (parent tables last)
		"GP Project",
		"GP Team",
		# User profile table
		"GP User Profile",
	]

	total_deleted = 0

	# Delete from each doctype table directly
	print("Clearing tables...")
	for doctype in gameplan_doctypes:
		try:
			table_name = f"tab{doctype}"

			# Get count before deletion for reporting
			count_result = frappe.db.sql(f"SELECT COUNT(*) FROM `{table_name}`")
			count = count_result[0][0] if count_result else 0

			if count > 0:
				# Delete all records from the table
				frappe.db.sql(f"DELETE FROM `{table_name}`")
				print(f"Deleted {count} from {doctype}")
				total_deleted += count
			else:
				pass

		except Exception as e:
			print(f"Error in {doctype}: {str(e)}")
			# Continue with other tables even if one fails
			continue

	# Delete Techflow demo users
	try:
		# Get count of users to delete
		user_count_result = frappe.db.sql("""
			SELECT COUNT(*) FROM `tabUser`
			WHERE email LIKE '%@techflow.com'
		""")
		user_count = user_count_result[0][0] if user_count_result else 0

		if user_count > 0:
			print("Deleting users...")
			# Delete users directly from database
			frappe.db.sql("""
				DELETE FROM `tabUser`
				WHERE email LIKE '%@techflow.com'
			""")
			print(f"Deleted {user_count} users")
			total_deleted += user_count
		else:
			print("No Techflow demo users found to delete")

	except Exception as e:
		print(f"❌ Error deleting Techflow users: {str(e)}")

	# Clear any related single doctype settings if needed
	print("\n🔄 Resetting sequences...")
	sequences_to_reset = ["GP Discussion", "GP Comment", "GP Project", "GP Task", "GP Team"]

	for doctype in sequences_to_reset:
		sequence_name = frappe.scrub(doctype + "_id_seq")
		try:
			frappe.db.sql(f"ALTER SEQUENCE `{sequence_name}` RESTART WITH 1")
			print(f"Reset {sequence_name}")
		except Exception:
			print(f"Skipped {sequence_name}")
			# Sequence might not exist, continue
			pass

	# Commit the transaction
	frappe.db.commit()

	print("\n✅ Demo data cleanup completed!")
	print(f"📊 Total records deleted: {total_deleted}")


def check_for_real_data():
	"""Check if database contains real/production data that might be affected."""
	warnings = []

	# Check for non-demo users (users that don't belong to techflow.com)
	real_users_result = frappe.db.sql("""
		SELECT COUNT(*) FROM `tabUser`
		WHERE email NOT LIKE '%@techflow.com'
		AND email NOT IN ('admin@example.com', 'guest@example.com')
		AND enabled = 1
	""")
	real_users_count = real_users_result[0][0] if real_users_result else 0

	if real_users_count > 0:
		user_text = "user" if real_users_count == 1 else "users"
		warnings.append(f"⚠️  {real_users_count} real {user_text} in the system")

	# Check for existing gameplan data that might not be demo data
	gameplan_data_checks = [
		("GP Project", "projects"),
		("GP Team", "teams"),
		("GP Discussion", "discussions"),
		("GP Task", "tasks"),
	]

	for doctype, label in gameplan_data_checks:
		try:
			result = frappe.db.sql(f"SELECT COUNT(*) FROM `tab{doctype}`")
			count = result[0][0] if result else 0
			if count > 0:
				warnings.append(f"⚠️  {count} existing {label}")
		except Exception:
			# Table might not exist yet
			continue

	return warnings, real_users_count


def confirm_operation(operation_name, warnings):
	"""Show warnings and ask for confirmation before proceeding."""
	if not warnings:
		return True

	print("\n🚨 WARNING: Production data detected!")
	print(f"Running '{operation_name}' will affect the following:")
	for warning in warnings:
		print(f"   {warning}")

	print("\nThis operation will:")
	if operation_name == "generate":
		print("   • Add demo users and content to your database")
		print("   • This is generally safe but will add test data")
	elif operation_name == "clear":
		print("   • DELETE ALL Gameplan data (projects, teams, discussions, tasks)")
		print("   • DELETE ALL @techflow.com demo users")
		print("   • This action is PERMANENT and CANNOT be undone!")

	response = input(f"\nAre you sure you want to {operation_name}? (y/N): ").strip().lower()
	return response in ["y", "yes"]


def demo_data_enabled():
	"""Check if demo data generation is enabled in site config."""
	return frappe.conf.get("gameplan_demo_enabled", False)


def generate_data_daily():
	"""Generate daily demo data for Gameplan. Executed by scheduler."""
	if not demo_data_enabled():
		return

	clear(ignore_real_data=True)
	print()
	generate(ignore_real_data=True)
