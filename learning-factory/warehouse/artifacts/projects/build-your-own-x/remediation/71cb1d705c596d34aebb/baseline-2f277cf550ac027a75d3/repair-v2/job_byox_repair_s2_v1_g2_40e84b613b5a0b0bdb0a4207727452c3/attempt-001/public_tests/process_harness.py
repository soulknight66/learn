#!/usr/bin/env python3
"""Bounded argv-only subprocess runner with process-group cleanup."""

import os
import signal
import subprocess
import time


def _signal_group(process, signal_number):
    try:
        os.killpg(process.pid, signal_number)
    except ProcessLookupError:
        pass


def _group_exists(process):
    try:
        os.killpg(process.pid, 0)
    except ProcessLookupError:
        return False
    return True


def _wait_for_group_exit(process, timeout):
    deadline = time.monotonic() + timeout
    while _group_exists(process):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return False
        time.sleep(min(0.02, remaining))
    return True


def _cleanup_after_timeout(process, expired):
    output = expired.output
    errors = expired.stderr
    communication_complete = False

    _signal_group(process, signal.SIGTERM)
    try:
        output, errors = process.communicate(timeout=0.5)
        communication_complete = True
    except subprocess.TimeoutExpired as cleanup_error:
        output = cleanup_error.output
        errors = cleanup_error.stderr

    if _group_exists(process):
        _signal_group(process, signal.SIGKILL)
    if process.poll() is None:
        process.kill()
    if not communication_complete:
        try:
            output, errors = process.communicate(timeout=1.0)
        except subprocess.TimeoutExpired as cleanup_error:
            output = cleanup_error.output
            errors = cleanup_error.stderr
            if process.poll() is None:
                process.kill()
            try:
                process.wait(timeout=0.25)
            except subprocess.TimeoutExpired:
                pass
        for stream in (process.stdout, process.stderr):
            if stream is not None:
                stream.close()
    _wait_for_group_exit(process, 0.5)
    return output, errors


def run_process(
    argv,
    *,
    input=None,
    text=False,
    cwd=None,
    env=None,
    timeout,
    check=False,
    stdin=None,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    preexec_fn=None,
):
    """Run argv in a new session and contain its group when the deadline expires."""
    if input is not None:
        if stdin is not None:
            raise ValueError("stdin and input arguments may not both be used")
        stdin = subprocess.PIPE
    process = subprocess.Popen(
        argv,
        stdin=stdin,
        stdout=stdout,
        stderr=stderr,
        text=text,
        cwd=cwd,
        env=env,
        preexec_fn=preexec_fn,
        start_new_session=True,
    )
    try:
        output, errors = process.communicate(input=input, timeout=timeout)
    except subprocess.TimeoutExpired as expired:
        output, errors = _cleanup_after_timeout(process, expired)
        raise subprocess.TimeoutExpired(
            argv, timeout, output=output, stderr=errors
        ) from None

    result = subprocess.CompletedProcess(argv, process.returncode, output, errors)
    if check:
        result.check_returncode()
    return result
