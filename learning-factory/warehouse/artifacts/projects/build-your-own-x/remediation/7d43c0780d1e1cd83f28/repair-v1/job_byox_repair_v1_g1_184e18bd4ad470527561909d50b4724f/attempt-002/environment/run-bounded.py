#!/usr/bin/env python3
"""Run one argv command with a process-group deadline and bounded captured output."""

import argparse
import errno
import os
import select
import signal
import subprocess
import sys
import time


MAX_OUTPUT_BYTES = 2 * 1024 * 1024
TERMINATION_GRACE_SECONDS = 1.0


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('seconds', type=float, help='wall-clock deadline from 1 through 3600 seconds')
    parser.add_argument('command', nargs=argparse.REMAINDER, help='argv command, conventionally after --')
    args = parser.parse_args(argv)
    if not 1 <= args.seconds <= 3600:
        parser.error('seconds must be from 1 through 3600')
    if args.command and args.command[0] == '--':
        args.command = args.command[1:]
    if not args.command:
        parser.error('a command is required after --')
    return args


def signal_group(process, requested_signal):
    try:
        os.killpg(process.pid, requested_signal)
    except OSError as error:
        if error.errno != errno.ESRCH:
            raise


def stop_group(process):
    signal_group(process, signal.SIGTERM)
    grace_deadline = time.monotonic() + TERMINATION_GRACE_SECONDS
    while process.poll() is None and time.monotonic() < grace_deadline:
        time.sleep(0.01)
    if process.poll() is None:
        signal_group(process, signal.SIGKILL)


def append_bounded(captured, block):
    remaining = MAX_OUTPUT_BYTES - len(captured)
    if len(block) > remaining:
        captured.extend(block[:remaining])
        return False
    captured.extend(block)
    return True


def drain_ready(file_descriptor, captured):
    """Read one available block; return (eof, within_limit)."""
    block = os.read(file_descriptor, 65536)
    if not block:
        return True, True
    return False, append_bounded(captured, block)


def run(args):
    try:
        process = subprocess.Popen(
            args.command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    except FileNotFoundError:
        print('[runner] command not found: {}'.format(args.command[0]), file=sys.stderr)
        return 127
    except PermissionError:
        print('[runner] command is not executable: {}'.format(args.command[0]), file=sys.stderr)
        return 126

    captured = bytearray()
    file_descriptor = process.stdout.fileno()
    deadline = time.monotonic() + args.seconds
    eof = False
    stopped_for = None

    while not eof:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            stopped_for = 'timeout'
            break
        readable, _, _ = select.select([file_descriptor], [], [], min(remaining, 0.1))
        if readable:
            eof, within_limit = drain_ready(file_descriptor, captured)
            if not within_limit:
                stopped_for = 'output limit'
                break
        elif process.poll() is not None:
            # The process exited; a descendant may still hold the pipe. Keep the
            # overall deadline authoritative rather than waiting indefinitely.
            continue

    if stopped_for is not None:
        stop_group(process)

    # Drain only data already ready after exit/termination. The same byte ceiling
    # remains in force, and this loop never waits longer than the termination grace.
    drain_deadline = time.monotonic() + TERMINATION_GRACE_SECONDS
    while not eof and time.monotonic() < drain_deadline:
        readable, _, _ = select.select([file_descriptor], [], [], 0.05)
        if not readable:
            if process.poll() is not None:
                break
            continue
        eof, within_limit = drain_ready(file_descriptor, captured)
        if not within_limit:
            stopped_for = stopped_for or 'output limit'
            stop_group(process)
            break

    sys.stdout.buffer.write(bytes(captured))
    sys.stdout.buffer.flush()

    if stopped_for == 'timeout':
        print('[runner] wall-clock deadline exceeded: {} seconds'.format(args.seconds), file=sys.stderr)
        return 124
    if stopped_for == 'output limit':
        print('[runner] captured output exceeded {} bytes'.format(MAX_OUTPUT_BYTES), file=sys.stderr)
        return 125

    return_code = process.poll()
    if return_code is None:
        stop_group(process)
        print('[runner] process group did not exit cleanly', file=sys.stderr)
        return 124
    if return_code < 0:
        return 128 + (-return_code)
    return return_code


def main(argv=None):
    return run(parse_args(argv))


if __name__ == '__main__':
    sys.exit(main())
