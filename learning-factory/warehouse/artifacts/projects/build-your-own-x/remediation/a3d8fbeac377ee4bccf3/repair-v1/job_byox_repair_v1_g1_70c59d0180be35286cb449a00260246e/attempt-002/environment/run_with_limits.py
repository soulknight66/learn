#!/usr/bin/env python3
"""Command-line adapter for environment.harness.run_process."""

import argparse
import os
import sys

try:
    from environment.harness import ProcessTimeout, run_process
except ImportError:
    from harness import ProcessTimeout, run_process


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeout", required=True, type=float)
    parser.add_argument("--max-output-bytes", type=int, default=131072)
    parser.add_argument("--cwd", default=None)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = list(args.command)
    if command and command[0] == "--":
        command.pop(0)
    if not command:
        parser.error("a command is required after --")
    if args.cwd is not None and not os.path.isdir(args.cwd):
        parser.error("--cwd must name a directory")

    try:
        result = run_process(
            command,
            timeout=args.timeout,
            cwd=args.cwd,
            max_output_bytes=args.max_output_bytes,
        )
    except ProcessTimeout as error:
        sys.stdout.write(error.stdout)
        sys.stderr.write(error.stderr)
        sys.stderr.write("worker deadline exceeded after {:.3f}s\n".format(error.timeout))
        return 124
    except OSError as error:
        sys.stderr.write("unable to execute command: {}\n".format(error))
        return 127

    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    if result.stdout_truncated:
        sys.stderr.write("worker stdout was truncated at {} bytes\n".format(args.max_output_bytes))
    if result.stderr_truncated:
        sys.stderr.write("worker stderr was truncated at {} bytes\n".format(args.max_output_bytes))
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
