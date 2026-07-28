#!/usr/bin/env python3
"""Turn a Cobertura XML report into the two things Gameplan reports coverage with:

a Markdown summary (job summary + pull request comment) and a self-contained SVG
badge for the README. No external badge or coverage service is involved.

	python .github/scripts/coverage_report.py sites/coverage.xml \
		--profile backend --markdown coverage.md --badge coverage.svg

Both layers emit Cobertura, so one script serves both: coverage.py for the Python
suite, nyc for the istanbul-instrumented Cypress run. `--profile` selects which
denominator, area map and caveat apply.

The measured denominator is *product* code. `frappe.coverage` points coverage at
the whole app directory, so an unfiltered backend report counts the test suite
itself -- which is ~100% covered by construction and silently inflates the headline
(87.6% against 83.7% at the time this was written). `excluded` is what that filter
drops, and the report footer always names it.
"""

import argparse
import sys
import xml.etree.ElementTree as ET

import safe_xml


class Profile:
	def __init__(self, heading, badge_label, excluded, areas, caveat):
		self.heading = heading
		self.badge_label = badge_label
		self.excluded = excluded
		self.areas = areas
		self.caveat = caveat


PROFILES = {
	# Not product code: the test suite and its seed API are covered by definition,
	# and the rest is developer or one-off tooling that ships behind no user path.
	"backend": Profile(
		heading="Backend coverage",
		badge_label="coverage",
		excluded=(
			("gameplan/tests/", "test suite"),
			("gameplan/ui_test_helpers.py", "Cypress seed API"),
			("gameplan/demo/", "demo data generator"),
			("gameplan/migrate_from_discourse/", "one-off Discourse importer"),
			("gameplan/patches/", "migration patches"),
			("gameplan/config/", "desk config stubs"),
		),
		# Longest prefix wins, so a doctype-local api.py lands under DocTypes.
		areas=(
			("gameplan/gameplan/doctype/", "DocTypes"),
			("gameplan/mixins/", "Mixins"),
			("gameplan/utils/", "Utilities"),
			("gameplan/permissions.py", "Permissions"),
			("gameplan/search_sqlite.py", "Search"),
			("gameplan/api.py", "HTTP API"),
			("gameplan/www/", "HTTP API"),
			("gameplan/extends/", "HTTP API"),
			("gameplan/email_digest.py", "Email digest"),
		),
		caveat="Measured over product code only.",
	),
	# The frontend number comes from Cypress driving an instrumented build, so it
	# says a line *ran*, not that a spec asserted anything about it. It is not the
	# same kind of number as the backend's and should not be read against it.
	"frontend": Profile(
		heading="Frontend coverage",
		badge_label="frontend",
		excluded=(("src/types/", "generated doctype types"),),
		areas=(
			("src/components/", "Components"),
			("src/pages/", "Pages"),
			("src/data/", "Data layer"),
			("src/utils/", "Utilities"),
			("src/composables/", "Composables"),
			("src/directives/", "Directives"),
		),
		caveat=(
			"Collected by Cypress against an istanbul-instrumented build, so it marks "
			"lines that **ran**, not lines a spec asserted on — read it to find untouched "
			"areas, not as a quality score against the backend number."
		),
	),
}

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


# A real report for this app is well under a megabyte. The cap and the entity
# refusal below matter because the fork reporter parses a file a fork produced:
# ElementTree expands internal entities, so an untrusted report could otherwise
# exhaust the runner ("billion laughs").
#
# Size caps and entity-declaration refusal live in safe_xml, shared with the JUnit
# renderer: both are handed fork-controlled artifacts by the privileged reporters,
# and a guard that only one of them remembers to apply is not a guard.
#
# Note that `<!DOCTYPE` itself is fine — nyc's Cobertura output legitimately points
# at the Cobertura DTD, and expat fetches no external DTD, so a doctype on its own
# expands nothing. Entity *declarations* are the whole attack.


def parse(path: str) -> list[File]:
	root = safe_xml.fromstring(safe_xml.read_capped(path))
	files = []
	for element in root.iter("class"):
		lines = element.find("lines")
		if lines is None:
			continue
		statements = len(lines)
		covered = sum(1 for line in lines if int(line.get("hits") or 0) > 0)
		files.append(File(element.get("filename") or "", covered, statements))
	return files


def is_product(name: str, profile: Profile) -> bool:
	return not name.startswith(tuple(prefix for prefix, _ in profile.excluded))


def area_of(name: str, profile: Profile) -> str:
	match = max(
		(prefix for prefix, _ in profile.areas if name.startswith(prefix)),
		key=len,
		default="",
	)
	return dict(profile.areas).get(match, "Other")


def totals(files: list[File]) -> tuple[int, int, float]:
	covered = sum(f.covered for f in files)
	statements = sum(f.statements for f in files)
	return covered, statements, (100.0 * covered / statements if statements else 0.0)


def render_markdown(files: list[File], profile: Profile, compact: bool = False) -> str:
	"""Full standalone report, or a fragment for the shared PR comment.

	Compact mode leads with the percentage alone and folds the tables away: in the
	PR comment this sits under a test-result line that has already earned the
	reader's attention, and the number is the part worth reading at a glance.
	"""
	covered, statements, rate = totals(files)
	if compact:
		out = [
			f"Coverage **{rate:.1f}%** ({covered:,} / {statements:,} statements)",
			"",
			f"<details><summary>{profile.heading} by area</summary>",
			"",
		]
	else:
		out = [
			f"## {profile.heading}",
			"",
			f"**{rate:.1f}%** of product statements covered ({covered:,} / {statements:,}).",
			"",
		]
	out += [
		"| Area | Covered | Statements | Coverage |",
		"| --- | --: | --: | --: |",
	]

	by_area: dict[str, list[File]] = {}
	for file in files:
		by_area.setdefault(area_of(file.name, profile), []).append(file)

	for area, group in sorted(by_area.items(), key=lambda item: -sum(f.statements for f in item[1])):
		area_covered, area_statements, area_rate = totals(group)
		out.append(f"| {area} | {area_covered:,} | {area_statements:,} | {area_rate:.1f}% |")
	out.append(f"| **Total** | **{covered:,}** | **{statements:,}** | **{rate:.1f}%** |")

	# A single "82.5%" is not actionable on its own; the gaps are what a reviewer
	# can act on. Small files are noise here, so only real modules are listed.
	weakest = sorted((f for f in files if f.statements >= 20), key=lambda f: f.rate)[:10]
	if weakest:
		# Already inside a <details> when compact; nesting a second one buries it.
		out.append("")
		if not compact:
			out += ["<details><summary>Least-covered modules</summary>", ""]
		else:
			out.append("**Least covered**")
			out.append("")
		out += ["| File | Coverage |", "| --- | --: |"]
		out += [f"| `{f.name}` | {f.rate:.1f}% ({f.covered}/{f.statements}) |" for f in weakest]
		if not compact:
			out.append("</details>")

	excluded = ", ".join(f"{label} (`{prefix}`)" for prefix, label in profile.excluded)
	out += [
		"",
		f"<sub>{profile.caveat} Excluded: {excluded}. "
		"Coverage is informational — no minimum threshold is enforced.</sub>",
	]
	if compact:
		out += ["", "</details>"]
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


def render_badge(rate: float, label: str) -> str:
	message = f"{rate:.1f}%"
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
	parser.add_argument(
		"--profile",
		choices=sorted(PROFILES),
		default="backend",
		help="which denominator, area map and caveat to apply (default: backend)",
	)
	parser.add_argument("--markdown", help="write the Markdown summary here (default: stdout)")
	parser.add_argument("--badge", help="write the README badge SVG here")
	parser.add_argument(
		"--compact",
		action="store_true",
		help="render as a fragment for the shared PR comment rather than a standalone report",
	)
	args = parser.parse_args()
	profile = PROFILES[args.profile]

	try:
		files = [f for f in parse(args.coverage_xml) if is_product(f.name, profile)]
	except (FileNotFoundError, ET.ParseError, ValueError) as exc:
		# Coverage is reporting, not a gate: a missing report says so rather than
		# reddening a suite that passed.
		print(f"Coverage results were unavailable: {exc}", file=sys.stderr)
		return 1

	if not files:
		print(f"No product files found in {args.coverage_xml}", file=sys.stderr)
		return 1

	markdown = render_markdown(files, profile, compact=args.compact)
	if args.markdown:
		with open(args.markdown, "w") as handle:
			handle.write(markdown)
	else:
		print(markdown, end="")

	if args.badge:
		with open(args.badge, "w") as handle:
			handle.write(render_badge(totals(files)[2], profile.badge_label))

	return 0


if __name__ == "__main__":
	raise SystemExit(main())
