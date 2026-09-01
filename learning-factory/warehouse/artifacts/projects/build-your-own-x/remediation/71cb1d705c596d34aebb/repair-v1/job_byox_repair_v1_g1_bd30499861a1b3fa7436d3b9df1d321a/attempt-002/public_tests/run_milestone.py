#!/usr/bin/env python3
"""Run one cumulative, learner-visible minish milestone check."""

from __future__ import print_function

import argparse
import os
from pathlib import Path
import pty
import select
import signal
import subprocess
import tempfile
import termios
import time


ROOT = Path(__file__).resolve().parents[1]
STARTER = ROOT / "starter"
BINARY = STARTER / "minish"
MILESTONES = ("lexer", "parser", "process", "descriptor", "job", "terminal")


class CheckFailed(Exception):
    pass


def require(condition, message):
    if not condition:
        raise CheckFailed(message)


def run(argv, cwd=None, input_text=None, timeout=10):
    environment = os.environ.copy()
    environment["LC_ALL"] = "C"
    return subprocess.run(
        [str(item) for item in argv],
        cwd=None if cwd is None else str(cwd),
        input=input_text,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        timeout=timeout,
        env=environment,
    )


def build_starter():
    result = run(
        [
            "make", "clean", "all",
            "CFLAGS=-std=c11 -Wall -Wextra -Wpedantic -Werror -g",
        ],
        cwd=STARTER,
        timeout=30,
    )
    require(result.returncode == 0, "strict build failed:\n" + result.stderr)


def compile_and_run_probe(name):
    source = Path(__file__).with_name("milestones") / (name + "_probe.c")
    with tempfile.TemporaryDirectory(prefix="minish-milestone-") as directory:
        probe = Path(directory) / (name + "_probe")
        result = run(
            [
                os.environ.get("CC", "cc"), "-std=c11", "-Wall", "-Wextra",
                "-Wpedantic", "-Werror", "-I", STARTER / "include", source,
                STARTER / "libminish.a", "-o", probe,
            ],
            timeout=20,
        )
        require(
            result.returncode == 0,
            name + " probe build failed:\n" + result.stderr,
        )
        result = run([probe], timeout=5)
        require(result.returncode == 0,
                name + " probe failed:\n" + result.stderr)


def check_lexer():
    compile_and_run_probe("lexer")


def check_parser():
    compile_and_run_probe("parser")


def check_process():
    result = run(
        [BINARY, "-c", "printf first\nexit 7\nprintf never"], timeout=5
    )
    require(result.returncode == 7, "exit or physical-line status was not 7")
    require(
        result.stdout == "first",
        "physical-line execution output was {!r}".format(result.stdout),
    )
    require(result.stderr == "",
            "unexpected process diagnostic: " + result.stderr)

    result = run(
        [BINARY, "-c", "definitely_missing_minish_command"], timeout=5
    )
    require(result.returncode == 127, "missing command did not return 127")
    require(
        "definitely_missing_minish_command" in result.stderr,
        "missing-command diagnostic omitted the command name",
    )


def check_descriptor():
    with tempfile.TemporaryDirectory(prefix="minish-descriptor-") as directory:
        result = run(
            [BINARY, "-c", "printf payload | cat > result ; cat < result"],
            cwd=directory,
            timeout=5,
        )
        require(
            result.returncode == 0,
            "redirection pipeline failed: " + result.stderr,
        )
        require(
            result.stdout == "payload",
            "redirection output was {!r}".format(result.stdout),
        )
        with open(os.path.join(directory, "result"), "r") as stream:
            require(stream.read() == "payload",
                    "redirected file content differed")

    result = run([BINARY, "-c", "seq 1 20000 | wc -l"], timeout=8)
    require(result.returncode == 0,
            "concurrent pipeline failed: " + result.stderr)
    require(
        result.stdout.strip() == "20000",
        "pipeline count was {!r}".format(result.stdout),
    )


def check_job():
    command = "sleep 0.20 & jobs ; fg %1 ; jobs ; printf done"
    result = run([BINARY, "-c", command], timeout=5)
    require(result.returncode == 0,
            "job lifecycle failed: " + result.stderr)
    require(
        result.stdout == "[1] Running sleep 0.20\ndone",
        "stable jobs output differed: {!r}".format(result.stdout),
    )

    command = "sh -c 'test \"$$\" -eq \"$(ps -o pgid= -p $$)\"'"
    result = run([BINARY, "-c", command], timeout=5)
    require(
        result.returncode == 0,
        "pipeline did not receive its own process group",
    )


def read_until(descriptor, marker, timeout):
    data = b""
    deadline = time.monotonic() + timeout
    while marker not in data:
        remaining = deadline - time.monotonic()
        require(
            remaining > 0,
            "terminal timed out; transcript={!r}".format(data),
        )
        readable, unused_writable, unused_exceptional = select.select(
            [descriptor], [], [], remaining
        )
        if not readable:
            continue
        try:
            chunk = os.read(descriptor, 4096)
        except OSError:
            chunk = b""
        require(chunk, "terminal closed; transcript={!r}".format(data))
        data += chunk
    return data


def wait_child(pid, timeout):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        waited, status = os.waitpid(pid, os.WNOHANG)
        if waited == pid:
            return status
        time.sleep(0.01)
    raise CheckFailed("shell did not exit after terminal check")


def check_terminal():
    pid, master = pty.fork()
    if pid == 0:
        environment = os.environ.copy()
        environment["LC_ALL"] = "C"
        os.execve(str(BINARY), [str(BINARY)], environment)

    reaped = False
    transcript = b""
    try:
        transcript += read_until(master, b"minish$ ", 2.0)
        attributes = termios.tcgetattr(master)
        attributes[3] &= ~termios.ECHO
        termios.tcsetattr(master, termios.TCSANOW, attributes)
        os.write(master, b"sh -c 'printf READY; sleep 10'\n")
        transcript += read_until(master, b"READY", 2.0)
        require(
            os.tcgetpgrp(master) != pid,
            "shell retained terminal ownership during a foreground job",
        )
        os.write(master, b"\x03")
        transcript += read_until(master, b"minish$ ", 2.0)
        os.write(master, b"exit 0\n")
        status = wait_child(pid, 2.0)
        reaped = True
        require(
            os.WIFEXITED(status) and os.WEXITSTATUS(status) == 0,
            "interactive shell exit failed; transcript={!r}".format(transcript),
        )
    finally:
        if not reaped:
            try:
                foreground = os.tcgetpgrp(master)
                if foreground > 0 and foreground != pid:
                    os.killpg(foreground, signal.SIGKILL)
            except (OSError, ProcessLookupError):
                pass
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            try:
                os.waitpid(pid, 0)
            except ChildProcessError:
                pass
        os.close(master)


CHECKS = {
    "lexer": check_lexer,
    "parser": check_parser,
    "process": check_process,
    "descriptor": check_descriptor,
    "job": check_job,
    "terminal": check_terminal,
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("milestone", choices=MILESTONES + ("all",))
    arguments = parser.parse_args()
    if arguments.milestone == "all":
        selected = MILESTONES
    else:
        selected = (arguments.milestone,)

    name = arguments.milestone
    try:
        build_starter()
        for name in selected:
            CHECKS[name]()
            print("milestone {}: PASS".format(name))
    except (CheckFailed, OSError, subprocess.SubprocessError) as error:
        print(
            "milestone {}: FAIL: {}".format(name, error),
            file=os.sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    os.sys.exit(main())
