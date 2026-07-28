# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""The bundled demo fixture must stay replayable by the seeder that ships with it.

``gameplan.demo.demo.generate`` commits a full ``clear()`` before the replay, so a
fixture the seeder cannot finish does not merely fail — it empties the site and then
raises, and ``generate_data_daily`` is on the ``daily`` scheduler hook. These are
static contract tests: they read the fixture and the handler set, never the database.
"""

import json
import os
import tempfile
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from gameplan.demo.demo import FIXTURE_DIR, generate
from gameplan.demo.seeder import Seeder

EVENTS_PATH = os.path.join(FIXTURE_DIR, "events.jsonl")


def _fixture_event_types() -> set[str]:
	with open(EVENTS_PATH, encoding="utf-8") as f:
		return {json.loads(line)["type"] for line in f if line.strip()}


def _handled_event_types() -> set[str]:
	prefix = "_event_"
	return {name[len(prefix) :] for name in dir(Seeder) if name.startswith(prefix)}


class TestDemoFixtureContract(FrappeTestCase):
	def test_every_fixture_event_type_has_a_seeder_handler(self):
		orphans = sorted(_fixture_event_types() - _handled_event_types())

		self.assertEqual(
			orphans,
			[],
			f"{EVENTS_PATH} contains event types with no Seeder._event_* handler: {orphans}. "
			"generate() commits clear() before replaying, so this wipes the site and then raises.",
		)

	def test_every_seeder_handler_is_exercised_by_the_fixture(self):
		unused = sorted(_handled_event_types() - _fixture_event_types())

		self.assertEqual(
			unused,
			[],
			f"Seeder handles event types the fixture never produces: {unused}. "
			"Either the fixture lost content or the handler is dead code.",
		)

	def test_the_bundled_fixture_passes_the_pre_clear_validation(self):
		self.assertEqual(Seeder.validate_events(EVENTS_PATH), [])


class TestDemoFixtureValidation(FrappeTestCase):
	"""``Seeder.validate_events`` is the guard that keeps a bad fixture from wiping a site."""

	def test_an_unknown_event_type_is_reported(self):
		problems = self._validate([{"t": "-1d 10:00", "type": "follow", "actor": "maya", "on": "art"}])

		self.assertEqual(len(problems), 1)
		self.assertIn("'follow'", problems[0])

	def test_an_unparseable_relative_time_is_reported(self):
		problems = self._validate([{"t": "yesterday", "type": "user"}])

		self.assertEqual(len(problems), 1)
		self.assertIn("invalid relative time", problems[0])

	def test_a_valid_log_reports_nothing(self):
		self.assertEqual(self._validate([{"t": "-1d 10:00", "type": "user"}]), [])

	def test_generate_refuses_before_clearing_when_an_event_has_no_handler(self):
		with tempfile.TemporaryDirectory() as fixture_dir:
			_write_events(fixture_dir, [{"t": "-1d 10:00", "type": "nosuchevent"}])

			# clear() is mocked so a regression here cannot delete anything: the point
			# of the assertion is that generate() never reaches it.
			with patch("gameplan.demo.demo.clear") as clear:
				with self.assertRaises(frappe.ValidationError):
					generate(fixture_path=fixture_dir, force=True)

			clear.assert_not_called()

	def _validate(self, events):
		with tempfile.TemporaryDirectory() as fixture_dir:
			return Seeder.validate_events(_write_events(fixture_dir, events))


def _write_events(fixture_dir, events) -> str:
	events_path = os.path.join(fixture_dir, "events.jsonl")
	with open(events_path, "w", encoding="utf-8") as f:
		for event in events:
			f.write(json.dumps(event) + "\n")
	return events_path
