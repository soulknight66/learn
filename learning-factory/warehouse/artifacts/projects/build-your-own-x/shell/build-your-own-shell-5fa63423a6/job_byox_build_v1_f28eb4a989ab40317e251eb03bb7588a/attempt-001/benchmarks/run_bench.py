#!/usr/bin/env python3
"""Bounded local timing harness for byosh; emits no precomputed results."""

from __future__ import print_function

import argparse
import hashlib
import json
import math
import os
import errno
import signal
import shutil
import statistics
import subprocess
import sys
import tempfile
import time


PS_TIMEOUT_SECONDS = 0.5
REAP_TIMEOUT_SECONDS = 1.0
SESSION_CLEANUP_PASSES = 4
DIAGNOSTIC_BYTES = 4000


def positive_integer(value):
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def nonnegative_integer(value):
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must not be negative")
    return parsed


def file_sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as source:
        while True:
            block = source.read(65536)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def require_tool(name):
    path = shutil.which(name)
    if path is None:
        raise RuntimeError("required utility is not available on PATH: {0}".format(name))
    return os.path.abspath(path)


def shell_quote(value):
    return "'" + value.replace("'", "'\\''") + "'"


def kill_helper(process):
    errors = []
    if process.poll() is not None:
        return errors
    try:
        if os.getsid(process.pid) == process.pid:
            os.killpg(process.pid, signal.SIGKILL)
        else:
            process.kill()
    except OSError as error:
        if error.errno != errno.ESRCH:
            errors.append("killpg: {0}".format(error))
    try:
        process.kill()
    except OSError as error:
        if error.errno != errno.ESRCH:
            errors.append("kill: {0}".format(error))
    return errors


def session_members(ps_path, session_id):
    process = subprocess.Popen(
        [
            ps_path,
            "-o",
            "pid=",
            "-o",
            "sid=",
            "-o",
            "stat=",
            "--sid",
            str(session_id),
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    try:
        output, standard_error = process.communicate(timeout=PS_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        errors = kill_helper(process)
        try:
            process.communicate(timeout=REAP_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            errors.append("helper could not be reaped within the cleanup timeout")
        detail = b"; ".join(
            item.encode("utf-8", "replace") for item in errors
        ).decode("utf-8", "replace")
        if detail:
            detail = ": " + detail
        raise RuntimeError("ps timed out while enumerating the sample session{0}".format(detail))

    if (process.returncode == 1 and not output.strip()
            and not standard_error.strip()):
        return []
    if process.returncode != 0:
        raise RuntimeError(
            "ps exited {0} while enumerating the sample session: {1}".format(
                process.returncode,
                standard_error.decode("utf-8", "replace").strip(),
            )
        )

    members = []
    for line in output.splitlines():
        fields = line.split()
        if len(fields) < 3:
            continue
        try:
            pid = int(fields[0])
            row_session_id = int(fields[1])
        except ValueError:
            continue
        if row_session_id == session_id:
            members.append((pid, fields[2].decode("ascii", "replace")))
    return members


def signal_session_process(pid, session_id):
    try:
        current_session_id = os.getsid(pid)
    except OSError as error:
        if error.errno == errno.ESRCH:
            return None
        return "getsid({0}): {1}".format(pid, error)
    if current_session_id != session_id:
        return "refused to signal reused pid {0}".format(pid)
    try:
        os.kill(pid, signal.SIGKILL)
    except OSError as error:
        if error.errno != errno.ESRCH:
            return "kill({0}): {1}".format(pid, error)
    return None


def fallback_kill(process, session_id):
    errors = [
        "scoped session enumeration failed; descendant cleanup is unverified"
    ]
    if process.poll() is None:
        error = signal_session_process(process.pid, session_id)
        if error:
            errors.append(error)
    return errors


def terminate_session(process, session_id, ps_path):
    notes = []
    for unused_pass in range(SESSION_CLEANUP_PASSES):
        try:
            rows = session_members(ps_path, session_id)
        except RuntimeError as error:
            notes.append(str(error))
            notes.extend(fallback_kill(process, session_id))
            return notes

        live_pids = [pid for pid, state in rows if not state.startswith("Z")]
        if process.poll() is None and process.pid not in live_pids:
            live_pids.append(process.pid)
        if not live_pids:
            return notes
        live_pids.sort(key=lambda pid: 0 if pid == session_id else 1)
        for pid in live_pids:
            error = signal_session_process(pid, session_id)
            if error:
                notes.append(error)

    try:
        rows = session_members(ps_path, session_id)
    except RuntimeError as error:
        notes.append(str(error))
        notes.extend(fallback_kill(process, session_id))
        return notes
    survivors = [pid for pid, state in rows if not state.startswith("Z")]
    for pid in survivors:
        error = signal_session_process(pid, session_id)
        if error:
            notes.append(error)
    if survivors:
        notes.append("session still listed live pids after cleanup: {0}".format(survivors))
    return notes


def reap_target(process, session_id):
    try:
        return process.communicate(timeout=REAP_TIMEOUT_SECONDS), []
    except subprocess.TimeoutExpired as error:
        notes = ["target did not reap within the first cleanup timeout"]
        if process.poll() is None:
            target_error = signal_session_process(process.pid, session_id)
            if target_error:
                notes.append(target_error)
        try:
            return process.communicate(timeout=REAP_TIMEOUT_SECONDS), notes
        except subprocess.TimeoutExpired:
            notes.append("target could not be reaped within the final cleanup timeout")
            return (getattr(error, "output", None), getattr(error, "stderr", None)), notes


def diagnostic_tail(value):
    if value is None:
        return "<not captured>"
    if not isinstance(value, bytes):
        value = value.encode("utf-8", "replace")
    return value[-DIAGNOSTIC_BYTES:].decode("utf-8", "replace")


def run_once(shell_path, specification, timeout_seconds, working_directory, ps_path):
    command = [shell_path] + specification["arguments"]
    payload = specification.get("stdin")
    standard_input = subprocess.PIPE if payload is not None else subprocess.DEVNULL
    with tempfile.TemporaryDirectory(
        prefix="sample-", dir=working_directory
    ) as sample_directory:
        started = time.perf_counter()
        process = subprocess.Popen(
            command,
            cwd=sample_directory,
            stdin=standard_input,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        try:
            unused_stdout, standard_error = process.communicate(
                input=payload, timeout=timeout_seconds
            )
        except subprocess.TimeoutExpired as error:
            notes = terminate_session(process, process.pid, ps_path)
            (unused_stdout, standard_error), reap_notes = reap_target(
                process, process.pid
            )
            notes.extend(reap_notes)
            if standard_error is None:
                standard_error = getattr(error, "stderr", None)
            raise RuntimeError(
                "workload {0} exceeded {1:.3f}s; stderr tail: {2}; cleanup: {3}".format(
                    specification["name"],
                    timeout_seconds,
                    diagnostic_tail(standard_error),
                    "; ".join(notes) if notes else "complete",
                )
            )
        except Exception:
            terminate_session(process, process.pid, ps_path)
            reap_target(process, process.pid)
            raise
        elapsed = time.perf_counter() - started
        try:
            rows = session_members(ps_path, process.pid)
        except RuntimeError:
            terminate_session(process, process.pid, ps_path)
            raise
        live_pids = [pid for pid, state in rows if not state.startswith("Z")]
        if live_pids:
            notes = terminate_session(process, process.pid, ps_path)
            raise RuntimeError(
                "workload {0} left live session processes {1}; cleanup: {2}".format(
                    specification["name"],
                    live_pids,
                    "; ".join(notes) if notes else "complete",
                )
            )
        if process.returncode != 0:
            raise RuntimeError(
                "workload {0} exited {1}: {2}".format(
                    specification["name"],
                    process.returncode,
                    diagnostic_tail(standard_error),
                )
            )
        return elapsed


def percentile_95(samples):
    ordered = sorted(samples)
    index = max(0, int(math.ceil(0.95 * len(ordered))) - 1)
    return ordered[index]


def summarize(raw_samples, operations):
    normalized = [sample / operations for sample in raw_samples]
    return {
        "operations_per_invocation": operations,
        "invocation_seconds": {
            "samples": raw_samples,
            "minimum": min(raw_samples),
            "median": statistics.median(raw_samples),
            "mean": statistics.mean(raw_samples),
            "p95_nearest_rank": percentile_95(raw_samples),
        },
        "seconds_per_operation": {
            "samples": normalized,
            "median": statistics.median(normalized),
        },
    }


def workload_definitions(tools):
    quoted_null = shell_quote(os.devnull)
    quoted_printf = shell_quote(tools["printf"])
    quote_line = os.fsencode(
        "{0} '%s\\n' 'a b' \"c d\" e\\ f > {1}\n".format(
            quoted_printf, quoted_null
        )
    )
    return [
        {
            "name": "cold_builtin",
            "arguments": ["-c", "pwd > {0}".format(quoted_null)],
            "operations": 1,
        },
        {
            "name": "cold_external",
            "arguments": ["-c", shell_quote(tools["true"])],
            "operations": 1,
        },
        {
            "name": "cold_pipeline",
            "arguments": [
                "-c",
                "{0} x | {1} > {2}".format(
                    quoted_printf, shell_quote(tools["cat"]), quoted_null
                ),
            ],
            "operations": 1,
        },
        {
            "name": "batch_builtins",
            "arguments": [],
            "stdin": os.fsencode("pwd > {0}\n".format(quoted_null)) * 100,
            "operations": 100,
        },
        {
            "name": "batch_quote_parse",
            "arguments": [],
            "stdin": quote_line * 100,
            "operations": 100,
        },
    ]


def parse_arguments(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shell", default="./sealed/reference/byosh")
    parser.add_argument("--warmups", type=nonnegative_integer, default=3)
    parser.add_argument("--iterations", type=positive_integer, default=20)
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument("--output", help="write JSON here instead of stdout")
    arguments = parser.parse_args(argv)
    if arguments.timeout <= 0.0:
        parser.error("--timeout must be greater than zero")
    if arguments.iterations > 10000 or arguments.warmups > 10000:
        parser.error("iteration counts above 10000 are refused")
    return arguments


def main(argv):
    arguments = parse_arguments(argv)
    shell_path = os.path.abspath(arguments.shell)
    if not os.path.isfile(shell_path):
        raise RuntimeError("shell is not a regular file: {0}".format(shell_path))
    if not os.access(shell_path, os.X_OK):
        raise RuntimeError("shell is not executable: {0}".format(shell_path))

    tools = dict(
        (name, require_tool(name)) for name in ("cat", "printf", "ps", "true")
    )

    workloads = workload_definitions(tools)
    samples = dict((item["name"], []) for item in workloads)

    with tempfile.TemporaryDirectory(prefix="byosh-benchmark-") as scratch:
        for warmup_index in range(arguments.warmups):
            for offset in range(len(workloads)):
                item = workloads[(warmup_index + offset) % len(workloads)]
                run_once(shell_path, item, arguments.timeout, scratch, tools["ps"])

        for iteration in range(arguments.iterations):
            for offset in range(len(workloads)):
                item = workloads[(iteration + offset) % len(workloads)]
                elapsed = run_once(
                    shell_path, item, arguments.timeout, scratch, tools["ps"]
                )
                samples[item["name"]].append(elapsed)

    report = {
        "schema_version": 1,
        "classification": "unvalidated local measurement",
        "clock": "time.perf_counter",
        "target": {
            "path": shell_path,
            "sha256": file_sha256(shell_path),
        },
        "parameters": {
            "warmups": arguments.warmups,
            "iterations": arguments.iterations,
            "timeout_seconds": arguments.timeout,
        },
        "workloads": {},
    }
    for item in workloads:
        report["workloads"][item["name"]] = summarize(
            samples[item["name"]], item["operations"]
        )

    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if arguments.output:
        with open(arguments.output, "w") as destination:
            destination.write(rendered)
    else:
        sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except (OSError, RuntimeError, ValueError) as error:
        print("benchmark error: {0}".format(error), file=sys.stderr)
        sys.exit(2)
