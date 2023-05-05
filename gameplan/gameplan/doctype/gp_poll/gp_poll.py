# Copyright (c) 2023, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt


class GPPoll(Document):
	def before_insert(self):
		self.options = [d for d in self.options if d.title]
		for option in self.options:
			option.title = option.title.strip()
		# dont allow duplicate options
		options = [d.title for d in self.options]
		if len(set(options)) != len(options):
			frappe.throw(frappe._("Duplicate options not allowed"))

	def validate(self):
		vote_count = {}
		vote_by_user = {}
		for d in self.votes:
			vote_count[d.title] = vote_count.get(d.title, 0) + 1
			vote_by_user[d.user] = vote_by_user.get(d.user, []) + [d.title]
		self.total_votes = len(vote_by_user)
		for option in self.options:
			option.votes = 0
			option.percentage = 0
			if option.title in vote_count:
				option.votes = vote_count[option.title]
				option.percentage = flt(vote_count[option.title] * 100 / self.total_votes, 2)

	@frappe.whitelist()
	def submit_vote(self, option):
		self.check_if_ended()

		for d in self.votes:
			if d.user == frappe.session.user:
				return
		self.append("votes", {"title": option, "user": frappe.session.user})
		self.save()

	@frappe.whitelist()
	def retract_vote(self):
		self.check_if_ended()

		self.votes = [d for d in self.votes if d.user != frappe.session.user]
		self.save()

	@frappe.whitelist()
	def end_poll(self):
		if self.end_time:
			return
		self.end_time = frappe.utils.now()
		self.save()

	def check_if_ended(self):
		if self.end_time and self.end_time < frappe.utils.now():
			frappe.throw(frappe._("Poll has ended"))


@frappe.whitelist()
def get_list(fields, filters=None, start=0, limit=20, order_by=None):
	query = frappe.qb.get_query('GP Poll',
		fields=fields,
		filters=filters,
		start=start,
		limit=limit,
		order_by=order_by
	)

	data = query.run(as_dict=1)
	return data