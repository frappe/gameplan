# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt


import datetime


class GPPollAttributes:
	title: str
	options: list
	multiple_answers: bool
	discussion: str
	votes: list
	total_votes: int
	stopped_at: datetime.datetime
	anonymous: bool
