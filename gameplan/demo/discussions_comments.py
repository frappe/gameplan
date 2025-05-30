# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and Contributors

import random

import frappe
from faker import Faker
from frappe.utils.user import get_user_fullname


def generate_discussions_and_comments():
	"""Generate demo discussions and comments for existing projects."""

	# Get all existing projects
	projects = frappe.get_all(
		"GP Project",
		fields=["name", "title", "team"],
		filters={"is_private": 0},  # Focus on public projects for demo
	)

	if not projects:
		print("No projects found. Please generate teams and projects first.")
		return

	created_discussions = []
	for i, project in enumerate(projects):
		frappe.utils.update_progress_bar("Generating Discussions", i, len(projects), absolute=True)
		# Generate 3-8 discussions per project
		num_discussions = random.randint(3, 8)
		project_discussions = generate_discussions_for_project(project, num_discussions)
		created_discussions.extend(project_discussions)
	frappe.utils.update_progress_bar("Generating Discussions", len(projects), len(projects), absolute=True)
	print()

	# Generate comments for discussions
	total_comments = 0
	for i, discussion in enumerate(created_discussions):
		frappe.utils.update_progress_bar("Generating Comments", i, len(created_discussions), absolute=True)

		comments_count = generate_comments_for_discussion(discussion)
		total_comments += comments_count
	frappe.utils.update_progress_bar(
		"Generating Comments", len(created_discussions), len(created_discussions), absolute=True
	)
	print()

	frappe.db.commit()


def generate_discussions_for_project(project, count):
	"""Generate discussions for a given project."""
	fake = Faker()
	created_discussions = []

	# Get project members to use as discussion creators
	project_doc = frappe.get_doc("GP Project", project.name)
	project_members = [member.user for member in project_doc.members] if project_doc.members else []

	# If no project members, get random Techflow users
	if not project_members:
		project_members = get_random_users(5)

	# Remove Administrator from project members
	project_members = [user for user in project_members if user != "Administrator"]

	# If no valid members after filtering, skip this project
	if not project_members:
		print(f"Skipping project '{project.title}' as it has no valid members.")
		return []

	discussion_templates = get_discussion_templates()

	for _ in range(count):
		# Random discussion data
		template = random.choice(discussion_templates)

		# Prepare all necessary Faker data once
		faker_params = {
			"project": project.title,
			"initiative": fake.catch_phrase(),
			"effort": fake.catch_phrase(),
			"word": fake.word().title(),
			"word2": fake.word(),
			"user": fake.name(),
			"company": fake.company(),
			"sentence": fake.sentence(),
			"bs": fake.bs().title(),
			"bs2": fake.bs().title(),
			"bs3": fake.bs().title(),
			"bs4": fake.bs().title(),
			"catch_phrase": fake.catch_phrase(),
			"catch_phrase2": fake.catch_phrase(),
			"day": fake.future_date(end_date="+7d").strftime("%A"),
			"time": fake.time(),
			# Add picsum.photos placeholder images with random dimensions
			"image_wide": f"https://picsum.photos/{random.randint(600, 800)}/{random.randint(300, 400)}",
			"image_square": f"https://picsum.photos/{random.randint(400, 600)}",
			"image_tall": f"https://picsum.photos/{random.randint(300, 400)}/{random.randint(500, 700)}",
			"image_small": f"https://picsum.photos/{random.randint(200, 300)}",
			"image_large": f"https://picsum.photos/{random.randint(800, 1000)}/{random.randint(400, 600)}",
		}

		# Add proper @mention format with HTML span elements
		if project_members:
			mention1_user = random.choice(project_members)
			mention2_user = random.choice(project_members)
			mention3_user = random.choice(project_members)

			# Get full names for the mentioned users
			mention1_fullname = get_user_fullname(mention1_user)
			mention2_fullname = get_user_fullname(mention2_user)
			mention3_fullname = get_user_fullname(mention3_user)

			# Create proper @mention HTML spans with full names
			faker_params.update(
				{
					"mention1": (
						f'<span class="mention" data-type="mention" '
						f'data-id="{mention1_user}" data-label="{mention1_fullname}">'
						f"@{mention1_fullname}</span>"
					),
					"mention2": (
						f'<span class="mention" data-type="mention" '
						f'data-id="{mention2_user}" data-label="{mention2_fullname}">'
						f"@{mention2_fullname}</span>"
					),
					"mention3": (
						f'<span class="mention" data-type="mention" '
						f'data-id="{mention3_user}" data-label="{mention3_fullname}">'
						f"@{mention3_fullname}</span>"
					),
				}
			)

		title = template["title"].format(**faker_params)
		content = template["content"].format(**faker_params)

		# Random creator from project members
		creator = random.choice(project_members)

		# Random creation time (last 30 days)
		creation_time = fake.date_time_between(start_date="-30d", end_date="now")

		try:
			# Store current user to restore later
			current_user = frappe.session.user

			# Set session user to the creator to ensure proper ownership
			frappe.set_user(creator)

			discussion_doc = frappe.new_doc("GP Discussion")
			discussion_doc.title = title
			discussion_doc.content = content
			discussion_doc.project = project.name
			discussion_doc.modified_by = creator

			# Add random reactions
			reactions = generate_random_reactions(project_members)
			for reaction in reactions:
				discussion_doc.append("reactions", reaction)

			discussion_doc.insert(ignore_permissions=True)

			# Update timestamps after insertion using direct database update
			frappe.db.set_value(
				"GP Discussion",
				discussion_doc.name,
				{"creation": creation_time, "modified": creation_time},
				update_modified=False,
			)

			created_discussions.append(discussion_doc)

		except Exception as e:
			print(f"Error creating discussion '{title}': {str(e)}")
			continue
		finally:
			# Always restore the original user
			frappe.set_user(current_user)

	return created_discussions


def generate_comments_for_discussion(discussion):
	"""Generate comments for a given discussion."""
	fake = Faker()

	# Get project to find members
	project_doc = frappe.get_doc("GP Project", discussion.project)
	project_members = [member.user for member in project_doc.members] if project_doc.members else []

	if not project_members:
		project_members = get_random_users(3)

	# Remove Administrator from project members
	project_members = [user for user in project_members if user != "Administrator"]

	# If no valid members after filtering, skip this discussion
	if not project_members:
		return 0

	# Generate 2-5 comments per discussion
	num_comments = random.randint(2, 5)

	comment_templates = get_comment_templates()
	comments_created = 0

	for _ in range(num_comments):
		template = random.choice(comment_templates)

		# Add random image parameters for comments
		comment_image_params = {
			"user": fake.name(),
			"project": project_doc.title,
			"idea": fake.catch_phrase(),
			"company": fake.company(),
			"sentence": fake.sentence(),
			"word": fake.word(),
			"catch_phrase": fake.catch_phrase(),
			"image_small": f"https://picsum.photos/{random.randint(200, 400)}",
			"image_wide": f"https://picsum.photos/{random.randint(400, 600)}/{random.randint(200, 300)}",
		}

		content = template.format(**comment_image_params)

		# Random commenter from project members
		commenter = random.choice(project_members)

		# Comment creation time should be after discussion creation
		min_time = frappe.utils.get_datetime(discussion.creation)

		comment_time = fake.date_time_between(start_date=min_time, end_date="now")

		try:
			# Store current user to restore later
			current_user = frappe.session.user

			# Set session user to the commenter to ensure proper ownership
			frappe.set_user(commenter)

			comment_doc = frappe.new_doc("GP Comment")
			comment_doc.content = content
			comment_doc.reference_doctype = "GP Discussion"
			comment_doc.reference_name = discussion.name
			comment_doc.modified_by = commenter

			# Add random reactions
			reactions = generate_random_reactions(project_members, max_reactions=3)
			for reaction in reactions:
				comment_doc.append("reactions", reaction)

			comment_doc.insert(ignore_permissions=True)

			# Update timestamps after insertion using direct database update
			frappe.db.set_value(
				"GP Comment",
				comment_doc.name,
				{"creation": comment_time, "modified": comment_time},
				update_modified=False,
			)

			comments_created += 1

		except Exception as e:
			print(f"Error creating comment for discussion '{discussion.title}': {str(e)}")
			continue
		finally:
			# Always restore the original user
			frappe.set_user(current_user)

	return comments_created


def get_discussion_templates():
	"""Get templates for different types of discussions using placeholders for Faker data."""

	# Technical Documentation Template
	technical_overview = """<h2>Overview</h2>
<p>This document outlines the technical specifications and implementation details for the {word}
component of {initiative}. {sentence}</p>

<img src="{image_wide}" alt="System Architecture Overview" />

<h2>Architecture & Design</h2>
<p>The proposed architecture follows {bs} principles and incorporates {catch_phrase} methodology.</p>

<h3>Core Components</h3>
<ol>
	<li><strong>{bs}</strong> - {sentence}</li>
	<li><strong>{bs2}</strong> - Handles {catch_phrase}</li>
	<li><strong>{bs3}</strong> - Manages {catch_phrase2}</li>
</ol>

<img src="{image_square}" alt="Component Diagram" />

<h3>Implementation Details</h3>
<p>Here's the proposed implementation approach:</p>

<pre><code>
// Example implementation for {word}
class {word}Manager {{
    constructor() {{
        this.config = {{
            enabled: true,
            timeout: 5000,
            retries: 3
        }};
    }}

    async process{word}() {{
        try {{
            const result = await this.{bs2}();
            return result;
        }} catch (error) {{
            console.error('Error in {word} processing:', error);
            throw error;
        }}
    }}
}}
</code></pre>

<h2>Dependencies & Requirements</h2>
<ul>
	<li>{bs} framework (v2.0+)</li>
	<li>{company} SDK integration</li>
	<li>{catch_phrase} middleware</li>
</ul>

<h2>Testing Strategy</h2>
<p>We need comprehensive testing for this implementation. {mention1}, could you help with the unit tests?
{mention2}, please review the integration approach.</p>

<p><strong>Test Coverage Areas:</strong></p>
<ol>
	<li>Unit tests for core functionality</li>
	<li>Integration tests with {bs2}</li>
	<li>Performance testing under load</li>
	<li>Edge case handling</li>
</ol>

<blockquote>
	<p><strong>Note:</strong> This implementation needs approval from {mention3} before we proceed.</p>
</blockquote>

<p>Looking forward to your feedback! 🚀</p>"""

	return [
		# Long-form Technical Documentation
		{
			"title": "📚 {initiative} {word} Technical Specification & Implementation Guide",
			"content": technical_overview,
		},
		# Long-form Project Retrospective
		{
			"title": "🔍 {initiative} Sprint Retrospective - What We Learned & Next Steps",
			"content": """<h2>Sprint Summary</h2>
<p>We've completed another sprint on {project} and it's time to reflect on our progress. {sentence}</p>

<img src="{image_wide}" alt="Sprint Progress Overview" />

<h2>What Went Well ✅</h2>
<ul>
	<li><strong>{bs}</strong> - Exceeded our expectations and delivered {catch_phrase}</li>
	<li><strong>Team Collaboration</strong> - Great teamwork between {mention1} and {mention2}</li>
	<li><strong>{bs2}</strong> - Implemented ahead of schedule</li>
	<li><strong>Code Quality</strong> - Maintained high standards with proper testing</li>
</ul>

<h2>Challenges We Faced ⚠️</h2>
<ol>
	<li><strong>{word} Integration Issues</strong>
		<p>{sentence} We encountered unexpected complications with {bs3}.</p>
		<pre><code>
// Problematic code that caused issues:
function problematic{word}() {{
    // This approach didn't work as expected
    return {company}.process();
}}
		</code></pre>
	</li>
	<li><strong>Performance Bottlenecks</strong>
		<p>The {catch_phrase2} process was slower than anticipated.</p>
	</li>
	<li><strong>Communication Gaps</strong>
		<p>Some requirements weren't clear initially, leading to rework.</p>
	</li>
</ol>

<h2>Key Metrics & Data</h2>
<p>Here's a breakdown of our sprint metrics:</p>

<h3>Completed Work</h3>
<ul>
	<li>✅ Story Points Completed: 45/50 (90%)</li>
	<li>✅ Bugs Fixed: 12</li>
	<li>✅ New Features: 3</li>
	<li>✅ Code Coverage: 85%</li>
</ul>

<h3>Technical Debt</h3>
<ul>
	<li>🔧 Refactoring needed in {bs} module</li>
	<li>🔧 Update dependencies for {word2} component</li>
	<li>🔧 Optimize {catch_phrase} queries</li>
</ul>

<h2>Action Items for Next Sprint</h2>
<ol>
	<li><strong>High Priority</strong>
		<ul>
			<li>Fix {word} integration issues - {mention1}</li>
			<li>Optimize performance bottlenecks - {mention2}</li>
			<li>Update documentation - {mention3}</li>
		</ul>
	</li>
	<li><strong>Medium Priority</strong>
		<ul>
			<li>Refactor {bs2} module</li>
			<li>Add more unit tests</li>
			<li>Set up automated {catch_phrase} monitoring</li>
		</ul>
	</li>
</ol>

<blockquote>
	<p><strong>Retrospective Meeting:</strong> Scheduled for {day} at {time}. All team members please attend to discuss these findings.</p>
</blockquote>

<p>Thanks for the great work everyone! Let's keep the momentum going! 💪</p>""",
		},
		# Long-form API Documentation
		{
			"title": "🔗 {initiative} API Documentation & Integration Guide",
			"content": """<h2>API Overview</h2>
<p>This document provides comprehensive documentation for the {project} {word} API. {sentence}</p>

<img src="{image_large}" alt="API Architecture Overview" />

<h2>Authentication</h2>
<p>All API requests require authentication using {bs} tokens.</p>

<h3>Getting an API Token</h3>
<ol>
	<li>Navigate to your account settings</li>
	<li>Generate a new API token</li>
	<li>Include the token in request headers</li>
</ol>

<pre><code>
curl -H "Authorization: Bearer YOUR_TOKEN" \\
     -H "Content-Type: application/json" \\
     https://api.{company}.com/v1/{word}
</code></pre>

<h2>Core Endpoints</h2>

<h3>1. {word} Management</h3>
<p>Endpoints for managing {word} resources:</p>

<h4>GET /api/v1/{word}</h4>
<p>Retrieve all {word} items with pagination support.</p>

<pre><code>
{{
  "data": [
    {{
      "id": "123",
      "name": "{bs}",
      "status": "active",
      "created_by": "{mention1}",
      "metadata": {{
        "type": "{catch_phrase}",
        "priority": "high"
      }}
    }}
  ],
  "pagination": {{
    "page": 1,
    "per_page": 25,
    "total": 150
  }}
}}
</code></pre>

<h4>POST /api/v1/{word}</h4>
<p>Create a new {word} resource.</p>

<pre><code>
// Request Body
{{
  "name": "{bs2}",
  "description": "{sentence}",
  "assignee": "{mention2}",
  "tags": ["{catch_phrase}", "{word2}"]
}}

// Response
{{
  "id": "124",
  "name": "{bs2}",
  "status": "pending",
  "created_at": "2024-01-15T10:30:00Z"
}}
</code></pre>

<h3>2. {word2} Integration</h3>
<p>Advanced endpoints for {word2} functionality:</p>

<h4>PUT /api/v1/{word}/{{id}}/{word2}</h4>
<p>Update {word2} configuration for a specific {word}.</p>

<h2>Error Handling</h2>
<p>The API uses standard HTTP status codes and returns detailed error messages:</p>

<pre><code>
{{
  "error": {{
    "code": "VALIDATION_ERROR",
    "message": "{sentence}",
    "details": [
      {{
        "field": "name",
        "message": "Name is required"
      }}
    ]
  }}
}}
</code></pre>

<h2>Rate Limiting</h2>
<ul>
	<li><strong>Standard Users:</strong> 1000 requests/hour</li>
	<li><strong>Premium Users:</strong> 5000 requests/hour</li>
	<li><strong>Enterprise:</strong> 20000 requests/hour</li>
</ul>

<h2>SDKs & Libraries</h2>
<p>We provide official SDKs for popular programming languages:</p>

<ul>
	<li><strong>JavaScript/Node.js:</strong> <code>npm install {project}-sdk</code></li>
	<li><strong>Python:</strong> <code>pip install {project}-python</code></li>
	<li><strong>Go:</strong> <code>go get github.com/{company}/{project}-go</code></li>
</ul>

<h3>Quick Start Example (JavaScript)</h3>
<pre><code>
import {{ {word}Client }} from '{project}-sdk';

const client = new {word}Client({{
  token: 'your-api-token',
  baseUrl: 'https://api.{company}.com'
}});

// Create a new {word}
const new{word} = await client.{word}.create({{
  name: '{bs3}',
  description: '{catch_phrase2}',
  assignee: '{mention3}'
}});

console.log('Created {word}:', new{word}.id);
</code></pre>

<h2>Webhooks</h2>
<p>Subscribe to real-time events in your {project} workspace:</p>

<ol>
	<li>{word}.created</li>
	<li>{word}.updated</li>
	<li>{word}.deleted</li>
	<li>{word2}.status_changed</li>
</ol>

<blockquote>
	<p><strong>Support:</strong> For technical questions, reach out to {mention1} or {mention2}. For API access issues, contact {mention3}.</p>
</blockquote>

<p>Happy coding! 🎯</p>""",
		},
		# Short Templates (keeping some variety)
		{
			"title": "🎉 {initiative} {word} Milestone Reached!",
			"content": """<p>Great news everyone! We've just hit a major milestone on {initiative}. {sentence}</p>

<img src="{image_square}" alt="Milestone Achievement" />

<p>Key achievements:</p>
<ul>
	<li>{bs}</li>
	<li>{catch_phrase}</li>
	<li>{bs2}</li>
</ul>
<p>Let's keep this momentum going! 🚀</p>""",
		},
		{
			"title": "📢 {initiative} {word} Update",
			"content": """<p>Here's our latest update on {initiative}:</p>
<p><strong>What we accomplished:</strong></p>
<ul>
	<li>{bs}</li>
	<li>{catch_phrase}</li>
	<li>{bs2}</li>
</ul>
<p><strong>What's next:</strong></p>
<ul>
	<li>{bs3}</li>
	<li>{catch_phrase2}</li>
	<li>{bs4}</li>
</ul>
<p>Great work everyone! 👏</p>""",
		},
		{
			"title": "Quick question about {initiative}",
			"content": """<p>Hey team, I had a quick question regarding the {word} for {initiative}. {sentence} Can anyone shed some light on this? {mention1} {mention2}</p>""",
		},
		{
			"title": "Thoughts on the new {word} for {initiative}?",
			"content": """<p>Hi all, what are your initial thoughts on the new {word} we're considering for {initiative}? {sentence} I'm particularly interested in feedback on {bs}.</p>""",
		},
		# Project Updates
		{
			"title": "🔄 {effort} {word} Planning Discussion",
			"content": """<p>It's time for our next planning session for {effort}!</p>
<p>{sentence}</p>
<ul>
	<li>{bs}</li>
	<li>{catch_phrase}</li>
	<li>{bs2}</li>
</ul>
<p>Meeting scheduled for {day} at {time}. See you there!</p>""",
		},
		{
			"title": "Update on {effort}: {catch_phrase}",
			"content": """<p>Just a quick update on where we are with {effort}. {sentence} We've made good progress on {bs} and are now focusing on {bs2}.</p>
<p>Next steps include {bs3}.</p>""",
		},
		# Questions
		{
			"title": "❓ {effort} {word} Question - Need Input",
			"content": """<p>Hey team, I need some input on a {word2} decision for {effort}.</p>
<p>We're facing a choice and I'd love to get everyone's perspective:</p>
<p><strong>Option A:</strong> {bs}</p>
<p><strong>Option B:</strong> {catch_phrase}</p>
<p>What are your thoughts? {sentence}</p>""",
		},
		{
			"title": "Need help with {word} for {effort}",
			"content": """<p>Hi team, I'm a bit stuck on the {word} for {effort}. {sentence} Specifically, I'm trying to {bs} but encountering {catch_phrase}. Any advice or suggestions would be greatly appreciated!</p>""",
		},
		# Problem-solving
		{
			"title": "🚨 {effort} {word} Discussion - Need Solutions",
			"content": """<p>We've encountered an issue with {effort} that needs attention.</p>
<p>The problem: {bs}</p>
<p>Impact: {sentence}</p>
<p>Let's brainstorm solutions. What are your thoughts on:</p>
<ul>
	<li>{bs2}</li>
	<li>{catch_phrase}</li>
	<li>{bs3}</li>
</ul>
<p>All ideas welcome!</p>""",
		},
		{
			"title": "Brainstorm: How to improve {word} in {effort}?",
			"content": """<p>Let's put our heads together for {effort}. How can we improve the {word}? {sentence} I was thinking we could try {bs}, or maybe {catch_phrase}. Open to all suggestions!</p>""",
		},
		{
			"title": "Feedback requested: {effort} - {word}",
			"content": """<p>Hi everyone, I'd appreciate your feedback on the current state of {word} for {effort}. {sentence} Please take a look at {bs} and let me know your thoughts by {day}.</p>""",
		},
		{
			"title": "Let's discuss {effort}'s {word2} strategy",
			"content": """<p>Team, I think it's a good time to discuss our strategy for {word2} within {effort}. {sentence} What's working well? What could be better? I'm proposing we consider {bs} and {catch_phrase}.</p>""",
		},
		{
			"title": "Important: {effort} deadline approaching for {word}",
			"content": """<p>Just a reminder that the deadline for {word} on {effort} is approaching on {day}. {sentence} Let's ensure all tasks related to {bs} are completed. Please update your progress.</p>""",
		},
		{
			"title": "Idea for {effort}: {catch_phrase2}",
			"content": """<p>I had an idea for {effort} that I wanted to share: {catch_phrase2}. {sentence} This could potentially help us with {bs}. What do you think?</p>""",
		},
		{
			"title": "Reviewing the {word} for {effort}",
			"content": """<p>Hi team, let's take some time to review the {word} for {effort}. {sentence} I've noticed {bs} and think we could improve by {catch_phrase}. Looking forward to your input.</p>""",
		},
	]


def get_comment_templates():
	"""Get templates for various comment types using Faker."""
	return [
		# Positive responses
		"<p>{sentence} Great thinking on this approach! 👍</p>",
		"<p>Love this direction! {sentence} 🎉</p>",
		"<p>Fantastic work! {sentence}</p>",
		"<p>I'm excited about this! {sentence} 🚀</p>",
		"<p>{catch_phrase}! Great insight.</p>",
		# Questions and clarifications
		"<p>Could you elaborate on {word}? {sentence}</p>",
		"<p>What's the timeline looking like? {sentence}</p>",
		"<p>How does this impact our {word} for {project}?</p>",
		"<p>Have we considered the potential {word}? {sentence}</p>",
		"<p>What {word} would we need to make this happen?</p>",
		# Suggestions and ideas
		"<p>Building on this idea, what if we also considered {idea}? {sentence}</p>",
		"<p>{sentence} What if we tried approaching it differently?</p>",
		"<p>This reminds me of {word}. {sentence}</p>",
		"<p>Great start! {sentence}</p>",
		"<p>I agree with the direction, but {sentence}</p>",
		# Technical responses
		"<p>From a technical standpoint, {sentence}</p>",
		"<p>The {word} looks good, but {sentence}</p>",
		"<p>I think we need to review our {word} strategy. {sentence}</p>",
		"<p>{sentence}</p>",
		# Supportive and collaborative
		"<p>I'm happy to help with this! {sentence}</p>",
		"<p>Count me in! {sentence}</p>",
		"<p>This ties in well with {word}. {sentence}</p>",
		"<p>I can provide some insights from {word}. DM me!</p>",
		# Short reactions
		"<p>Absolutely agree! 💯</p>",
		"<p>This! 🎯</p>",
		"<p>Makes sense to me! ✅</p>",
		"<p>{word} timing for this discussion!</p>",
		"<p>Thanks for bringing this up!</p>",
		"<p>Noted! {sentence}</p>",
		"<p>Good catch! {sentence}</p>",
		"<p>Interesting point! {sentence}</p>",
		# Longer form technical analysis comments
		"""<p>Thanks for sharing this! I've been thinking about the {word} approach and have a few thoughts:</p>

<img src="{image_wide}" alt="Technical Analysis Diagram" />

<p><strong>Pros:</strong></p>
<ul>
	<li>{sentence}</li>
	<li>The {catch_phrase} methodology aligns well with our current stack</li>
	<li>Should integrate smoothly with existing {word} systems</li>
</ul>
<p><strong>Considerations:</strong></p>
<ul>
	<li>We might need to factor in {sentence}</li>
	<li>Performance implications for {word} processing</li>
</ul>
<p>Overall, I think this is a solid direction. What are your thoughts on the implementation timeline?</p>""",
		"""<p>Great discussion starter! This touches on something I've been researching lately.</p>
<p>From my experience with similar {word} implementations, here are some key factors to consider:</p>
<ol>
	<li><strong>Scalability:</strong> {sentence} We should ensure our approach can handle growth.</li>
	<li><strong>Maintainability:</strong> The {catch_phrase} pattern tends to be easier to debug and extend.</li>
	<li><strong>Integration:</strong> How will this work with our existing {word} infrastructure?</li>
</ol>
<p>I'd recommend starting with a pilot implementation to validate our assumptions. {sentence}</p>
<p>Happy to collaborate on the technical specs if helpful! 🤝</p>""",
		# Longer form project management comments
		"""<p>Thanks for the update! This is really helpful context.</p>

<img src="{image_small}" alt="Project Timeline" />

<p>Looking at our current roadmap, I think we should prioritize:</p>
<ol>
	<li><strong>Short-term (next 2 weeks):</strong> {sentence}</li>
	<li><strong>Medium-term (this month):</strong> Focus on {word} optimization</li>
	<li><strong>Long-term (next quarter):</strong> {catch_phrase} implementation</li>
</ol>
<p>The dependencies look manageable, but we should keep an eye on the {word} integration piece. {sentence}</p>
<p>Should we schedule a planning session to align on priorities? I'm available most of this week.</p>""",
		"""<p>I appreciate you bringing this up - it's definitely worth discussing as a team.</p>
<p>From my perspective, the main challenges I see are:</p>
<ul>
	<li><strong>Resource allocation:</strong> {sentence}</li>
	<li><strong>Timeline coordination:</strong> Making sure {word} doesn't conflict with other initiatives</li>
	<li><strong>Quality assurance:</strong> {catch_phrase} needs thorough testing</li>
</ul>
<p>That said, I think the benefits outweigh the challenges. {sentence}</p>
<p>Would it be helpful to create a detailed project plan with milestones? I can take a first pass at it.</p>""",
		# Longer form feedback and review comments
		"""<p>Really impressed with the thoroughness of this analysis! 👏</p>
<p>A few observations and suggestions:</p>
<p><strong>What's working well:</strong></p>
<ul>
	<li>The {word} approach is clean and well-structured</li>
	<li>{sentence}</li>
	<li>Good consideration of edge cases</li>
</ul>
<p><strong>Areas for potential improvement:</strong></p>
<ul>
	<li>Could we optimize the {word} performance? {sentence}</li>
	<li>Documentation could be expanded for the {catch_phrase} section</li>
</ul>
<p>Overall this looks ready to move forward. Great work! 🚀</p>""",
		"""<p>Thanks for sharing this draft! I've had a chance to review it in detail.</p>
<p>The overall direction looks solid. {sentence} I particularly like how you've addressed the {word} requirements.</p>
<p><strong>Specific feedback:</strong></p>
<ol>
	<li><strong>Section 2:</strong> The {catch_phrase} explanation is clear and comprehensive</li>
	<li><strong>Section 3:</strong> Consider adding more examples for {word} implementation</li>
	<li><strong>Section 4:</strong> {sentence}</li>
</ol>
<p>I made some detailed comments in the document. The changes are mostly minor clarifications and formatting suggestions.</p>
<p>Once these are addressed, I think we're good to go! Let me know if you'd like to discuss any of the feedback.</p>""",
		# Longer form brainstorming and ideation comments
		"""<p>Love where this conversation is heading! 💡</p>
<p>Building on the ideas shared so far, what if we also considered:</p>
<p><strong>Alternative approach 1:</strong> {sentence} This could give us more flexibility with {word} management.</p>
<p><strong>Alternative approach 2:</strong> Using {catch_phrase} methodology might simplify the implementation.</p>
<p>I'm also wondering about the integration possibilities. {sentence}</p>
<p>Would it be worth running a quick proof-of-concept to test these ideas? I could put together a prototype over the next few days.</p>""",
		"""<p>This is exactly the kind of innovative thinking we need! 🎯</p>
<p>Your point about {word} really resonates with me. I've been seeing similar patterns in other {sentence}</p>
<p><strong>Building on your idea:</strong></p>
<ul>
	<li>We could extend this to include {catch_phrase} functionality</li>
	<li>Integration with existing {word} systems would be straightforward</li>
	<li>The user experience would be significantly improved</li>
</ul>
<p>I'm excited to explore this further. {sentence} Should we set up a brainstorming session to flesh out the details?</p>
<p>I can bring some examples from similar implementations I've worked on.</p>""",
		# Longer form problem-solving comments
		"""<p>Thanks for flagging this issue - it's definitely something we need to address.</p>
<p>I've encountered similar {word} problems before. Here's what worked for me:</p>
<p><strong>Immediate steps:</strong></p>
<ol>
	<li>Check the {sentence} configuration</li>
	<li>Verify {word} dependencies are up to date</li>
	<li>Review recent changes to {catch_phrase} settings</li>
</ol>
<p><strong>Longer-term solution:</strong></p>
<p>We might want to implement {sentence} to prevent this from happening again.</p>
<p>I can help troubleshoot if you'd like. Also happy to pair program on a more robust solution.</p>""",
		"""<p>Good catch on identifying this potential issue early! 🕵️</p>
<p>Looking at the symptoms you described, this seems similar to a {word} problem we solved last quarter.</p>
<p><strong>Root cause analysis:</strong></p>
<ul>
	<li>The {sentence} is likely causing the bottleneck</li>
	<li>{catch_phrase} configuration might need adjustment</li>
	<li>Database optimization could help with performance</li>
</ul>
<p><strong>Proposed solution:</strong></p>
<p>I suggest we implement a phased approach: first optimize the {word} queries, then introduce caching for {sentence}</p>
<p>Would you like me to create a detailed action plan? I can also help with implementation.</p>""",
	]


def generate_random_reactions(users, max_reactions=5):
	"""Generate random reactions from users using Faker emojis."""
	if not users:
		return []

	# Limit number of reactions
	num_reactions = random.randint(0, min(max_reactions, len(users)))

	if num_reactions == 0:
		return []

	# fmt: off
	emojis = [
		"👍","👎","💖","🔥","👏🏻","🤔","😱","🤯","😡","⚡️",
		"🥳", "🎉","💩","🤩","😢","😂","🍿","🙈","🌚","🚀"
	]
	# fmt: on

	reactions = []
	selected_users = random.sample(users, num_reactions)

	for user in selected_users:
		emoji = random.choice(emojis)
		reactions.append({"emoji": emoji, "user": user})

	return reactions


def get_random_users(count=5):
	"""Get random users from existing Techflow users."""
	try:
		# Get users from the @techflow.com domain
		users = frappe.get_all(
			"User",
			filters={"email": ["like", "%@techflow.com"]},
			fields=["name"],
			limit=count * 2,  # Get more than needed to have options
		)

		if users:
			user_names = [user.name for user in users if user.name != "Administrator"]
			# Return random selection
			selected_count = min(count, len(user_names))
			if selected_count > 0:
				return random.sample(user_names, selected_count)
			else:
				return []
		else:
			# No users available
			return []

	except Exception as e:
		print(f"Error getting random users: {str(e)}")
		return []
