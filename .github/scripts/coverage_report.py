#!/usr/bin/env python3
"""Turn coverage.py XML into the two things Gameplan reports coverage with:

a Markdown summary (job summary + pull request comment) and a self-contained SVG
badge for the README. No external badge or coverage service is involved.

	python .github/scripts/coverage_report.py sites/coverage.xml \
		--markdown coverage.md --badge .github/badges/coverage.svg

The measured denominator is *product* code. `frappe.coverage` points coverage at
the whole app directory, so an unfiltered report counts the test suite itself --
which is ~100% covered by construction and silently inflates the headline (87.6%
against 83.7% at the time this was written). EXCLUDED is what that filter drops.
"""

import argparse
import sys
import xml.etree.ElementTree as ET

# Not product code: the test suite and its seed API are covered by definition,
# and the rest is developer or one-off tooling that ships behind no user path.
EXCLUDED = (
	("gameplan/tests/", "test suite"),
	("gameplan/ui_test_helpers.py", "Cypress seed API"),
	("gameplan/demo/", "demo data generator"),
	("gameplan/migrate_from_discourse/", "one-off Discourse importer"),
	("gameplan/patches/", "migration patches"),
	("gameplan/config/", "desk config stubs"),
)

# Longest prefix wins, so doctype-local api.py lands under DocTypes rather than API.
AREAS = (
	("gameplan/gameplan/doctype/", "DocTypes"),
	("gameplan/mixins/", "Mixins"),
	("gameplan/utils/", "Utilities"),
	("gameplan/permissions.py", "Permissions"),
	("gameplan/search_sqlite.py", "Search"),
	("gameplan/api.py", "HTTP API"),
	("gameplan/www/", "HTTP API"),
	("gameplan/extends/", "HTTP API"),
	("gameplan/email_digest.py", "Email digest"),
)

BADGE_COLORS = (
	(90, "#4c1"),  # brightgreen
	(80, "#97ca00"),  # green
	(70, "#a4a61d"),  # yellowgreen
	(60, "#dfb317"),  # yellow
	(50, "#fe7d37"),  # orange
	(0, "#e05d44"),  # red
)


class File:
	def __init__(self, name: str, covered: int, statements: int):
		self.name = name
		self.covered = covered
		self.statements = statements

	@property
	def rate(self) -> float:
		return 100.0 * self.covered / self.statements if self.statements else 100.0


def parse(path: str) -> list[File]:
	root = ET.parse(path).getroot()
	files = []
	for element in root.iter("class"):
		lines = element.find("lines")
		if lines is None:
			continue
		statements = len(lines)
		covered = sum(1 for line in lines if int(line.get("hits") or 0) > 0)
		files.append(File(element.get("filename") or "", covered, statements))
	return files


def is_product(name: str) -> bool:
	return not name.startswith(tuple(prefix for prefix, _ in EXCLUDED))


def area_of(name: str) -> str:
	match = max(
		(prefix for prefix, _ in AREAS if name.startswith(prefix)),
		key=len,
		default="",
	)
	return dict(AREAS).get(match, "Other")


def totals(files: list[File]) -> tuple[int, int, float]:
	covered = sum(f.covered for f in files)
	statements = sum(f.statements for f in files)
	return covered, statements, (100.0 * covered / statements if statements else 0.0)


def render_markdown(files: list[File]) -> str:
	covered, statements, rate = totals(files)
	out = [
		"## Backend coverage",
		"",
		f"**{rate:.1f}%** of product statements covered ({covered:,} / {statements:,}).",
		"",
		"| Area | Covered | Statements | Coverage |",
		"| --- | --: | --: | --: |",
	]

	by_area: dict[str, list[File]] = {}
	for file in files:
		by_area.setdefault(area_of(file.name), []).append(file)

	for area, group in sorted(by_area.items(), key=lambda item: -sum(f.statements for f in item[1])):
		area_covered, area_statements, area_rate = totals(group)
		out.append(f"| {area} | {area_covered:,} | {area_statements:,} | {area_rate:.1f}% |")
	out.append(f"| **Total** | **{covered:,}** | **{statements:,}** | **{rate:.1f}%** |")

	# A single "82.5%" is not actionable on its own; the gaps are what a reviewer
	# can act on. Small files are noise here, so only real modules are listed.
	weakest = sorted((f for f in files if f.statements >= 20), key=lambda f: f.rate)[:10]
	if weakest:
		out += ["", "<details><summary>Least-covered modules</summary>", ""]
		out += ["| File | Coverage |", "| --- | --: |"]
		out += [f"| `{f.name}` | {f.rate:.1f}% ({f.covered}/{f.statements}) |" for f in weakest]
		out.append("</details>")

	excluded = ", ".join(f"{label} (`{prefix}`)" for prefix, label in EXCLUDED)
	out += [
		"",
		f"<sub>Measured over product code only. Excluded: {excluded}. "
		"Coverage is informational — no minimum threshold is enforced.</sub>",
	]
	return "\n".join(out) + "\n"


# Approximate 11px Verdana advance widths, enough to keep the badge text centred
# without shipping a font metrics dependency.
CHAR_WIDTHS = {".": 4.0, "%": 10.5, " ": 3.5, "1": 6.0}


def text_width(text: str) -> float:
	return sum(CHAR_WIDTHS.get(character, 6.8) for character in text)


def badge_text(text: str, centre: int, width: int) -> list[str]:
	"""The drop shadow plus the label itself, drawn at 1/10th scale as shields.io does.

	`textLength` forces the glyphs to fill `width` exactly, so CHAR_WIDTHS only has to
	be close enough to pick a sensible box — it cannot push the text off-centre.
	"""
	length = width * 10
	shadow = 'fill="#010101" fill-opacity=".3"'
	return [
		f'\t\t<text aria-hidden="true" x="{centre}" y="150" {shadow} '
		f'transform="scale(.1)" textLength="{length}">{text}</text>',
		f'\t\t<text x="{centre}" y="140" transform="scale(.1)" ' f'textLength="{length}">{text}</text>',
	]


def render_badge(rate: float) -> str:
	label, message = "coverage", f"{rate:.1f}%"
	color = next(color for threshold, color in BADGE_COLORS if rate >= threshold)
	label_width = round(text_width(label)) + 20
	message_width = round(text_width(message)) + 20
	total = label_width + message_width
	font = "Verdana,Geneva,DejaVu Sans,sans-serif"

	lines = [
		f'<svg xmlns="http://www.w3.org/2000/svg" width="{total}" height="20" '
		f'role="img" aria-label="{label}: {message}">',
		f"\t<title>{label}: {message}</title>",
		'\t<linearGradient id="s" x2="0" y2="100%">',
		'\t\t<stop offset="0" stop-color="#bbb" stop-opacity=".1"/>',
		'\t\t<stop offset="1" stop-opacity=".1"/>',
		"\t</linearGradient>",
		f'\t<clipPath id="r"><rect width="{total}" height="20" rx="3" fill="#fff"/></clipPath>',
		'\t<g clip-path="url(#r)">',
		f'\t\t<rect width="{label_width}" height="20" fill="#555"/>',
		f'\t\t<rect x="{label_width}" width="{message_width}" height="20" fill="{color}"/>',
		f'\t\t<rect width="{total}" height="20" fill="url(#s)"/>',
		"\t</g>",
		f'\t<g fill="#fff" text-anchor="middle" font-family="{font}" '
		'font-size="110" text-rendering="geometricPrecision">',
		*badge_text(label, label_width * 5, label_width - 20),
		*badge_text(message, label_width * 10 + message_width * 5, message_width - 20),
		"\t</g>",
		"</svg>",
	]
	return "\n".join(lines) + "\n"


def main() -> int:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("coverage_xml", nargs="?", default="coverage.xml")
	parser.add_argument("--markdown", help="write the Markdown summary here (default: stdout)")
	parser.add_argument("--badge", help="write the README badge SVG here")
	args = parser.parse_args()

	try:
		files = [f for f in parse(args.coverage_xml) if is_product(f.name)]
	except (FileNotFoundError, ET.ParseError) as exc:
		# Coverage is reporting, not a gate: a missing report says so rather than
		# reddening a suite that passed.
		print(f"Coverage results were unavailable: {exc}", file=sys.stderr)
		return 1

	if not files:
		print(f"No product files found in {args.coverage_xml}", file=sys.stderr)
		return 1

	markdown = render_markdown(files)
	if args.markdown:
		with open(args.markdown, "w") as handle:
			handle.write(markdown)
	else:
		print(markdown, end="")

	if args.badge:
		with open(args.badge, "w") as handle:
			handle.write(render_badge(totals(files)[2]))

	return 0


if __name__ == "__main__":
	raise SystemExit(main())
