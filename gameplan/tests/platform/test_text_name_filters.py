import re
from pathlib import Path

from gameplan.tests.base import GameplanTestCase

APP = Path(__file__).resolve().parents[2]
# A filter on a link column with a document's own number. The column holds text, so MariaDB
# cannot use its index and reads the whole table: 12 s to open a discussion with 5M replies.
BARE_NUMBER = re.compile(r'"(reference_name|discussion)":\s*(self|doc)\.name\b(?!\))')


class TestTextNameFilters(GameplanTestCase):
	def test_filters_on_link_columns_pass_the_name_as_text(self):
		offenders = []
		for path in APP.rglob("*.py"):
			if "tests" in path.parts or "patches" in path.parts or "migrate_from_discourse" in path.parts:
				continue
			for number, line in enumerate(path.read_text().splitlines(), 1):
				if BARE_NUMBER.search(line) and "str(" not in line:
					offenders.append(f"{path.relative_to(APP)}:{number}: {line.strip()}")
		self.assertEqual(offenders, [])
