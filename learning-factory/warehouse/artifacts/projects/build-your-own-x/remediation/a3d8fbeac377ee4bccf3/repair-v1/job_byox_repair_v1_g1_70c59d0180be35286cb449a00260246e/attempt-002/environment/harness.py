#!/usr/bin/env python3
"""Bounded POSIX process execution and read-only Mica fixtures.

This module is deliberately independent of the Pascal implementation.  Test and
benchmark entry points use it whenever they execute a learner-supplied binary.
"""

import contextlib
import errno
import io
import os
import signal
import subprocess
import tempfile
import threading
import time


DEFAULT_MAX_OUTPUT_BYTES = 65536
DEFAULT_GROUP_GRACE_SECONDS = 0.25


class ProcessResult(object):
    """A small, Python-3.6-compatible completed-process record."""

    def __init__(self, args, returncode, stdout, stderr,
                 stdout_truncated=False, stderr_truncated=False):
        self.args = list(args)
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.stdout_truncated = stdout_truncated
        self.stderr_truncated = stderr_truncated


class ProcessTimeout(RuntimeError):
    """Raised after a timed-out process group has been terminated and reaped."""

    def __init__(self, args, timeout, stdout, stderr,
                 stdout_truncated=False, stderr_truncated=False):
        RuntimeError.__init__(
            self,
            "command exceeded {:.3f}s deadline: {}".format(
                timeout, " ".join(args)
            ),
        )
        self.command = list(args)
        self.timeout = timeout
        self.stdout = stdout
        self.stderr = stderr
        self.stdout_truncated = stdout_truncated
        self.stderr_truncated = stderr_truncated


class _BoundedCapture(object):
    def __init__(self, limit):
        self.limit = limit
        self.data = bytearray()
        self.truncated = False

    def consume(self, chunk):
        remaining = self.limit - len(self.data)
        if remaining > 0:
            self.data.extend(chunk[:remaining])
        if len(chunk) > remaining:
            self.truncated = True

    def text(self):
        return bytes(self.data).decode("utf-8", "replace")


def _drain(stream, capture):
    try:
        while True:
            chunk = stream.read(8192)
            if not chunk:
                return
            capture.consume(chunk)
    finally:
        stream.close()


def _signal_group(process_group, sig):
    try:
        os.killpg(process_group, sig)
        return True
    except OSError as error:
        if error.errno == errno.ESRCH:
            return False
        raise


def _group_exists(process_group):
    try:
        os.killpg(process_group, 0)
        return True
    except OSError as error:
        if error.errno == errno.ESRCH:
            return False
        if error.errno == errno.EPERM:  # The group exists but is not signalable.
            return True
        raise


def _terminate_group(process, grace_seconds):
    """Terminate the new process group and always reap its direct child."""

    process_group = process.pid
    _signal_group(process_group, signal.SIGTERM)
    deadline = time.monotonic() + grace_seconds
    while _group_exists(process_group) and time.monotonic() < deadline:
        if process.poll() is None:
            try:
                process.wait(timeout=min(0.05, max(0.001, deadline - time.monotonic())))
            except subprocess.TimeoutExpired:
                pass
        time.sleep(0.005)

    if _group_exists(process_group):
        _signal_group(process_group, signal.SIGKILL)

    if process.poll() is None:
        try:
            process.wait(timeout=max(1.0, grace_seconds))
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=1.0)


def run_process(argv, timeout, cwd=None, env=None,
                max_output_bytes=DEFAULT_MAX_OUTPUT_BYTES,
                group_grace_seconds=DEFAULT_GROUP_GRACE_SECONDS):
    """Run one argv in a new session with a deadline and bounded log capture.

    Both pipes are drained continuously, but at most ``max_output_bytes`` from
    each stream is retained.  On normal completion the process group is still
    checked and terminated so a background descendant cannot outlive its leader.
    POSIX process groups cannot contain a descendant that deliberately creates a
    separate session; stronger hostile-code isolation requires a worker-owned
    container or cgroup outside this educational pack.
    """

    if os.name != "posix":
        raise RuntimeError("the Mica worker harness requires POSIX process groups")
    if not isinstance(argv, (list, tuple)) or not argv:
        raise ValueError("argv must be a non-empty list or tuple")
    if not all(isinstance(item, str) and item for item in argv):
        raise ValueError("every argv item must be a non-empty string")
    if timeout <= 0:
        raise ValueError("timeout must be positive")
    if max_output_bytes < 1:
        raise ValueError("max_output_bytes must be positive")
    if group_grace_seconds < 0:
        raise ValueError("group_grace_seconds must not be negative")

    stdout_capture = _BoundedCapture(max_output_bytes)
    stderr_capture = _BoundedCapture(max_output_bytes)
    process = subprocess.Popen(
        list(argv),
        cwd=cwd,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        close_fds=True,
        start_new_session=True,
    )
    stdout_thread = threading.Thread(
        target=_drain, args=(process.stdout, stdout_capture)
    )
    stderr_thread = threading.Thread(
        target=_drain, args=(process.stderr, stderr_capture)
    )
    stdout_thread.daemon = True
    stderr_thread.daemon = True
    stdout_thread.start()
    stderr_thread.start()

    timed_out = False
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
    finally:
        _terminate_group(process, group_grace_seconds)

    stdout_thread.join(timeout=1.0)
    stderr_thread.join(timeout=1.0)
    if stdout_thread.is_alive() or stderr_thread.is_alive():
        raise RuntimeError("captured process pipes did not close after group cleanup")

    stdout = stdout_capture.text()
    stderr = stderr_capture.text()
    if timed_out:
        raise ProcessTimeout(
            argv,
            timeout,
            stdout,
            stderr,
            stdout_capture.truncated,
            stderr_capture.truncated,
        )
    return ProcessResult(
        argv,
        process.returncode,
        stdout,
        stderr,
        stdout_capture.truncated,
        stderr_capture.truncated,
    )


@contextlib.contextmanager
def readonly_source(source, filename="input.mica", prefix="mica-attempt-"):
    """Materialize one ASCII source in a fresh, read-only attempt directory."""

    if not isinstance(source, str):
        raise TypeError("source must be text")
    if not filename or os.path.basename(filename) != filename:
        raise ValueError("filename must be one path component")

    with tempfile.TemporaryDirectory(prefix=prefix) as directory:
        path = os.path.join(directory, filename)
        with io.open(path, "w", encoding="ascii", newline="") as handle:
            handle.write(source)
        os.chmod(path, 0o444)
        os.chmod(directory, 0o555)
        try:
            yield directory, path
        finally:
            os.chmod(directory, 0o700)
            if os.path.isfile(path) and not os.path.islink(path):
                os.chmod(path, 0o600)


@contextlib.contextmanager
def readonly_scratch(prefix="mica-attempt-"):
    """Create an empty per-attempt directory and freeze it during execution."""

    with tempfile.TemporaryDirectory(prefix=prefix) as directory:
        os.chmod(directory, 0o555)
        try:
            yield directory
        finally:
            os.chmod(directory, 0o700)


def sanitized_environment(scratch_directory):
    """Return the small deterministic environment exposed to a tested binary."""

    return {
        "LANG": "C",
        "LC_ALL": "C",
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "TMPDIR": scratch_directory,
        "TZ": "UTC",
    }
