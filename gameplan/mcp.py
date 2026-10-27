import frappe

# No blank lines: sync finds the block by the next blank line.
AGENT_INSTRUCTIONS = """\
Gameplan (gameplan app):
Gameplan is an async discussions app. The UI says Community for GP Team and Space for GP Project.
- Call document methods with call_document_method.
- A Space belongs to a Community through its team field. A GP Discussion belongs to a Space through its project field.
- GP Task and GP Page are deprecated. Do not create them or suggest them to people.
- Replies are GP Comment with reference_doctype "GP Discussion" and reference_name set to the discussion name. Closed discussions take no new replies.
- content fields are HTML. Mention a person with <span class="mention" data-type="mention" data-id="<user email>" data-label="<full name>">@<full name></span>.
- Create discussions and replies with create_document. Do not update project, closed_at or pinned_at. Use these GP Discussion methods instead: move_to_project {"project": "<space>"}, close_discussion, reopen_discussion, pin_discussion {"pin_scope": "Space" or "Category"} (Category pins it in the Community), unpin_discussion.
- Mark a discussion as read with its track_visit method, or a whole Space with GP Project mark_all_as_read.
- React to a GP Discussion, GP Comment or GP Poll with its react method, args {"operations": [{"emoji": "👍", "operation": "add" or "remove"}]}. Bookmark with add_bookmark and remove_bookmark.
- Vote with GP Poll submit_vote {"option": "<option title>"}. Undo with retract_vote.
- Search posts with call_method gameplan.api.search_sqlite, args {"query": "<text>"}.
- Change membership with GP Project join, leave, add_member {"user": "<email>"} and remove_member, or GP Team add_members {"users": ["<email>"]} and remove_member.
- Gameplan admins invite people with call_method gameplan.api.invite_by_email, args {"emails": "<comma separated emails>", "role": "Gameplan Member"}.
- Do not create or edit GP Reaction, GP Bookmark, GP Unread Record, GP Discussion Visit or GP Notification. They hold each person's own state."""  # noqa: E501
AGENT_INSTRUCTIONS_HEADING = AGENT_INSTRUCTIONS.splitlines()[0]


def sync_agent_instructions():
	"""Write the current guide into System Settings > Agent Instructions on install and migrate.

	Gameplan's block runs from its heading to the next blank line. It is replaced in place, or appended
	when missing. Text outside the block is kept.
	"""
	# Frappe versions without the built-in MCP server have no such field.
	if not frappe.get_meta("System Settings").has_field("agent_instructions"):
		return

	current = frappe.db.get_single_value("System Settings", "agent_instructions") or ""
	before, heading, after = current.partition(AGENT_INSTRUCTIONS_HEADING)
	if heading:
		_block, blank_line, rest = after.partition("\n\n")
		instructions = before + AGENT_INSTRUCTIONS + blank_line + rest
	elif current.strip():
		instructions = f"{current.rstrip()}\n\n{AGENT_INSTRUCTIONS}"
	else:
		instructions = AGENT_INSTRUCTIONS

	if instructions != current:
		frappe.db.set_single_value("System Settings", "agent_instructions", instructions)
