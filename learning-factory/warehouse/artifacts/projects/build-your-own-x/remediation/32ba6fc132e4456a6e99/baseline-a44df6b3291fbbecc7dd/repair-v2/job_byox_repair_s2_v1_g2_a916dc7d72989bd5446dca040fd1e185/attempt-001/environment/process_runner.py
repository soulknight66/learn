"""Bounded subprocess and scratch-directory helpers for challenge runners."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from contextlib import contextmanager
import os
from pathlib import Path
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile


def run_process(
    argv: Sequence[str],
    cwd: Path,
    *,
    timeout_seconds: float = 60,
    termination_grace_seconds: float = 5,
) -> int:
    """Run one argv in a new session and kill its whole process group on timeout."""

    command = [str(argument) for argument in argv]
    print("$ " + shlex.join(command), flush=True)
    try:
        process = subprocess.Popen(
            command,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
    except OSError as failure:
        print(f"unable to start process: {failure}", file=sys.stderr)
        return 127

    timed_out = False
    try:
        stdout, stderr = process.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        _signal_process_group(process.pid, signal.SIGTERM)
        try:
            stdout, stderr = process.communicate(timeout=termination_grace_seconds)
        except subprocess.TimeoutExpired:
            _signal_process_group(process.pid, signal.SIGKILL)
            try:
                stdout, stderr = process.communicate(
                    timeout=termination_grace_seconds
                )
            except subprocess.TimeoutExpired as failure:
                stdout = _captured_text(failure.stdout)
                stderr = _captured_text(failure.stderr)
                stderr += (
                    "process did not exit after SIGKILL within "
                    f"{termination_grace_seconds:g} seconds\n"
                )
        else:
            # The direct child may exit while a descendant that closed its
            # inherited pipes ignores SIGTERM. Kill any surviving group member.
            _signal_process_group(process.pid, signal.SIGKILL)

    if stdout:
        print(stdout, end="")
    if stderr:
        print(stderr, end="", file=sys.stderr)
    if timed_out:
        print(f"TIMEOUT after {timeout_seconds:g} seconds", file=sys.stderr)
        return 124
    return process.returncode


def _signal_process_group(process_group_id: int, requested_signal: signal.Signals) -> None:
    try:
        os.killpg(process_group_id, requested_signal)
    except ProcessLookupError:
        pass


def _captured_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode(errors="replace")
    return value


@contextmanager
def build_directory(
    repository: Path,
    prefix: str,
    requested_root: Path | None,
) -> Iterator[Path]:
    """Create removable scratch space without relying on the host's default /tmp."""

    repository = repository.resolve()
    if requested_root is not None:
        root = requested_root
        if not root.is_absolute():
            root = repository / root
        candidates = (root.resolve(),)
    else:
        # A writable source tree is common during development; an immutable
        # CANDIDATE directory commonly has a writable per-attempt parent.
        candidates = (
            repository / ".minilog-runner-tmp",
            repository.parent / ".minilog-runner-tmp",
        )

    failures: list[str] = []
    temporary: Path | None = None
    created_root: Path | None = None
    for root in candidates:
        made_root = False
        try:
            if root.is_symlink():
                raise OSError("scratch root must not be a symlink")
            if not root.exists():
                root.mkdir(mode=0o700)
                made_root = True
            if not root.is_dir():
                raise OSError("scratch root is not a directory")
            temporary = Path(tempfile.mkdtemp(prefix=prefix, dir=root))
            if made_root:
                created_root = root
            break
        except OSError as failure:
            failures.append(f"{root}: {failure}")
            if made_root:
                try:
                    root.rmdir()
                except OSError:
                    pass

    if temporary is None:
        details = "; ".join(failures)
        raise OSError(f"no usable build directory ({details})")

    try:
        yield temporary
    finally:
        shutil.rmtree(temporary)
        if created_root is not None:
            try:
                created_root.rmdir()
            except OSError:
                pass
