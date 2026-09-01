#!/usr/bin/env python3
"""Small dependency-free black-box suite for a Mini-C executable."""

from __future__ import print_function

import os
import subprocess
import sys

from process_control import (SuiteBudgetExpired, SuiteDeadline, run_bounded)


HERE = os.path.dirname(os.path.abspath(__file__))
CASES = os.path.join(HERE, "cases")
ROOT = os.path.dirname(HERE)


def invoke(executable, arguments, timeout):
    return run_bounded([executable] + arguments, timeout, ROOT)


def preview(text):
    if len(text) <= 500:
        return repr(text)
    return repr(text[:500] + "...[runner display truncated]")


def main():
    if len(sys.argv) != 2:
        print("usage: run_tests.py EXECUTABLE", file=sys.stderr)
        return 2
    executable = os.path.abspath(sys.argv[1])
    arithmetic = os.path.join(CASES, "arithmetic.mc")
    checks = [
        ("arithmetic", [arithmetic], 0, "14\n20\n", None),
        ("control", [os.path.join(CASES, "control.mc")], 0, "120\n", None),
        ("functions", [os.path.join(CASES, "functions.mc")], 0, "42\n", None),
        ("short-circuit", [os.path.join(CASES, "short_circuit.mc")], 0, "0\n1\n", None),
        ("syntax-error", [os.path.join(CASES, "bad_syntax.mc")], 65, "", "expected"),
        ("step-limit", ["--max-steps", "20", os.path.join(CASES, "infinite.mc")],
         70, "", "step limit"),
        ("usage-plus-budget", ["--max-steps", "+1", arithmetic], 64, "", "usage:"),
        ("usage-minus-budget", ["--max-steps", "-1", arithmetic], 64, "", "usage:"),
        ("usage-space-budget", ["--max-steps", " 1", arithmetic], 64, "", "usage:"),
        ("usage-trailing-space-budget", ["--max-steps", "1 ", arithmetic], 64, "",
         "usage:"),
        ("usage-zero-budget", ["--max-steps", "0", arithmetic], 64, "", "usage:"),
        ("usage-overflow-budget",
         ["--max-steps", "18446744073709551616", arithmetic], 64, "", "usage:"),
        ("usage-empty-budget", ["--max-steps", "", arithmetic], 64, "", "usage:"),
        ("usage-nondigit-budget", ["--max-steps", "1x", arithmetic], 64, "", "usage:"),
        ("usage-missing-value", ["--max-steps"], 64, "", "usage:"),
        ("usage-missing-source", ["--max-steps", "1"], 64, "", "usage:"),
        ("usage-unknown-option", ["--unknown"], 64, "", "usage:"),
        ("usage-extra-argument", [arithmetic, arithmetic], 64, "", "usage:"),
    ]
    failures = 0
    deadline = SuiteDeadline(90)
    for name, arguments, returncode, stdout, stderr_fragment in checks:
        try:
            result = invoke(executable, arguments, deadline.case_timeout(5))
            ok = (not result.timed_out and not result.stdout_truncated and
                  not result.stderr_truncated and result.returncode == returncode and
                  result.stdout == stdout)
            if stderr_fragment is not None:
                ok = ok and stderr_fragment in result.stderr.lower()
            if ok:
                print("PASS", name)
            else:
                failures += 1
                print("FAIL", name)
                if result.timed_out:
                    print("  timed out after {:.3f}s".format(result.elapsed))
                if result.stdout_truncated or result.stderr_truncated:
                    print("  captured output reached the 65536-byte per-stream limit")
                print("  exit: expected {}, got {}".format(returncode, result.returncode))
                print("  stdout: expected {!r}, got {}".format(stdout, preview(result.stdout)))
                if stderr_fragment is not None:
                    print("  stderr needed {!r}, got {}".format(
                        stderr_fragment, preview(result.stderr)))
        except SuiteBudgetExpired as error:
            failures += 1
            print("FAIL", name, error)
        except (OSError, subprocess.SubprocessError) as error:
            failures += 1
            print("FAIL", name, error)
    print("{} passed; {} failed".format(len(checks) - failures, failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
