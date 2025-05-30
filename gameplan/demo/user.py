# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and Contributors

import random

import frappe
from faker import Faker


def generate_users():
	"""Generate all demo users with user profiles"""
	users_data = generate_users_data()

	created_count = 0
	for i, user_data in enumerate(users_data):
		frappe.utils.update_progress_bar("Creating users", i, len(users_data), absolute=True)
		if create_user_and_profile(user_data):
			created_count += 1
	frappe.utils.update_progress_bar("Creating users", len(users_data), len(users_data), absolute=True)
	print()

	frappe.db.commit()
	return created_count


def generate_avatar_url(first_name, last_name, seed=None):
	"""Generate a random avatar URL using various avatar services."""
	if seed is None:
		seed = f"{first_name.lower()}{last_name.lower()}"
	else:
		seed = str(seed)

	avatar_url = f"https://api.dicebear.com/9.x/open-peeps/svg?seed={seed}&backgroundColor=b6e3f4,c0aede,d1d4f9,ffd5dc,ffdfbf"
	return avatar_url


def generate_users_data():
	"""Generate a list of 35 users for Techflow Inc."""
	fake = Faker()

	# Departments at Techflow Inc
	departments = [
		"Engineering",
		"Product",
		"Design",
		"Marketing",
		"Sales",
		"Operations",
		"HR",
		"Finance",
		"Customer Success",
		"Security",
	]

	# Job titles by department
	job_titles = {
		"Engineering": [
			"Software Engineer",
			"Senior Software Engineer",
			"Tech Lead",
			"Engineering Manager",
			"DevOps Engineer",
			"Full Stack Developer",
		],
		"Product": ["Product Manager", "Senior Product Manager", "Product Designer", "Product Analyst"],
		"Design": ["UI/UX Designer", "Senior Designer", "Design Lead", "Visual Designer"],
		"Marketing": [
			"Marketing Manager",
			"Content Marketing Specialist",
			"Digital Marketing Manager",
			"Growth Hacker",
		],
		"Sales": ["Sales Representative", "Account Executive", "Sales Manager", "Business Development"],
		"Operations": ["Operations Manager", "Project Manager", "Business Analyst"],
		"HR": ["HR Manager", "Talent Acquisition Specialist", "People Operations"],
		"Finance": ["Financial Analyst", "Accounting Manager", "Finance Manager"],
		"Customer Success": ["Customer Success Manager", "Support Engineer", "Account Manager"],
		"Security": ["Security Engineer", "InfoSec Analyst"],
	}

	# Tech stack and interests for realistic bios
	tech_interests = [
		"Python",
		"JavaScript",
		"React",
		"Vue.js",
		"Node.js",
		"Django",
		"Flask",
		"AWS",
		"Docker",
		"Kubernetes",
		"Machine Learning",
		"Data Science",
		"AI",
		"GraphQL",
		"REST APIs",
		"Microservices",
		"Cloud Computing",
		"DevOps",
		"Mobile Development",
		"Web Development",
		"Product Strategy",
		"User Research",
		"Digital Marketing",
		"Content Strategy",
		"Growth Hacking",
		"Analytics",
	]

	users = []

	for i in range(35):
		fake.seed_instance(i)

		first_name = fake.first_name()
		last_name = fake.last_name()
		email = f"{first_name.lower()}.{last_name.lower()}@techflow.com"
		department = random.choice(departments)
		job_title = random.choice(job_titles[department])

		# Generate a realistic bio
		num_interests = random.randint(2, 4)
		interests = random.sample(tech_interests, num_interests)
		bio_templates = [
			f"Passionate {job_title.lower()} with expertise in {', '.join(interests[:2])}",
			f"{job_title} focusing on {interests[0]} and "
			+ f"{interests[1] if len(interests) > 1 else 'innovation'}",
			f"Building great products with {', '.join(interests[:2])} at Techflow",
			f"{job_title} who loves {interests[0]} and solving complex problems",
			f"Tech enthusiast specializing in {', '.join(interests[:2])}",
		]
		bio = random.choice(bio_templates)

		# Generate HTML readme content
		readme_content = generate_readme_content(first_name, job_title, department, interests)

		# Generate avatar URL
		avatar_url = generate_avatar_url(first_name, last_name, i)

		user = {
			"email": email,
			"first_name": first_name,
			"last_name": last_name,
			"avatar_url": avatar_url,
			"department": department,
			"job_title": job_title,
			"bio": bio,
			"readme": readme_content,
			"location": random.choice(
				[
					"San Francisco, CA",
					"New York, NY",
					"Austin, TX",
					"Seattle, WA",
					"Boston, MA",
					"London, UK",
					"Berlin, Germany",
					"Toronto, Canada",
					"Remote",
					"Amsterdam, Netherlands",
					"Barcelona, Spain",
					"Sydney, Australia",
				]
			),
			"years_experience": random.randint(1, 15),
		}

		users.append(user)

	return users


def generate_readme_content(first_name, job_title, department, interests):
	"""Generate HTML readme content for a user."""

	# Template 1
	template1 = f"""<h3>Hi there! 👋 I'm {first_name}</h3>
<p>I'm a {job_title} in the {department} team at Techflow Inc. I'm passionate about
building amazing products and working with cutting-edge technologies.</p>

<h4>🚀 What I'm working on</h4>
<ul>
<li>Leading initiatives in {interests[0] if interests else "technology"}</li>
<li>Collaborating with cross-functional teams to deliver impactful solutions</li>
<li>Mentoring junior team members and sharing knowledge</li>
</ul>

<h4>💡 Interests & Expertise</h4>
<p>I specialize in <strong>{", ".join(interests[:3]) if len(interests) >= 3 else ", ".join(interests)}</strong>
and love exploring new technologies and methodologies.</p>

<h4>📫 Let's connect!</h4>
<p>Always happy to chat about technology, product ideas, or collaboration opportunities.
Feel free to reach out!</p>"""

	# Template 2
	template2 = f"""<h3>Welcome to my profile!</h3>
<p>I'm {first_name}, a {job_title} passionate about {
		interests[0] if interests else "technology"
	} and innovation.</p>

<h4>🎯 Currently focused on</h4>
<ul>
<li>Driving excellence in {department.lower()}</li>
<li>Implementing best practices with {
		", ".join(interests[:2])
		if len(interests) >= 2
		else interests[0]
		if interests
		else "modern technologies"
	}</li>
<li>Building scalable and user-friendly solutions</li>
</ul>

<h4>🛠️ Tech Stack</h4>
<p>I work extensively with <strong>{
		", ".join(interests)
	}</strong> and am always eager to learn new technologies.</p>

<h4>🌟 Fun fact</h4>
<p>{
		random.choice(
			[
				"I once built a side project that got featured on Product Hunt!",
				"I love contributing to open source projects in my spare time.",
				"I organize local tech meetups and enjoy speaking at conferences.",
				"I'm a coffee enthusiast and know the best spots in every city I visit.",
				"I enjoy hiking and often get my best ideas while on trails.",
			]
		)
	}</p>"""

	# Template 3
	template3 = f"""<h3>About {first_name}</h3>
<p>As a {
		job_title
	} at Techflow, I'm dedicated to creating exceptional user experiences and driving product innovation.</p>

<h4>🏢 Role & Responsibilities</h4>
<ul>
<li>Leading {department.lower()} initiatives and strategy</li>
<li>Collaborating with design, engineering, and business teams</li>
<li>Implementing {interests[0] if interests else "modern"} solutions and best practices</li>
</ul>

<h4>🚀 Skills & Technologies</h4>
<p>Expert in: <strong>{", ".join(interests)}</strong></p>
<p>Always exploring new ways to improve processes and deliver value.</p>

<h4>💭 Philosophy</h4>
<p>I believe in {
		random.choice(
			[
				"building products that users love and solving real problems",
				"continuous learning and sharing knowledge with the team",
				"the power of collaboration and diverse perspectives",
				"making technology accessible and user-friendly",
				"creating sustainable and scalable solutions",
			]
		)
	}.</p>"""

	return random.choice([template1, template2, template3])


def create_user_and_profile(user_data):
	"""Create a User and update the automatically created GP User Profile."""
	try:
		# Check if user already exists
		if frappe.db.exists("User", user_data["email"]):
			return False

		# Create User record
		user_doc = frappe.get_doc(
			{
				"doctype": "User",
				"email": user_data["email"],
				"first_name": user_data["first_name"],
				"last_name": user_data["last_name"],
				"user_image": user_data.get("avatar_url"),
				"send_welcome_email": 0,
				"user_type": "System User",
				"roles": [{"role": "Gameplan Member"}],
			}
		)

		user_doc.insert(ignore_permissions=True)

		try:
			profile_doc = frappe.get_doc("GP User Profile", {"user": user_data["email"]})
		except frappe.DoesNotExistError:
			# If profile wasn't created automatically, create it manually
			profile_doc = frappe.get_doc(
				{
					"doctype": "GP User Profile",
					"user": user_data["email"],
					"bio": user_data["bio"],
					"readme": user_data["readme"],
					"image": user_data.get("avatar_url"),
				}
			)
			profile_doc.insert(ignore_permissions=True)
		else:
			# Update the existing profile
			profile_doc.bio = user_data["bio"]
			profile_doc.readme = user_data["readme"]
			profile_doc.image = user_data.get("avatar_url")
			profile_doc.save(ignore_permissions=True)

		frappe.db.commit()
		return True

	except Exception as e:
		print(f"Error creating user/profile for {user_data['email']}: {str(e)}")
		frappe.log_error(f"Demo User Creation Error: {str(e)}", "Demo Data Generation")
		return False
