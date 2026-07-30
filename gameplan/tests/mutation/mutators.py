"""AST mutation site discovery and application.

A mutant is produced by re-parsing the pristine source, mutating exactly one site,
and unparsing the whole module. Re-parsing per mutant keeps every mutant independent
and means a site never has to be "undone" in a shared tree.

Sites are addressed by their index in ``list(ast.walk(tree))``. That ordering is a
pure function of the tree shape, so it is stable for a given source text, and the
source text is guaranteed pristine at address time because the harness restores the
file after every run. It is NOT stable across edits to the file: anything re-applying
a journalled mutant later must re-derive the site from the current source via its
``key`` (see ``campaign._verify_one``), never trust a stored ``node_index``.

Every text that feeds a mutant key comes from ``ast.unparse``, never from the raw
source. Unparsing normalises formatting and drops comments, so a reformat or a comment
edit cannot invalidate a journalled verdict; only a real change to the code the key
describes can. See ``mutant_key`` for the full stability envelope.
"""

from __future__ import annotations

import ast
import copy
import hashlib
from collections import Counter
from dataclasses import dataclass, field

# Comparison operators are flipped to their adjacent/negated form. Boundary flips
# (< <-> <=) catch off-by-one bugs; negation flips catch inverted guards.
COMPARE_FLIP: dict[type[ast.cmpop], type[ast.cmpop]] = {
	ast.Lt: ast.LtE,
	ast.LtE: ast.Lt,
	ast.Gt: ast.GtE,
	ast.GtE: ast.Gt,
	ast.Eq: ast.NotEq,
	ast.NotEq: ast.Eq,
	ast.Is: ast.IsNot,
	ast.IsNot: ast.Is,
	ast.In: ast.NotIn,
	ast.NotIn: ast.In,
}

ARITH_FLIP: dict[type[ast.operator], type[ast.operator]] = {
	ast.Add: ast.Sub,
	ast.Sub: ast.Add,
	ast.Mult: ast.Div,
	ast.Div: ast.Mult,
}

MUTATOR_COMPARISON = "comparison"
MUTATOR_BOOLEAN_OP = "boolean-op"
MUTATOR_REMOVE_NOT = "remove-not"
MUTATOR_BOOLEAN_CONST = "boolean-const"
MUTATOR_NUMBER_INCREMENT = "number-increment"
MUTATOR_NUMBER_ZERO = "number-zero"
MUTATOR_ARITHMETIC = "arithmetic"
MUTATOR_RETURN_NONE = "return-none"
MUTATOR_STRING_CONST = "string-const"


@dataclass
class MutationSite:
	"""One candidate mutation, addressable independently of line numbers."""

	rel_path: str
	node_index: int
	mutator: str
	param: int | None
	line: int
	col: int
	function: str
	original_segment: str
	mutated_segment: str
	key: str = field(default="")

	def to_dict(self) -> dict:
		return {
			"file": self.rel_path,
			"line": self.line,
			"col": self.col,
			"function": self.function,
			"mutator": self.mutator,
			"original_segment": self.original_segment,
			"mutated_segment": self.mutated_segment,
			"node_index": self.node_index,
			"param": self.param,
			"key": self.key,
		}


def _parent_map(tree: ast.AST) -> dict[int, tuple[ast.AST, str, int | None]]:
	mapping: dict[int, tuple[ast.AST, str, int | None]] = {}
	for parent in ast.walk(tree):
		for field_name, value in ast.iter_fields(parent):
			if isinstance(value, list):
				for index, item in enumerate(value):
					if isinstance(item, ast.AST):
						mapping[id(item)] = (parent, field_name, index)
			elif isinstance(value, ast.AST):
				mapping[id(value)] = (parent, field_name, None)
	return mapping


def _is_type_checking_test(test: ast.expr) -> bool:
	if isinstance(test, ast.Name):
		return test.id == "TYPE_CHECKING"
	if isinstance(test, ast.Attribute):
		return test.attr == "TYPE_CHECKING"
	return False


def _docstring_constant(node: ast.AST) -> ast.Constant | None:
	body = getattr(node, "body", None)
	if not body or not isinstance(body, list):
		return None
	first = body[0]
	if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
		if isinstance(first.value.value, str):
			return first.value
	return None


def _targets_dunder_all(node: ast.AST) -> bool:
	targets: list[ast.expr] = []
	if isinstance(node, ast.Assign):
		targets = list(node.targets)
	elif isinstance(node, ast.AugAssign | ast.AnnAssign):
		targets = [node.target]
	return any(isinstance(t, ast.Name) and t.id == "__all__" for t in targets)


def _excluded_ids(tree: ast.AST) -> set[int]:
	"""Node ids that must never be mutated (imports, docstrings, __all__, TYPE_CHECKING)."""
	excluded: set[int] = set()

	def mark(subtree: ast.AST) -> None:
		for node in ast.walk(subtree):
			excluded.add(id(node))

	for node in ast.walk(tree):
		if isinstance(node, ast.Import | ast.ImportFrom):
			mark(node)
		elif isinstance(node, ast.If) and _is_type_checking_test(node.test):
			for stmt in node.body:
				mark(stmt)
		elif isinstance(node, ast.Assign | ast.AugAssign | ast.AnnAssign) and _targets_dunder_all(node):
			mark(node)
		if isinstance(node, ast.Module | ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
			doc = _docstring_constant(node)
			if doc is not None:
				excluded.add(id(doc))
	return excluded


def _scopes(tree: ast.AST) -> dict[int, tuple[str, ast.AST]]:
	"""Map every node id to its enclosing class/function scope: dotted name and node."""
	scopes: dict[int, tuple[str, ast.AST]] = {}

	def visit(node: ast.AST, name: str, owner: ast.AST) -> None:
		scopes[id(node)] = (name, owner)
		for child in ast.iter_child_nodes(node):
			child_name, child_owner = name, owner
			if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
				child_name = f"{name}.{child.name}" if name else child.name
				child_owner = child
			visit(child, child_name, child_owner)

	visit(tree, "", tree)
	return scopes


def _enclosing_statement(node: ast.AST, parents: dict[int, tuple[ast.AST, str, int | None]]) -> ast.AST:
	current = node
	while not isinstance(current, ast.stmt):
		entry = parents.get(id(current))
		if entry is None:
			return current
		current = entry[0]
	return current


def _normalise(text: str) -> str:
	return " ".join(text.split())


def _segment(node: ast.AST) -> str:
	"""Normalised source-equivalent text of one node.

	Unparsed rather than sliced out of the source: the slice would carry the file's
	comments and line breaks into the mutant key, and it would not be comparable with
	``mutated_segment``, which ``build_mutant`` produces with ``ast.unparse``.
	"""
	try:
		return _normalise(ast.unparse(node))
	except Exception:  # noqa: BLE001 - segment text is cosmetic, never fatal
		return f"<{type(node).__name__}>"


def _statement_header(node: ast.AST) -> str:
	"""The statement's own line, without the block it introduces.

	``ast.unparse`` always renders a header on one line, so the first line of a
	compound statement is exactly its header. Excluding the body is what keeps a
	mutant in an ``if``/``for``/``def`` header independent of every edit inside the
	block it governs.
	"""
	if getattr(node, "decorator_list", None):
		# Decorators unparse *above* the def line and would hide the signature, where
		# default-argument mutants live.
		node = copy.copy(node)
		node.decorator_list = []
	try:
		text = ast.unparse(node)
	except Exception:  # noqa: BLE001 - context text is cosmetic, never fatal
		return f"<{type(node).__name__}>"
	return _normalise(text.split("\n", 1)[0])


def _scope_path(node: ast.AST, parents: dict[int, tuple[ast.AST, str, int | None]], scope: ast.AST) -> str:
	"""Structural route from ``scope`` down to ``node``, e.g. ``body[3]/orelse[0]/test``.

	Unique per node and blind to comments and formatting, so it can tell two otherwise
	identical mutation sites apart. Positional, though: it is only ever used together
	with a fingerprint of the whole scope, so that a deletion or a reorder changes the
	fingerprint rather than quietly handing one site another's route.
	"""
	steps: list[str] = []
	current = node
	while current is not scope:
		entry = parents.get(id(current))
		if entry is None:
			break
		parent, field_name, index = entry
		steps.append(field_name if index is None else f"{field_name}[{index}]")
		current = parent
	return "/".join(reversed(steps))


def _digest(payload: str) -> str:
	return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def mutant_key(
	rel_path: str,
	mutator: str,
	param: int | None,
	function: str,
	original: str,
	mutated: str,
	context: str,
	discriminator: str,
) -> str:
	"""Stable identity for a mutant.

	Deliberately excludes line/column: editing a file shifts every line below the edit,
	which would make a line-based key skip brand-new mutants and re-run stale ones. Every
	component is unparsed AST text, so comments and formatting are invisible to the key.

	``context`` is the enclosing statement's header only, and ``discriminator`` comes from
	``collect_sites``: empty when nothing else in the file shares those components, and a
	scope fingerprint when something does. The envelope this buys:

	* reformatting, comment edits and edits inside an unrelated block: key unchanged.
	* The site's own code changes: key changes, and the mutant is re-run.
	* Two or more sites in one scope identical in every other component: each is pinned to
	its route through a fingerprint of that whole scope, so deleting or reordering one
	re-keys the group and every member is re-evaluated. A bare positional ordinal instead
	hands the deleted site's verdict to a survivor, which is the one failure mode a
	resumable journal must never have.

	The residual: a mutant deleted and an identical one later added to the same scope,
	with no other change to that scope, reuses the old key. Both are the same mutation of
	the same statement, so the inherited verdict is at least about the same code.
	"""
	payload = "\x00".join(
		[rel_path, mutator, str(param), function, original, mutated, context, discriminator]
	)
	return _digest(payload)


def _candidate_specs(
	tree: ast.AST, excluded: set[int], mutate_strings: bool
) -> list[tuple[int, str, int | None]]:
	"""Enumerate (node_index, mutator, param) triples without applying anything."""
	specs: list[tuple[int, str, int | None]] = []
	for index, node in enumerate(ast.walk(tree)):
		if id(node) in excluded:
			continue
		if isinstance(node, ast.Compare):
			for op_index, op in enumerate(node.ops):
				if type(op) in COMPARE_FLIP:
					specs.append((index, MUTATOR_COMPARISON, op_index))
		elif isinstance(node, ast.BoolOp):
			specs.append((index, MUTATOR_BOOLEAN_OP, None))
		elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
			specs.append((index, MUTATOR_REMOVE_NOT, None))
		elif isinstance(node, ast.BinOp) and type(node.op) in ARITH_FLIP:
			specs.append((index, MUTATOR_ARITHMETIC, None))
		elif isinstance(node, ast.Return):
			# A bare `return` or an explicit `return None` already returns None.
			if node.value is not None and not (
				isinstance(node.value, ast.Constant) and node.value.value is None
			):
				specs.append((index, MUTATOR_RETURN_NONE, None))
		elif isinstance(node, ast.Constant):
			value = node.value
			if isinstance(value, bool):
				specs.append((index, MUTATOR_BOOLEAN_CONST, None))
			elif isinstance(value, int | float) and not isinstance(value, complex):
				specs.append((index, MUTATOR_NUMBER_INCREMENT, None))
				specs.append((index, MUTATOR_NUMBER_ZERO, None))
			elif isinstance(value, str) and mutate_strings:
				specs.append((index, MUTATOR_STRING_CONST, None))
	return specs


def apply_to_tree(tree: ast.AST, node_index: int, mutator: str, param: int | None) -> ast.AST | None:
	"""Mutate ``tree`` in place at one site. Returns the node to render, or None if unapplicable."""
	nodes = list(ast.walk(tree))
	if node_index >= len(nodes):
		return None
	node = nodes[node_index]

	if mutator == MUTATOR_COMPARISON:
		if not isinstance(node, ast.Compare) or param is None or param >= len(node.ops):
			return None
		flipped = COMPARE_FLIP.get(type(node.ops[param]))
		if flipped is None:
			return None
		node.ops[param] = flipped()
		return node

	if mutator == MUTATOR_BOOLEAN_OP:
		if not isinstance(node, ast.BoolOp):
			return None
		node.op = ast.Or() if isinstance(node.op, ast.And) else ast.And()
		return node

	if mutator == MUTATOR_REMOVE_NOT:
		if not isinstance(node, ast.UnaryOp) or not isinstance(node.op, ast.Not):
			return None
		parents = _parent_map(tree)
		entry = parents.get(id(node))
		if entry is None:
			return None
		parent, field_name, list_index = entry
		if list_index is None:
			setattr(parent, field_name, node.operand)
		else:
			getattr(parent, field_name)[list_index] = node.operand
		return node.operand

	if mutator == MUTATOR_ARITHMETIC:
		if not isinstance(node, ast.BinOp):
			return None
		flipped = ARITH_FLIP.get(type(node.op))
		if flipped is None:
			return None
		node.op = flipped()
		return node

	if mutator == MUTATOR_RETURN_NONE:
		if not isinstance(node, ast.Return):
			return None
		node.value = ast.Constant(value=None)
		return node

	if mutator == MUTATOR_BOOLEAN_CONST:
		if not isinstance(node, ast.Constant) or not isinstance(node.value, bool):
			return None
		node.value = not node.value
		return node

	if mutator == MUTATOR_NUMBER_INCREMENT:
		if not isinstance(node, ast.Constant) or isinstance(node.value, bool):
			return None
		if not isinstance(node.value, int | float):
			return None
		node.value = node.value + 1
		return node

	if mutator == MUTATOR_NUMBER_ZERO:
		if not isinstance(node, ast.Constant) or isinstance(node.value, bool):
			return None
		if not isinstance(node.value, int | float):
			return None
		# Zeroing an already-zero constant is a no-op, so flip to 1 to keep a real mutant.
		# Keep the literal's type: `0.0 -> 1` would otherwise differ from the increment
		# mutant's `0.0 -> 1.0` in text while being identical in behaviour.
		node.value = type(node.value)(1) if node.value == 0 else type(node.value)(0)
		return node

	if mutator == MUTATOR_STRING_CONST:
		if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
			return None
		node.value = node.value + "XX"
		return node

	return None


def build_mutant(source: str, node_index: int, mutator: str, param: int | None) -> tuple[str, str] | None:
	"""Return ``(mutated_source, mutated_segment)`` or None if the mutant is a no-op."""
	baseline_tree = ast.parse(source)
	baseline_text = ast.unparse(baseline_tree)

	tree = ast.parse(source)
	rendered = apply_to_tree(tree, node_index, mutator, param)
	if rendered is None:
		return None
	ast.fix_missing_locations(tree)
	mutated_text = ast.unparse(tree)
	# An identical unparse means the mutation had no observable effect; running the
	# suite for it would burn a full bench invocation for nothing.
	if mutated_text == baseline_text:
		return None
	try:
		ast.parse(mutated_text)
	except SyntaxError:
		return None
	return mutated_text, " ".join(ast.unparse(rendered).split())


@dataclass
class _Draft:
	"""A discovered site, before its ambiguity with other sites has been resolved."""

	node_index: int
	mutator: str
	param: int | None
	line: int
	col: int
	function: str
	original_segment: str
	mutated_segment: str
	context: str
	scope: ast.AST
	path: str

	@property
	def ident(self) -> tuple[str, str, str, str, str]:
		"""Everything about the mutant except where in its scope it sits."""
		return (self.mutator, self.function, self.original_segment, self.mutated_segment, self.context)


def collect_sites(source: str, rel_path: str, mutate_strings: bool = False) -> list[MutationSite]:
	"""Discover every viable mutation site in ``source``."""
	tree = ast.parse(source)
	excluded = _excluded_ids(tree)
	scopes = _scopes(tree)
	parents = _parent_map(tree)
	nodes = list(ast.walk(tree))

	drafts: list[_Draft] = []
	seen_texts: set[str] = set()

	for node_index, mutator, param in _candidate_specs(tree, excluded, mutate_strings):
		built = build_mutant(source, node_index, mutator, param)
		if built is None:
			continue
		mutated_text, mutated_segment = built
		# Two mutators can land on identical code: `0 + 1` and "zero -> 1" both render
		# the same module. build_mutant only compares against the pristine baseline, so
		# it cannot see that. Without this, the duplicate burns a second full bench run
		# and counts twice in the score denominator.
		text_hash = _digest(mutated_text)
		if text_hash in seen_texts:
			continue
		seen_texts.add(text_hash)
		node = nodes[node_index]
		statement = _enclosing_statement(node, parents)
		function, scope = scopes.get(id(node), ("", tree))
		drafts.append(
			_Draft(
				node_index=node_index,
				mutator=mutator,
				param=param,
				line=getattr(node, "lineno", 0),
				col=getattr(node, "col_offset", 0),
				function=function,
				original_segment=_segment(node),
				mutated_segment=mutated_segment,
				context=_statement_header(statement),
				scope=scope,
				path=_scope_path(node, parents, scope),
			)
		)

	# A site nothing else in the file can be confused with needs no discriminator, and
	# leaving it out is what keeps its key alive across edits elsewhere in the file.
	# Sites that ARE confusable get one built from their route through the scope plus a
	# fingerprint of the whole scope: the route separates them, and the fingerprint means
	# any edit to that scope - a deletion, a reorder, a new duplicate - re-keys every
	# member of the group, so they are re-measured instead of one silently inheriting
	# another's verdict. Scope text is unparsed, so comments and layout do not disturb it.
	group_sizes = Counter(draft.ident for draft in drafts)
	scope_texts: dict[int, str] = {}

	sites: list[MutationSite] = []
	for draft in drafts:
		discriminator = ""
		if group_sizes[draft.ident] > 1:
			text = scope_texts.get(id(draft.scope))
			if text is None:
				text = scope_texts[id(draft.scope)] = _segment(draft.scope)
			discriminator = _digest(f"{draft.path}\x00{text}")[:16]
		sites.append(
			MutationSite(
				rel_path=rel_path,
				node_index=draft.node_index,
				mutator=draft.mutator,
				param=draft.param,
				line=draft.line,
				col=draft.col,
				function=draft.function,
				original_segment=draft.original_segment,
				mutated_segment=draft.mutated_segment,
				key=mutant_key(
					rel_path,
					draft.mutator,
					draft.param,
					draft.function,
					draft.original_segment,
					draft.mutated_segment,
					draft.context,
					discriminator,
				),
			)
		)
	return sites
