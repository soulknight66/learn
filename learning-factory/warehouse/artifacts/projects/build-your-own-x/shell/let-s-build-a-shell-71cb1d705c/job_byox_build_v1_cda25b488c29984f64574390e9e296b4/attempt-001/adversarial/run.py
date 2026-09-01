#!/usr/bin/env python3
"""Run minish adversarial inputs with capture and a deadline; provide no oracle."""

from __future__ import print_function

import argparse
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time


HERE = os.path.dirname(os.path.abspath(__file__))
CASE_DIR = os.path.join(HERE, "cases")


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("shell", help="path to the minish executable")
    parser.add_argument("--case", dest="case_name",
                        help="run only this case filename")
    parser.add_argument("--timeout", type=float, default=3.0,
                        help="seconds allowed per case (default: 3)")
    parser.add_argument("--max-output", type=int, default=4000,
                        help="bytes shown per output stream (default: 4000)")
    return parser.parse_args()


def render(data, limit):
    clipped = data[:limit]
    text = clipped.decode("utf-8", "backslashreplace")
    if len(data) > limit:
        text += "\n... {} bytes omitted ...".format(len(data) - limit)
    return text


def session_groups(session_id):
    """Find every process group in a disposable session."""
    try:
        listing = subprocess.run(
            ["ps", "-e", "-o", "sid=", "-o", "pgid="],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            timeout=2,
            check=True)
    except (OSError, subprocess.SubprocessError):
        return {session_id}
    groups = set()
    for row in listing.stdout.splitlines():
        fields = row.split()
        if len(fields) == 2 and fields[0].isdigit() and fields[1].isdigit():
            if int(fields[0]) == session_id and int(fields[1]) > 0:
                groups.add(int(fields[1]))
    return groups


def signal_session(session_id, signal_number):
    """Signal all groups in a session, repeating to narrow fork races."""
    for unused_round in range(3):
        groups = session_groups(session_id)
        if not groups:
            return
        for group in groups:
            try:
                os.killpg(group, signal_number)
            except ProcessLookupError:
                pass
        time.sleep(0.01)


def terminate_session(process):
    signal_session(process.pid, signal.SIGTERM)
    signal_session(process.pid, signal.SIGKILL)


def run_case(shell_path, case_path, timeout, max_output):
    with open(case_path, "rb") as source:
        command_input = source.read()

    workdir = tempfile.mkdtemp(prefix="minish-adversarial-")
    process = None
    timed_out = False
    try:
        process = subprocess.Popen(
            [shell_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=workdir,
            start_new_session=True)
        try:
            stdout, stderr = process.communicate(command_input, timeout=timeout)
        except subprocess.TimeoutExpired as expired:
            timed_out = True
            terminate_session(process)
            try:
                process.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=1.0)
            stdout = expired.output or b""
            stderr = expired.stderr or b""
            for stream in (process.stdin, process.stdout, process.stderr):
                if stream is not None and not stream.closed:
                    stream.close()
    finally:
        shutil.rmtree(workdir)

    name = os.path.basename(case_path)
    if timed_out:
        outcome = "TIMEOUT"
    elif process.returncode < 0:
        outcome = "SIGNALED({})".format(-process.returncode)
    elif process.returncode == 0:
        outcome = "completed(status=0)"
    else:
        outcome = "nonzero(status={})".format(process.returncode)

    print("=== {}: {} ===".format(name, outcome))
    print("--- stdout ({} bytes) ---".format(len(stdout)))
    print(render(stdout, max_output))
    print("--- stderr ({} bytes) ---".format(len(stderr)))
    print(render(stderr, max_output))
    return timed_out or process.returncode < 0


def main():
    args = parse_args()
    if args.timeout <= 0 or args.max_output < 0:
        print("timeout must be positive and max-output nonnegative", file=sys.stderr)
        return 2

    shell_path = os.path.abspath(args.shell)
    if not os.path.isfile(shell_path) or not os.access(shell_path, os.X_OK):
        print("not an executable file: {}".format(shell_path), file=sys.stderr)
        return 2

    if args.case_name:
        if os.path.basename(args.case_name) != args.case_name:
            print("--case must be a filename from adversarial/cases", file=sys.stderr)
            return 2
        case_paths = [os.path.join(CASE_DIR, args.case_name)]
    else:
        case_paths = [os.path.join(CASE_DIR, name)
                      for name in sorted(os.listdir(CASE_DIR))
                      if name.endswith(".minish")]

    missing = [path for path in case_paths if not os.path.isfile(path)]
    if missing:
        print("case not found: {}".format(missing[0]), file=sys.stderr)
        return 2

    severe_failure = False
    for case_path in case_paths:
        if run_case(shell_path, case_path, args.timeout, args.max_output):
            severe_failure = True
    return 1 if severe_failure else 0


if __name__ == "__main__":
    sys.exit(main())
