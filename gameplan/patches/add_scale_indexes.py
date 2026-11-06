# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

"""Add the indexes that posting and the moderation queues need on a large forum.

Frappe runs a doctype's index hook only when its definition changes, so existing sites would
never get these. Each call skips an index that already exists, so running this twice is safe.
On a site with millions of replies, expect each index to take a few minutes to build.
"""

from gameplan.gameplan.doctype.gp_comment.gp_comment import add_indexes as add_comment_indexes
from gameplan.gameplan.doctype.gp_discussion.gp_discussion import on_doctype_update as add_discussion_indexes
from gameplan.gameplan.doctype.gp_member.gp_member import on_doctype_update as add_member_indexes
from gameplan.gameplan.doctype.gp_notification.gp_notification import (
	on_doctype_update as add_notification_indexes,
)
from gameplan.gameplan.doctype.gp_unread_record.gp_unread_record import add_indexes as add_unread_indexes


def execute():
	add_member_indexes()
	add_notification_indexes()
	add_unread_indexes()
	add_comment_indexes()
	add_discussion_indexes()
