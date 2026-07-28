#!/usr/bin/env python3
"""Maintain one PR comment that several workflows write different sections of.

	pr_comment.py --repo owner/name --pr 12 --section backend --body-file part.md

Server Tests and UI Tests finish at different times and each knows only its own
half of the story, but a pull request should carry a single test report rather
than one comment per workflow. So the comment is addressed by a hidden marker and
divided into named sections; each workflow rewrites only its own section and
leaves the rest of the body untouched.

Concurrency: the GitHub comments API has no compare-and-swap, so two workflows
finishing within the same moment can both read the body before either writes, and
the later write drops the earlier section. That is why the write is verified and
retried — a clobbered writer re-reads the winner's body, re-applies its own
section on top, and the comment converges. The reverse case (this job is the one
that clobbered) is repaired by the other job's identical retry.
"""

import argparse
import json
import re
import subprocess
import sys
import time

MARKER = "<!-- sticky:{header} -->"
SECTION_OPEN = "<!-- section:{name} -->"
SECTION_CLOSE = "<!-- /section:{name} -->"

# Sections render in this order no matter which workflow writes first, so the
# comment does not reshuffle itself as runs land.
SECTION_ORDER = ("backend", "frontend")

TITLE = "### Test report"

MAX_ATTEMPTS = 4


def gh(*args: str, input_text: str | None = None) -> str:
	result = subprocess.run(["gh", *args], capture_output=True, text=True, check=False, input=input_text)
	if result.returncode != 0:
		raise RuntimeError(f"gh {' '.join(args)} failed: {result.stderr.strip()}")
	return result.stdout


def find_comment(repo: str, pr: str, marker: str) -> dict | None:
	# --jq flattens the pages into one object per line; without it --paginate
	# concatenates a separate JSON array per page, which is awkward to parse back.
	# Restricted to bot-authored comments so a human comment quoting the marker
	# (a review discussing this script, say) cannot be mistaken for the report.
	raw = gh(
		"api",
		f"repos/{repo}/issues/{pr}/comments",
		"--paginate",
		"--jq",
		'.[] | select(.user.type == "Bot") | {id: .id, body: .body}',
	)
	for line in raw.splitlines():
		line = line.strip()
		if not line:
			continue
		try:
			comment = json.loads(line)
		except json.JSONDecodeError:
			continue
		if marker in (comment.get("body") or ""):
			return comment
	return None


def split_sections(body: str) -> dict[str, str]:
	"""Pull each delimited section out of an existing comment body."""
	found = {}
	for name in SECTION_ORDER:
		pattern = re.compile(
			re.escape(SECTION_OPEN.format(name=name))
			+ r"\n(.*?)\n"
			+ re.escape(SECTION_CLOSE.format(name=name)),
			re.S,
		)
		match = pattern.search(body)
		if match:
			found[name] = match.group(1)
	return found


def render(marker: str, sections: dict[str, str], footer: str) -> str:
	parts = [marker, TITLE, ""]
	for name in SECTION_ORDER:
		if name not in sections:
			continue
		parts.append(SECTION_OPEN.format(name=name))
		parts.append(sections[name])
		parts.append(SECTION_CLOSE.format(name=name))
		parts.append("")
	if footer:
		parts.append(footer)
	return "\n".join(parts).rstrip() + "\n"


def write(repo: str, pr: str, comment: dict | None, body: str) -> dict:
	# The body goes through a file: it contains newlines, backticks and markdown
	# tables, none of which survive being spliced into an argument list reliably.
	payload = json.dumps({"body": body})
	if comment:
		out = gh(
			"api",
			"-X",
			"PATCH",
			f"repos/{repo}/issues/comments/{comment['id']}",
			"--input",
			"-",
			input_text=payload,
		)
	else:
		out = gh(
			"api",
			"-X",
			"POST",
			f"repos/{repo}/issues/{pr}/comments",
			"--input",
			"-",
			input_text=payload,
		)
	return json.loads(out)


def main() -> int:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--repo", required=True)
	parser.add_argument("--pr", required=True)
	parser.add_argument("--section", required=True, choices=SECTION_ORDER)
	parser.add_argument("--body-file", required=True)
	parser.add_argument("--header", default="test-report")
	parser.add_argument("--footer", default="")
	args = parser.parse_args()

	with open(args.body_file, encoding="utf-8") as handle:
		section_body = handle.read().strip()

	if not section_body:
		print("Nothing to report; leaving the comment alone.")
		return 0

	marker = MARKER.format(header=args.header)

	for attempt in range(1, MAX_ATTEMPTS + 1):
		comment = find_comment(args.repo, args.pr, marker)
		sections = split_sections(comment["body"]) if comment else {}
		sections[args.section] = section_body
		body = render(marker, sections, args.footer)

		try:
			write(args.repo, args.pr, comment, body)
		except RuntimeError as error:
			# A comment deleted between the read and the write 404s; retrying
			# re-reads and posts a fresh one.
			print(f"Attempt {attempt} failed: {error}", file=sys.stderr)
			if attempt == MAX_ATTEMPTS:
				return 1
			time.sleep(2 * attempt)
			continue

		# Confirm the section survived. If another workflow wrote between this
		# read and write, its body won this round and ours needs re-applying.
		time.sleep(1)
		current = find_comment(args.repo, args.pr, marker)
		if current and section_body in (current.get("body") or ""):
			print(f"Wrote the {args.section} section of the test report.")
			return 0
		print(
			f"The {args.section} section was overwritten by a concurrent run; retrying.",
			file=sys.stderr,
		)
		time.sleep(2 * attempt)

	print("Gave up trying to write the test report comment.", file=sys.stderr)
	return 1


if __name__ == "__main__":
	raise SystemExit(main())
