"""Append-only JSONL journal used for resumability.

Every record is flushed and fsynced immediately: a campaign is hours long and a crash
must never cost more than the single mutant that was in flight.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import IO


class Journal:
	"""Durable append-only record store keyed by mutant key."""

	def __init__(self, path: Path) -> None:
		self.path = path
		self._handle: IO[str] | None = None

	def __enter__(self) -> Journal:
		self.path.parent.mkdir(parents=True, exist_ok=True)
		self._handle = open(self.path, "a", encoding="utf-8")
		return self

	def __exit__(self, *exc: object) -> None:
		self.close()

	def close(self) -> None:
		if self._handle is not None:
			self._handle.close()
			self._handle = None

	def append(self, record: dict) -> None:
		if self._handle is None:
			raise RuntimeError("journal is not open")
		self._handle.write(json.dumps(record, sort_keys=True) + "\n")
		self._handle.flush()
		# fsync so an abrupt kill cannot lose already-completed work sitting in the
		# OS page cache.
		os.fsync(self._handle.fileno())


def read_records(path: Path) -> list[dict]:
	"""Read a JSONL journal, tolerating a truncated final line from a hard crash."""
	if not path.exists():
		return []
	records: list[dict] = []
	with open(path, encoding="utf-8") as handle:
		for line in handle:
			line = line.strip()
			if not line:
				continue
			try:
				records.append(json.loads(line))
			except ValueError:
				continue
	return records


def completed_keys(path: Path, exclude_statuses: frozenset[str] | set[str] | None = None) -> set[str]:
	"""Keys that count as done for resume purposes.

	``exclude_statuses`` keeps transient outcomes (a bench that failed to spawn, a
	locked site) out of the set so the next run re-evaluates them instead of leaving
	them stuck at their non-verdict forever.
	"""
	exclude = exclude_statuses or frozenset()
	# Keyed on the *latest* record so a re-run that errored is retried again, and a
	# re-run that produced a real verdict is not.
	return {key for key, record in latest_by_key(path).items() if record.get("status") not in exclude}


def latest_by_key(path: Path) -> dict[str, dict]:
	"""Last record wins, so a re-run of a mutant supersedes the earlier verdict."""
	result: dict[str, dict] = {}
	for record in read_records(path):
		key = record.get("key")
		if key:
			result[key] = record
	return result
