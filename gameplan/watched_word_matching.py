import fnmatch
import re
from functools import lru_cache

import frappe
from bs4 import BeautifulSoup, Comment, NavigableString
from frappe.utils.caching import request_cache


@request_cache
def rules_for(community, action):
	return frappe.get_all(
		"GP Watched Word",
		filters={"community": community, "action": action},
		fields=["word", "case_sensitive"],
		limit=2000,
	)


@lru_cache(maxsize=8192)
def pattern(word, case_sensitive=False):
	# fnmatch uses atomic groups for internal wildcards, avoiding exponential backtracking.
	translated = fnmatch.translate(word.replace("[", "[[]").replace("?", "[?]"))[4:-3]
	translated = translated.replace(".*?", r"\S*?").replace(".*", r"\S*")
	return re.compile(r"(?<!\w)(?:" + translated + r")(?!\w)", 0 if case_sensitive else re.IGNORECASE)


def prose(content, *, links=False):
	soup = BeautifulSoup(content or "", "html.parser")
	for node in soup.find_all(["code", "pre", "script", "style"]):
		node.replace_with("\n")
	for block in soup.find_all(["p", "div", "li", "blockquote", "br"]):
		block.insert_after("\n")
	text = soup.get_text()
	if links:
		text += " " + " ".join(str(a.get("href", "")) for a in soup.find_all("a"))
	return text


def matches(community, action, title, content):
	text = (title or "") + "\n" + prose(content, links=True)
	return [
		row.word for row in rules_for(community, action) if pattern(row.word, row.case_sensitive).search(text)
	]


def censor(community, text, *, html=False):
	if not text:
		return text
	rules = rules_for(community, "Censor")
	if not rules:
		return text

	def mask(value):
		characters = list(value)
		for row in rules:
			for match in pattern(row.word, row.case_sensitive).finditer(value):
				characters[match.start() : match.end()] = "■" * (match.end() - match.start())
		return "".join(characters)

	if not html:
		return mask(text)
	soup = BeautifulSoup(text, "html.parser")
	group = []
	changed = False
	last_block = None

	def flush():
		nonlocal changed
		text = "".join(str(node) for node in group)
		masked, offset = mask(text), 0
		changed = changed or masked != text
		for node in group:
			length = len(str(node))
			node.replace_with(masked[offset : offset + length])
			offset += length
		group.clear()

	for node in list(soup.descendants):
		if getattr(node, "name", None) == "br":
			flush()
		if not isinstance(node, NavigableString) or isinstance(node, Comment):
			continue
		anchor = node.find_parent("a")
		block = node.find_parent(["p", "div", "li", "blockquote", "h1", "h2", "h3"])
		if node.find_parent(["code", "pre", "script", "style"]) or (
			anchor and str(node).strip() == anchor.get("href")
		):
			flush()
			continue
		if block is not last_block:
			flush()
		last_block = block
		group.append(node)
	flush()
	return str(soup) if changed else text
