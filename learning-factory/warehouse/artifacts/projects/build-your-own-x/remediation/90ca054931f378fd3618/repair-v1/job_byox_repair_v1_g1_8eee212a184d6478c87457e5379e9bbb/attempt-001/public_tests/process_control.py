#!/usr/bin/env python3
"""POSIX subprocess containment shared by the black-box test runners."""

from __future__ import print_function

import errno
import math
import os
import resource
import signal
import subprocess
import tempfile
import time


CAPTURE_LIMIT = 65536
ADDRESS_SPACE_LIMIT = 256 * 1024 * 1024
OPEN_FILE_LIMIT = 64


class BoundedResult(object):
    """A small CompletedProcess-like result with containment metadata."""

    def __init__(self, returncode, stdout, stderr, timed_out,
                 stdout_truncated, stderr_truncated, elapsed):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.timed_out = timed_out
        self.stdout_truncated = stdout_truncated
        self.stderr_truncated = stderr_truncated
        self.elapsed = elapsed


class SuiteBudgetExpired(Exception):
    """Raised before starting a case when the aggregate wall budget is spent."""


class SuiteDeadline(object):
    """Cap aggregate suite wall time in addition to per-case time."""

    def __init__(self, seconds):
        if seconds <= 0:
            raise ValueError("suite deadline must be positive")
        self._deadline = time.monotonic() + seconds

    def case_timeout(self, per_case_seconds):
        remaining = self._deadline - time.monotonic()
        if remaining <= 0:
            raise SuiteBudgetExpired("aggregate suite wall-time limit reached")
        return min(per_case_seconds, remaining)


def _set_limit(limit_name, requested):
    limit = getattr(resource, limit_name, None)
    if limit is None:
        return
    unused_soft, hard = resource.getrlimit(limit)
    del unused_soft
    value = requested
    if hard != resource.RLIM_INFINITY:
        value = min(value, hard)
    resource.setrlimit(limit, (value, value))


def _child_limits(timeout):
    cpu_seconds = max(1, int(math.ceil(timeout)) + 1)
    _set_limit("RLIMIT_CORE", 0)
    _set_limit("RLIMIT_FSIZE", CAPTURE_LIMIT)
    _set_limit("RLIMIT_AS", ADDRESS_SPACE_LIMIT)
    _set_limit("RLIMIT_NOFILE", OPEN_FILE_LIMIT)
    _set_limit("RLIMIT_CPU", cpu_seconds)


def _kill_process_group(group_id):
    try:
        os.killpg(group_id, signal.SIGKILL)
    except OSError as error:
        if error.errno != errno.ESRCH:
            raise


def _read_capture(stream):
    stream.seek(0)
    data = stream.read(CAPTURE_LIMIT)
    truncated = len(data) == CAPTURE_LIMIT
    return data.decode("utf-8", "replace"), truncated


def run_bounded(argv, timeout, scratch_directory=None):
    """Run argv in a new session, bound resources, and clean its process group."""
    if not argv:
        raise ValueError("argv must not be empty")
    if timeout <= 0:
        raise ValueError("timeout must be positive")

    started = time.monotonic()
    timed_out = False
    with tempfile.TemporaryFile(mode="w+b", dir=scratch_directory) as stdout_file:
        with tempfile.TemporaryFile(mode="w+b", dir=scratch_directory) as stderr_file:
            process = subprocess.Popen(
                list(argv),
                stdin=subprocess.DEVNULL,
                stdout=stdout_file,
                stderr=stderr_file,
                close_fds=True,
                start_new_session=True,
                preexec_fn=lambda: _child_limits(timeout),
            )
            try:
                process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
                _kill_process_group(process.pid)
                process.wait()
            else:
                # A direct child may exit while descendants retain the group.
                _kill_process_group(process.pid)

            stdout, stdout_truncated = _read_capture(stdout_file)
            stderr, stderr_truncated = _read_capture(stderr_file)

    return BoundedResult(
        process.returncode,
        stdout,
        stderr,
        timed_out,
        stdout_truncated,
        stderr_truncated,
        time.monotonic() - started,
    )
