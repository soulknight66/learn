"""Fail-closed local sandbox for executing untrusted validation commands.

This module is deliberately independent from the job/validation layers.  A
later integration may feed it checksum-bound artifact snapshots, but no caller
should treat an exit status alone as proof that an artifact builds or passes
meaningful tests.

The implementation uses three containment layers on Linux:

* ``unshare`` creates private user/mount/PID/network/IPC/UTS namespaces.  A
  trusted, memory-limited launcher mounts one byte-and-inode-capped tmpfs and
  copies a checksum-bound regular input tree into it through stable file
  descriptors.
* ``bubblewrap`` uses that tmpfs as its entire root.  Only ``/work``, ``/tmp``,
  and ``/dev/shm`` are writable views; all share the same cap.  The base runtime
  and checksum-bound toolchain snapshots are read-only.
* A descendant user namespace with no ID mapping gives the command a non-root
  overflow identity that does not own the host runtime; trusted setup views are
  remounted read-only.  A generated libseccomp filter denies keyring,
  namespace, mount, and other host-facing syscalls.  Bubblewrap's JSON status
  descriptor—not stderr—is the trusted bootstrap/result channel.

There is intentionally no unsandboxed fallback.  A matching exit is reported
as ``EXECUTED``, never ``PASS``: independent immutable grader evidence and a
fresh-inode publication boundary remain mandatory before job promotion.
"""

from __future__ import annotations

import argparse
import ctypes
import dataclasses
import errno
import fcntl
import functools
import hashlib
import json
import math
import os
import re
import resource
import secrets
import select
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence


_SCHEMA_VERSION = 3
_SANDBOX_POLICY = "learnfactory-bwrap-validator-v3"
_HOST_TOOL_PATH = "/usr/bin:/bin"
_APPROVED_TOOLCHAIN_PREFIX = Path("/arm/tools")
_BASE_EXECUTABLES = frozenset(
    {
        PurePosixPath("/usr/bin/prlimit"),
        PurePosixPath("/usr/bin/python3"),
        PurePosixPath("/usr/bin/sleep"),
        PurePosixPath("/usr/bin/true"),
        PurePosixPath("/bin/sleep"),
        PurePosixPath("/bin/true"),
    }
)
_CGROUP_TRUSTED_TASK_OVERHEAD = 12
_MAX_REQUEST_BYTES = 256 * 1024
_MAX_RESULT_BYTES = 256 * 1024
_MAX_ARGV_ITEMS = 256
_MAX_ARGV_BYTES = 128 * 1024
_MAX_ENV_ITEMS = 128
_MAX_ENV_BYTES = 128 * 1024
_MAX_TREE_ENTRIES = 10_000
_MAX_TREE_BYTES = 128 * 1024 * 1024
_MAX_TREE_PATH_BYTES = 2 * 1024 * 1024
_MAX_TREE_DEPTH = 64
_READ_SIZE = 64 * 1024
_ENV_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_PROTECTED_ENV_NAMES = frozenset(
    {
        "HOME",
        "LANG",
        "LC_ALL",
        "PATH",
        "PYTHONDONTWRITEBYTECODE",
        "TMPDIR",
    }
)
_SECRET_ENV_PARTS = frozenset(
    {"AUTH", "AUTHORIZATION", "CREDENTIAL", "KEY", "PASSWORD", "PASSWD", "SECRET", "TOKEN"}
)
_UNSAFE_ENV_EXACT = frozenset(
    {
        "BASH_ENV",
        "CDPATH",
        "ENV",
        "GCONV_PATH",
        "GIT_SSH_COMMAND",
        "GLIBC_TUNABLES",
        "HOSTALIASES",
        "IFS",
        "JAVA_TOOL_OPTIONS",
        "JDK_JAVA_OPTIONS",
        "LOCALDOMAIN",
        "LOCPATH",
        "MALLOC_CHECK_",
        "MALLOC_PERTURB_",
        "NODE_OPTIONS",
        "PERL5LIB",
        "PERL5OPT",
        "PERLLIB",
        "PYTHONHOME",
        "PYTHONPATH",
        "RUBYLIB",
        "RUBYOPT",
        "TZDIR",
    }
)
_UNSAFE_ENV_PREFIXES = (
    "DYLD_",
    "GIT_CONFIG",
    "LD_",
    "NIX_",
    "PYTHON",
    "SSLKEYLOG",
    "_JAVA_OPTIONS",
)
_DENIED_SYSCALLS = (
    "add_key",
    "request_key",
    "keyctl",
    "mount",
    "umount2",
    "pivot_root",
    "move_mount",
    "fsopen",
    "fsconfig",
    "fsmount",
    "open_tree",
    "mount_setattr",
    "unshare",
    "setns",
    "clone3",
    "bpf",
    "perf_event_open",
    "ptrace",
    "kexec_load",
    "kexec_file_load",
    "reboot",
    "swapon",
    "swapoff",
    "init_module",
    "finit_module",
    "delete_module",
    # Anonymous in-memory files and SysV shared memory are charged by the
    # mandatory cgroup as well, but denying them removes two historically
    # useful ways to evade path-based writable accounting.
    "memfd_create",
    "shmget",
    "shmat",
    "shmdt",
    "shmctl",
)
_CLONE_NAMESPACE_FLAGS = (
    0x00000080,  # CLONE_NEWTIME
    0x00020000,  # CLONE_NEWNS
    0x02000000,  # CLONE_NEWCGROUP
    0x04000000,  # CLONE_NEWUTS
    0x08000000,  # CLONE_NEWIPC
    0x10000000,  # CLONE_NEWUSER
    0x20000000,  # CLONE_NEWPID
    0x40000000,  # CLONE_NEWNET
)
# Only local Unix sockets and TCP/IP sockets inside the empty network
# namespace are permitted.  All currently assigned families below AF_INET6
# are denied explicitly and future/high-numbered families (including VSOCK)
# are denied with one greater-than comparison.
_DENIED_LOW_SOCKET_FAMILIES = (0, 3, 4, 5, 6, 7, 8, 9)
_COMMAND_SUPERVISOR_SOURCE = r'''# Trusted immutable sandbox command supervisor.
import ctypes
import json
import os
import signal
import sys

def close_untrusted_fds(keep):
    for name in os.listdir('/proc/self/fd'):
        try:
            descriptor = int(name)
        except ValueError:
            continue
        if descriptor >= 3 and descriptor not in keep:
            try:
                os.close(descriptor)
            except OSError:
                pass

def main():
    if len(sys.argv) < 3:
        return 125
    report_fd = int(sys.argv[1])
    if report_fd < 3:
        return 125
    # Same-UID children must not inspect the supervisor's memory or report FD.
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(4, 0, 0, 0, 0) != 0:  # PR_SET_DUMPABLE
        return 125
    close_untrusted_fds({report_fd})
    child = os.fork()
    if child == 0:
        os.close(report_fd)
        libc.prctl(1, signal.SIGKILL, 0, 0, 0)  # PR_SET_PDEATHSIG
        os.execve(sys.argv[2], sys.argv[2:], os.environ)
    _, status = os.waitpid(child, 0)
    if os.WIFEXITED(status):
        report = {'kind': 'exit', 'exit_code': os.WEXITSTATUS(status)}
        wrapper_exit = report['exit_code']
    elif os.WIFSIGNALED(status):
        report = {'kind': 'signal', 'signal': os.WTERMSIG(status)}
        wrapper_exit = 128 + report['signal']
    else:
        report = {'kind': 'invalid'}
        wrapper_exit = 125
    encoded = json.dumps(report, sort_keys=True, separators=(',', ':')).encode('ascii')
    if os.write(report_fd, encoded) != len(encoded):
        return 125
    os.close(report_fd)
    return wrapper_exit

if __name__ == '__main__':
    sys.exit(main())
'''
_BROAD_OR_PROTECTED_TOOLCHAIN_ROOTS = frozenset(
    {
        Path("/"),
        Path("/arm"),
        Path("/arm/tools"),
        Path("/arm/ref"),
        Path("/arm/ip"),
        Path("/arm/projectscratch"),
        Path("/etc"),
        Path("/home"),
        Path("/projects"),
        Path("/tmp"),
        Path("/usr"),
        Path("/var"),
    }
)


class SandboxContractError(ValueError):
    """The caller supplied a malformed or unsafe sandbox request."""


@dataclasses.dataclass(frozen=True)
class SandboxLimits:
    """Finite resource ceilings for one command.

    ``address_space_bytes`` and ``cpu_seconds`` are per process.  The trusted
    PID-namespace launcher also monitors aggregate RSS/CPU and task count.
    ``writable_bytes`` is a kernel-enforced tmpfs size rather than a post-hoc
    filesystem measurement.
    """

    wall_seconds: float = 30.0
    output_bytes: int = 4 * 1024 * 1024
    retained_output_bytes: int = 256 * 1024
    writable_bytes: int = 256 * 1024 * 1024
    writable_inodes: int = 20_000
    input_bytes: int = 128 * 1024 * 1024
    input_entries: int = 10_000
    input_path_bytes: int = 2 * 1024 * 1024
    input_depth: int = 64
    file_bytes: int = 64 * 1024 * 1024
    open_files: int = 256
    cpu_seconds: int = 20
    address_space_bytes: int = 256 * 1024 * 1024
    aggregate_memory_bytes: int = 512 * 1024 * 1024
    launcher_memory_bytes: int = 256 * 1024 * 1024
    max_tasks: int = 16

    def validated(self) -> "SandboxLimits":
        if (
            isinstance(self.wall_seconds, bool)
            or not isinstance(self.wall_seconds, (int, float))
            or not math.isfinite(float(self.wall_seconds))
            or self.wall_seconds <= 0
            or self.wall_seconds > 3600
        ):
            raise SandboxContractError("wall_seconds must be finite and from 0 through 3600")
        integer_fields = (
            "output_bytes",
            "retained_output_bytes",
            "writable_bytes",
            "writable_inodes",
            "input_bytes",
            "input_entries",
            "input_path_bytes",
            "input_depth",
            "file_bytes",
            "open_files",
            "cpu_seconds",
            "address_space_bytes",
            "aggregate_memory_bytes",
            "launcher_memory_bytes",
            "max_tasks",
        )
        for name in integer_fields:
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise SandboxContractError(f"{name} must be a positive integer")
        if self.retained_output_bytes > self.output_bytes:
            raise SandboxContractError("retained_output_bytes cannot exceed output_bytes")
        if self.output_bytes > 256 * 1024 * 1024:
            raise SandboxContractError("output_bytes cannot exceed 256 MiB")
        if self.writable_bytes > 2 * 1024 * 1024 * 1024:
            raise SandboxContractError("writable_bytes cannot exceed 2 GiB")
        if self.input_bytes > self.writable_bytes:
            raise SandboxContractError("input_bytes cannot exceed writable_bytes")
        if self.file_bytes > self.writable_bytes:
            raise SandboxContractError("file_bytes cannot exceed writable_bytes")
        if self.open_files > 4096:
            raise SandboxContractError("open_files cannot exceed 4096")
        if self.max_tasks > 128:
            raise SandboxContractError("max_tasks cannot exceed 128")
        if self.address_space_bytes < 32 * 1024 * 1024:
            raise SandboxContractError("address_space_bytes must be at least 32 MiB")
        if self.aggregate_memory_bytes > self.address_space_bytes * self.max_tasks:
            raise SandboxContractError(
                "aggregate_memory_bytes cannot exceed address_space_bytes * max_tasks"
            )
        if self.launcher_memory_bytes < self.address_space_bytes:
            raise SandboxContractError(
                "launcher_memory_bytes cannot be lower than address_space_bytes"
            )
        if self.writable_inodes > 100_000:
            raise SandboxContractError("writable_inodes cannot exceed 100000")
        if self.input_entries > min(_MAX_TREE_ENTRIES, self.writable_inodes):
            raise SandboxContractError("input_entries exceeds the hard or writable inode ceiling")
        if self.input_path_bytes > _MAX_TREE_PATH_BYTES:
            raise SandboxContractError("input_path_bytes exceeds the hard ceiling")
        if self.input_depth > _MAX_TREE_DEPTH:
            raise SandboxContractError("input_depth exceeds the hard ceiling")
        if self.launcher_memory_bytes < 64 * 1024 * 1024:
            raise SandboxContractError("launcher_memory_bytes must be at least 64 MiB")
        if self.launcher_memory_bytes > 4 * 1024 * 1024 * 1024:
            raise SandboxContractError("launcher_memory_bytes cannot exceed 4 GiB")
        return self

    def as_dict(self) -> dict[str, int | float]:
        return dataclasses.asdict(self)


@dataclasses.dataclass(frozen=True)
class ToolchainRoot:
    """A recursively verified, checksum-bound toolchain snapshot."""

    path: Path
    expected_sha256: str


@dataclasses.dataclass(frozen=True)
class SandboxRequest:
    argv: tuple[str, ...]
    input_root: Path | None = None
    expected_input_sha256: str | None = None
    cwd: str = "."
    env: Mapping[str, str] = dataclasses.field(default_factory=dict)
    toolchain_roots: tuple[ToolchainRoot, ...] = ()
    expected_exit: int = 0
    limits: SandboxLimits = dataclasses.field(default_factory=SandboxLimits)
    scratch_root: Path | None = None


@dataclasses.dataclass(frozen=True)
class SandboxResult:
    status: str
    reason: str
    exit_code: int | None
    signal: int | None
    stdout: str
    stderr: str
    evidence: dict[str, Any]

    @property
    def passed(self) -> bool:
        """Always fail closed: sandbox execution alone never authorizes promotion."""

        return self.status == "PASS"

    @property
    def execution_succeeded(self) -> bool:
        """Whether the command produced the configured exit code in containment."""

        return self.status == "EXECUTED"

    @property
    def promotion_eligible(self) -> bool:
        """An immutable independent grader is required outside this primitive."""

        return False


@dataclasses.dataclass(frozen=True)
class SandboxCapabilities:
    available: bool
    reason: str
    evidence: dict[str, Any]


@dataclasses.dataclass(frozen=True)
class _Tools:
    bwrap: Path
    unshare: Path
    setpriv: Path
    mount: Path
    systemd_run: Path

    def as_dict(self) -> dict[str, str]:
        return {field.name: str(getattr(self, field.name)) for field in dataclasses.fields(self)}


class _Capture:
    """Drain a stream while retaining bounded head/tail bytes."""

    def __init__(self, retained: int, budget: "_OutputBudget"):
        self.retained = retained
        self.budget = budget
        self.total = 0
        self._head = bytearray()
        self._tail = bytearray()
        self._stream: Any = None
        self._error: BaseException | None = None
        self._thread: threading.Thread | None = None

    def start(self, stream: Any, name: str) -> None:
        self._stream = stream

        def drain() -> None:
            try:
                while True:
                    chunk = stream.read(_READ_SIZE)
                    if not chunk:
                        break
                    self.total += len(chunk)
                    over_budget = self.budget.add(len(chunk))
                    half = self.retained // 2
                    room = half - len(self._head)
                    if room > 0:
                        self._head.extend(chunk[:room])
                        chunk = chunk[room:]
                    if chunk:
                        self._tail.extend(chunk)
                        tail_limit = self.retained - half
                        if len(self._tail) > tail_limit:
                            del self._tail[: len(self._tail) - tail_limit]
                    # Closing the read end immediately after the first
                    # over-budget chunk bounds overshoot to pipe/read buffers;
                    # the supervisor concurrently tears down the namespace.
                    if over_budget:
                        break
            except BaseException as error:  # pragma: no cover - OS pipe failure
                self._error = error
            finally:
                try:
                    stream.close()
                except OSError:
                    pass

        self._thread = threading.Thread(target=drain, name=name, daemon=True)
        self._thread.start()

    def finish(self) -> None:
        if self._thread is None:
            return
        self._thread.join(5)
        if self._thread.is_alive():
            raise RuntimeError("sandbox output capture did not terminate")
        if self._error is not None:
            raise RuntimeError(f"sandbox output capture failed: {self._error}")

    def rendered(self) -> str:
        omitted = max(0, self.total - len(self._head) - len(self._tail))
        marker = (
            f"\n[learnfactory: {omitted} output bytes omitted]\n".encode("ascii")
            if omitted
            else b""
        )
        return _redact((bytes(self._head) + marker + bytes(self._tail)).decode("utf-8", "replace"))


class _OutputBudget:
    def __init__(self, maximum: int):
        self.maximum = maximum
        self.total = 0
        self.exceeded = threading.Event()
        self._lock = threading.Lock()

    def add(self, amount: int) -> bool:
        with self._lock:
            self.total += amount
            if self.total > self.maximum:
                self.exceeded.set()
                return True
            return False


def tree_sha256(
    root: Path,
    *,
    maximum_bytes: int = _MAX_TREE_BYTES,
    maximum_entries: int = _MAX_TREE_ENTRIES,
    maximum_path_bytes: int = _MAX_TREE_PATH_BYTES,
    maximum_depth: int = _MAX_TREE_DEPTH,
) -> str:
    """Hash a regular tree through stable ``O_NOFOLLOW`` descriptors.

    Enumeration, path storage, bytes read, and recursion are all bounded before
    allocation or I/O.  Symlinks, hard links, special files, mount crossings,
    and objects replaced while being read fail closed.
    """

    return _scan_regular_tree(
        Path(root),
        destination=None,
        maximum_bytes=maximum_bytes,
        maximum_entries=maximum_entries,
        maximum_path_bytes=maximum_path_bytes,
        maximum_depth=maximum_depth,
        writable_copy=False,
    )["sha256"]


def _scan_regular_tree(
    source: Path,
    *,
    destination: Path | None,
    maximum_bytes: int,
    maximum_entries: int,
    maximum_path_bytes: int,
    maximum_depth: int,
    writable_copy: bool,
) -> dict[str, Any]:
    """Hash, and optionally copy, one stable regular tree in a single walk."""

    if not 0 < maximum_entries <= _MAX_TREE_ENTRIES:
        raise SandboxContractError("tree entry ceiling is outside the hard limit")
    if not 0 < maximum_bytes <= 2 * 1024 * 1024 * 1024:
        raise SandboxContractError("tree byte ceiling is outside the hard limit")
    if not 0 < maximum_path_bytes <= _MAX_TREE_PATH_BYTES:
        raise SandboxContractError("tree path-byte ceiling is outside the hard limit")
    if not 0 < maximum_depth <= _MAX_TREE_DEPTH:
        raise SandboxContractError("tree depth ceiling is outside the hard limit")
    directory_flags = (
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )
    expected_root = os.lstat(source)
    source_fd = os.open(source, directory_flags)
    destination_fd: int | None = None
    digest = hashlib.sha256()
    digest.update(b"learnfactory-tree-sha256-v3\0")
    counters: dict[str, Any] = {
        "entries": 0,
        "files": 0,
        "bytes": 0,
        "path_bytes": 0,
    }
    seen_files: set[tuple[int, int]] = set()
    try:
        root_snapshot = os.fstat(source_fd)
        if not stat.S_ISDIR(root_snapshot.st_mode) or not _same_snapshot(
            expected_root, root_snapshot
        ):
            raise SandboxContractError("input root changed before traversal")
        root_mount_id = _fd_mount_id(source_fd)
        digest.update(b"R")
        _hash_field(digest, (root_snapshot.st_mode & 0o7777).to_bytes(4, "big"))
        if destination is not None:
            destination_fd = os.open(destination, directory_flags)
        _scan_directory_fd(
            source_fd,
            destination_fd,
            (),
            digest,
            counters,
            seen_files,
            root_snapshot.st_dev,
            root_mount_id,
            maximum_bytes,
            maximum_entries,
            maximum_path_bytes,
            maximum_depth,
            writable_copy,
            directory_flags,
        )
        if not _same_snapshot(root_snapshot, os.fstat(source_fd)):
            raise SandboxContractError("input root changed during traversal")
    finally:
        if destination_fd is not None:
            os.close(destination_fd)
        os.close(source_fd)
    counters["sha256"] = digest.hexdigest()
    return counters


def _scan_directory_fd(
    source_fd: int,
    destination_fd: int | None,
    relative_parts: tuple[str, ...],
    digest: Any,
    counters: dict[str, Any],
    seen_files: set[tuple[int, int]],
    root_device: int,
    root_mount_id: int,
    maximum_bytes: int,
    maximum_entries: int,
    maximum_path_bytes: int,
    maximum_depth: int,
    writable_copy: bool,
    directory_flags: int,
) -> None:
    if len(relative_parts) > maximum_depth:
        raise SandboxContractError("input tree is too deep")
    names: list[str] = []
    with os.scandir(source_fd) as iterator:
        for entry in iterator:
            name = entry.name
            if name in {"", ".", ".."} or "/" in name:
                raise SandboxContractError("input tree contains an unsafe name")
            try:
                name.encode("utf-8")
            except UnicodeEncodeError as error:
                raise SandboxContractError("input tree name is not UTF-8") from error
            counters["entries"] += 1
            if counters["entries"] > maximum_entries:
                raise SandboxContractError("input tree has too many entries")
            rendered = "/".join((*relative_parts, name)).encode("utf-8")
            counters["path_bytes"] += len(rendered)
            if counters["path_bytes"] > maximum_path_bytes:
                raise SandboxContractError("input tree paths exceed the configured byte limit")
            names.append(name)
    names.sort()
    for name in names:
        relative_parts_next = (*relative_parts, name)
        relative = "/".join(relative_parts_next).encode("utf-8")
        expected = os.stat(name, dir_fd=source_fd, follow_symlinks=False)
        if expected.st_dev != root_device:
            raise SandboxContractError("input tree crosses a filesystem boundary")
        if stat.S_ISLNK(expected.st_mode):
            raise SandboxContractError("input tree contains a symbolic link")
        if stat.S_ISDIR(expected.st_mode):
            child_source = os.open(name, directory_flags, dir_fd=source_fd)
            child_destination: int | None = None
            try:
                child_snapshot = os.fstat(child_source)
                if _fd_mount_id(child_source) != root_mount_id:
                    raise SandboxContractError("input tree crosses a mount boundary")
                if not stat.S_ISDIR(child_snapshot.st_mode) or not _same_snapshot(
                    expected, child_snapshot
                ):
                    raise SandboxContractError("input directory changed during traversal")
                digest.update(b"D")
                _hash_field(digest, relative)
                _hash_field(
                    digest, (expected.st_mode & 0o7777).to_bytes(4, "big")
                )
                if destination_fd is not None:
                    mode = 0o777 if writable_copy else expected.st_mode & 0o777
                    os.mkdir(name, mode=mode, dir_fd=destination_fd)
                    child_destination = os.open(name, directory_flags, dir_fd=destination_fd)
                    os.fchmod(child_destination, mode)
                _scan_directory_fd(
                    child_source,
                    child_destination,
                    relative_parts_next,
                    digest,
                    counters,
                    seen_files,
                    root_device,
                    root_mount_id,
                    maximum_bytes,
                    maximum_entries,
                    maximum_path_bytes,
                    maximum_depth,
                    writable_copy,
                    directory_flags,
                )
                if not _same_snapshot(child_snapshot, os.fstat(child_source)):
                    raise SandboxContractError("input directory changed during traversal")
            finally:
                if child_destination is not None:
                    os.close(child_destination)
                os.close(child_source)
            continue
        if not stat.S_ISREG(expected.st_mode):
            raise SandboxContractError("input tree contains a special file")
        identity = (expected.st_dev, expected.st_ino)
        if expected.st_nlink != 1 or identity in seen_files:
            raise SandboxContractError("input tree contains a hard-linked file")
        seen_files.add(identity)
        if expected.st_size < 0 or counters["bytes"] + expected.st_size > maximum_bytes:
            raise SandboxContractError("input tree exceeds the configured byte limit")
        source_flags = (
            os.O_RDONLY
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_NONBLOCK", 0)
        )
        file_fd = os.open(name, source_flags, dir_fd=source_fd)
        output_fd: int | None = None
        try:
            file_snapshot = os.fstat(file_fd)
            if _fd_mount_id(file_fd) != root_mount_id:
                raise SandboxContractError("input tree crosses a mount boundary")
            if not stat.S_ISREG(file_snapshot.st_mode) or not _same_snapshot(
                expected, file_snapshot
            ):
                raise SandboxContractError("input file changed before traversal")
            mode = expected.st_mode & 0o777
            digest.update(b"F")
            _hash_field(digest, relative)
            _hash_field(digest, mode.to_bytes(4, "big"))
            if destination_fd is not None:
                output_fd = os.open(
                    name,
                    os.O_WRONLY
                    | os.O_CREAT
                    | os.O_EXCL
                    | getattr(os, "O_CLOEXEC", 0)
                    | getattr(os, "O_NOFOLLOW", 0),
                    0o600,
                    dir_fd=destination_fd,
                )
            file_digest = hashlib.sha256()
            copied = 0
            while True:
                chunk = os.read(file_fd, _READ_SIZE)
                if not chunk:
                    break
                copied += len(chunk)
                if counters["bytes"] + copied > maximum_bytes:
                    raise SandboxContractError("input tree exceeds the configured byte limit")
                file_digest.update(chunk)
                if output_fd is not None:
                    remaining = memoryview(chunk)
                    while remaining:
                        written = os.write(output_fd, remaining)
                        if written <= 0:
                            raise OSError("short write while copying input")
                        remaining = remaining[written:]
            if copied != file_snapshot.st_size or not _same_snapshot(
                file_snapshot, os.fstat(file_fd)
            ):
                raise SandboxContractError("input file changed during traversal")
            counters["bytes"] += copied
            counters["files"] += 1
            _hash_field(digest, file_digest.digest())
            if output_fd is not None:
                copied_mode = 0o777 if mode & 0o111 else 0o666 if writable_copy else mode
                if not writable_copy:
                    copied_mode = mode
                os.fchmod(output_fd, copied_mode)
                os.fsync(output_fd)
        finally:
            if output_fd is not None:
                os.close(output_fd)
            os.close(file_fd)


def run_sandbox(
    request: SandboxRequest,
    *,
    cancel_event: threading.Event | None = None,
) -> SandboxResult:
    """Run one exact argv in the isolated validator environment.

    Missing kernel/tool support returns ``BLOCKED``.  Malformed requests raise
    :class:`SandboxContractError`.  There is no host-execution fallback.
    """

    normalized = _normalize_request(request)
    try:
        tools = _discover_tools()
    except RuntimeError as error:
        return _blocked_result("prerequisite-unavailable", str(error), normalized)

    scratch = normalized["scratch_root"]
    try:
        scratch_metadata = os.lstat(scratch)
        if stat.S_ISLNK(scratch_metadata.st_mode) or not stat.S_ISDIR(scratch_metadata.st_mode):
            raise OSError("scratch root is not a real directory")
    except OSError as error:
        return _blocked_result("scratch-unavailable", str(error), normalized)

    owned_root: Path | None = None
    process: subprocess.Popen[bytes] | None = None
    report_read: int | None = None
    report_write: int | None = None
    request_fd: int | None = None
    started = time.monotonic()
    budget = _OutputBudget(normalized["limits"].output_bytes)
    stdout_capture = _Capture(normalized["limits"].retained_output_bytes, budget)
    stderr_capture = _Capture(normalized["limits"].retained_output_bytes, budget)
    interruption: str | None = None
    launcher_report: dict[str, Any] | None = None
    cleanup_error: str | None = None
    try:
        owned_root = Path(tempfile.mkdtemp(prefix="learnfactory-validator-", dir=scratch))
        os.chmod(owned_root, 0o700)
        mountpoint = owned_root / "sandbox-tmpfs"
        mountpoint.mkdir(mode=0o700)
        report_read, report_write = os.pipe()
        scope_unit = (
            f"learnfactory-validator-{os.getpid()}-{secrets.token_hex(8)}.scope"
        )
        payload = {
            "schema_version": _SCHEMA_VERSION,
            "policy": _SANDBOX_POLICY,
            "mountpoint": str(mountpoint),
            "argv": list(normalized["argv"]),
            "cwd": normalized["cwd"],
            "env": normalized["env"],
            "fixed_path": normalized["fixed_path"],
            "input_root": str(normalized["input_root"]) if normalized["input_root"] else None,
            "expected_input_sha256": normalized["expected_input_sha256"],
            "toolchain_roots": list(normalized["toolchain_roots"]),
            "expected_exit": normalized["expected_exit"],
            "limits": normalized["limits"].as_dict(),
            "host_uid_tasks": _count_uid_tasks(os.getuid()),
            "tools": tools.as_dict(),
            "resource_scope_unit": scope_unit,
        }
        request_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        if len(request_bytes) > _MAX_REQUEST_BYTES:
            raise SandboxContractError("serialized sandbox request is too large")
        request_fd = _sealed_memfd("learnfactory-validator-request", request_bytes)
        launcher_argv = [
            str(tools.setpriv),
            "--pdeathsig",
            "SIGKILL",
            "--",
            str(tools.unshare),
            "--map-root-user",
            "--mount",
            "--net",
            "--ipc",
            "--uts",
            "--pid",
            "--fork",
            "--kill-child=SIGKILL",
            "--mount-proc",
            "--propagation",
            "private",
            sys.executable,
            "-I",
            str(Path(__file__).resolve()),
            "--launcher",
            "--result-fd",
            str(report_write),
            "--request-fd",
            str(request_fd),
        ]
        # The launcher and every descendant must enter a kernel-enforced
        # memory/pids cgroup before any untrusted input is copied or executed.
        # systemd-run --scope execs the command in the new scope and fails
        # rather than running it without the requested properties.
        launcher_argv = [
            str(tools.systemd_run),
            "--user",
            "--scope",
            "--quiet",
            "--collect",
            "--unit",
            scope_unit,
            "--property",
            f"MemoryMax={normalized['limits'].aggregate_memory_bytes}",
            "--property",
            "MemorySwapMax=0",
            "--property",
            f"TasksMax={normalized['limits'].max_tasks + _CGROUP_TRUSTED_TASK_OVERHEAD}",
            "--",
            *launcher_argv,
        ]

        def apply_launcher_limits() -> None:
            launcher_memory = normalized["limits"].launcher_memory_bytes
            resource.setrlimit(resource.RLIMIT_AS, (launcher_memory, launcher_memory))
            resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
            os.umask(0o077)

        process = subprocess.Popen(
            launcher_argv,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=_resource_controller_environment(),
            close_fds=True,
            pass_fds=(report_write, request_fd),
            start_new_session=True,
            preexec_fn=apply_launcher_limits,
        )
        os.close(report_write)
        report_write = None
        os.close(request_fd)
        request_fd = None
        assert process.stdout is not None
        assert process.stderr is not None
        stdout_capture.start(process.stdout, "sandbox-stdout")
        stderr_capture.start(process.stderr, "sandbox-stderr")
        deadline = started + normalized["limits"].wall_seconds
        while process.poll() is None:
            if cancel_event is not None and cancel_event.wait(0.02):
                interruption = "cancelled"
                break
            if budget.exceeded.is_set():
                interruption = "output-limit"
                break
            if time.monotonic() >= deadline:
                interruption = "wall-time-limit"
                break
            time.sleep(0.01)
        if interruption is not None:
            _terminate_process_group(process)
        else:
            process.wait()
        stdout_capture.finish()
        stderr_capture.finish()
        if report_read is not None:
            launcher_report = _read_launcher_report(report_read)
            os.close(report_read)
            report_read = None
    except SandboxContractError:
        raise
    except (OSError, RuntimeError, ValueError) as error:
        interruption = interruption or "launcher-error"
        if process is not None:
            _terminate_process_group(process)
        try:
            stdout_capture.finish()
            stderr_capture.finish()
        except RuntimeError:
            pass
        launcher_report = {"status": "BLOCKED", "reason": _redact(str(error))}
    finally:
        if report_write is not None:
            os.close(report_write)
        if request_fd is not None:
            os.close(request_fd)
        if report_read is not None:
            os.close(report_read)
        if owned_root is not None and owned_root.exists():
            try:
                shutil.rmtree(owned_root)
            except OSError as error:
                cleanup_error = _redact(str(error))

    duration = time.monotonic() - started
    base_evidence: dict[str, Any] = {
        "schema_version": _SCHEMA_VERSION,
        "policy": _SANDBOX_POLICY,
        "argv_sha256": _sequence_sha256(normalized["argv"]),
        "argv_count": len(normalized["argv"]),
        "cwd": normalized["cwd"],
        "env_names": sorted(normalized["env"]),
        "env_values_recorded": False,
        "fixed_environment": {
            "HOME": "/tmp",
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "PATH": normalized["fixed_path"],
            "PYTHONDONTWRITEBYTECODE": "1",
            "TMPDIR": "/tmp",
        },
        "toolchain_roots": [
            {"path": item["path"], "sha256": item["sha256"]}
            for item in normalized["toolchain_roots"]
        ],
        "base_runtime_policy": "explicit-files-and-python-stdlib",
        "resource_controller": "systemd-user-scope",
        "network": "unshared",
        "unsafe_fallback_used": False,
        "promotion_eligible": False,
        "external_grader_required": True,
        "input_root_exposed_to_command": False,
        "expected_input_sha256": normalized["expected_input_sha256"],
        "limits": normalized["limits"].as_dict(),
        "duration_seconds": duration,
        "stdout_total_bytes": stdout_capture.total,
        "stderr_total_bytes": stderr_capture.total,
        "combined_output_bytes": budget.total,
        "cleanup_succeeded": cleanup_error is None,
        "launcher": launcher_report,
    }
    if cleanup_error is not None:
        base_evidence["cleanup_error"] = cleanup_error
        return SandboxResult(
            "ERROR",
            "cleanup-failed",
            None,
            None,
            stdout_capture.rendered(),
            stderr_capture.rendered(),
            base_evidence,
        )
    if interruption in {"cancelled", "output-limit", "wall-time-limit"}:
        return SandboxResult(
            "CANCELLED" if interruption == "cancelled" else "LIMIT",
            interruption,
            None,
            None,
            stdout_capture.rendered(),
            stderr_capture.rendered(),
            base_evidence,
        )
    if launcher_report is None:
        return SandboxResult(
            "BLOCKED",
            "launcher-produced-no-evidence",
            None,
            None,
            stdout_capture.rendered(),
            stderr_capture.rendered(),
            base_evidence,
        )
    report_status = str(launcher_report.get("status", "ERROR"))
    reason = str(launcher_report.get("reason", "launcher-error"))
    exit_code = launcher_report.get("exit_code")
    terminating_signal = launcher_report.get("signal")
    rendered_stderr = stderr_capture.rendered()
    if report_status == "BLOCKED":
        status = "BLOCKED"
    elif report_status == "LIMIT":
        status = "LIMIT"
    elif report_status == "PASS":
        status = "ERROR"
        reason = "invalid-promoting-launcher-status"
    elif report_status == "EXECUTED":
        status = "EXECUTED"
    elif report_status == "FAIL":
        status = "FAIL"
    else:
        status = "ERROR"
    return SandboxResult(
        status,
        reason,
        int(exit_code) if isinstance(exit_code, int) else None,
        int(terminating_signal) if isinstance(terminating_signal, int) else None,
        stdout_capture.rendered(),
        rendered_stderr,
        base_evidence,
    )


def probe_capabilities(*, scratch_root: Path | None = None) -> SandboxCapabilities:
    """Exercise the complete containment stack with a harmless command."""

    request = SandboxRequest(
        argv=("/usr/bin/true",),
        expected_input_sha256=_empty_tree_digest(),
        scratch_root=scratch_root,
    )
    result = run_sandbox(request)
    return SandboxCapabilities(result.execution_succeeded, result.reason, result.evidence)


def _normalize_request(request: SandboxRequest) -> dict[str, Any]:
    if not isinstance(request, SandboxRequest):
        raise SandboxContractError("request must be SandboxRequest")
    limits = request.limits.validated()
    if not isinstance(request.argv, tuple) or not request.argv:
        raise SandboxContractError("argv must be a nonempty tuple")
    if len(request.argv) > _MAX_ARGV_ITEMS or any(
        not isinstance(value, str) for value in request.argv
    ):
        raise SandboxContractError("argv contains too many or non-text values")
    if any(not value or "\0" in value for value in request.argv):
        raise SandboxContractError("argv values must be nonempty and contain no NUL")
    if sum(len(value.encode("utf-8")) for value in request.argv) > _MAX_ARGV_BYTES:
        raise SandboxContractError("argv is too large")
    if any(_contains_secret_material(value) for value in request.argv):
        raise SandboxContractError("argv appears to contain credential material")
    executable = PurePosixPath(request.argv[0])
    if not executable.is_absolute() or ".." in executable.parts:
        raise SandboxContractError("argv[0] must be an absolute sandbox path")

    cwd = request.cwd
    if not isinstance(cwd, str) or "\0" in cwd:
        raise SandboxContractError("cwd must be safe text")
    if cwd != ".":
        relative_cwd = PurePosixPath(cwd)
        if relative_cwd.is_absolute() or not relative_cwd.parts or any(
            part in {"", ".", ".."} for part in relative_cwd.parts
        ):
            raise SandboxContractError("cwd must be relative to /work")

    if isinstance(request.env, (str, bytes)) or not isinstance(request.env, Mapping):
        raise SandboxContractError("env must be a mapping")
    if len(request.env) > _MAX_ENV_ITEMS:
        raise SandboxContractError("env has too many entries")
    env: dict[str, str] = {}
    env_bytes = 0
    for name, value in request.env.items():
        if not isinstance(name, str) or not isinstance(value, str):
            raise SandboxContractError("env keys and values must be text")
        if not _ENV_NAME.fullmatch(name) or name in _PROTECTED_ENV_NAMES:
            raise SandboxContractError(f"env name is invalid or reserved: {name!r}")
        upper_name = name.upper()
        compact_name = re.sub(r"[^A-Z0-9]", "", upper_name)
        parts = frozenset(part for part in re.split(r"[^A-Z0-9]+", upper_name) if part)
        if parts & _SECRET_ENV_PARTS or any(
            marker in compact_name
            for marker in ("AUTH", "CREDENTIAL", "ACCESSKEY", "APIKEY", "PASS", "SECRET", "TOKEN")
        ):
            raise SandboxContractError("credential-bearing environment names are forbidden")
        if upper_name in _UNSAFE_ENV_EXACT or upper_name.startswith(_UNSAFE_ENV_PREFIXES):
            raise SandboxContractError("loader- or runtime-control environment names are forbidden")
        if "\0" in value:
            raise SandboxContractError("env values may not contain NUL")
        if _contains_secret_material(value):
            raise SandboxContractError("environment value appears to contain credential material")
        env_bytes += len(name.encode()) + len(value.encode())
        env[name] = value
    if env_bytes > _MAX_ENV_BYTES:
        raise SandboxContractError("env is too large")

    if isinstance(request.expected_exit, bool) or not isinstance(request.expected_exit, int):
        raise SandboxContractError("expected_exit must be an integer")
    if not 0 <= request.expected_exit <= 255:
        raise SandboxContractError("expected_exit is outside the supported range")

    input_root: Path | None = None
    expected = request.expected_input_sha256
    if request.input_root is not None:
        input_root = Path(os.path.abspath(request.input_root))
        try:
            metadata = os.lstat(input_root)
        except OSError as error:
            raise SandboxContractError(f"input_root is unavailable: {error}") from error
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            raise SandboxContractError("input_root must be a real directory")
        if not isinstance(expected, str) or not _DIGEST.fullmatch(expected):
            raise SandboxContractError("input_root requires a lowercase SHA-256 tree digest")
    else:
        if expected is None:
            expected = _empty_tree_digest()
        if not isinstance(expected, str) or expected != _empty_tree_digest():
            raise SandboxContractError("an empty input must use the empty tree digest")

    roots: list[dict[str, str]] = []
    for raw_root in request.toolchain_roots:
        if not isinstance(raw_root, ToolchainRoot):
            raise SandboxContractError("toolchain roots require a checksum-bound ToolchainRoot")
        root = Path(raw_root.path)
        if not root.is_absolute():
            raise SandboxContractError("toolchain roots must be absolute")
        try:
            resolved = root.resolve(strict=True)
        except OSError as error:
            raise SandboxContractError(f"toolchain root is unavailable: {error}") from error
        if resolved in _BROAD_OR_PROTECTED_TOOLCHAIN_ROOTS:
            raise SandboxContractError("toolchain root is too broad or protected")
        try:
            relative = resolved.relative_to(_APPROVED_TOOLCHAIN_PREFIX)
        except ValueError as error:
            raise SandboxContractError("toolchain root is outside /arm/tools") from error
        if len(relative.parts) < 3:
            raise SandboxContractError("toolchain root beneath /arm/tools is too broad")
        if not resolved.is_dir():
            raise SandboxContractError("toolchain root must be a directory")
        if not isinstance(raw_root.expected_sha256, str) or not _DIGEST.fullmatch(
            raw_root.expected_sha256
        ):
            raise SandboxContractError("toolchain root requires a lowercase tree SHA-256")
        if not any(item["path"] == str(resolved) for item in roots):
            roots.append({"path": str(resolved), "sha256": raw_root.expected_sha256})

    allowed_executable = executable in _BASE_EXECUTABLES or _pure_within(
        executable, PurePosixPath("/work")
    ) or any(
        _pure_within(executable, PurePosixPath(root["path"])) for root in roots
    )
    if not allowed_executable:
        raise SandboxContractError("argv[0] is outside the sandbox executable roots")

    scratch = Path(os.path.abspath(request.scratch_root or tempfile.gettempdir()))
    path_entries = [
        f"{root['path']}/bin" for root in roots if (Path(root["path"]) / "bin").is_dir()
    ]
    path_entries.append("/usr/bin")
    return {
        "argv": request.argv,
        "cwd": cwd,
        "env": dict(sorted(env.items())),
        "toolchain_roots": tuple(roots),
        "fixed_path": ":".join(path_entries),
        "input_root": input_root,
        "expected_input_sha256": expected,
        "expected_exit": request.expected_exit,
        "limits": limits,
        "scratch_root": scratch,
    }


def _discover_tools() -> _Tools:
    discovered: dict[str, Path] = {}
    for name in ("bwrap", "unshare", "setpriv", "mount", "systemd-run"):
        raw = shutil.which(name, path=_HOST_TOOL_PATH)
        if raw is None:
            raise RuntimeError(f"required sandbox tool is unavailable: {name}")
        path = Path(raw).resolve(strict=True)
        if not path.is_file() or not os.access(path, os.X_OK):
            raise RuntimeError(f"required sandbox tool is not executable: {name}")
        discovered[name.replace("-", "_")] = path
    if not Path(sys.executable).is_file() or not os.access(sys.executable, os.X_OK):
        raise RuntimeError("Python launcher executable is unavailable")
    if not hasattr(os, "memfd_create"):
        raise RuntimeError("sealed in-memory request descriptors are unavailable")
    try:
        ctypes.CDLL("libseccomp.so.2")
    except OSError as error:
        raise RuntimeError("libseccomp is unavailable") from error
    return _Tools(**discovered)


def _blocked_result(code: str, detail: str, normalized: Mapping[str, Any]) -> SandboxResult:
    return SandboxResult(
        "BLOCKED",
        code,
        None,
        None,
        "",
        "",
        {
            "schema_version": _SCHEMA_VERSION,
            "policy": _SANDBOX_POLICY,
            "reason": _redact(detail),
            "unsafe_fallback_used": False,
            "argv_sha256": _sequence_sha256(normalized["argv"]),
            "argv_count": len(normalized["argv"]),
            "env_names": sorted(normalized["env"]),
            "env_values_recorded": False,
            "promotion_eligible": False,
            "external_grader_required": True,
            "limits": normalized["limits"].as_dict(),
        },
    )


def _fixed_host_environment() -> dict[str, str]:
    return {
        "HOME": "/tmp",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PATH": _HOST_TOOL_PATH,
        "PYTHONDONTWRITEBYTECODE": "1",
        "TMPDIR": "/tmp",
    }


def _resource_controller_environment() -> dict[str, str]:
    """Minimal trusted environment needed to reach the user's systemd bus."""

    environment = _fixed_host_environment()
    expected_runtime = f"/run/user/{os.getuid()}"
    runtime = os.environ.get("XDG_RUNTIME_DIR")
    bus = os.environ.get("DBUS_SESSION_BUS_ADDRESS")
    if runtime != expected_runtime or not Path(expected_runtime).is_dir():
        raise RuntimeError("systemd user runtime directory is unavailable or unexpected")
    expected_bus = f"unix:path={expected_runtime}/bus"
    if bus != expected_bus or not Path(expected_runtime, "bus").exists():
        raise RuntimeError("systemd user bus is unavailable or unexpected")
    environment["XDG_RUNTIME_DIR"] = runtime
    environment["DBUS_SESSION_BUS_ADDRESS"] = bus
    return environment


def _count_uid_tasks(uid: int) -> int:
    count = 0
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            status_lines = (entry / "status").read_text(
                encoding="ascii", errors="replace"
            ).splitlines()
            for line in status_lines:
                if line.startswith("Uid:") and int(line.split()[1]) == uid:
                    count += sum(1 for _ in (entry / "task").iterdir())
                    break
        except (FileNotFoundError, PermissionError, ProcessLookupError, ValueError):
            continue
    return count


def _read_launcher_report(descriptor: int) -> dict[str, Any] | None:
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = os.read(descriptor, min(_READ_SIZE, _MAX_RESULT_BYTES + 1 - total))
        if not chunk:
            break
        chunks.append(chunk)
        total += len(chunk)
        if total > _MAX_RESULT_BYTES:
            return {"status": "ERROR", "reason": "launcher-report-too-large"}
    if not chunks:
        return None
    try:
        value = json.loads(b"".join(chunks))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {"status": "ERROR", "reason": "launcher-report-malformed"}
    return (
        value
        if isinstance(value, dict)
        else {"status": "ERROR", "reason": "launcher-report-not-object"}
    )


def _terminate_process_group(process: subprocess.Popen[bytes]) -> None:
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=0.5)
        return
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired as error:  # pragma: no cover - kernel failure
        raise RuntimeError("sandbox process group could not be reaped") from error


def _launcher(result_fd: int, request_fd: int) -> int:
    """Trusted PID-namespace launcher; invoked only through :func:`run_sandbox`."""

    report: dict[str, Any] = {"status": "ERROR", "reason": "launcher-failed"}
    try:
        raw = _read_bounded_fd(request_fd, _MAX_REQUEST_BYTES)
        os.close(request_fd)
        request_fd = -1
        if len(raw) > _MAX_REQUEST_BYTES:
            raise RuntimeError("launcher request is too large")
        payload = json.loads(raw)
        if not isinstance(payload, dict) or payload.get("policy") != _SANDBOX_POLICY:
            raise RuntimeError("launcher request policy is invalid")
        # systemd-run needs the user bus only until this process enters its
        # scope.  Do not retain those host-control paths in the trusted PID 1
        # environment or pass them to any descendant.
        os.environ.clear()
        os.environ.update(_fixed_host_environment())
        mountpoint = Path(str(payload["mountpoint"]))
        if mountpoint.is_symlink() or not mountpoint.is_dir():
            raise RuntimeError("launcher mountpoint is unsafe")
        limits = SandboxLimits(**payload["limits"]).validated()
        resource_scope = _verify_kernel_resource_scope(payload, limits)
        mount_tool = str(payload["tools"]["mount"])
        mounted = subprocess.run(
            [
                mount_tool,
                "-t",
                "tmpfs",
                "-o",
                (
                    f"size={limits.writable_bytes},nr_inodes={limits.writable_inodes},"
                    "mode=0700,nosuid,nodev"
                ),
                "learnfactory-validator",
                str(mountpoint),
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=_fixed_host_environment(),
            check=False,
            timeout=10,
        )
        if mounted.returncode != 0:
            report = {
                "status": "BLOCKED",
                "reason": "tmpfs-mount-unavailable",
                "detail": _redact(mounted.stderr.decode("utf-8", "replace")),
            }
        else:
            report = _run_inner(payload, mountpoint, limits)
            report["kernel_resource_scope"] = resource_scope
    except (KeyError, TypeError, ValueError, OSError, RuntimeError, json.JSONDecodeError) as error:
        report = {
            "status": "BLOCKED",
            "reason": "launcher-prerequisite-failed",
            "detail": _redact(str(error)),
        }
    encoded = json.dumps(report, sort_keys=True, separators=(",", ":")).encode("utf-8")
    if len(encoded) > _MAX_RESULT_BYTES:
        encoded = b'{"status":"ERROR","reason":"launcher-report-too-large"}'
    try:
        os.write(result_fd, encoded)
    finally:
        os.close(result_fd)
    if request_fd >= 0:
        os.close(request_fd)
    return 0 if report.get("status") in {"EXECUTED", "FAIL", "LIMIT", "BLOCKED"} else 1


def _verify_kernel_resource_scope(
    payload: Mapping[str, Any], limits: SandboxLimits
) -> dict[str, Any]:
    """Prove this launcher is in real memory and pids controller groups.

    A systemd unit property is not evidence: on cgroup-v1 hosts a user manager
    may create a name=systemd scope while leaving memory and pids in an
    unlimited session cgroup.  Read the kernel controller files and bind their
    paths to the unpredictable requested unit name.  Any missing delegation,
    unlimited value, or looser value fails closed.
    """

    unit = payload.get("resource_scope_unit")
    if not isinstance(unit, str) or not re.fullmatch(
        r"learnfactory-validator-[0-9]+-[0-9a-f]{16}\.scope", unit
    ):
        raise RuntimeError("kernel resource scope identity is malformed")
    try:
        lines = Path("/proc/self/cgroup").read_text(encoding="ascii").splitlines()
    except OSError as error:
        raise RuntimeError("kernel cgroup membership is unavailable") from error
    memberships: dict[str, str] = {}
    unified: str | None = None
    for line in lines:
        fields = line.split(":", 2)
        if len(fields) != 3:
            raise RuntimeError("kernel cgroup membership is malformed")
        _, controllers, raw_path = fields
        path = PurePosixPath(raw_path)
        if not path.is_absolute() or ".." in path.parts:
            raise RuntimeError("kernel cgroup membership path is unsafe")
        if controllers == "":
            unified = raw_path
        for controller in controllers.split(","):
            if controller:
                memberships[controller] = raw_path

    expected_tasks = limits.max_tasks + _CGROUP_TRUSTED_TASK_OVERHEAD
    if unified is not None:
        if PurePosixPath(unified).name != unit:
            raise RuntimeError("launcher is outside its requested cgroup-v2 scope")
        root = Path("/sys/fs/cgroup").joinpath(*PurePosixPath(unified).parts[1:])
        memory = _read_cgroup_ceiling(root / "memory.max")
        tasks = _read_cgroup_ceiling(root / "pids.max")
        swap = _read_cgroup_ceiling(root / "memory.swap.max", allow_zero=True)
        version = 2
    else:
        memory_path = memberships.get("memory")
        pids_path = memberships.get("pids")
        if memory_path is None or pids_path is None:
            raise RuntimeError("memory and pids cgroup controllers are not delegated")
        if (
            PurePosixPath(memory_path).name != unit
            or PurePosixPath(pids_path).name != unit
        ):
            raise RuntimeError("launcher is outside real memory/pids controller scopes")
        memory_root = Path("/sys/fs/cgroup/memory").joinpath(
            *PurePosixPath(memory_path).parts[1:]
        )
        pids_root = Path("/sys/fs/cgroup/pids").joinpath(
            *PurePosixPath(pids_path).parts[1:]
        )
        memory = _read_cgroup_ceiling(memory_root / "memory.limit_in_bytes")
        tasks = _read_cgroup_ceiling(pids_root / "pids.max")
        # On v1 memsw is memory+swap, so equality to memory proves zero swap.
        swap_total = _read_cgroup_ceiling(memory_root / "memory.memsw.limit_in_bytes")
        swap = max(0, swap_total - memory)
        version = 1
    if memory <= 0 or memory > limits.aggregate_memory_bytes:
        raise RuntimeError("kernel aggregate memory ceiling is absent or too loose")
    if tasks <= 0 or tasks > expected_tasks:
        raise RuntimeError("kernel aggregate task ceiling is absent or too loose")
    if swap != 0:
        raise RuntimeError("kernel swap ceiling is absent or too loose")
    return {
        "version": version,
        "unit": unit,
        "memory_max": memory,
        "swap_max": swap,
        "tasks_max": tasks,
        "verified": True,
    }


def _read_cgroup_ceiling(path: Path, *, allow_zero: bool = False) -> int:
    try:
        raw = path.read_text(encoding="ascii").strip()
    except OSError as error:
        raise RuntimeError(f"kernel cgroup control is unavailable: {path.name}") from error
    if raw == "max":
        raise RuntimeError(f"kernel cgroup control is unlimited: {path.name}")
    try:
        value = int(raw)
    except ValueError as error:
        raise RuntimeError(f"kernel cgroup control is malformed: {path.name}") from error
    if value < 0 or (value == 0 and not allow_zero):
        raise RuntimeError(f"kernel cgroup control is invalid: {path.name}")
    return value


def _run_inner(payload: dict[str, Any], mountpoint: Path, limits: SandboxLimits) -> dict[str, Any]:
    root, work, prepared_toolchains, runtime_bindings, copied = _prepare_sandbox_root(
        payload, mountpoint, limits
    )
    source_checksum = copied["input"]["sha256"]
    if source_checksum != payload.get("expected_input_sha256"):
        return {
            "status": "BLOCKED",
            "reason": "input-checksum-mismatch",
            "observed_input_sha256": source_checksum,
            "copy": copied,
        }
    initial_checksum = tree_sha256(
        work,
        maximum_bytes=limits.input_bytes,
        maximum_entries=limits.input_entries,
        maximum_path_bytes=limits.input_path_bytes,
        maximum_depth=limits.input_depth,
    )
    cwd = work if payload["cwd"] == "." else work / str(payload["cwd"])
    if cwd.is_symlink() or not cwd.is_dir() or not _path_within(cwd, work):
        return {"status": "BLOCKED", "reason": "sandbox-cwd-missing-or-unsafe"}

    executable = _host_path_for_sandbox_executable(
        str(payload["argv"][0]), work, prepared_toolchains
    )
    try:
        executable_metadata = os.stat(executable, follow_symlinks=True)
    except OSError:
        return {"status": "BLOCKED", "reason": "sandbox-executable-unavailable"}
    if not stat.S_ISREG(executable_metadata.st_mode) or not os.access(executable, os.X_OK):
        return {"status": "BLOCKED", "reason": "sandbox-executable-unavailable"}

    nproc_limit = int(payload["host_uid_tasks"]) + limits.max_tasks + 8
    setup: subprocess.Popen[bytes] | None = None
    namespace_fds: tuple[int, int] | None = None
    status_read: int | None = None
    status_write: int | None = None
    command_status_read: int | None = None
    command_status_write: int | None = None
    seccomp_fd: int | None = None
    inner: subprocess.Popen[bytes] | None = None
    try:
        setup, namespace_fds = _start_non_owner_user_namespaces(payload)
        status_read, status_write = os.pipe2(getattr(os, "O_CLOEXEC", 0))
        os.set_inheritable(status_write, True)
        command_status_read, command_status_write = os.pipe2(getattr(os, "O_CLOEXEC", 0))
        os.set_inheritable(command_status_write, True)
        seccomp_fd, seccomp_sha256, seccomp_rules = _create_seccomp_filter()
        bwrap_argv = _build_bwrap_argv(
            payload,
            root,
            work,
            prepared_toolchains,
            runtime_bindings,
            nproc_limit,
            namespace_fds,
            status_write,
            seccomp_fd,
            command_status_write,
        )

        def apply_limits() -> None:
            resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
            resource.setrlimit(resource.RLIMIT_FSIZE, (limits.file_bytes, limits.file_bytes))
            resource.setrlimit(resource.RLIMIT_NOFILE, (limits.open_files, limits.open_files))
            resource.setrlimit(
                resource.RLIMIT_AS, (limits.address_space_bytes, limits.address_space_bytes)
            )
            resource.setrlimit(resource.RLIMIT_CPU, (limits.cpu_seconds, limits.cpu_seconds + 1))
            os.umask(0o077)

        started = time.monotonic()
        inherited_fds = (
            *namespace_fds,
            status_write,
            seccomp_fd,
            command_status_write,
        )
        inner = subprocess.Popen(
            bwrap_argv,
            stdin=subprocess.DEVNULL,
            stdout=None,
            stderr=None,
            env=_fixed_host_environment(),
            close_fds=True,
            pass_fds=inherited_fds,
            preexec_fn=apply_limits,
        )
        os.close(status_write)
        status_write = None
        os.close(command_status_write)
        command_status_write = None
        limit_reason: str | None = None
        peak_tasks = 0
        peak_rss = 0
        peak_cpu = 0.0
        while inner.poll() is None:
            tasks, rss, cpu = _namespace_usage()
            # PID 1 is the launcher.  The setup holder, empty-namespace
            # holder, and bubblewrap reaper are trusted fixed overhead; RSS is
            # deliberately not subtracted so the aggregate cap is hard.
            untrusted_tasks = max(0, tasks - 3)
            peak_tasks = max(peak_tasks, untrusted_tasks)
            peak_rss = max(peak_rss, rss)
            peak_cpu = max(peak_cpu, cpu)
            if untrusted_tasks > limits.max_tasks:
                limit_reason = "task-limit"
            elif rss > limits.aggregate_memory_bytes:
                limit_reason = "aggregate-memory-limit"
            elif cpu > limits.cpu_seconds * limits.max_tasks:
                limit_reason = "aggregate-cpu-limit"
            if limit_reason is not None:
                try:
                    inner.kill()
                except ProcessLookupError:
                    pass
                break
            time.sleep(0.02)
        bwrap_return_code = inner.wait()
        trusted_status = _read_bwrap_status(status_read)
        os.close(status_read)
        status_read = None
        command_status = _read_command_status(command_status_read)
        os.close(command_status_read)
        command_status_read = None
        final_error: str | None = None
        final_checksum: str | None = None
        try:
            final_checksum = tree_sha256(
                work,
                maximum_bytes=limits.writable_bytes,
                maximum_entries=min(_MAX_TREE_ENTRIES, limits.writable_inodes),
                maximum_path_bytes=min(
                    _MAX_TREE_PATH_BYTES, max(limits.input_path_bytes, limits.writable_inodes * 128)
                ),
                maximum_depth=limits.input_depth,
            )
        except (SandboxContractError, OSError) as error:
            final_error = _redact(str(error))
        usage = resource.getrusage(resource.RUSAGE_CHILDREN)
        root_stats = os.statvfs(root)
        evidence = {
            "initial_work_sha256": initial_checksum,
            "final_work_sha256": final_checksum,
            "final_tree_error": final_error,
            "copy": copied,
            "tmpfs_capacity_bytes": root_stats.f_blocks * root_stats.f_frsize,
            "tmpfs_inode_capacity": root_stats.f_files,
            "single_writable_filesystem": True,
            "command_identity": "unmapped-user-namespace-overflow",
            "command_uid": 65534,
            "peak_tasks_observed": peak_tasks,
            "peak_rss_bytes_observed": peak_rss,
            "peak_cpu_seconds_observed": peak_cpu,
            "child_user_cpu_seconds": usage.ru_utime,
            "child_system_cpu_seconds": usage.ru_stime,
            "duration_seconds": time.monotonic() - started,
            "bwrap_argv_sha256": _sequence_sha256(bwrap_argv),
            "bwrap_return_code": bwrap_return_code,
            "trusted_bwrap_status": trusted_status,
            "trusted_command_status": command_status,
            "seccomp_sha256": seccomp_sha256,
            "seccomp_denied_syscalls": seccomp_rules,
        }
        if limit_reason is not None:
            return {
                "status": "LIMIT",
                "reason": limit_reason,
                "exit_code": None,
                "signal": signal.SIGKILL,
                **evidence,
            }
        if not trusted_status.get("bootstrap_complete"):
            return {
                "status": "BLOCKED",
                "reason": "sandbox-bootstrap-failed",
                "exit_code": None,
                "signal": None,
                **evidence,
            }
        if command_status.get("kind") == "exit":
            wrapper_expected = command_status.get("exit_code")
        elif command_status.get("kind") == "signal" and isinstance(
            command_status.get("signal"), int
        ):
            wrapper_expected = 128 + int(command_status["signal"])
        else:
            wrapper_expected = None
        if (
            wrapper_expected is not None
            and trusted_status.get("exit_code") != wrapper_expected
        ):
            return {
                "status": "BLOCKED",
                "reason": "command-and-sandbox-status-disagree",
                "exit_code": None,
                "signal": None,
                **evidence,
            }
        if command_status.get("kind") == "signal":
            terminating_signal = command_status.get("signal")
            if not isinstance(terminating_signal, int) or isinstance(
                terminating_signal, bool
            ):
                return {
                    "status": "BLOCKED",
                    "reason": "command-status-malformed",
                    "exit_code": None,
                    "signal": None,
                    **evidence,
                }
            return {
                "status": "FAIL",
                "reason": "command-terminated-by-signal",
                "exit_code": None,
                "signal": terminating_signal,
                **evidence,
            }
        if command_status.get("kind") != "exit":
            return {
                "status": "BLOCKED",
                "reason": "command-status-missing-or-malformed",
                "exit_code": None,
                "signal": None,
                **evidence,
            }
        if final_error is not None:
            return {
                "status": "FAIL",
                "reason": "unsafe-final-work-tree",
                "exit_code": None,
                "signal": None,
                **evidence,
            }
        # Bubblewrap's trusted JSON channel reports positive exits verbatim.
        # Never reinterpret 128+N as a signal; a command may intentionally
        # return 137 or 153.  Supervisor-caused limits are tracked above.
        exit_code = command_status.get("exit_code")
        if not isinstance(exit_code, int) or isinstance(exit_code, bool):
            return {
                "status": "BLOCKED",
                "reason": "sandbox-bootstrap-failed",
                "exit_code": None,
                "signal": None,
                **evidence,
            }
        expected_exit = int(payload["expected_exit"])
        executed = exit_code == expected_exit
        return {
            "status": "EXECUTED" if executed else "FAIL",
            "reason": (
                "expected-exit-non-promoting" if executed else "unexpected-exit"
            ),
            "exit_code": exit_code,
            "signal": None,
            **evidence,
        }
    finally:
        for descriptor in (
            status_read,
            status_write,
            command_status_read,
            command_status_write,
            seccomp_fd,
        ):
            if descriptor is not None:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
        if namespace_fds is not None:
            for descriptor in namespace_fds:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
        if setup is not None:
            try:
                setup.terminate()
            except ProcessLookupError:
                pass
            try:
                setup.wait(timeout=1)
            except subprocess.TimeoutExpired:
                setup.kill()
                setup.wait(timeout=1)


def _prepare_sandbox_root(
    payload: dict[str, Any], mountpoint: Path, limits: SandboxLimits
) -> tuple[
    Path,
    Path,
    list[dict[str, str]],
    list[dict[str, str]],
    dict[str, Any],
]:
    root = mountpoint / "root"
    root.mkdir(mode=0o755)
    for relative, mode in (
        ("work", 0o777),
        ("tmp", 0o1777),
        ("tmp/dev-shm", 0o1777),
        ("etc", 0o755),
        ("etc/alternatives", 0o755),
        ("dev", 0o755),
        ("dev/shm", 0o755),
        ("proc", 0o555),
        ("usr", 0o755),
        ("usr/bin", 0o755),
        ("usr/lib", 0o755),
        ("usr/lib64", 0o755),
        # Writable only while trusted setup creates the supervisor and mask
        # directories; tightened to 0555 before bubblewrap sees the root.
        (".learnfactory", 0o755),
        (".learnfactory/empty", 0o555),
        (".learnfactory/masked-proc-1", 0o555),
        (".toolchains", 0o700),
    ):
        target = root / relative
        target.mkdir(parents=True, exist_ok=True, mode=mode)
        os.chmod(target, mode)
    for device in ("null", "zero", "random", "urandom"):
        descriptor = os.open(
            root / "dev" / device,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0),
            0o600,
        )
        os.close(descriptor)
    (root / "dev/fd").symlink_to("/proc/self/fd")
    (root / "dev/stdin").symlink_to("/proc/self/fd/0")
    (root / "dev/stdout").symlink_to("/proc/self/fd/1")
    (root / "dev/stderr").symlink_to("/proc/self/fd/2")
    for link, target in (
        ("bin", "usr/bin"),
        ("lib", "usr/lib"),
        ("lib64", "usr/lib64"),
        ("sbin", "usr/sbin"),
    ):
        (root / link).symlink_to(target)
    supervisor = root / ".learnfactory/command_supervisor.py"
    supervisor.write_text(_COMMAND_SUPERVISOR_SOURCE, encoding="ascii")
    os.chmod(supervisor, 0o555)
    runtime_bindings = _prepare_minimal_runtime_targets(root)
    os.chmod(root / ".learnfactory", 0o555)

    remaining_bytes = limits.input_bytes
    remaining_entries = limits.input_entries
    work = root / "work"
    input_root_raw = payload.get("input_root")
    if input_root_raw is not None:
        input_copy = _scan_regular_tree(
            Path(str(input_root_raw)),
            destination=work,
            maximum_bytes=remaining_bytes,
            maximum_entries=remaining_entries,
            maximum_path_bytes=limits.input_path_bytes,
            maximum_depth=limits.input_depth,
            writable_copy=True,
        )
    else:
        input_copy = {
            "entries": 0,
            "files": 0,
            "bytes": 0,
            "path_bytes": 0,
            "sha256": _empty_tree_digest(),
        }
    remaining_bytes -= int(input_copy["bytes"])
    remaining_entries -= int(input_copy["entries"])
    prepared_toolchains: list[dict[str, str]] = []
    toolchain_copies: list[dict[str, Any]] = []
    for index, item in enumerate(payload["toolchain_roots"]):
        target_path = PurePosixPath(str(item["path"]))
        destination = root / ".toolchains" / f"{index:04d}"
        destination.mkdir(mode=0o700)
        copied = _scan_regular_tree(
            Path(str(item["path"])),
            destination=destination,
            maximum_bytes=max(1, remaining_bytes),
            maximum_entries=max(1, remaining_entries),
            maximum_path_bytes=limits.input_path_bytes,
            maximum_depth=limits.input_depth,
            writable_copy=False,
        )
        if copied["sha256"] != item["sha256"]:
            raise SandboxContractError("toolchain checksum mismatch")
        remaining_bytes -= int(copied["bytes"])
        remaining_entries -= int(copied["entries"])
        if remaining_bytes < 0 or remaining_entries < 0:
            raise SandboxContractError("combined input and toolchains exceed configured limits")
        mount_target = root.joinpath(*target_path.parts[1:])
        mount_target.mkdir(parents=True, exist_ok=True)
        prepared = {
            "target": str(target_path),
            "snapshot": str(destination),
            "sha256": str(copied["sha256"]),
        }
        prepared_toolchains.append(prepared)
        toolchain_copies.append({k: v for k, v in copied.items() if k != "path_bytes"})
    return root, work, prepared_toolchains, runtime_bindings, {
        "input": input_copy,
        "toolchains": toolchain_copies,
        "combined_bytes": limits.input_bytes - remaining_bytes,
        "combined_entries": limits.input_entries - remaining_entries,
    }


def _prepare_minimal_runtime_targets(root: Path) -> list[dict[str, str]]:
    bindings: list[dict[str, str]] = []
    for source, target, kind in _minimal_runtime_sources():
        destination = root.joinpath(*PurePosixPath(target).parts[1:])
        destination.parent.mkdir(parents=True, exist_ok=True)
        if kind == "directory":
            destination.mkdir(parents=True, exist_ok=True)
        else:
            descriptor = os.open(
                destination,
                os.O_WRONLY
                | os.O_CREAT
                | os.O_EXCL
                | getattr(os, "O_CLOEXEC", 0)
                | getattr(os, "O_NOFOLLOW", 0),
                0o400,
            )
            os.close(descriptor)
        bindings.append({"source": source, "target": target})
    # Prevent Python's vendor package directories from expanding the runtime
    # authority beyond the standard library selected above.
    empty = str(root / ".learnfactory/empty")
    stdlib = PurePosixPath(_system_python_stdlib())
    alternate_parent = PurePosixPath(
        "/usr/lib" if str(stdlib.parent) == "/usr/lib64" else "/usr/lib64"
    )
    for target_path in (
        stdlib / "site-packages",
        alternate_parent / stdlib.name / "site-packages",
    ):
        target = str(target_path)
        root.joinpath(*PurePosixPath(target).parts[1:]).mkdir(
            parents=True, exist_ok=True
        )
        bindings.append({"source": empty, "target": target})
    return bindings


@functools.lru_cache(maxsize=1)
def _minimal_runtime_sources() -> tuple[tuple[str, str, str], ...]:
    """Return exact host files needed by the four approved base commands."""

    base_targets = (
        "/usr/bin/python3",
        "/usr/bin/prlimit",
        "/usr/bin/sleep",
        "/usr/bin/true",
    )
    bindings: dict[str, tuple[str, str, str]] = {}
    binaries: list[Path] = []
    for target in base_targets:
        raw = Path(target)
        try:
            source = raw.resolve(strict=True)
        except OSError as error:
            raise RuntimeError(f"minimal runtime executable is unavailable: {target}") from error
        if not source.is_file() or not os.access(source, os.X_OK):
            raise RuntimeError(f"minimal runtime executable is invalid: {target}")
        bindings[target] = (str(source), target, "file")
        binaries.append(source)

    python_root = Path(_system_python_stdlib())
    if not python_root.is_dir():
        raise RuntimeError("minimal system Python standard library is unavailable")
    bindings[str(python_root)] = (str(python_root), str(python_root), "directory")

    # ldd is applied only to immutable, administrator-owned base binaries and
    # standard-library extension modules—not to caller input or toolchains.
    extensions = sorted((python_root / "lib-dynload").glob("*.so"))
    for binary in [*binaries, *extensions]:
        completed = subprocess.run(
            ["/usr/bin/ldd", str(binary)],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=_fixed_host_environment(),
            check=False,
            timeout=5,
        )
        if completed.returncode != 0 or len(completed.stdout) > 256 * 1024:
            raise RuntimeError(f"minimal runtime dependency discovery failed: {binary.name}")
        rendered = completed.stdout.decode("utf-8", "strict")
        for matched in re.findall(r"(?:=>\s*)?(/(?:usr/)?lib(?:64)?/[^\s(]+)", rendered):
            raw_dependency = Path(matched)
            try:
                dependency = raw_dependency.resolve(strict=True)
            except OSError as error:
                raise RuntimeError(
                    f"minimal runtime dependency is unavailable: {raw_dependency.name}"
                ) from error
            if not dependency.is_file():
                raise RuntimeError("minimal runtime dependency is not a regular file")
            if matched.startswith("/lib64/"):
                target = "/usr/lib64/" + raw_dependency.name
            elif matched.startswith("/lib/"):
                target = "/usr/lib/" + raw_dependency.name
            else:
                target = matched
            if not target.startswith(("/usr/lib/", "/usr/lib64/")):
                raise RuntimeError("minimal runtime dependency escaped system libraries")
            bindings.setdefault(target, (str(dependency), target, "file"))
    return tuple(bindings[target] for target in sorted(bindings))


@functools.lru_cache(maxsize=1)
def _system_python_stdlib() -> str:
    completed = subprocess.run(
        (
            "/usr/bin/python3",
            "-I",
            "-c",
            "import sysconfig; print(sysconfig.get_path('stdlib'))",
        ),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=_fixed_host_environment(),
        check=False,
        timeout=5,
    )
    if completed.returncode != 0 or len(completed.stdout) > 4096:
        raise RuntimeError("minimal system Python standard library discovery failed")
    try:
        rendered = completed.stdout.decode("utf-8", "strict").strip()
    except UnicodeDecodeError as error:
        raise RuntimeError("minimal system Python standard library path is malformed") from error
    root = Path(rendered)
    if (
        not root.is_absolute()
        or root.parent not in {Path("/usr/lib"), Path("/usr/lib64")}
        or re.fullmatch(r"python[0-9]+\.[0-9]+", root.name) is None
        or not root.is_dir()
    ):
        raise RuntimeError("minimal system Python standard library path is unsafe")
    return str(root)


def _build_bwrap_argv(
    payload: dict[str, Any],
    root: Path,
    work: Path,
    prepared_toolchains: list[dict[str, str]],
    runtime_bindings: list[dict[str, str]],
    nproc_limit: int,
    namespace_fds: tuple[int, int],
    status_fd: int,
    seccomp_fd: int,
    command_status_fd: int,
) -> list[str]:
    setup_userns, command_userns = namespace_fds
    command = [
        str(payload["tools"]["bwrap"]),
        "--die-with-parent",
        "--new-session",
        "--userns",
        str(setup_userns),
        "--userns2",
        str(command_userns),
        "--unshare-pid",
        "--unshare-uts",
        "--unshare-ipc",
        "--unshare-net",
        "--hostname",
        "learnfactory-validator",
        "--cap-drop",
        "ALL",
        "--json-status-fd",
        str(status_fd),
        "--seccomp",
        str(seccomp_fd),
        "--ro-bind",
        str(root),
        "/",
        "--bind",
        str(work),
        "/work",
        "--bind",
        str(root / "tmp"),
        "/tmp",
        "--bind",
        str(root / "tmp/dev-shm"),
        "/dev/shm",
        "--proc",
        "/proc",
        "--ro-bind",
        str(root / ".learnfactory/masked-proc-1"),
        "/proc/1",
    ]
    for device in ("null", "zero", "random", "urandom"):
        command.extend(["--dev-bind", f"/dev/{device}", f"/dev/{device}"])
    for proc_path in ("/proc/keys", "/proc/key-users", "/proc/kcore", "/proc/sysrq-trigger"):
        if Path(proc_path).exists():
            command.extend(["--ro-bind", "/dev/null", proc_path])
    for item in runtime_bindings:
        command.extend(["--ro-bind", item["source"], item["target"]])
    for item in prepared_toolchains:
        command.extend(["--ro-bind", item["snapshot"], item["target"]])
    cwd = "/work" if payload["cwd"] == "." else f"/work/{payload['cwd']}"
    command.extend(["--chdir", cwd])
    fixed = {
        "HOME": "/tmp",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PATH": str(payload["fixed_path"]),
        "PYTHONDONTWRITEBYTECODE": "1",
        "TMPDIR": "/tmp",
        **payload["env"],
    }
    for name, value in sorted(fixed.items()):
        command.extend(["--setenv", name, value])
    command.extend(
        [
            "--",
            "/usr/bin/prlimit",
            f"--nproc={nproc_limit}:{nproc_limit}",
            "--",
            "/usr/bin/python3",
            "-I",
            "/.learnfactory/command_supervisor.py",
            str(command_status_fd),
            *payload["argv"],
        ]
    )
    return command


def _host_path_for_sandbox_executable(
    executable: str, work: Path, prepared_toolchains: list[dict[str, str]]
) -> Path:
    """Map an already-normalized sandbox executable to the launcher's view."""

    sandbox_path = PurePosixPath(executable)
    if _pure_within(sandbox_path, PurePosixPath("/work")):
        relative = sandbox_path.relative_to(PurePosixPath("/work"))
        candidate = work.joinpath(*relative.parts)
        if not _path_within(candidate, work):
            raise RuntimeError("sandbox executable escapes /work")
        return candidate
    if _pure_within(sandbox_path, PurePosixPath("/bin")):
        relative = sandbox_path.relative_to(PurePosixPath("/bin"))
        return Path("/usr/bin").joinpath(*relative.parts)
    for item in prepared_toolchains:
        target = PurePosixPath(item["target"])
        if _pure_within(sandbox_path, target):
            relative = sandbox_path.relative_to(target)
            return Path(item["snapshot"]).joinpath(*relative.parts)
    return Path(executable)


def _start_non_owner_user_namespaces(
    payload: Mapping[str, Any],
) -> tuple[subprocess.Popen[bytes], tuple[int, int]]:
    """Create setup and descendant unmapped command user namespaces.

    Bubblewrap performs mounts with capabilities in the first namespace, then
    switches to the empty descendant.  The command therefore runs as an
    unmapped overflow identity, cannot own the host runtime, and receives only
    read-only trusted setup views plus deliberately writable capped scratch.
    """

    tools = payload["tools"]
    setup = subprocess.Popen(
        [
            str(tools["setpriv"]),
            "--pdeathsig",
            "SIGKILL",
            "--",
            str(tools["unshare"]),
            "--map-root-user",
            "--user",
            sys.executable,
            "-I",
            str(Path(__file__).resolve()),
            "--userns-holder",
            "--unshare-tool",
            str(tools["unshare"]),
            "--setpriv-tool",
            str(tools["setpriv"]),
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=_fixed_host_environment(),
        close_fds=True,
    )
    try:
        assert setup.stdout is not None
        ready, _, _ = select.select([setup.stdout], [], [], 5.0)
        if not ready:
            raise RuntimeError("command user namespace setup timed out")
        line = setup.stdout.readline(128)
        if len(line) >= 128 or not line.endswith(b"\n"):
            raise RuntimeError("command user namespace setup returned malformed evidence")
        target_pid = int(line.strip())
        if target_pid <= 0 or setup.poll() is not None:
            raise RuntimeError("command user namespace setup exited early")
        namespace_flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
        setup_fd = os.open(f"/proc/{setup.pid}/ns/user", namespace_flags)
        try:
            target_fd = os.open(f"/proc/{target_pid}/ns/user", namespace_flags)
        except BaseException:
            os.close(setup_fd)
            raise
        if os.fstat(setup_fd).st_ino == os.fstat(target_fd).st_ino:
            os.close(setup_fd)
            os.close(target_fd)
            raise RuntimeError("command identity namespace is not distinct")
        return setup, (setup_fd, target_fd)
    except BaseException:
        try:
            setup.terminate()
        except ProcessLookupError:
            pass
        try:
            setup.wait(timeout=1)
        except subprocess.TimeoutExpired:
            setup.kill()
            setup.wait(timeout=1)
        raise


def _userns_holder(unshare_tool: str, setpriv_tool: str) -> int:
    ready_read, ready_write = os.pipe2(getattr(os, "O_CLOEXEC", 0))
    os.set_inheritable(ready_write, True)
    target = subprocess.Popen(
        [
            setpriv_tool,
            "--pdeathsig",
            "SIGKILL",
            "--",
            unshare_tool,
            "--user",
            sys.executable,
            "-I",
            str(Path(__file__).resolve()),
            "--empty-userns-holder",
            "--ready-fd",
            str(ready_write),
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=_fixed_host_environment(),
        close_fds=True,
        pass_fds=(ready_write,),
    )
    os.close(ready_write)
    try:
        ready, _, _ = select.select([ready_read], [], [], 5.0)
        if not ready or os.read(ready_read, 1) != b"R":
            return 3
        os.write(1, f"{target.pid}\n".encode("ascii"))
        # The setup parent owns stdin.  EOF or termination tears down the
        # descendant through PR_SET_PDEATHSIG.
        while os.read(0, 4096):
            pass
        return 0
    finally:
        os.close(ready_read)
        try:
            target.terminate()
        except ProcessLookupError:
            pass
        try:
            target.wait(timeout=1)
        except subprocess.TimeoutExpired:
            target.kill()
            target.wait(timeout=1)


def _empty_userns_holder(ready_fd: int) -> int:
    os.write(ready_fd, b"R")
    os.close(ready_fd)
    while True:
        signal.pause()


class _ScmpArgCmp(ctypes.Structure):
    _fields_ = (
        ("arg", ctypes.c_uint),
        ("op", ctypes.c_int),
        ("datum_a", ctypes.c_uint64),
        ("datum_b", ctypes.c_uint64),
    )


def _create_seccomp_filter() -> tuple[int, str, list[str]]:
    """Generate a libseccomp BPF deny filter in a sealed descriptor."""

    library = ctypes.CDLL("libseccomp.so.2", use_errno=True)
    library.seccomp_init.argtypes = (ctypes.c_uint32,)
    library.seccomp_init.restype = ctypes.c_void_p
    library.seccomp_release.argtypes = (ctypes.c_void_p,)
    library.seccomp_syscall_resolve_name.argtypes = (ctypes.c_char_p,)
    library.seccomp_syscall_resolve_name.restype = ctypes.c_int
    library.seccomp_rule_add_array.argtypes = (
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_int,
        ctypes.c_uint,
        ctypes.POINTER(_ScmpArgCmp),
    )
    library.seccomp_rule_add_array.restype = ctypes.c_int
    library.seccomp_export_bpf.argtypes = (ctypes.c_void_p, ctypes.c_int)
    library.seccomp_export_bpf.restype = ctypes.c_int
    allow = 0x7FFF0000
    deny = 0x00050000 | errno.EPERM
    context = library.seccomp_init(allow)
    if not context:
        raise RuntimeError("libseccomp could not initialize a filter")
    rules: list[str] = []
    descriptor: int | None = None
    try:
        for name in _DENIED_SYSCALLS:
            number = library.seccomp_syscall_resolve_name(name.encode("ascii"))
            if number < 0:
                if name in {"add_key", "request_key", "keyctl", "mount", "unshare", "setns"}:
                    raise RuntimeError(f"required seccomp syscall is unknown: {name}")
                continue
            result = library.seccomp_rule_add_array(context, deny, number, 0, None)
            if result != 0:
                raise RuntimeError(f"libseccomp rejected the {name} rule: {result}")
            rules.append(name)
        clone_number = library.seccomp_syscall_resolve_name(b"clone")
        if clone_number < 0:
            raise RuntimeError("required seccomp clone syscall is unknown")
        for namespace_flag in _CLONE_NAMESPACE_FLAGS:
            comparison = _ScmpArgCmp(0, 7, namespace_flag, namespace_flag)
            result = library.seccomp_rule_add_array(
                context, deny, clone_number, 1, ctypes.byref(comparison)
            )
            if result != 0:
                raise RuntimeError(f"libseccomp rejected a clone namespace rule: {result}")
        rules.append("clone(namespace-flags)")
        socket_number = library.seccomp_syscall_resolve_name(b"socket")
        socketpair_number = library.seccomp_syscall_resolve_name(b"socketpair")
        if socket_number < 0 or socketpair_number < 0:
            raise RuntimeError("required socket syscalls are unknown")
        for address_family in _DENIED_LOW_SOCKET_FAMILIES:
            comparison = _ScmpArgCmp(0, 4, address_family, 0)  # SCMP_CMP_EQ
            result = library.seccomp_rule_add_array(
                context, deny, socket_number, 1, ctypes.byref(comparison)
            )
            if result != 0:
                raise RuntimeError(
                    f"libseccomp rejected socket family {address_family}: {result}"
                )
        greater_than_inet6 = _ScmpArgCmp(0, 6, 10, 0)  # SCMP_CMP_GT
        result = library.seccomp_rule_add_array(
            context, deny, socket_number, 1, ctypes.byref(greater_than_inet6)
        )
        if result != 0:
            raise RuntimeError(f"libseccomp rejected high socket families: {result}")
        non_unix_socketpair = _ScmpArgCmp(0, 1, 1, 0)  # SCMP_CMP_NE
        result = library.seccomp_rule_add_array(
            context, deny, socketpair_number, 1, ctypes.byref(non_unix_socketpair)
        )
        if result != 0:
            raise RuntimeError(f"libseccomp rejected socketpair family policy: {result}")
        rules.extend(
            [
                "socket(allow=AF_UNIX,AF_INET,AF_INET6)",
                "socketpair(allow=AF_UNIX)",
            ]
        )
        descriptor = os.memfd_create(
            "learnfactory-validator-seccomp",
            getattr(os, "MFD_CLOEXEC", 0) | getattr(os, "MFD_ALLOW_SEALING", 0),
        )
        if library.seccomp_export_bpf(context, descriptor) != 0:
            raise RuntimeError("libseccomp could not export BPF")
        size = os.lseek(descriptor, 0, os.SEEK_END)
        if size <= 0 or size > 1024 * 1024:
            raise RuntimeError("libseccomp produced an invalid BPF size")
        bpf = os.pread(descriptor, size, 0)
        if len(bpf) != size:
            raise RuntimeError("libseccomp BPF could not be read back")
        os.lseek(descriptor, 0, os.SEEK_SET)
        _seal_memfd(descriptor)
        return descriptor, hashlib.sha256(bpf).hexdigest(), sorted(rules)
    except BaseException:
        if descriptor is not None:
            os.close(descriptor)
        raise
    finally:
        library.seccomp_release(context)


def _read_bwrap_status(descriptor: int) -> dict[str, Any]:
    raw = _read_bounded_fd(descriptor, 64 * 1024)
    child_pid: int | None = None
    exit_code: int | None = None
    malformed = False
    for line in raw.splitlines():
        try:
            item = json.loads(line)
        except (UnicodeDecodeError, json.JSONDecodeError):
            malformed = True
            continue
        if not isinstance(item, dict):
            malformed = True
            continue
        if isinstance(item.get("child-pid"), int) and not isinstance(item["child-pid"], bool):
            child_pid = int(item["child-pid"])
        if isinstance(item.get("exit-code"), int) and not isinstance(item["exit-code"], bool):
            exit_code = int(item["exit-code"])
    return {
        "bootstrap_complete": child_pid is not None and exit_code is not None and not malformed,
        "child_started": child_pid is not None,
        "exit_code": exit_code,
        "malformed": malformed,
    }


def _read_command_status(descriptor: int) -> dict[str, Any]:
    try:
        raw = _read_bounded_fd(descriptor, 1024)
        value = json.loads(raw)
    except (OSError, RuntimeError, UnicodeDecodeError, json.JSONDecodeError):
        return {"kind": "malformed"}
    if not isinstance(value, dict) or set(value) not in (
        {"kind", "exit_code"},
        {"kind", "signal"},
    ):
        return {"kind": "malformed"}
    if value.get("kind") == "exit":
        exit_code = value.get("exit_code")
        if (
            isinstance(exit_code, int)
            and not isinstance(exit_code, bool)
            and 0 <= exit_code <= 255
        ):
            return {"kind": "exit", "exit_code": exit_code}
    if value.get("kind") == "signal":
        terminating_signal = value.get("signal")
        if (
            isinstance(terminating_signal, int)
            and not isinstance(terminating_signal, bool)
            and 1 <= terminating_signal < signal.NSIG
        ):
            return {"kind": "signal", "signal": terminating_signal}
    return {"kind": "malformed"}


def _namespace_usage() -> tuple[int, int, float]:
    tasks = 0
    rss = 0
    cpu_ticks = 0
    clock_ticks = os.sysconf("SC_CLK_TCK")
    page_size = os.sysconf("SC_PAGE_SIZE")
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit() or entry.name == "1":
            continue
        try:
            tasks += sum(1 for _ in (entry / "task").iterdir())
            stat_fields = (entry / "stat").read_text(encoding="ascii").split()
            cpu_ticks += int(stat_fields[13]) + int(stat_fields[14])
            rss_pages = int((entry / "statm").read_text(encoding="ascii").split()[1])
            rss += rss_pages * page_size
        except (FileNotFoundError, ProcessLookupError, PermissionError, IndexError, ValueError):
            continue
    return tasks, rss, cpu_ticks / clock_ticks


def _same_snapshot(left: os.stat_result, right: os.stat_result) -> bool:
    return all(
        getattr(left, name) == getattr(right, name)
        for name in ("st_dev", "st_ino", "st_mode", "st_size", "st_mtime_ns", "st_ctime_ns")
    )


def _fd_mount_id(descriptor: int) -> int:
    """Return Linux's mount ID for an open object, failing closed if absent."""

    try:
        fields = Path(f"/proc/self/fdinfo/{descriptor}").read_text(
            encoding="ascii", errors="strict"
        ).splitlines()
    except (OSError, UnicodeError) as error:
        raise SandboxContractError("mount identity is unavailable") from error
    values = [line.split(":", 1)[1].strip() for line in fields if line.startswith("mnt_id:")]
    if len(values) != 1:
        raise SandboxContractError("mount identity is unavailable")
    try:
        value = int(values[0])
    except ValueError as error:
        raise SandboxContractError("mount identity is malformed") from error
    if value <= 0:
        raise SandboxContractError("mount identity is malformed")
    return value


def _path_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _pure_within(path: PurePosixPath, root: PurePosixPath) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _hash_field(digest: Any, value: bytes) -> None:
    digest.update(len(value).to_bytes(8, "big"))
    digest.update(value)


def _empty_tree_digest() -> str:
    return hashlib.sha256(b"learnfactory-tree-sha256-v3\0").hexdigest()


def _read_bounded_fd(descriptor: int, maximum: int) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = os.read(descriptor, min(_READ_SIZE, maximum + 1 - total))
        if not chunk:
            break
        total += len(chunk)
        if total > maximum:
            raise RuntimeError("descriptor payload exceeds its byte ceiling")
        chunks.append(chunk)
    return b"".join(chunks)


def _seal_memfd(descriptor: int) -> None:
    seals = (
        getattr(fcntl, "F_SEAL_SEAL", 0x0001)
        | getattr(fcntl, "F_SEAL_SHRINK", 0x0002)
        | getattr(fcntl, "F_SEAL_GROW", 0x0004)
        | getattr(fcntl, "F_SEAL_WRITE", 0x0008)
    )
    fcntl.fcntl(descriptor, getattr(fcntl, "F_ADD_SEALS", 1033), seals)


def _sealed_memfd(name: str, payload: bytes) -> int:
    descriptor = os.memfd_create(
        name,
        getattr(os, "MFD_CLOEXEC", 0) | getattr(os, "MFD_ALLOW_SEALING", 0),
    )
    try:
        view = memoryview(payload)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError("short write to sealed request descriptor")
            view = view[written:]
        os.lseek(descriptor, 0, os.SEEK_SET)
        _seal_memfd(descriptor)
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _sequence_sha256(values: Sequence[str]) -> str:
    return hashlib.sha256(
        json.dumps(list(values), ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _contains_secret_material(value: str) -> bool:
    patterns = (
        r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{8,}",
        r"(?i)\bbasic\s+[A-Za-z0-9+/=]{8,}",
        r"\bsk-[A-Za-z0-9_-]{8,}\b",
        r"\bAKIA[0-9A-Z]{12,}\b",
        r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b",
        r"\b(?:xox[aboprs]-|xapp-)[A-Za-z0-9-]{10,}\b",
        r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b",
        r"(?s)-----BEGIN (?:[A-Z0-9 ]+ )?PRIVATE KEY-----",
        r"(?i)[a-z][a-z0-9+.-]*://[^/@\s:]+:[^/@\s]+@",
        r"(?i)['\"]?(?:authorization|api[_-]?key|token|secret|password|passwd)"
        r"['\"]?\s*[=:]\s*(?:\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'|[^\s,;]+)",
    )
    return any(re.search(pattern, value) is not None for pattern in patterns)


def _redact(value: str) -> str:
    # One shared sanitizer handles structured JSON-ish logs, shell-ish
    # assignments, bearer credentials, and common provider key formats.
    value = re.sub(
        r"(?s)-----BEGIN (?:[A-Z0-9 ]+ )?PRIVATE KEY-----.*?"
        r"-----END (?:[A-Z0-9 ]+ )?PRIVATE KEY-----",
        "<redacted-private-key>",
        value,
    )
    value = re.sub(
        r"(?s)-----BEGIN (?:[A-Z0-9 ]+ )?PRIVATE KEY-----.*\Z",
        "<redacted-private-key>",
        value,
    )
    value = re.sub(
        r"(?s)\A.*?-----END (?:[A-Z0-9 ]+ )?PRIVATE KEY-----",
        "<redacted-private-key>",
        value,
    )
    value = re.sub(
        r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]+", "Bearer <redacted>", value
    )
    value = re.sub(
        r"(?i)\bbasic\s+[A-Za-z0-9+/=]+", "Basic <redacted>", value
    )
    value = re.sub(
        r"(?i)([a-z][a-z0-9+.-]*://)[^/@\s:]+:[^/@\s]+@",
        r"\1<redacted>@",
        value,
    )
    value = re.sub(
        r"(?i)(['\"]?(?:authorization|api[_-]?key|access[_-]?key|token|secret|"
        r"password|passwd)['\"]?\s*[=:]\s*)"
        r"(?:\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'|[^\s,;}\]]+)",
        r"\1<redacted>",
        value,
    )
    value = re.sub(r"\bsk-[A-Za-z0-9_-]{8,}\b", "<redacted-api-key>", value)
    value = re.sub(r"\bAKIA[0-9A-Z]{12,}\b", "<redacted-access-key>", value)
    value = re.sub(
        r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b",
        "<redacted-github-token>",
        value,
    )
    value = re.sub(
        r"\b(?:xox[aboprs]-|xapp-)[A-Za-z0-9-]{10,}\b",
        "<redacted-slack-token>",
        value,
    )
    value = re.sub(
        r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b",
        "<redacted-jwt>",
        value,
    )
    return value


def _main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--launcher", action="store_true")
    parser.add_argument("--result-fd", type=int)
    parser.add_argument("--request-fd", type=int)
    parser.add_argument("--userns-holder", action="store_true")
    parser.add_argument("--empty-userns-holder", action="store_true")
    parser.add_argument("--ready-fd", type=int)
    parser.add_argument("--unshare-tool")
    parser.add_argument("--setpriv-tool")
    arguments = parser.parse_args(argv)
    if arguments.launcher:
        if (
            arguments.result_fd is None
            or arguments.result_fd < 3
            or arguments.request_fd is None
            or arguments.request_fd < 3
        ):
            return 2
        return _launcher(arguments.result_fd, arguments.request_fd)
    if arguments.userns_holder:
        if not arguments.unshare_tool or not arguments.setpriv_tool:
            return 2
        return _userns_holder(arguments.unshare_tool, arguments.setpriv_tool)
    if arguments.empty_userns_holder:
        if arguments.ready_fd is None or arguments.ready_fd < 3:
            return 2
        return _empty_userns_holder(arguments.ready_fd)
    return 2


if __name__ == "__main__":
    raise SystemExit(_main())
