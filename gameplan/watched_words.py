import hashlib

import frappe
from frappe.utils import cint
from frappe.utils.csvutils import build_csv_response, read_csv_content

from gameplan.paging import page_start
from gameplan.permissions import require_can_manage_community
from gameplan.watched_word_matching import matches

ACTIONS = ("Block", "Censor", "Require approval", "Flag")


def validate_rule(doc):
	require_can_manage_community(doc.community)
	before = doc.get_doc_before_save()
	if before:
		require_can_manage_community(before.community)
	normalize_rule(doc)
	frappe.db.get_value("GP Team", doc.community, "name", for_update=True)
	if (
		doc.is_new()
		and not frappe.db.exists("GP Watched Word", {"rule_key": doc.rule_key})
		and frappe.db.count("GP Watched Word", {"community": doc.community, "action": doc.action}) >= 2000
	):
		frappe.throw("A Community can have at most 2,000 rules per action")
	frappe.local.request_cache.clear()


def normalize_rule(doc):
	if doc.action not in ACTIONS:
		frappe.throw("Choose a watched-word action")
	doc.word = (doc.word or "").strip()
	if not doc.word.strip("* ") or len(doc.word) > 100 or "\n" in doc.word or "\r" in doc.word:
		frappe.throw("Enter a word or phrase of 1–100 characters; wildcards need a word")
	doc.case_sensitive = cint(doc.case_sensitive)
	word = doc.word if doc.case_sensitive else doc.word.casefold()
	doc.rule_key = hashlib.sha256(
		frappe.as_json([doc.community, doc.action, word, doc.case_sensitive]).encode()
	).hexdigest()


@frappe.whitelist(methods=["GET", "POST"])
def rules(community: str, action: str, start: int = 0):
	"""List one Community's watched words for its admins."""
	require_can_manage_community(community)
	if action not in ACTIONS:
		frappe.throw("Choose a watched-word action")
	rows = frappe.get_all(
		"GP Watched Word",
		filters={"community": community, "action": action},
		fields=["name", "word", "case_sensitive"],
		order_by="creation desc, name desc",
		limit_start=page_start(start),
		limit_page_length=41,
	)
	return {"items": rows[:40], "has_more": len(rows) > 40}


@frappe.whitelist(methods=["POST"])
def add(community: str, action: str, word: str, case_sensitive: bool = False):
	"""Add a word or phrase to a Community's moderation rules."""
	doc = frappe.get_doc(
		doctype="GP Watched Word",
		community=community,
		action=action,
		word=word,
		case_sensitive=case_sensitive,
	)
	validate_rule(doc)
	if not frappe.db.exists("GP Watched Word", {"rule_key": doc.rule_key}):
		doc.insert(ignore_permissions=True)
	return {"added": bool(doc.name)}


@frappe.whitelist(methods=["POST"])
def remove(community: str, name: str):
	"""Delete one watched-word rule within the admin's Community."""
	require_can_manage_community(community)
	doc = frappe.get_doc("GP Watched Word", name)
	if doc.community != community:
		frappe.throw("This rule is unavailable", frappe.PermissionError)
	doc.delete(ignore_permissions=True)
	frappe.local.request_cache.clear()


@frappe.whitelist(methods=["GET"])
def download(community: str, action: str, sample: bool = False):
	"""Download watched words or an import sample in Discourse's CSV format."""
	require_can_manage_community(community)
	if action not in ACTIONS:
		frappe.throw("Choose a watched-word action")
	rows = (
		[["example phrase", "", "false"]]
		if sample
		else [
			[row.word, "", "true" if row.case_sensitive else "false"]
			for row in frappe.get_all(
				"GP Watched Word",
				filters={"community": community, "action": action},
				fields=["word", "case_sensitive"],
				order_by="word asc",
				limit=2000,
			)
		]
	)
	build_csv_response(rows, "watched-words")


@frappe.whitelist(methods=["POST"])
def upload(community: str, action: str, file: str, expected: str = ""):
	"""Preview a private CSV, or atomically import it after its preview is confirmed."""
	require_can_manage_community(community)
	if action not in ACTIONS:
		frappe.throw("Choose a watched-word action")
	file_doc = frappe.get_doc("File", file)
	file_doc.check_permission("read")
	if (
		not (file_doc.file_url or "").startswith("/private/files/")
		or file_doc.owner != frappe.session.user
		or not file_doc.get("is_private")
		or file_doc.attached_to_doctype
	):
		frappe.throw("Choose your own unattached private CSV upload", frappe.PermissionError)
	if file_doc.file_size > 1024 * 1024:
		frappe.throw("CSV uploads must be at most 1 MB")
	content = file_doc.get_content()
	if len(content.encode() if isinstance(content, str) else content) > 1024 * 1024:
		frappe.throw("CSV uploads must be at most 1 MB")
	if isinstance(content, str):
		content = content.lstrip("\ufeff")
	else:
		content = content.removeprefix(b"\xef\xbb\xbf")
	try:
		rows = read_csv_content(content)
	except Exception:
		frappe.throw("Upload a valid comma-separated CSV")
	if len(rows) > 2000:
		frappe.throw("Upload at most 2,000 CSV rows")
	frappe.db.get_value("GP Team", community, "name", for_update=True)
	existing = set(
		frappe.get_all(
			"GP Watched Word",
			filters={"community": community, "action": action},
			pluck="rule_key",
			limit=2000,
		)
	)
	pending, duplicates, seen = [], 0, set(existing)
	for number, row in enumerate(rows, 1):
		if not row or not any(row):
			continue
		if (
			len(row) > 3
			or not row[0]
			or (len(row) > 2 and row[2] and row[2].lower() not in {"true", "false"})
		):
			frappe.throw(f"Row {number}: expected word/phrase, unused column, optional true/false")
		doc = frappe.get_doc(
			doctype="GP Watched Word",
			community=community,
			action=action,
			word=row[0],
			case_sensitive=len(row) > 2 and str(row[2]).lower() == "true",
		)
		try:
			normalize_rule(doc)
		except frappe.ValidationError as error:
			frappe.throw(f"Row {number}: {error}")
		if doc.rule_key in seen:
			duplicates += 1
		else:
			seen.add(doc.rule_key)
			pending.append(doc)
	if len(existing) + len(pending) > 2000:
		frappe.throw("This import would exceed 2,000 rules for this action")
	digest = hashlib.sha256(frappe.as_json([community, action, sorted(seen)]).encode()).hexdigest()
	if expected:
		if expected != digest:
			frappe.throw(
				"The file or rules changed. Preview the import again.", frappe.TimestampMismatchError
			)
		from frappe.model.document import bulk_insert

		# Every row and the Community limit were validated under the same parent lock.
		for doc in pending:
			doc.name = frappe.generate_hash(length=10)
		bulk_insert("GP Watched Word", pending)
		frappe.local.request_cache.clear()
	return {
		"expected": digest,
		"added": len(pending),
		"duplicates": duplicates,
		"words": [doc.word for doc in pending[:40]],
		"applied": bool(expected),
	}


@frappe.whitelist(methods=["POST"])
def test(community: str, title: str = "", content: str = ""):
	"""Test content against the Community's four watched-word actions without publishing."""
	require_can_manage_community(community)
	return {action: matches(community, action, title, content) for action in ACTIONS}


def delete_rules(doc, method=None):
	frappe.db.delete("GP Watched Word", {"community": doc.name})
