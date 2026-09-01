#!/usr/bin/env python3
"""Small dependency-free black-box suite for a Mini-C executable."""

from __future__ import print_function

import os
import subprocess
import sys


HERE = os.path.dirname(os.path.abspath(__file__))
CASES = os.path.join(HERE, "cases")


def invoke(executable, arguments):
    return subprocess.run(
        [executable] + arguments,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        timeout=5,
    )


def main():
    if len(sys.argv) != 2:
        print("usage: run_tests.py EXECUTABLE", file=sys.stderr)
        return 2
    executable = os.path.abspath(sys.argv[1])
    checks = [
        ("arithmetic", [os.path.join(CASES, "arithmetic.mc")], 0, "14\n20\n", None),
        ("control", [os.path.join(CASES, "control.mc")], 0, "120\n", None),
        ("functions", [os.path.join(CASES, "functions.mc")], 0, "42\n", None),
        ("short-circuit", [os.path.join(CASES, "short_circuit.mc")], 0, "0\n1\n", None),
        ("syntax-error", [os.path.join(CASES, "bad_syntax.mc")], 65, "", "expected"),
        ("step-limit", ["--max-steps", "20", os.path.join(CASES, "infinite.mc")],
         70, "", "step limit"),
    ]
    failures = 0
    for name, arguments, returncode, stdout, stderr_fragment in checks:
        try:
            result = invoke(executable, arguments)
            ok = result.returncode == returncode and result.stdout == stdout
            if stderr_fragment is not None:
                ok = ok and stderr_fragment in result.stderr.lower()
            if ok:
                print("PASS", name)
            else:
                failures += 1
                print("FAIL", name)
                print("  exit: expected {}, got {}".format(returncode, result.returncode))
                print("  stdout: expected {!r}, got {!r}".format(stdout, result.stdout))
                if stderr_fragment is not None:
                    print("  stderr needed {!r}, got {!r}".format(
                        stderr_fragment, result.stderr))
        except (OSError, subprocess.TimeoutExpired) as error:
            failures += 1
            print("FAIL", name, error)
    print("{} passed; {} failed".format(len(checks) - failures, failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
