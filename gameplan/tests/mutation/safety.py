"""Crash-safe in-place source file mutation.

The harness edits files in the developer's real working tree, so every layer here
exists to make an interrupted run recoverable:

1. ``try/finally`` restores after each mutant.
2. ``atexit`` restores if an exception unwinds past the finally.
3. SIGINT/SIGTERM/SIGHUP/SIGQUIT handlers restore before the process dies. SIGHUP in
   particular matters: an hours-long campaign outlives many terminals and SSH sessions,
   and a default-disposition signal does not run ``atexit``.
4. A sidecar ``.orig`` backup on disk survives SIGKILL and power loss, which none of
   the in-process mechanisms can.
5. A sha256 comparison after every restore proves the bytes actually went back.
6. An exclusive campaign lock stops a second invocation from restoring (and deleting
   the backup of) a mutant that another process is still measuring.
"""

from __future__ import annotations

import atexit
import difflib
import fcntl
import hashlib
import json
import os
import signal
import stat
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from .config import APP_ROOT, BACKUP_DIR, LOCK_PATH


class RestoreError(RuntimeError):
	"""Raised when a source file could not be put back exactly as it was found."""


class LockError(RuntimeError):
	"""Raised when another live harness process owns the working tree."""


def sha256_bytes(data: bytes) -> str:
	return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
	return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _default_file_mode() -> int:
	umask = os.umask(0)
	os.umask(umask)
	return 0o666 & ~umask


def write_atomic(path: Path, data: bytes) -> None:
	"""Replace ``path`` with ``data`` such that a crash can never leave it truncated.

	The temp file must live in the same directory so ``os.replace`` stays an atomic
	rename on the same filesystem.

	``os.replace`` swaps the whole inode, so the target would otherwise inherit
	mkstemp's 0600 and the running user's ownership. git tracks only the exec bit, so
	that change would be invisible in ``git status`` and would survive a "restore".
	"""
	directory = path.parent
	try:
		st: os.stat_result | None = os.stat(path)
	except FileNotFoundError:
		st = None
	mode = stat.S_IMODE(st.st_mode) if st is not None else _default_file_mode()

	fd, tmp_name = tempfile.mkstemp(dir=directory, prefix=f".{path.name}.", suffix=".tmp")
	try:
		with os.fdopen(fd, "wb") as handle:
			handle.write(data)
			handle.flush()
			os.fsync(handle.fileno())
		os.chmod(tmp_name, mode)
		if st is not None and (st.st_uid != os.getuid() or st.st_gid != os.getgid()):
			try:
				os.chown(tmp_name, st.st_uid, st.st_gid)
			except OSError:
				# Not privileged enough to hand the file back to its owner; the mode is
				# still correct, and refusing to write at all would be worse.
				pass
		os.replace(tmp_name, path)
	except BaseException:
		# Never leave a stray temp file behind in the user's source tree.
		if os.path.exists(tmp_name):
			os.unlink(tmp_name)
		raise


def _read_json(path: Path) -> dict:
	"""Parse a sidecar json file. A missing or corrupt one reads as ``{}``."""
	try:
		payload = json.loads(path.read_text())
	except (OSError, ValueError):
		return {}
	return payload if isinstance(payload, dict) else {}


def pid_is_alive(pid: int | None) -> bool:
	if not pid or pid <= 0:
		return False
	try:
		os.kill(pid, 0)
	except ProcessLookupError:
		return False
	except PermissionError:
		# Exists, owned by somebody else.
		return True
	return True


class CampaignLock:
	"""Exclusive, cross-process claim on the working tree.

	Backup paths are derived from the target path alone, so two harness processes
	would share them: one would restore (and delete the sidecar of) the other's
	in-flight mutant, leaving the campaign measuring clean code and, after a later
	SIGKILL, a mutant on disk with nothing left to detect it.
	"""

	def __init__(self, path: Path = LOCK_PATH) -> None:
		self.path = path
		self._held = False
		self._fd: int | None = None

	def _read_owner(self) -> int | None:
		payload = _read_json(self.path)
		pid = payload.get("pid")
		return pid if isinstance(pid, int) else None

	def _flock_is_held(self) -> bool:
		"""True if some open file description still holds the advisory lock.

		The kernel drops an ``flock`` however the owning process dies, so this answers
		"is the owner still running?" without trusting a pid that may since have been
		recycled onto an unrelated process.
		"""
		try:
			fd = os.open(self.path, os.O_RDONLY)
		except OSError:
			return False
		try:
			try:
				fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
			except OSError:
				return True
			# We took it only to ask the question; hand it straight back.
			fcntl.flock(fd, fcntl.LOCK_UN)
			return False
		finally:
			os.close(fd)

	def _is_live(self) -> bool:
		"""Whether the existing lock file must be left alone."""
		owner = self._read_owner()
		if owner == os.getpid():
			# Our own leftover, and flock would report it held by our own descriptor.
			return False
		if self._flock_is_held():
			return True
		# A lock file we cannot parse has an unknown owner, and an unknown owner cannot
		# be proven dead. Refusing is recoverable by hand; stealing is not.
		return owner is None or pid_is_alive(owner)

	def _claim(self, payload: bytes) -> bool:
		"""Publish a fully-formed lock file at ``self.path``. False if one already exists.

		``os.link`` fails when the destination exists, so the lock becomes visible only
		once it already holds the owning pid. Creating an empty file and writing the pid
		afterwards would leave a window in which a second process reads no owner, calls
		the live lock stale, and steals it.
		"""
		fd, tmp_name = tempfile.mkstemp(dir=self.path.parent, prefix=f".{self.path.name}.", suffix=".tmp")
		try:
			with os.fdopen(fd, "wb") as handle:
				handle.write(payload)
				handle.flush()
				os.fsync(handle.fileno())
			os.chmod(tmp_name, 0o644)
			try:
				os.link(tmp_name, self.path)
			except FileExistsError:
				return False
		finally:
			os.unlink(tmp_name)
		return True

	def acquire(self) -> None:
		self.path.parent.mkdir(parents=True, exist_ok=True)
		payload = json.dumps({"pid": os.getpid(), "started": time.time()}).encode("utf-8")
		for _ in range(2):
			if not self._claim(payload):
				if self._is_live():
					owner = self._read_owner()
					raise LockError(
						f"another mutation run (pid {owner}) is using this working tree. "
						f"Wait for it, or remove {self.path} if you are sure it is dead."
					)
				# Stale lock from a crashed run: nobody holds it any more, so reclaim it.
				try:
					self.path.unlink()
				except FileNotFoundError:
					pass
				continue
			# Held for as long as this process lives, so a SIGKILL leaves a lock file
			# that the next run can prove is stale rather than merely guess about.
			# Blocking, because the only descriptor that can be contending here is
			# another process's liveness probe, which holds it for an instant.
			self._fd = os.open(self.path, os.O_RDONLY)
			fcntl.flock(self._fd, fcntl.LOCK_EX)
			self._held = True
			return
		raise LockError(f"could not acquire {self.path}")

	def release(self) -> None:
		if not self._held:
			return
		# Only drop the lock if it is still ours.
		if self._read_owner() == os.getpid():
			try:
				self.path.unlink()
			except FileNotFoundError:
				pass
		if self._fd is not None:
			os.close(self._fd)
			self._fd = None
		self._held = False

	def __enter__(self) -> CampaignLock:
		self.acquire()
		return self

	def __exit__(self, *exc: object) -> None:
		self.release()


def lock_owner() -> int | None:
	"""Pid of a live process currently holding the campaign lock, if any."""
	owner = CampaignLock()._read_owner()
	return owner if pid_is_alive(owner) else None


def _backup_slug(path: Path) -> str:
	return sha256_text(str(path.resolve()))


class FileGuard:
	"""Owns the pristine bytes of one source file and can always put them back."""

	def __init__(self, path: Path) -> None:
		self.path = path.resolve()
		self.original_bytes = self.path.read_bytes()
		self.original_sha = sha256_bytes(self.original_bytes)
		slug = _backup_slug(self.path)
		self.backup_path = BACKUP_DIR / f"{slug}.orig"
		self.manifest_path = BACKUP_DIR / f"{slug}.json"
		self._backed_up = False

	@property
	def source(self) -> str:
		return self.original_bytes.decode("utf-8")

	def _write_manifest(self, mutated_sha: str | None) -> None:
		manifest = {
			"path": str(self.path),
			"sha256": self.original_sha,
			"mutated_sha256": mutated_sha,
			"pid": os.getpid(),
		}
		write_atomic(self.manifest_path, json.dumps(manifest, indent=2).encode("utf-8"))

	def install_backup(self) -> None:
		"""Persist the pristine copy before the first mutation of this file.

		A backup already sitting at our slug is never a leftover to overwrite: the slug
		is derived from the target path alone, so it is the pristine copy an earlier run
		took of *this* file and never put back. Overwriting it with what is on disk now
		would promote that run's mutant to "the original", and every later restore would
		then faithfully write the mutant back.
		"""
		if self._backed_up:
			return
		BACKUP_DIR.mkdir(parents=True, exist_ok=True)
		if self.backup_path.exists():
			self._adopt_existing_backup()
			return
		write_atomic(self.backup_path, self.original_bytes)
		self._write_manifest(None)
		self._backed_up = True

	def _adopt_existing_backup(self) -> None:
		"""Take over an unreleased backup, undoing the crashed run's mutation first."""
		if _manifest_owned_by_other_live_process(self.manifest_path):
			raise LockError(
				f"{self.backup_path} belongs to a mutation run that is still alive "
				f"(pid {_read_json(self.manifest_path).get('pid')}). Wait for it to finish."
			)
		pristine = self.backup_path.read_bytes()
		pristine_sha = sha256_bytes(pristine)
		manifest = _read_json(self.manifest_path)
		recorded_sha = manifest.get("sha256")
		if recorded_sha and recorded_sha != pristine_sha:
			raise RestoreError(
				f"backup {self.backup_path} is itself corrupt: its sha256 {pristine_sha} does not "
				f"match the {recorded_sha} recorded in {self.manifest_path}. Resolve it by hand."
			)

		if pristine_sha != self.original_sha:
			# The bytes we read at construction are a previous run's mutant, not the
			# original. Only the mutant it recorded may be overwritten; anything else is
			# an edit made since the crash and may be the only copy in existence.
			if manifest.get("mutated_sha256") != self.original_sha:
				raise RestoreError(
					f"{self.path} matches neither the pristine backup {self.backup_path} nor the "
					f"mutant recorded in {self.manifest_path}, so it has been edited since an "
					f"earlier run crashed. Inspect it, then either copy the backup over it or "
					f"delete the backup to keep what is on disk."
				)
			write_atomic(self.path, pristine)
			current = sha256_bytes(self.path.read_bytes())
			if current != pristine_sha:
				raise RestoreError(f"failed to restore {self.path} from {self.backup_path}")
			self.original_bytes = pristine
			self.original_sha = pristine_sha
			print(
				f"[mutation] recovered {self.path} from {self.backup_path}: "
				f"a previous run left a mutant on disk.",
				file=sys.stderr,
			)

		self._backed_up = True
		self._write_manifest(None)

	def apply(self, mutated_source: str) -> None:
		data = mutated_source.encode("utf-8")
		if self._backed_up:
			# Record what we are about to put on disk *before* writing it, so a crash
			# recovery can tell "this file still holds our mutant" (safe to overwrite)
			# from "somebody has edited this file since" (must not be overwritten).
			self._write_manifest(sha256_bytes(data))
		write_atomic(self.path, data)

	def restore(self) -> None:
		"""Put the original bytes back and prove it worked."""
		write_atomic(self.path, self.original_bytes)
		current = sha256_bytes(self.path.read_bytes())
		if current != self.original_sha:
			raise RestoreError(
				f"failed to restore {self.path}: sha256 {current} != expected {self.original_sha}. "
				f"Pristine copy is at {self.backup_path}"
			)
		# Stamping our pid on a manifest another live process owns would erase the only
		# record that its backup is not ours to delete - and that record is exactly what
		# release() reads a moment later.
		if self._backed_up and not _manifest_owned_by_other_live_process(self.manifest_path):
			self._write_manifest(None)

	def release(self) -> None:
		"""Drop the on-disk backup once the file is verified clean again."""
		self.restore()
		if self._backed_up and _manifest_owned_by_other_live_process(self.manifest_path):
			# Somebody else's manifest is sitting at our slug; deleting their backup
			# would strand their mutant. Leave it and let them clean up.
			print(
				f"[mutation] WARNING: not deleting {self.backup_path}; "
				f"it belongs to another live process.",
				file=sys.stderr,
			)
			self._backed_up = False
			return
		for path in (self.backup_path, self.manifest_path):
			if path.exists():
				path.unlink()
		self._backed_up = False


def _manifest_owned_by_other_live_process(manifest_path: Path) -> bool:
	pid = _read_json(manifest_path).get("pid")
	return pid != os.getpid() and pid_is_alive(pid)


# Guards that currently have (or may have) a mutated file on disk. The signal and
# atexit handlers walk this so no exit path can leave a mutant behind.
_ACTIVE_GUARDS: list[FileGuard] = []
_HANDLERS_INSTALLED = False
_PREVIOUS_HANDLERS: dict[int, object] = {}


def register(guard: FileGuard) -> None:
	if guard not in _ACTIVE_GUARDS:
		_ACTIVE_GUARDS.append(guard)


def unregister(guard: FileGuard) -> None:
	if guard in _ACTIVE_GUARDS:
		_ACTIVE_GUARDS.remove(guard)


def restore_all() -> None:
	"""Best-effort restore-and-release of every registered guard. Never raises.

	``release`` rather than ``restore``: it restores first and only then drops the sidecar,
	so the backup is deleted exactly when it has provably done its job. Leaving the sidecar
	behind used to look like the safer choice, but the file is already back - what remains
	is a manifest describing a crash that has been fully undone, and the next run has no
	way to tell it from a real one. It classifies the target as an orphan, and if the file
	has changed since (a new commit, a fresh clone at another revision) it classifies it
	"unknown" and REFUSES TO START, which ``--yes`` cannot override. That is a permanently
	wedged campaign as the price of a backup nobody needs.

	If the restore fails, ``release`` raises before unlinking anything, so the one case
	where the sidecar is still the only copy of the original keeps it.
	"""
	for guard in list(_ACTIVE_GUARDS):
		try:
			guard.release()
		except Exception as exc:  # noqa: BLE001 - last-ditch handler, must not raise
			print(f"[mutation] CRITICAL: could not restore {guard.path}: {exc}", file=sys.stderr)
		else:
			unregister(guard)


def _signal_handler(signum: int, frame: object) -> None:
	print(f"\n[mutation] signal {signum} received - restoring source files...", file=sys.stderr)
	restore_all()
	kill_active_child()
	previous = _PREVIOUS_HANDLERS.get(signum)
	if callable(previous):
		previous(signum, frame)
	# Re-raise with the default disposition so the exit status reflects the signal.
	signal.signal(signum, signal.SIG_DFL)
	os.kill(os.getpid(), signum)


# SIGHUP (closed terminal, dropped SSH) and SIGQUIT (Ctrl-\) kill the process with
# their default disposition, which does not run atexit. A campaign is hours long, so
# both are ordinary events rather than edge cases.
_RESTORE_SIGNALS = tuple(
	getattr(signal, name) for name in ("SIGINT", "SIGTERM", "SIGHUP", "SIGQUIT") if hasattr(signal, name)
)


def install_handlers() -> None:
	"""Wire atexit + the fatal signals to the restore path. Idempotent."""
	global _HANDLERS_INSTALLED
	if _HANDLERS_INSTALLED:
		return
	atexit.register(restore_all)
	for signum in _RESTORE_SIGNALS:
		_PREVIOUS_HANDLERS[signum] = signal.getsignal(signum)
		signal.signal(signum, _signal_handler)
	_HANDLERS_INSTALLED = True


# The currently running test subprocess and the process group it was spawned into,
# tracked so a signal can tear down the whole group instead of orphaning bench
# children that hold the site's file lock.
_ACTIVE_CHILD: tuple[subprocess.Popen, int | None] | None = None


def set_active_child(proc: subprocess.Popen | None, pgid: int | None = None) -> None:
	global _ACTIVE_CHILD
	_ACTIVE_CHILD = None if proc is None else (proc, pgid)


def kill_process_group(proc: subprocess.Popen, pgid: int | None = None) -> None:
	"""SIGKILL the subprocess's entire process group.

	``bench`` forks a python child and exits, so by the time a timeout fires the direct
	child is usually already reaped: ``proc.poll()`` returns an exit status and
	``os.getpgid(proc.pid)`` raises, while the grandchildren are still alive holding the
	SQLite site lock and the inherited stdout pipe. The group id is therefore captured at
	spawn time and killed unconditionally - checking liveness first is exactly what lets
	the orphans survive.
	"""
	if pgid is None:
		try:
			pgid = os.getpgid(proc.pid)
		except (ProcessLookupError, PermissionError):
			pgid = None

	if pgid is not None:
		for attempt in range(3):
			try:
				os.killpg(pgid, signal.SIGKILL)
			except ProcessLookupError:
				break  # the whole group is gone
			except PermissionError:
				break
			if attempt < 2:
				time.sleep(0.2)

	try:
		proc.kill()
	except (ProcessLookupError, OSError):
		pass


def kill_active_child() -> None:
	if _ACTIVE_CHILD is not None:
		proc, pgid = _ACTIVE_CHILD
		kill_process_group(proc, pgid)


def find_orphaned_backups() -> list[dict]:
	"""Return manifests for backups left behind by a hard crash.

	Backups whose owning pid is still alive are *not* orphans: they belong to a
	campaign that is running right now, and restoring them would both invalidate that
	mutant's verdict and delete the only copy of the pristine file.
	"""
	if not BACKUP_DIR.exists():
		return []
	orphans = []
	for manifest_path in sorted(BACKUP_DIR.glob("*.json")):
		manifest = _read_json(manifest_path)
		if not manifest.get("path"):
			continue
		orig_path = manifest_path.with_suffix(".orig")
		if not orig_path.exists():
			continue
		if _manifest_owned_by_other_live_process(manifest_path):
			continue
		manifest["manifest_path"] = str(manifest_path)
		manifest["backup_path"] = str(orig_path)
		orphans.append(manifest)
	return orphans


def orphan_state(manifest: dict) -> str:
	"""Classify what is currently on disk at an orphan's target path.

	``clean``   - already identical to the pristine backup, nothing to do.
	``mutated`` - still holds the exact mutant we recorded, safe to overwrite.
	``missing`` - the file is gone.
	``unknown`` - neither; somebody has written to this file since the crash.
	"""
	target = Path(manifest["path"])
	try:
		current = sha256_bytes(target.read_bytes())
	except FileNotFoundError:
		return "missing"
	if current == manifest.get("sha256"):
		return "clean"
	if manifest.get("mutated_sha256") and current == manifest["mutated_sha256"]:
		return "mutated"
	return "unknown"


def orphan_diff(manifest: dict, max_lines: int = 40) -> str:
	"""Unified diff from the pristine backup to whatever is on disk right now."""
	target = Path(manifest["path"])
	try:
		current = target.read_text(encoding="utf-8", errors="replace").splitlines()
	except OSError:
		return "<target unreadable>"
	try:
		pristine = Path(manifest["backup_path"]).read_text(encoding="utf-8", errors="replace").splitlines()
	except OSError:
		return "<backup unreadable>"
	lines = list(
		difflib.unified_diff(pristine, current, fromfile="pristine backup", tofile=str(target), lineterm="")
	)
	if not lines:
		return "<no difference>"
	if len(lines) > max_lines:
		lines = lines[:max_lines] + [f"... ({len(lines) - max_lines} more diff lines)"]
	return "\n".join(lines)


def restore_orphan(manifest: dict) -> bool:
	"""Restore one orphaned backup. Returns True if the file now matches the backup.

	Refuses to overwrite a target whose current contents are neither the pristine bytes
	nor the mutant we recorded: that means the file has been edited since the crash, and
	those edits may be the only copy in existence.
	"""
	target = Path(manifest["path"])
	backup = Path(manifest["backup_path"])
	data = backup.read_bytes()
	expected = manifest.get("sha256") or sha256_bytes(data)
	if sha256_bytes(data) != expected:
		raise RestoreError(f"backup {backup} is itself corrupt (sha256 mismatch)")

	state = orphan_state(manifest)
	if state == "unknown":
		raise RestoreError(
			f"refusing to restore {target}: its current contents match neither the pristine "
			f"backup nor the mutant this harness wrote, so it has been edited since the crash. "
			f"Inspect it, then either delete {manifest['manifest_path']} and {backup} to keep "
			f"what is on disk, or copy {backup} over it yourself."
		)

	if state != "clean":
		if state != "missing":
			# Unconditional escape hatch: whatever we are about to destroy is kept.
			rescue = backup.with_suffix(".rescue")
			try:
				write_atomic(rescue, target.read_bytes())
				print(f"[mutation] saved pre-restore copy of {target} to {rescue}", file=sys.stderr)
			except OSError as exc:
				raise RestoreError(f"could not save a rescue copy of {target}: {exc}") from exc
		write_atomic(target, data)
		if sha256_bytes(target.read_bytes()) != expected:
			raise RestoreError(f"failed to restore {target} from {backup}")

	backup.unlink()
	Path(manifest["manifest_path"]).unlink()
	return True


def git_is_clean(rel_paths: list[str]) -> tuple[bool, list[str]]:
	"""Check that none of ``rel_paths`` has uncommitted (staged or unstaged) changes.

	A clean tree is the escape hatch of last resort: if the process is SIGKILLed and
	the sidecar backup is also lost, ``git checkout -- <file>`` still recovers it.

	"Clean" therefore has to mean *recoverable*, not merely "git diff is silent". A file
	git does not track, or one flagged assume-unchanged/skip-worktree, produces no diff
	at all while having no committed copy to check out - the promise in the paragraph
	above would be false for it, so it counts as dirty.
	"""
	dirty: list[str] = []
	for rel in rel_paths:
		if not _git_has_recoverable_copy(rel):
			dirty.append(rel)
			continue
		for args in (["diff", "--quiet", "--"], ["diff", "--cached", "--quiet", "--"]):
			result = subprocess.run(
				["git", *args, rel],
				cwd=APP_ROOT,
				capture_output=True,
			)
			if result.returncode != 0:
				dirty.append(rel)
				break
	return (not dirty), dirty


def _git_has_recoverable_copy(rel: str) -> bool:
	"""True if ``git checkout -- rel`` would actually restore the file's committed bytes."""
	result = subprocess.run(
		["git", "ls-files", "-v", "--error-unmatch", "--", rel],
		cwd=APP_ROOT,
		capture_output=True,
		text=True,
	)
	if result.returncode != 0:
		# Untracked, or not a git repository at all.
		return False
	# ``ls-files -v`` prefixes each path with its index tag. "H" is an ordinary cached
	# entry; lowercase means assume-unchanged and "S" means skip-worktree, both of which
	# make git ignore the working-tree copy on diff *and* on checkout.
	tag = result.stdout[:1]
	return tag == "H"
