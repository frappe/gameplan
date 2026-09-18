# Copyright (c) 2026, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

"""Who a notification goes to, and how its row is written.

The event sources — the mention and reaction mixins, comment and discussion hooks — call
into here rather than into `GP Notification` directly. `resolver` answers "should this user
be told?" from the user's global level and their per-discussion choices; `records` writes
or merges the row. Delivery beyond the in-app inbox (email, push) is a later step that
reads the rows these two produce.
"""
