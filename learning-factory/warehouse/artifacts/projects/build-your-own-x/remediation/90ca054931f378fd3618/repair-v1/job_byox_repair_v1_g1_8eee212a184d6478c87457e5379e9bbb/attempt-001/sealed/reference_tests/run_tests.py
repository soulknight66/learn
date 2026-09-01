#!/usr/bin/env python3
"""Sealed black-box conformance tests for the independently generated reference."""

from __future__ import print_function

import os
import subprocess
import sys
import tempfile


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CASES = os.path.join(ROOT, "sealed", "reference_tests", "cases")
META = os.path.join(ROOT, "sealed", "reference", "examples", "meta_vm.mc")
PUBLIC = os.path.join(ROOT, "public_tests", "cases")
PUBLIC_TOOLS = os.path.join(ROOT, "public_tests")
if PUBLIC_TOOLS not in sys.path:
    sys.path.insert(0, PUBLIC_TOOLS)

from process_control import (SuiteBudgetExpired, SuiteDeadline, run_bounded)  # noqa: E402


def run(executable, arguments, timeout):
    return run_bounded([executable] + arguments, timeout, ROOT)


def file_case(name):
    return os.path.join(CASES, name)


def generated_case(directory, name, source):
    path = os.path.join(directory, name)
    with open(path, "w") as handle:
        handle.write(source)
    return path


def preview(text):
    if len(text) <= 500:
        return repr(text)
    return repr(text[:500] + "...[runner display truncated]")


def boundary_tests(directory):
    token_exact = generated_case(
        directory,
        "token_exact.mc",
        "int main(){int a;" + "0;" * 32762 + "return 0;}",
    )
    token_over = generated_case(
        directory,
        "token_over.mc",
        "int main(){int a;" + "0;" * 32761 + "!0;return 0;}",
    )
    nesting_exact = generated_case(
        directory,
        "nesting_exact.mc",
        "int main(){print(" + "(" * 512 + "1" + ")" * 512 + ");return 0;}",
    )
    nesting_over = generated_case(
        directory,
        "nesting_over.mc",
        "int main(){print(" + "(" * 513 + "1" + ")" * 513 + ");return 0;}",
    )
    deep_regression = generated_case(
        directory,
        "deep_regression.mc",
        "int main(){print(" + "(" * 32760 + "1" + ")" * 32760 + ");return 0;}",
    )
    unary_regression = generated_case(
        directory,
        "unary_regression.mc",
        "int main(){print(" + "!" * 32760 + "1);return 0;}",
    )
    statements_exact = generated_case(
        directory,
        "statements_exact.mc",
        "int main(){" + "{" * 511 + "print(1);" + "}" * 511 + "return 0;}",
    )
    statements_over = generated_case(
        directory,
        "statements_over.mc",
        "int main(){" + "{" * 512 + "print(1);" + "}" * 512 + "return 0;}",
    )
    return [
        ("token-exact-65536", [token_exact], 0, "", ""),
        ("token-one-over", [token_over], 65, "", "too many tokens"),
        ("expression-nesting-exact", [nesting_exact], 0, "1\n", ""),
        ("expression-nesting-one-over", [nesting_over], 65, "",
         "expression nesting exceeds 512"),
        ("deep-parentheses-regression", [deep_regression], 65, "",
         "expression nesting exceeds 512"),
        ("deep-unary-iterative", [unary_regression], 0, "1\n", ""),
        ("statement-level-exact", [statements_exact], 0, "1\n", ""),
        ("statement-level-one-over", [statements_over], 65, "",
         "statement nesting exceeds 512"),
    ]


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
        ("budget-u64-exact",
         ["--max-steps", "18446744073709551615", file_case("two_steps.mc")],
         0, "", ""),
        ("usage-zero-budget", ["--max-steps", "0", META], 64, "", "usage:"),
        ("missing-input", [file_case("does_not_exist.mc")], 66, "", "cannot open input"),
    ]
    failures = 0
    deadline = SuiteDeadline(180)
    with tempfile.TemporaryDirectory(prefix=".reference-tests-", dir=ROOT) as directory:
        tests.extend(boundary_tests(directory))
        for name, arguments, expected_code, expected_out, expected_error in tests:
            try:
                result = run(executable, arguments, deadline.case_timeout(8))
                ok = (not result.timed_out and not result.stdout_truncated and
                      not result.stderr_truncated and result.returncode == expected_code and
                      result.stdout == expected_out and
                      expected_error.lower() in result.stderr.lower())
                if ok:
                    print("PASS", name)
                else:
                    failures += 1
                    print("FAIL", name)
                    if result.timed_out:
                        print("  timed out after {:.3f}s".format(result.elapsed))
                    if result.stdout_truncated or result.stderr_truncated:
                        print("  captured output reached the 65536-byte per-stream limit")
                    print("  exit: expected {}, got {}".format(expected_code,
                                                               result.returncode))
                    print("  stdout: expected {!r}, got {}".format(expected_out,
                                                                    preview(result.stdout)))
                    print("  stderr needed {!r}, got {}".format(expected_error,
                                                                 preview(result.stderr)))
            except SuiteBudgetExpired as error:
                failures += 1
                print("FAIL", name, error)
            except (OSError, subprocess.SubprocessError) as error:
                failures += 1
                print("FAIL", name, error)
    print("{} passed; {} failed".format(len(tests) - failures, failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
