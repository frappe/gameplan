#!/usr/bin/env python3
"""Guards for XML that a fork pull request controls.

The `*-report.yml` reporters run in the trusted base repo with a write-scoped
token and parse artifacts produced by an untrusted fork — coverage reports and
JUnit results alike. Every read of that XML goes through here so a single place
decides what is refused, rather than each renderer hardening itself and one of
them forgetting.

Two distinct hazards:

* **Size.** An artifact is whatever the fork chose to upload. Caps are applied
  per document, across a whole directory, and to the number of documents, so a
  reporter cannot be made to read gigabytes or a million tiny files.
* **Entity expansion.** A few nested internal entities expand to gigabytes
  ("billion laughs"). Scanning raw bytes for `<!ENTITY` does not work: XML
  declares its own encoding, so the identical declaration in UTF-16 shares no
  bytes with an ASCII needle and slips past while expat parses and expands it
  regardless. Asking expat itself runs the check after decoding, so it holds for
  every encoding.
"""

import xml.etree.ElementTree as ET
import xml.parsers.expat as expat

# Real reports are far below these: the 545-test backend JUnit file is ~200 KB and
# a Cobertura report for the whole frontend ~1 MB. They exist to bound the damage,
# not to fit the data.
MAX_DOCUMENT_BYTES = 16 * 1024 * 1024
MAX_TOTAL_BYTES = 64 * 1024 * 1024
MAX_DOCUMENTS = 2000


class _PrologParsed(Exception):
	"""Raised to stop expat once the root element starts."""


def read_capped(path: str, limit: int = MAX_DOCUMENT_BYTES) -> bytes:
	"""Read a file, refusing one larger than `limit`."""
	with open(path, "rb") as handle:
		raw = handle.read(limit + 1)
	if len(raw) > limit:
		raise ValueError(f"{path} is larger than {limit} bytes")
	return raw


def reject_entity_declarations(raw: bytes) -> None:
	"""Refuse a document that declares XML entities, whatever its encoding.

	Entity declarations live in the DOCTYPE, which precedes the root element, so
	parsing stops as soon as that element opens: the prolog alone is enough to
	decide and nothing large is ever expanded.
	"""
	parser = expat.ParserCreate()

	def refuse(*_args):
		raise ValueError("refusing to parse XML that declares entities")

	parser.EntityDeclHandler = refuse
	parser.UnparsedEntityDeclHandler = refuse
	parser.StartElementHandler = lambda *_args: (_ for _ in ()).throw(_PrologParsed())

	try:
		parser.Parse(raw, True)
	except _PrologParsed:
		pass
	except expat.ExpatError as exc:
		raise ValueError(f"not valid XML: {exc}") from exc


def fromstring(raw: bytes):
	"""Parse bytes into an element tree, refusing entity declarations first."""
	reject_entity_declarations(raw)
	return ET.fromstring(raw)


class Budget:
	"""Caps the total bytes and document count read across many files."""

	def __init__(self, max_total: int = MAX_TOTAL_BYTES, max_documents: int = MAX_DOCUMENTS):
		self.max_total = max_total
		self.max_documents = max_documents
		self.spent = 0
		self.documents = 0

	def read(self, path: str) -> bytes:
		self.documents += 1
		if self.documents > self.max_documents:
			raise ValueError(f"refusing to read more than {self.max_documents} XML files")
		raw = read_capped(path)
		self.spent += len(raw)
		if self.spent > self.max_total:
			raise ValueError(f"refusing to read more than {self.max_total} bytes of XML")
		return raw
