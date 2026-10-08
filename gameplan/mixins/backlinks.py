import re
from urllib.parse import urlparse

import frappe
from bs4 import BeautifulSoup
from frappe.utils import get_url

DISCUSSION_PATH = re.compile(r"^/g/(?:.+/)?discussion/(\d+)(?:/|$)")


class HasBacklinks:
	def update_backlinks(self):
		if self.doctype == "GP Discussion":
			own_discussion = self.name
		elif self.reference_doctype == "GP Discussion":
			own_discussion = self.reference_name
		else:
			return

		discussions = self._get_linked_discussions(own_discussion)
		if sorted(str(row.discussion) for row in self.backlinks) != discussions:
			self.set("backlinks", [{"discussion": name} for name in discussions])

	def _get_linked_discussions(self, own_discussion):
		if not self.content:
			return []

		site_host = urlparse(get_url()).hostname
		names = set()
		for anchor in BeautifulSoup(self.content, "html.parser").find_all("a", href=True):
			url = urlparse(anchor["href"])
			if url.hostname not in (None, site_host):
				continue
			match = DISCUSSION_PATH.match(url.path)
			if match and match.group(1) != str(own_discussion):
				names.add(match.group(1))

		if not names:
			return []

		existing = frappe.get_all("GP Discussion", filters={"name": ["in", list(names)]}, pluck="name")
		return sorted(str(name) for name in existing)
