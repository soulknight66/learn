#!/usr/bin/env python3
"""Check the minimal local toolchain without invoking a command shell."""

from __future__ import print_function

import os
import signal
import subprocess
import sys
import tempfile


def run(arguments, timeout=5):
    process = subprocess.Popen(
        arguments,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        start_new_session=True,
    )
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.communicate()
        raise RuntimeError("timeout: " + " ".join(arguments))
    if process.returncode != 0:
        raise RuntimeError("command failed: %s\n%s" %
                           (" ".join(arguments), stderr))
    return stdout


def first_line(text):
    lines = text.splitlines()
    return lines[0] if lines else "(no version text)"


def main():
    try:
        cc_version = first_line(run(["cc", "--version"]))
        make_version = first_line(run(["make", "--version"]))
        with tempfile.TemporaryDirectory(prefix="sprig-env-") as directory:
            source = os.path.join(directory, "probe.c")
            binary = os.path.join(directory, "probe")
            with open(source, "w") as output:
                output.write(
                    "#include <stdint.h>\n"
                    "#include <stdio.h>\n"
                    "int main(void) {\n"
                    "  int64_t value = INT64_C(42);\n"
                    "  printf(\"%lld\\n\", (long long)value);\n"
                    "  return sizeof(value) == 8 ? 0 : 1;\n"
                    "}\n"
                )
            run(["cc", "-std=c11", "-Wall", "-Wextra", "-Wpedantic",
                 "-Werror", source, "-o", binary])
            probe_output = run([binary])
        if probe_output != "42\n":
            raise RuntimeError("compiled probe returned unexpected output")
    except (OSError, RuntimeError) as error:
        print("environment check: FAIL: " + str(error), file=sys.stderr)
        return 1

    print("environment check: PASS")
    print("compiler: " + cc_version)
    print("make: " + make_version)
    print("python: " + sys.version.splitlines()[0])
    print("C11 int64_t compile/run probe: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
