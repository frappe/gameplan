import frappe

from gameplan.watched_word_matching import censor_rules_for


class ResponseScopes:
	"""Resolve post scopes in three batch reads and load censor rules in one batch."""

	def __init__(self, payload, *, verified=False, community=None):
		self.comments = {}
		self.discussions = {}
		self.projects = {}
		self.rules = {}
		comment_names, discussion_names, projects = set(), set(), set()
		for row in self.rows(payload):
			# Search supplies scope from its live permission-checked joins.
			if verified and row.get("project") and row.get("team"):
				project = str(row["project"])
				self.projects[project] = row["team"]
				if row.get("doctype") == "GP Discussion":
					self.discussions[str(row["name"])] = project
				elif row.get("doctype") == "GP Comment" and row.get("reference_doctype") == "GP Discussion":
					parent = str(row["reference_name"])
					self.comments[str(row["name"])] = parent
					self.discussions[parent] = project
				continue
			doctype = row.get("_watched_doctype") or row.get("doctype")
			if name := row.get("name"):
				if doctype == "GP Comment":
					comment_names.add(str(name))
				elif doctype == "GP Discussion":
					discussion_names.add(str(name))
			if (row.get("_watched_reference_doctype") or row.get("reference_doctype")) == "GP Discussion":
				if name := row.get("_watched_reference_name") or row.get("reference_name"):
					discussion_names.add(str(name))
			if name := row.get("discussion"):
				discussion_names.add(str(name))
			if isinstance(project := row.get("_watched_project") or row.get("project"), str | int):
				projects.add(str(project))
		if comment_names:
			for row in frappe.get_all(
				"GP Comment",
				filters={"name": ["in", list(comment_names)]},
				fields=["name", "reference_doctype", "reference_name"],
			):
				if row.reference_doctype == "GP Discussion":
					self.comments[str(row.name)] = str(row.reference_name)
					discussion_names.add(str(row.reference_name))
		if discussion_names:
			for row in frappe.get_all(
				"GP Discussion", filters={"name": ["in", list(discussion_names)]}, fields=["name", "project"]
			):
				self.discussions[str(row.name)] = str(row.project)
				projects.add(str(row.project))
		if projects:
			self.projects = {
				str(row.name): row.team
				for row in frappe.get_all(
					"GP Project", filters={"name": ["in", list(projects)]}, fields=["name", "team"]
				)
			}

		communities = set(self.projects.values())
		if community:
			communities.add(community)
		if communities:
			self.rules = censor_rules_for(tuple(sorted(communities)))

	def target(self, doctype, name):
		name = str(name)
		if doctype == "GP Comment":
			name = self.comments.get(name)
		elif doctype != "GP Discussion":
			return None
		return self.projects.get(self.discussions.get(name))

	@classmethod
	def rows(cls, payload):
		if isinstance(payload, list | tuple):
			for row in payload:
				yield from cls.rows(row)
		elif isinstance(payload, dict):
			yield payload
			for key, value in payload.items():
				if key == "data" and isinstance(value, str):
					try:
						value = frappe.parse_json(value)
					except (ValueError, TypeError):
						continue
				yield from cls.rows(value)
