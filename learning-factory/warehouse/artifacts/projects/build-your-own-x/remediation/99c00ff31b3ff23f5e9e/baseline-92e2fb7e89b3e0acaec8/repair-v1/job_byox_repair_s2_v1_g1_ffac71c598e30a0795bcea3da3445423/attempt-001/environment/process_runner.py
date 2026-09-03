#!/usr/bin/env python3
"""Run one argv-only child in a contained process group with bounded capture."""

import os
import selectors
import signal
import subprocess
import time


CAPTURE_LIMIT = 64 * 1024
TERMINATE_GRACE_SECONDS = 0.25
_READ_SIZE = 8192


def _signal_group(process_group, signal_number):
    try:
        os.killpg(process_group, signal_number)
    except ProcessLookupError:
        pass


def _group_exists(process_group):
    try:
        os.killpg(process_group, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _read_ready(selector, buffers, truncated, capture_limit, wait):
    for key, _ in selector.select(wait):
        stream = key.fileobj
        name = key.data
        try:
            chunk = os.read(stream.fileno(), _READ_SIZE)
        except BlockingIOError:
            continue
        if not chunk:
            selector.unregister(stream)
            stream.close()
            continue
        remaining = capture_limit - len(buffers[name])
        if remaining > 0:
            buffers[name].extend(chunk[:remaining])
        if len(chunk) > remaining:
            truncated[name] = True


def _drain_until(selector, buffers, truncated, capture_limit, deadline):
    while selector.get_map():
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        _read_ready(selector, buffers, truncated, capture_limit, remaining)


def _terminate_group(process, selector, buffers, truncated, capture_limit):
    process_group = process.pid
    _signal_group(process_group, signal.SIGTERM)
    grace_deadline = time.monotonic() + TERMINATE_GRACE_SECONDS
    _drain_until(selector, buffers, truncated, capture_limit, grace_deadline)
    while process.poll() is None and time.monotonic() < grace_deadline:
        time.sleep(0.01)

    if process.poll() is None or _group_exists(process_group):
        _signal_group(process_group, signal.SIGKILL)
    kill_deadline = time.monotonic() + TERMINATE_GRACE_SECONDS
    _drain_until(selector, buffers, truncated, capture_limit, kill_deadline)
    try:
        process.wait(timeout=max(0.0, kill_deadline - time.monotonic()))
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()

    for key in list(selector.get_map().values()):
        selector.unregister(key.fileobj)
        key.fileobj.close()


def _decoded(buffer):
    return bytes(buffer).decode("utf-8", errors="replace")


def run(argv, timeout=5.0, cwd=None, env=None, stdout=None,
        capture_limit=CAPTURE_LIMIT):
    """Return a CompletedProcess; clean the whole child group on every exit.

    Standard error and, by default, standard output are retained only up to
    ``capture_limit`` bytes per stream. Extra bytes are drained and discarded
    so a verbose child cannot block on a full pipe or grow harness memory.
    ``stdout`` may be an already-open binary sink for output-failure tests.
    """
    if not isinstance(argv, (list, tuple)) or not argv:
        raise ValueError("argv must be a non-empty list or tuple")
    if timeout <= 0:
        raise ValueError("timeout must be positive")
    if capture_limit < 0:
        raise ValueError("capture_limit must be nonnegative")

    normalized_argv = [os.fspath(argument) for argument in argv]
    capture_stdout = stdout is None
    process = subprocess.Popen(
        normalized_argv,
        cwd=os.fspath(cwd) if cwd is not None else None,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE if capture_stdout else stdout,
        stderr=subprocess.PIPE,
        close_fds=True,
        start_new_session=True,
    )
    selector = selectors.DefaultSelector()
    buffers = {"stdout": bytearray(), "stderr": bytearray()}
    truncated = {"stdout": False, "stderr": False}
    if capture_stdout:
        os.set_blocking(process.stdout.fileno(), False)
        selector.register(process.stdout, selectors.EVENT_READ, "stdout")
    os.set_blocking(process.stderr.fileno(), False)
    selector.register(process.stderr, selectors.EVENT_READ, "stderr")

    deadline = time.monotonic() + timeout
    timed_out = False
    while selector.get_map() or process.poll() is None:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            timed_out = True
            break
        if selector.get_map():
            _read_ready(selector, buffers, truncated, capture_limit, remaining)
        else:
            try:
                process.wait(timeout=remaining)
            except subprocess.TimeoutExpired:
                timed_out = True
            break

    if timed_out:
        _terminate_group(process, selector, buffers, truncated, capture_limit)
        output = _decoded(buffers["stdout"]) if capture_stdout else None
        error = _decoded(buffers["stderr"])
        raise subprocess.TimeoutExpired(
            normalized_argv, timeout, output=output, stderr=error)

    returncode = process.wait()
    if _group_exists(process.pid):
        _terminate_group(process, selector, buffers, truncated, capture_limit)
    selector.close()

    result = subprocess.CompletedProcess(
        normalized_argv,
        returncode,
        _decoded(buffers["stdout"]) if capture_stdout else None,
        _decoded(buffers["stderr"]),
    )
    result.stdout_truncated = truncated["stdout"]
    result.stderr_truncated = truncated["stderr"]
    return result
