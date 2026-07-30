# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

"""Unit tests for mutation site discovery and mutant identity.

The mutant key is the harness's memory. A campaign is hours long, so every verdict is
cached under it and resumed from it; the verify stage re-derives a survivor's site from
the current source by that key alone. Two properties therefore matter more than anything
else in this module, and both are pinned here:

* STABILITY - a behaviour-neutral edit (a comment, a reformat, a change inside an
  unrelated block) must not change a key, or hours of verdicts are thrown away and
  journalled survivors are silently dropped from the verify pass.
* NON-REBINDING - a key must never move from one site to another. Deleting one of
  several identical sites used to shift a positional ordinal, handing the deleted site's
  cached verdict to a site that was never evaluated. Invalidation costs a re-run;
  rebinding reports a fabricated verdict, so the tests below insist on the former.

Deliberately no site, no bench, no subprocess: ``collect_sites`` takes a source string
and returns dataclasses, so these stay pure.
"""

from __future__ import annotations

import ast
import unittest
from pathlib import Path

from gameplan.tests.mutation import mutators

REL = "sample.py"

# Two mutation sites that are identical in every respect except where they sit: same
# function, same statement, same mutator, same original and mutated text.
TWINS = """
def f(a, b):
	x = 1
	if a or b:
		x = 2
	y = 3
	if a or b:
		y = 4
	return x, y
"""

RICH = '''
"""Module docstring - never mutated."""
from __future__ import annotations

import os

__all__ = ["run"]

LIMIT = 10


class Thing:
	"""Class docstring."""

	def __init__(self, size=3):
		self.size = size

	def check(self, other, strict=False):
		"""Method docstring."""
		if self.size > other.size and not strict:
			return True
		total = self.size + other.size - 1
		for index in range(0, total):
			if index == LIMIT or index in (1, 2):
				return index / 2
		return "fallback"


def run(items, retries=2):
	if items is None or len(items) <= 0:
		return None
	while retries > 0:
		retries = retries - 1
	return os.path.join("a", "b")
'''


def keys(source: str, mutator: str | None = None, rel_path: str = REL) -> list[str]:
	return [s.key for s in sites(source, mutator, rel_path)]


def sites(
	source: str, mutator: str | None = None, rel_path: str = REL, mutate_strings: bool = False
) -> list[mutators.MutationSite]:
	found = mutators.collect_sites(source, rel_path, mutate_strings=mutate_strings)
	return [s for s in found if mutator is None or s.mutator == mutator]


def normalised(text: str) -> str:
	return " ".join(text.split())


class TestKeyStability(unittest.TestCase):
	"""Behaviour-neutral edits must leave every key untouched."""

	def test_comments_do_not_change_keys(self):
		base = "def g(x):\n\tif x > 1 and x < 9:\n\t\treturn 1\n\treturn 2\n"
		commented = (
			"def g(x):\n"
			"\t# explain the guard\n"
			"\tif x > 1 and x < 9:\n"
			"\t\t# and the body\n"
			"\t\treturn 1\n"
			"\treturn 2\n"
		)
		self.assertEqual(keys(base), keys(commented))

	def test_reformatting_does_not_change_keys(self):
		base = "def g(x):\n\tif x > 1 and x < 9:\n\t\treturn h(x, 1)\n\treturn 2\n"
		# What `ruff format` does to a long line: explode it and add a trailing comma.
		reformatted = (
			"def g(x):\n"
			"\tif (\n\t\tx > 1\n\t\tand x < 9\n\t):\n"
			"\t\treturn h(\n\t\t\tx,\n\t\t\t1,\n\t\t)\n"
			"\treturn 2\n"
		)
		self.assertEqual(keys(base), keys(reformatted))

	def test_editing_a_block_does_not_rekey_its_header(self):
		"""A site in an `if` header is not about the block's body, so body edits are none of its business."""
		base = "def g(x):\n\tif x > 1:\n\t\treturn 1\n\treturn 2\n"
		bigger_body = "def g(x):\n\tif x > 1:\n\t\tlog('hi')\n\t\treturn compute(x)\n\treturn 2\n"
		header_key = keys(base, mutators.MUTATOR_COMPARISON)
		self.assertEqual(len(header_key), 1)
		self.assertIn(header_key[0], keys(bigger_body, mutators.MUTATOR_COMPARISON))

	def test_editing_another_function_does_not_rekey(self):
		base = "def g(x):\n\tif x > 1:\n\t\treturn 1\n\treturn 2\n"
		with_neighbour = "def new_helper(y):\n\treturn y or 0\n\n\n" + base
		self.assertTrue(set(keys(base)).issubset(set(keys(with_neighbour))))

	def test_key_is_scoped_to_the_file(self):
		base = "def g(x):\n\tif x > 1:\n\t\treturn 1\n"
		self.assertNotEqual(keys(base, rel_path="a.py"), keys(base, rel_path="b.py"))


class TestIdenticalSites(unittest.TestCase):
	"""Sites that differ only in position must stay distinguishable, and must never swap keys."""

	def test_identical_sites_get_distinct_keys(self):
		found = keys(TWINS, mutators.MUTATOR_BOOLEAN_OP)
		self.assertEqual(len(found), 2)
		self.assertEqual(len(set(found)), 2)

	def test_every_key_in_a_file_is_unique(self):
		found = keys(RICH)
		self.assertEqual(len(found), len(set(found)))

	def test_deleting_one_twin_does_not_rebind_the_other(self):
		before = keys(TWINS, mutators.MUTATOR_BOOLEAN_OP)
		trimmed = """
def f(a, b):
	x = 1
	y = 3
	if a or b:
		y = 4
	return x, y
"""
		after = keys(trimmed, mutators.MUTATOR_BOOLEAN_OP)
		self.assertEqual(len(after), 1)
		# The survivor may be re-keyed (it gets re-run, which is cheap and honest), but it
		# must never adopt the key the deleted site's verdict is filed under.
		self.assertNotIn(after[0], before)

	def test_reordering_twins_does_not_rebind(self):
		before = keys(TWINS, mutators.MUTATOR_BOOLEAN_OP)
		reordered = """
def f(a, b):
	if a or b:
		y = 4
	x = 1
	y = 3
	if a or b:
		x = 2
	return x, y
"""
		after = keys(reordered, mutators.MUTATOR_BOOLEAN_OP)
		self.assertEqual(len(after), 2)
		self.assertEqual(set(after) & set(before), set())

	def test_twins_are_stable_when_nothing_changes(self):
		self.assertEqual(keys(TWINS), keys(TWINS))

	def test_twins_survive_a_comment(self):
		commented = TWINS.replace("\tx = 1\n", "\t# set up\n\tx = 1\n")
		self.assertEqual(
			keys(commented, mutators.MUTATOR_BOOLEAN_OP), keys(TWINS, mutators.MUTATOR_BOOLEAN_OP)
		)

	def test_three_identical_sites_are_all_addressable(self):
		source = "def f(a, b):\n" + "\tif a or b:\n\t\tpass\n" * 3
		found = keys(source, mutators.MUTATOR_BOOLEAN_OP)
		self.assertEqual(len(found), 3)
		self.assertEqual(len(set(found)), 3)


class TestMutantValidity(unittest.TestCase):
	"""Every site the campaign is handed must render to Python that actually parses."""

	def assert_all_mutants_parse(self, source: str, mutate_strings: bool = False):
		found = sites(source, mutate_strings=mutate_strings)
		self.assertTrue(found)
		for site in found:
			built = mutators.build_mutant(source, site.node_index, site.mutator, site.param)
			self.assertIsNotNone(built, f"{site.mutator} at line {site.line} produced no mutant")
			mutated_source, _ = built
			ast.parse(mutated_source)
			self.assertNotEqual(ast.unparse(ast.parse(source)), mutated_source)

	def test_synthetic_module(self):
		self.assert_all_mutants_parse(RICH, mutate_strings=True)

	def test_a_real_target_file(self):
		"""Smoke test against shipped code: synthetic sources do not cover every node shape."""
		target = Path(mutators.__file__).resolve().parents[3] / "gameplan" / "mixins" / "reactions.py"
		self.assert_all_mutants_parse(target.read_text())

	def test_mutated_segment_is_what_gets_written(self):
		for site in sites(RICH, mutate_strings=True):
			mutated_source, segment = mutators.build_mutant(RICH, site.node_index, site.mutator, site.param)
			self.assertEqual(segment, site.mutated_segment)
			self.assertIn(site.mutated_segment, normalised(mutated_source))

	def test_original_segment_is_the_unmutated_code(self):
		baseline = normalised(ast.unparse(ast.parse(RICH)))
		for site in sites(RICH, mutate_strings=True):
			self.assertIn(site.original_segment, baseline)

	def test_line_and_column_point_at_the_site(self):
		found = sites("def g(x):\n\tif x > 1:\n\t\treturn 1\n", mutators.MUTATOR_COMPARISON)
		self.assertEqual([(s.line, s.col) for s in found], [(2, 4)])


class TestSiteSelection(unittest.TestCase):
	"""What is and is not a mutation site."""

	def test_strings_are_not_mutated_by_default(self):
		found = sites(RICH)
		self.assertEqual([s for s in found if s.mutator == mutators.MUTATOR_STRING_CONST], [])

	def test_mutate_strings_enables_string_constants(self):
		found = sites(RICH, mutators.MUTATOR_STRING_CONST, mutate_strings=True)
		self.assertTrue(found)
		self.assertIn("fallback", [s.original_segment.strip("'\"") for s in found])

	def test_docstrings_are_never_mutated(self):
		found = sites(RICH, mutators.MUTATOR_STRING_CONST, mutate_strings=True)
		originals = {s.original_segment.strip("'\"") for s in found}
		self.assertNotIn("Module docstring - never mutated.", originals)
		self.assertNotIn("Class docstring.", originals)
		self.assertNotIn("Method docstring.", originals)

	def test_imports_and_dunder_all_are_never_mutated(self):
		found = sites(RICH, mutate_strings=True)
		self.assertNotIn("run", [s.original_segment.strip("'\"") for s in found])
		self.assertEqual([s for s in found if s.line in (3, 5)], [])

	def test_type_checking_blocks_are_never_mutated(self):
		source = (
			"from typing import TYPE_CHECKING\n\n"
			"if TYPE_CHECKING:\n\tLIMIT = 5\n\n"
			"def g(x):\n\treturn x > 5\n"
		)
		self.assertEqual([s.line for s in sites(source, mutators.MUTATOR_NUMBER_INCREMENT)], [7])

	def test_bare_return_has_no_return_none_mutant(self):
		source = "def g(x):\n\tif x:\n\t\treturn\n\treturn None\n"
		self.assertEqual(sites(source, mutators.MUTATOR_RETURN_NONE), [])


class TestNumberMutants(unittest.TestCase):
	"""The number mutators must not spend a bench run on a mutant they already produced."""

	def numeric_segments(self, source: str) -> list[str]:
		return sorted(s.mutated_segment for s in sites(source) if s.mutator.startswith("number-"))

	def test_zero_yields_one_mutant_not_two(self):
		"""increment(0) and zero(0) both render `1`, so the second is a duplicate, not a site."""
		self.assertEqual(self.numeric_segments("def g():\n\treturn f(0)\n"), ["1"])

	def test_nonzero_yields_both_mutants(self):
		self.assertEqual(self.numeric_segments("def g():\n\treturn f(7)\n"), ["0", "8"])

	def test_zeroing_keeps_the_literal_type(self):
		self.assertEqual(self.numeric_segments("def g():\n\treturn f(0.0)\n"), ["1.0"])

	def test_booleans_are_flipped_not_incremented(self):
		found = sites("def g():\n\treturn f(True)\n")
		constants = [(s.mutator, s.mutated_segment) for s in found if s.original_segment == "True"]
		self.assertEqual(constants, [(mutators.MUTATOR_BOOLEAN_CONST, "False")])


if __name__ == "__main__":
	unittest.main()
