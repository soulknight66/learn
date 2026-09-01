#!/usr/bin/env python3
"""Sealed black-box conformance tests for the independently generated reference."""

from __future__ import print_function

import os
import subprocess
import sys


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CASES = os.path.join(ROOT, "sealed", "reference_tests", "cases")
META = os.path.join(ROOT, "sealed", "reference", "examples", "meta_vm.mc")
PUBLIC = os.path.join(ROOT, "public_tests", "cases")


def run(executable, arguments):
    return subprocess.run(
        [executable] + arguments,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        timeout=8,
    )


def file_case(name):
    return os.path.join(CASES, name)


def main():
    if len(sys.argv) != 2:
        print("usage: run_tests.py EXECUTABLE", file=sys.stderr)
        return 2
    executable = os.path.abspath(sys.argv[1])
    tests = [
        ("comments-zero", [file_case("comments_and_zero.mc")], 0, "0\n7\n", ""),
        ("forward-call", [file_case("forward_call.mc")], 0, "42\n", ""),
        ("evaluation-order", [file_case("left_to_right.mc")], 0, "1\n2\n42\n", ""),
        ("signed-math", [file_case("signed_math.mc")], 0, "-2\n-1\n-2\n1\n", ""),
        ("recursive", [os.path.join(ROOT, "sealed", "reference", "examples",
                                    "recursive_fibonacci.mc")], 0, "55\n", ""),
        ("nested-interpreter", [META], 0, "42\n", ""),
        ("add-overflow", [file_case("add_overflow.mc")], 70, "", "addition overflow"),
        ("sub-overflow", [file_case("sub_overflow.mc")], 70, "", "subtraction overflow"),
        ("mul-overflow", [file_case("mul_overflow.mc")], 70, "", "multiplication overflow"),
        ("neg-overflow", [file_case("neg_overflow.mc")], 70, "", "negation overflow"),
        ("divide-overflow", [file_case("div_overflow.mc")], 70, "", "division overflow"),
        ("remainder-overflow", [file_case("rem_overflow.mc")], 70, "", "remainder overflow"),
        ("divide-zero", [file_case("divide_zero.mc")], 70, "", "division by zero"),
        ("literal-overflow", [file_case("literal_overflow.mc")], 65, "",
         "literal exceeds"),
        ("unterminated-comment", [file_case("unterminated_comment.mc")], 65, "",
         "unterminated block comment"),
        ("undefined-function", [file_case("undefined_function.mc")], 65, "",
         "undefined function"),
        ("wrong-arity", [file_case("wrong_arity.mc")], 65, "", "expects 2 arguments"),
        ("duplicate-local", [file_case("duplicate_local.mc")], 65, "", "duplicate local"),
        ("missing-main", [file_case("missing_main.mc")], 65, "", "missing function"),
        ("main-parameter", [file_case("main_parameter.mc")], 65, "", "zero parameters"),
        ("frame-limit", [file_case("deep_recursion.mc")], 70, "", "frame capacity"),
        ("step-exact", ["--max-steps", "1", os.path.join(PUBLIC, "arithmetic.mc")],
         70, "", "step limit"),
        ("two-step-success", ["--max-steps", "2", file_case("two_steps.mc")],
         0, "", ""),
        ("usage-zero-budget", ["--max-steps", "0", META], 64, "", "usage:"),
        ("missing-input", [file_case("does_not_exist.mc")], 66, "", "cannot open input"),
    ]
    failures = 0
    for name, arguments, expected_code, expected_out, expected_error in tests:
        try:
            result = run(executable, arguments)
            ok = (result.returncode == expected_code and result.stdout == expected_out and
                  expected_error.lower() in result.stderr.lower())
            if ok:
                print("PASS", name)
            else:
                failures += 1
                print("FAIL", name)
                print("  exit: expected {}, got {}".format(expected_code, result.returncode))
                print("  stdout: expected {!r}, got {!r}".format(expected_out, result.stdout))
                print("  stderr needed {!r}, got {!r}".format(expected_error, result.stderr))
        except (OSError, subprocess.TimeoutExpired) as error:
            failures += 1
            print("FAIL", name, error)
    print("{} passed; {} failed".format(len(tests) - failures, failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
