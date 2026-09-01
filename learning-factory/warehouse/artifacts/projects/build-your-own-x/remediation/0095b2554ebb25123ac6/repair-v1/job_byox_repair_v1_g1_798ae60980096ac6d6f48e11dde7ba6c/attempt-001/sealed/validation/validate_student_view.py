#!/usr/bin/env python3
"""Build a learner view and prove its boundary in a bubblewrap process."""

import argparse
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys

import learner_view


PROBE = r'''
import os
import sys

allowed = {
    "README.md", "AGENTS.md", "MANIFEST.yaml", "REQUIREMENTS.md",
    "CONCEPTS.md", "DESIGN_QUESTIONS.md", "starter", "public_tests", "environment",
}
actual = set(os.listdir("/workspace"))
if actual != allowed:
    raise SystemExit("unexpected learner top level: {}".format(sorted(actual)))

source = sys.argv[1]
targets = [
    "/workspace/sealed/reference/README.md",
    "/workspace/sealed/DESIGN.md",
    os.path.join(source, "sealed", "reference", "README.md"),
    os.path.join(source, "sealed", "debugging", "scanner-position", "ANSWER.md"),
]
for target in targets:
    try:
        with open(target, "rb") as stream:
            stream.read(1)
    except OSError:
        continue
    raise SystemExit("sealed material readable: {}".format(target))
print("PASS sealed/reference/answer material absent and unreadable in learner process")
'''


def run_bounded(argv, timeout):
    process = subprocess.Popen(
        argv,
        env={"PATH": "/usr/bin:/bin"},
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        start_new_session=True,
        universal_newlines=True,
    )
    try:
        output, unused_stderr = process.communicate(timeout=timeout)
        return process.returncode, output
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        output, unused_stderr = process.communicate()
        return 124, output + "TIMEOUT after {} seconds\n".format(timeout)


def runtime_mounts(python_executable, source):
    roots = []
    for candidate in (Path("/usr"), Path("/lib"), Path("/lib64")):
        if candidate.exists():
            roots.append(candidate)
    executable = Path(python_executable).resolve(strict=True)
    if not any(str(executable).startswith(str(root) + os.sep) for root in roots):
        tool_root = Path(executable.anchor) / executable.parts[1]
        if str(source).startswith(str(tool_root) + os.sep):
            raise learner_view.ViewError("Python runtime shares the source-pack mount")
        roots.append(tool_root)
    for root in roots:
        if source == root or str(source).startswith(str(root) + os.sep):
            raise learner_view.ViewError("runtime mount would expose the source pack: {}".format(root))
    return roots


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--destination", required=True)
    parser.add_argument("--bwrap", default=shutil.which("bwrap"))
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args(argv)
    if not args.bwrap:
        print("BLOCKED bubblewrap executable not found", file=sys.stderr)
        return 2
    if args.timeout < 1 or args.timeout > 120:
        print("FAIL timeout must be between 1 and 120", file=sys.stderr)
        return 2

    try:
        source = Path(args.source).resolve(strict=True)
        destination = Path(args.destination)
        result = learner_view.materialize(source, destination)
        destination = destination.resolve(strict=True)
        python_executable = str(Path(sys.executable).resolve(strict=True))
        command = [
            str(Path(args.bwrap).resolve(strict=True)),
            "--unshare-all",
            "--die-with-parent",
            "--new-session",
            "--setenv", "PATH", "/usr/bin:/bin",
            "--proc", "/proc",
            "--dev", "/dev",
            "--tmpfs", "/tmp",
            "--dir", "/workspace",
        ]
        for root in runtime_mounts(python_executable, source):
            command.extend(("--ro-bind", str(root), str(root)))
        for relative, unused_kind, access in learner_view.EXPECTED_ALLOWED:
            option = "--bind" if access == "read-write" else "--ro-bind"
            command.extend((option, str(destination / relative), "/workspace/" + relative))
        command.extend((
            "--chdir", "/workspace",
            python_executable,
            "-c",
            PROBE,
            str(source),
        ))
        status, output = run_bounded(command, args.timeout)
    except (OSError, learner_view.ViewError) as error:
        print("FAIL {}".format(error), file=sys.stderr)
        return 1

    sys.stdout.write(output)
    if status != 0:
        print("FAIL learner isolation probe exit {}".format(status), file=sys.stderr)
        return 1
    print("PASS learner view content digest: {}".format(result["content_sha256"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
