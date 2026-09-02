#!/usr/bin/env python3
"""Generate deterministic adversarial Sprig inputs, without expected answers."""

from __future__ import print_function

import argparse
import os
import sys


def write_case(directory, name, content):
    path = os.path.join(directory, name + ".sprig")
    if isinstance(content, str):
        content = content.encode("ascii")
    with open(path, "wb") as output:
        output.write(content)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output_directory")
    options = parser.parse_args()
    target = os.path.abspath(options.output_directory)
    if os.path.exists(target):
        if not os.path.isdir(target) or os.listdir(target):
            parser.error("output directory must be absent or empty")
    else:
        os.makedirs(target)

    declarations = "".join("let v%d = %d;\n" % (i, i) for i in range(64))
    right_heavy = "1"
    for unused in range(260):
        right_heavy = "1+(" + right_heavy + ")"
    too_deep = "1"
    for unused in range(513):
        too_deep = "(" + too_deep + ")"

    write_case(target, "max_variables", declarations + "print v63;\n")
    write_case(target, "too_many_variables", declarations + "let extra = 0;\n")
    write_case(target, "instruction_limit",
               "print " + "+".join(["1"] * 513) + ";\n")
    write_case(target, "right_heavy_stack", "print " + right_heavy + ";\n")
    write_case(target, "nesting_limit", "print " + too_deep + ";\n")
    write_case(target, "add_overflow", "print 9223372036854775807 + 1;\n")
    write_case(target, "computed_minimum",
               "print -9223372036854775807 - 1;\n")
    write_case(target, "long_identifier", "let " + "a" * 32 + " = 1;\n")
    write_case(target, "embedded_nul", b"print 1;\x00print 2;\n")
    write_case(target, "comment_at_eof", "print 1; # no final newline")
    print("generated 10 cases in " + target)
    return 0


if __name__ == "__main__":
    sys.exit(main())
