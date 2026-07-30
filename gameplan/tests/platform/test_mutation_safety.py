# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

"""Tests for the mutation harness's crash-safety net.

The harness edits real source files in place, so this module is the only thing standing
between an interrupted run and a corrupted working tree. Every test here pins a way the
net used to have a hole while still looking intact:

* ``install_backup`` overwrote an existing sidecar backup with whatever was on disk, so
  a crash that left a mutant behind turned that mutant into "the original" - and the
  next restore wrote it back permanently.
* the "belongs to another live process" guard in ``release()`` ran after ``restore()``
  had already stamped our own pid on the manifest, so it could never fire.
* ``CampaignLock.acquire`` created the lock file and wrote the owning pid in two steps,
  and a second process arriving in between read no owner and stole a live lock.
* ``git_is_clean`` called an untracked file clean, promising a ``git checkout --``
  escape hatch that does not exist for it.

Pure unit tests: tempfile only, no site and no bench.
"""

import fcntl
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from gameplan.tests.mutation import safety

ORIGINAL = "def answer():\n\treturn 42\n"
MUTANT = "def answer():\n\treturn 43\n"
HAND_EDIT = "def answer():\n\treturn 'edited by a human'\n"

# pid 1 always exists and is never us, so it is a stable stand-in for "another live
# process" (os.kill raises PermissionError rather than ProcessLookupError for it).
LIVE_FOREIGN_PID = 1


def dead_pid() -> int:
	"""A pid that is guaranteed to have exited and been reaped."""
	proc = subprocess.Popen([sys.executable, "-c", ""])
	proc.wait()
	return proc.pid


class MutationSafetyTestCase(unittest.TestCase):
	"""Redirects the sidecar backup directory into a scratch dir."""

	def setUp(self):
		self.tmp = tempfile.TemporaryDirectory()
		self.addCleanup(self.tmp.cleanup)
		self.root = Path(self.tmp.name)
		self.backup_dir = self.root / "backup"
		self.backup_dir.mkdir()
		patcher = mock.patch.object(safety, "BACKUP_DIR", self.backup_dir)
		patcher.start()
		self.addCleanup(patcher.stop)
		self.source = self.root / "target.py"
		self.source.write_text(ORIGINAL)

	def guard(self) -> safety.FileGuard:
		return safety.FileGuard(self.source)

	def crashed_run(self) -> safety.FileGuard:
		"""Leave a mutant on disk with its backup and manifest intact, as a SIGKILL would."""
		guard = self.guard()
		guard.install_backup()
		guard.apply(MUTANT)
		self.assertEqual(self.source.read_text(), MUTANT)
		return guard


class TestFileGuardRoundTrip(MutationSafetyTestCase):
	def test_backup_restore_round_trip(self):
		guard = self.guard()
		guard.install_backup()
		self.assertEqual(self.backup_dir_bytes(guard), ORIGINAL)

		guard.apply(MUTANT)
		self.assertEqual(self.source.read_text(), MUTANT)

		guard.restore()
		self.assertEqual(self.source.read_text(), ORIGINAL)

	def test_release_restores_and_drops_the_backup(self):
		guard = self.crashed_run()
		guard.release()
		self.assertEqual(self.source.read_text(), ORIGINAL)
		self.assertFalse(guard.backup_path.exists())
		self.assertFalse(guard.manifest_path.exists())

	def test_restore_detects_a_file_that_did_not_go_back(self):
		guard = self.guard()
		guard.install_backup()
		guard.apply(MUTANT)
		# Simulate a restore that silently fails to land: the sha check must catch it.
		with mock.patch.object(safety, "write_atomic"):
			with self.assertRaises(safety.RestoreError):
				guard.restore()

	def test_manifest_records_the_mutant_before_it_is_written(self):
		guard = self.crashed_run()
		manifest = json.loads(guard.manifest_path.read_text())
		self.assertEqual(manifest["sha256"], safety.sha256_text(ORIGINAL))
		self.assertEqual(manifest["mutated_sha256"], safety.sha256_text(MUTANT))

	def backup_dir_bytes(self, guard: safety.FileGuard) -> str:
		return guard.backup_path.read_text()


class TestInstallBackupNeverOverwrites(MutationSafetyTestCase):
	"""An existing backup is evidence of an unrestored crash, not a stale file."""

	def test_recovers_the_original_instead_of_backing_up_the_mutant(self):
		crashed = self.crashed_run()

		# A fresh run over the same file: it reads the mutant as its "original".
		guard = self.guard()
		self.assertEqual(guard.source, MUTANT)
		guard.install_backup()

		self.assertEqual(guard.backup_path, crashed.backup_path)
		self.assertEqual(guard.backup_path.read_text(), ORIGINAL, "the backup was overwritten")
		self.assertEqual(self.source.read_text(), ORIGINAL, "the mutant was not undone")
		self.assertEqual(guard.source, ORIGINAL, "the guard still thinks the mutant is pristine")
		self.assertEqual(guard.original_sha, safety.sha256_text(ORIGINAL))

	def test_recovered_guard_restores_the_original_not_the_mutant(self):
		self.crashed_run()
		guard = self.guard()
		guard.install_backup()
		guard.apply("def answer():\n\treturn 44\n")
		guard.release()
		self.assertEqual(self.source.read_text(), ORIGINAL)

	def test_adopts_a_leftover_backup_when_the_file_is_already_clean(self):
		crashed = self.crashed_run()
		crashed.restore()  # crashed after restoring but before deleting the sidecar
		before = crashed.backup_path.read_bytes()

		guard = self.guard()
		guard.install_backup()
		self.assertEqual(guard.backup_path.read_bytes(), before)
		self.assertEqual(self.source.read_text(), ORIGINAL)

	def test_refuses_when_the_target_was_edited_since_the_crash(self):
		crashed = self.crashed_run()
		self.source.write_text(HAND_EDIT)

		guard = self.guard()
		with self.assertRaises(safety.RestoreError):
			guard.install_backup()

		self.assertEqual(self.source.read_text(), HAND_EDIT, "a human edit was destroyed")
		self.assertEqual(crashed.backup_path.read_text(), ORIGINAL)

	def test_refuses_a_backup_owned_by_a_live_process(self):
		crashed = self.crashed_run()
		manifest = json.loads(crashed.manifest_path.read_text())
		manifest["pid"] = LIVE_FOREIGN_PID
		crashed.manifest_path.write_text(json.dumps(manifest))

		with self.assertRaises(safety.LockError):
			self.guard().install_backup()
		self.assertEqual(crashed.backup_path.read_text(), ORIGINAL)

	def test_refuses_a_corrupt_backup(self):
		crashed = self.crashed_run()
		crashed.backup_path.write_text("truncated")
		with self.assertRaises(safety.RestoreError):
			self.guard().install_backup()


class TestReleaseOwnershipGuard(MutationSafetyTestCase):
	"""The 'this backup belongs to somebody else' branch has to be reachable."""

	def test_does_not_delete_a_backup_owned_by_another_live_process(self):
		guard = self.crashed_run()
		manifest = json.loads(guard.manifest_path.read_text())
		manifest["pid"] = LIVE_FOREIGN_PID
		guard.manifest_path.write_text(json.dumps(manifest))

		guard.release()

		self.assertEqual(self.source.read_text(), ORIGINAL, "a mutant was left on disk")
		self.assertTrue(guard.backup_path.exists(), "another process's backup was deleted")
		self.assertTrue(guard.manifest_path.exists())
		owner = json.loads(guard.manifest_path.read_text())["pid"]
		self.assertEqual(owner, LIVE_FOREIGN_PID, "we stamped our own pid on their manifest")

	def test_restore_does_not_steal_a_foreign_manifest(self):
		guard = self.crashed_run()
		manifest = json.loads(guard.manifest_path.read_text())
		manifest["pid"] = LIVE_FOREIGN_PID
		guard.manifest_path.write_text(json.dumps(manifest))

		guard.restore()

		self.assertEqual(json.loads(guard.manifest_path.read_text())["pid"], LIVE_FOREIGN_PID)

	def test_deletes_its_own_backup_when_the_owner_is_dead(self):
		guard = self.crashed_run()
		manifest = json.loads(guard.manifest_path.read_text())
		manifest["pid"] = dead_pid()
		guard.manifest_path.write_text(json.dumps(manifest))

		guard.release()

		self.assertFalse(guard.backup_path.exists())
		self.assertFalse(guard.manifest_path.exists())


class TestCampaignLock(unittest.TestCase):
	def setUp(self):
		self.tmp = tempfile.TemporaryDirectory()
		self.addCleanup(self.tmp.cleanup)
		self.path = Path(self.tmp.name) / "nested" / "campaign.lock"

	def lock(self) -> safety.CampaignLock:
		return safety.CampaignLock(self.path)

	def test_acquire_writes_the_owner_and_release_removes_the_file(self):
		lock = self.lock()
		lock.acquire()
		self.assertTrue(self.path.exists())
		self.assertEqual(json.loads(self.path.read_text())["pid"], os.getpid())
		lock.release()
		self.assertFalse(self.path.exists())

	def test_context_manager_releases(self):
		with self.lock():
			self.assertTrue(self.path.exists())
		self.assertFalse(self.path.exists())

	def test_stale_lock_from_a_dead_pid_is_reclaimed(self):
		self.path.parent.mkdir(parents=True)
		self.path.write_text(json.dumps({"pid": dead_pid(), "started": 0}))

		lock = self.lock()
		lock.acquire()
		self.addCleanup(lock.release)
		self.assertEqual(json.loads(self.path.read_text())["pid"], os.getpid())

	def test_live_lock_is_not_stolen(self):
		self.path.parent.mkdir(parents=True)
		self.path.write_text(json.dumps({"pid": LIVE_FOREIGN_PID, "started": 0}))

		with self.assertRaises(safety.LockError):
			self.lock().acquire()
		self.assertEqual(json.loads(self.path.read_text())["pid"], LIVE_FOREIGN_PID)

	def test_half_written_lock_is_not_stolen(self):
		"""The exact state that used to exist between O_EXCL create and the pid write."""
		self.path.parent.mkdir(parents=True)
		self.path.write_text("")

		with self.assertRaises(safety.LockError):
			self.lock().acquire()
		self.assertEqual(self.path.read_text(), "")

	def test_flock_held_by_another_descriptor_is_not_stolen(self):
		"""Liveness comes from the held descriptor, not from a pid that may be recycled."""
		self.path.parent.mkdir(parents=True)
		self.path.write_text(json.dumps({"pid": dead_pid(), "started": 0}))
		fd = os.open(self.path, os.O_RDONLY)
		self.addCleanup(os.close, fd)
		fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)

		with self.assertRaises(safety.LockError):
			self.lock().acquire()

	def test_lock_file_is_never_published_without_an_owner(self):
		"""Whatever a concurrent reader sees at the lock path, it names a pid."""
		lock = self.lock()
		lock.acquire()
		self.addCleanup(lock.release)
		self.assertIsNotNone(safety.CampaignLock(self.path)._read_owner())

	def test_release_leaves_a_lock_that_is_no_longer_ours(self):
		lock = self.lock()
		lock.acquire()
		self.path.write_text(json.dumps({"pid": LIVE_FOREIGN_PID, "started": 0}))
		lock.release()
		self.assertTrue(self.path.exists())


class TestGitIsClean(unittest.TestCase):
	def setUp(self):
		self.tmp = tempfile.TemporaryDirectory()
		self.addCleanup(self.tmp.cleanup)
		self.repo = Path(self.tmp.name)
		self.git("init", "-q")
		self.git("config", "user.email", "test@example.com")
		self.git("config", "user.name", "Test")
		(self.repo / "tracked.py").write_text(ORIGINAL)
		(self.repo / "staged.py").write_text(ORIGINAL)
		(self.repo / "hidden.py").write_text(ORIGINAL)
		self.git("add", "tracked.py", "staged.py", "hidden.py")
		self.git("commit", "-qm", "seed")
		patcher = mock.patch.object(safety, "APP_ROOT", self.repo)
		patcher.start()
		self.addCleanup(patcher.stop)

	def git(self, *args: str) -> None:
		subprocess.run(["git", *args], cwd=self.repo, check=True, capture_output=True)

	def test_committed_file_is_clean(self):
		self.assertEqual(safety.git_is_clean(["tracked.py"]), (True, []))

	def test_modified_file_is_dirty(self):
		(self.repo / "tracked.py").write_text(MUTANT)
		self.assertEqual(safety.git_is_clean(["tracked.py"]), (False, ["tracked.py"]))

	def test_staged_file_is_dirty(self):
		(self.repo / "staged.py").write_text(MUTANT)
		self.git("add", "staged.py")
		self.assertEqual(safety.git_is_clean(["staged.py"]), (False, ["staged.py"]))

	def test_untracked_file_is_dirty(self):
		(self.repo / "untracked.py").write_text(ORIGINAL)
		# git diff is silent about it, but 'git checkout -- untracked.py' cannot
		# recover it, so the escape hatch the check promises does not exist.
		clean, dirty = safety.git_is_clean(["untracked.py"])
		self.assertFalse(clean)
		self.assertEqual(dirty, ["untracked.py"])

	def test_assume_unchanged_file_is_dirty(self):
		self.git("update-index", "--assume-unchanged", "hidden.py")
		(self.repo / "hidden.py").write_text(MUTANT)
		clean, dirty = safety.git_is_clean(["hidden.py"])
		self.assertFalse(clean)
		self.assertEqual(dirty, ["hidden.py"])

	def test_reports_every_dirty_path(self):
		(self.repo / "tracked.py").write_text(MUTANT)
		(self.repo / "untracked.py").write_text(ORIGINAL)
		clean, dirty = safety.git_is_clean(["tracked.py", "staged.py", "untracked.py"])
		self.assertFalse(clean)
		self.assertEqual(dirty, ["tracked.py", "untracked.py"])


if __name__ == "__main__":
	unittest.main()
