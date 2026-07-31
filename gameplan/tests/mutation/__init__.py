"""Mutation testing harness for the Gameplan Frappe app.

Mutants are applied by rewriting the source file in place, running the mapped test
modules through ``bench run-tests``, then restoring the original bytes. In-place
rewriting is required because the bench imports the app from its fixed path, so a
copied mutants/ tree would never be the code the tests actually import.

See ``cli.py`` for the command surface and ``safety.py`` for the crash-recovery
guarantees around editing files in a live working tree.
"""

from .cli import main

__all__ = ["main"]
