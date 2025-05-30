# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and Contributors

import random

import frappe

from gameplan.gemoji import get_random_gemoji


def generate_teams_and_projects():
	"""Generate demo teams and projects for Techflow Inc."""

	# Generate teams first
	teams_data = generate_teams_data()
	created_teams = []

	for i, team_data in enumerate(teams_data):
		frappe.utils.update_progress_bar("Creating Teams", i, len(teams_data), absolute=True)
		team = create_team(team_data)
		if team:
			created_teams.append(team)
	frappe.utils.update_progress_bar("Creating Teams", len(teams_data), len(teams_data), absolute=True)
	print()

	# Generate projects for each team
	projects_to_create = []
	created_projects = []
	for team in created_teams:
		projects_to_create += generate_projects_data_for_team(team)

	for i, project_data in enumerate(projects_to_create):
		frappe.utils.update_progress_bar("Creating Projects", i, len(projects_to_create), absolute=True)
		project = create_project(project_data)
		if project:
			created_projects.append(project)

	frappe.utils.update_progress_bar(
		"Creating Projects",
		len(projects_to_create),
		len(projects_to_create),
		absolute=True,
	)
	print()

	# Assign users to projects with realistic variations
	assign_users_to_projects(created_projects)

	frappe.db.commit()


def generate_teams_data():
	"""Generate data for 8-10 teams."""
	teams = [
		{"title": "Engineering"},
		{"title": "Marketing"},
		{"title": "Product"},
		{"title": "Design"},
		{"title": "Sales"},
		{"title": "Customer Success"},
		{"title": "Operations"},
		{"title": "Human Resources"},
		{"title": "Finance"},
		{"title": "Data Science"},
		{"title": "Company"},
	]

	return teams


def generate_projects_data_for_team(team):
	"""Generate 3-6 projects for a given team."""
	project_templates = {
		"Engineering": [
			"Coffee-Driven API",
			"Zero-Downtime Dreams",
			"Bug Hunt 2025",
			"Midnight Deploy Club",
			"Scale or Die Trying",
			"The Great Refactor",
			"Ship It Friday",
			"Architecture Rebellion",
			"Database Whisperer",
		],
		"Marketing": [
			"Viral or Bust Campaign",
			"Growth Hacking Olympics",
			"Content Chaos Theory",
			"The Meme Strategy",
			"Influencer Invasion",
			"Brand Storm 2025",
			"Customer Love Fest",
			"SEO Ninja Project",
			"Social Media Takeover",
		],
		"Product": [
			"User-First Revolution",
			"Feature Flag Fiesta",
			"MVP Speed Run",
			"Product Hunt Domination",
			"Feedback Frenzy",
			"A/B Test Everything",
			"Customer Discovery Quest",
			"Roadmap Reality Check",
			"Launch Week Madness",
		],
		"Design": [
			"Pixel Perfect Pursuit",
			"Design System Savior",
			"UX Research Rampage",
			"Prototype Power Hour",
			"Color Palette Wars",
			"User Journey Mapping",
			"Accessibility Heroes",
			"Mobile-First Manifesto",
			"Design Token Revolution",
		],
		"Sales": [
			"Pipeline Pressure Cooker",
			"Deal Closing Olympics",
			"Lead Gen Machine",
			"Revenue Rush Hour",
			"Customer Hunt 2025",
			"Sales Funnel Optimization",
			"Quota Crusher Campaign",
			"Prospect Paradise Project",
			"Win-Rate Warrior",
		],
		"Customer Success": [
			"Happiness Metrics Mission",
			"Churn Prevention Squad",
			"Onboarding Blitz",
			"Support Ticket Terminator",
			"Customer Health Monitor",
			"Renewal Rush Campaign",
			"Success Story Factory",
			"Feedback Loop Hero",
			"Training Boot Camp",
		],
		"Operations": [
			"Process Optimization Overdrive",
			"Automation Army",
			"Efficiency Emergency",
			"Workflow Wizard Project",
			"Remote Work Revolution",
			"Office Space Tetris",
			"Vendor Negotiation Ninja",
			"Cost Cutting Crusade",
			"Quality Control Quest",
		],
		"Human Resources": [
			"Culture Code Rewrite",
			"Talent Acquisition Acceleration",
			"Performance Review Revamp",
			"Remote Onboarding Overhaul",
			"Diversity & Inclusion Drive",
			"Employee Engagement Engine",
			"Benefits Buffet Upgrade",
			"Career Ladder Construction",
			"Wellness Wednesday Warriors",
		],
		"Finance": [
			"Budget Battle Royale",
			"Cash Flow Command Center",
			"Expense Report Revolution",
			"Investment Strategy Sprint",
			"Financial Forecast Frenzy",
			"Compliance Crusaders",
			"Revenue Recognition Rescue",
			"Cost Center Cleanup",
			"Profit Margin Maximizer",
		],
		"Data Science": [
			"Algorithm Alchemy",
			"Data Pipeline Paradise",
			"ML Model Mayhem",
			"Analytics Avengers",
			"Prediction Engine Project",
			"Dashboard Dynasty",
			"Data Quality Detective",
			"AI Experiment Lab",
			"Business Intelligence Blitz",
		],
		"Company": [
			"Annual General Meeting Prep",
			"Q3 Strategy Review",
			"Company Offsite Planning",
			"New Office Setup",
			"Investor Relations Update",
		],
	}

	# Get project templates for this team
	templates = project_templates.get(
		team.title,
		[
			"Startup Sprint Alpha",
			"Growth Hack Beta",
			"MVP Gamma",
			"Scale Delta",
			"Pivot Epsilon",
			"Launch Zeta",
			"Iterate Eta",
			"Disrupt Theta",
		],
	)

	# Generate 3-6 projects per team
	num_projects = random.randint(3, 6)
	selected_templates = random.sample(templates, min(num_projects, len(templates)))

	projects = []
	for i, template in enumerate(selected_templates):
		# Make 1-2 projects private per team
		is_private = 1 if i < 2 and random.random() < 0.3 else 0

		project = {
			"title": template,
			"team": team.name,
			"icon": get_random_gemoji().emoji,
			"is_private": is_private,
			"members": [],  # Members will be added later
		}
		projects.append(project)

	return projects


def create_team(team_data):
	"""Create a GP Team record."""
	try:
		# Check if team already exists
		if frappe.db.exists("GP Team", {"title": team_data["title"]}):
			return frappe.get_doc("GP Team", {"title": team_data["title"]})

		team_doc = frappe.new_doc("GP Team")
		team_doc.title = team_data["title"]
		team_doc.insert()
		return team_doc

	except Exception as e:
		print(f"Error creating team {team_data['title']}: {str(e)}")
		return None


def create_project(project_data):
	"""Create a GP Project record."""
	try:
		# Check if project already exists
		project_exists = frappe.db.exists(
			"GP Project", {"title": project_data["title"], "team": project_data["team"]}
		)
		if project_exists:
			return None

		project_doc = frappe.new_doc("GP Project")
		project_doc.title = project_data["title"]
		project_doc.team = project_data["team"]
		project_doc.icon = project_data["icon"]
		project_doc.is_private = project_data["is_private"]
		project_doc.insert()
		return project_doc

	except Exception as e:
		print(f"Error creating project {project_data['title']}: {str(e)}")
		return None


def get_random_users(count=5):
	"""Get random users from existing Techflow users."""
	try:
		# Get users from the @techflow.com domain
		users = frappe.get_all(
			"User",
			filters={"email": ["like", "%@techflow.com"]},
			fields=["name"],
			limit=count * 2,
		)

		if not users:
			# If no Techflow users, get random active users
			users = frappe.get_all(
				"User", filters={"enabled": 1, "user_type": "System User"}, fields=["name"], limit=count * 2
			)

		if users:
			# Return random selection
			selected_count = min(count, len(users))
			return [user.name for user in random.sample(users, selected_count)]
		else:
			# Fallback to Administrator if no other users
			return ["Administrator"]

	except Exception as e:
		print(f"Error getting random users: {str(e)}")
		return ["Administrator"]


def assign_users_to_projects(projects):
	"""Assign users to projects with realistic variations in involvement levels."""
	# Get all Techflow users
	all_users = get_all_techflow_users()

	# Create user archetypes with different involvement levels
	heavy_contributors = all_users[: int(len(all_users) * 0.15)]  # 15% - high involvement
	active_members = all_users[int(len(all_users) * 0.15) : int(len(all_users) * 0.4)]  # 25% - medium-high
	regular_members = all_users[int(len(all_users) * 0.4) : int(len(all_users) * 0.75)]  # 35% - medium
	occasional_members = all_users[int(len(all_users) * 0.75) :]  # 25% - low involvement

	# Shuffle to randomize which users get which archetype
	random.shuffle(all_users)
	heavy_contributors = all_users[: int(len(all_users) * 0.15)]
	active_members = all_users[int(len(all_users) * 0.15) : int(len(all_users) * 0.4)]
	regular_members = all_users[int(len(all_users) * 0.4) : int(len(all_users) * 0.75)]
	occasional_members = all_users[int(len(all_users) * 0.75) :]

	# Track user assignments
	user_stats = {user: {"projects": 0, "teams": set()} for user in all_users}

	# Assign users to projects based on their archetype
	for project in projects:
		project_members = []

		# Heavy contributors: 80-90% chance to be in any project
		for user in heavy_contributors:
			if random.random() < 0.85:
				project_members.append(user)

		# Active members: 50-70% chance
		for user in active_members:
			if random.random() < 0.6:
				project_members.append(user)

		# Regular members: 30-50% chance
		for user in regular_members:
			if random.random() < 0.4:
				project_members.append(user)

		# Occasional members: 15-25% chance
		for user in occasional_members:
			if random.random() < 0.2:
				project_members.append(user)

		# Ensure each project has at least 3 members and at most 8
		if len(project_members) < 3:
			# Add more users randomly
			remaining_users = [u for u in all_users if u not in project_members]
			needed = 3 - len(project_members)
			project_members.extend(random.sample(remaining_users, min(needed, len(remaining_users))))

		if len(project_members) > 8:
			# Randomly remove some members
			project_members = random.sample(project_members, 8)

		# Add members to project
		for user in project_members:
			project.append("members", {"user": user})
			user_stats[user]["projects"] += 1
			user_stats[user]["teams"].add(project.team)

		project.save()

	# Ensure minimum requirements: every user in at least 4 projects across 3 teams
	for user in all_users:
		stats = user_stats[user]

		if stats["projects"] < 4 or len(stats["teams"]) < 3:
			# Find projects to add this user to
			suitable_projects = []
			for project in projects:
				current_members = [m.user for m in project.members]
				if user not in current_members:
					# Prefer projects from teams the user hasn't been in
					priority = 0 if project.team not in stats["teams"] else 1
					suitable_projects.append((priority, project))

			# Sort by priority and add user to projects
			suitable_projects.sort(key=lambda x: x[0])

			added = 0
			for _priority, project in suitable_projects:
				if stats["projects"] >= 4 and len(stats["teams"]) >= 3:
					break

				project.append("members", {"user": user})
				project.save()
				stats["projects"] += 1
				stats["teams"].add(project.team)
				added += 1

				if added >= 5:  # Don't add to too many projects at once
					break


def get_all_techflow_users():
	"""Get all Techflow users for tracking assignments."""
	try:
		# Get users from the @techflow.com domain
		users = frappe.get_all(
			"User",
			filters={"email": ["like", "%@techflow.com"], "enabled": 1},
			fields=["name"],
		)

		if not users:
			# If no Techflow users, get random active users
			users = frappe.get_all(
				"User", filters={"enabled": 1, "user_type": "System User"}, fields=["name"], limit=20
			)

		return [user.name for user in users]

	except Exception as e:
		print(f"Error getting Techflow users: {str(e)}")
		return ["Administrator"]
