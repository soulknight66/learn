#!/usr/bin/env python3
"""Run immutable public and sealed tests against a harness-selected module."""

import argparse
import hashlib
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile


PACK_ROOT = Path(__file__).resolve().parents[2]
LOCKED_INPUTS = (
    Path("starter/types_test.go"),
    Path("public_tests/compiler_test.go"),
    Path("sealed/learner_tests/contract_test.go"),
)
EXPECTED_SUITE_SHA256 = "a3f62d3b7370066dc4e7d7aa6f9c563cad5614fcc27a573e817ded056c90b032"


class HarnessError(Exception):
    pass


def suite_digest():
    digest = hashlib.sha256()
    digest.update(b"pebble-learner-suites-v1\0")
    for relative in LOCKED_INPUTS:
        data = (PACK_ROOT / relative).read_bytes()
        name = relative.as_posix().encode("utf-8")
        digest.update(str(len(name)).encode("ascii") + b":" + name)
        digest.update(str(len(data)).encode("ascii") + b":" + data)
    return digest.hexdigest()


def verify_locked_inputs():
    actual = suite_digest()
    if actual != EXPECTED_SUITE_SHA256:
        raise HarnessError("suite content lock mismatch: {}".format(actual))
    for relative in LOCKED_INPUTS:
        path = PACK_ROOT / relative
        if not path.is_file() or path.is_symlink():
            raise HarnessError("suite input is not a regular file: {}".format(relative))
    return actual


def write_module(path, candidate):
    candidate_text = str(candidate)
    if "\n" in candidate_text or "\r" in candidate_text:
        raise HarnessError("candidate path contains a line break")
    content = (
        "module example.com/pebble-harness-tests\n\n"
        "go 1.21\n\n"
        "require example.com/pebble v0.0.0\n\n"
        "replace example.com/pebble => {}\n".format(candidate_text)
    )
    (path / "go.mod").write_text(content, encoding="utf-8")


def prepare_suite(scratch, name, test_source, candidate):
    destination = scratch / name
    destination.mkdir()
    shutil.copyfile(str(test_source), str(destination / test_source.name))
    write_module(destination, candidate)
    return destination


def go_environment(scratch, go_executable):
    cache = scratch / "go-cache"
    modules = scratch / "module-cache"
    temporary = scratch / "tmp"
    for path in (cache, modules, temporary):
        path.mkdir(exist_ok=True)
    return {
        "PATH": str(Path(go_executable).parent),
        "CGO_ENABLED": "0",
        "GOCACHE": str(cache),
        "GOENV": "off",
        "GOFLAGS": "-mod=mod",
        "GOMODCACHE": str(modules),
        "GONOSUMDB": "*",
        "GOPROXY": "off",
        "GOSUMDB": "off",
        "GOTOOLCHAIN": "local",
        "GOWORK": "off",
        "TMPDIR": str(temporary),
    }


def run_bounded(argv, cwd, environment, timeout):
    process = subprocess.Popen(
        argv,
        cwd=str(cwd),
        env=environment,
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


def run_candidate(candidate, scratch, go_executable, timeout, label):
    candidate = candidate.resolve(strict=True)
    if not (candidate / "go.mod").is_file() or (candidate / "go.mod").is_symlink():
        raise HarnessError("candidate has no regular go.mod: {}".format(candidate))
    public_suite = prepare_suite(
        scratch, label + "-public", PACK_ROOT / "public_tests/compiler_test.go", candidate
    )
    sealed_suite = prepare_suite(
        scratch, label + "-sealed", PACK_ROOT / "sealed/learner_tests/contract_test.go", candidate
    )
    environment = go_environment(scratch, go_executable)
    results = {}
    for name, directory in (("candidate-local", candidate), ("public", public_suite), ("sealed", sealed_suite)):
        status, output = run_bounded(
            [go_executable, "test", "./..."], directory, environment, timeout
        )
        results[name] = status
        print("=== {} / {} / exit {}".format(label, name, status))
        sys.stdout.write(output)
        if output and not output.endswith("\n"):
            sys.stdout.write("\n")
    return results


def materialize_reference(destination):
    destination.mkdir()
    reference = PACK_ROOT / "sealed/reference"
    for source in sorted(reference.glob("*.go"), key=lambda path: path.name):
        if source.is_symlink() or not source.is_file():
            raise HarnessError("reference input is not regular: {}".format(source))
        shutil.copyfile(str(source), str(destination / source.name))
    shutil.copyfile(
        str(PACK_ROOT / "starter/types_test.go"), str(destination / "starter_contract_test.go")
    )
    (destination / "go.mod").write_text("module example.com/pebble\n\ngo 1.21\n", encoding="utf-8")


MUTATIONS = {
    "forged-coordinate-accepted": (
        "parser.go",
        "func possibleIgnoredGap(previous, next Position) bool {\n\treturn possiblePositionAdvance(previous, next)\n}",
        "func possibleIgnoredGap(previous, next Position) bool {\n\treturn next.Offset >= previous.Offset && next.Line >= previous.Line\n}",
    ),
    "negative-slot-accepted": (
        "validator.go",
        "return operand >= 0 && operand < int64(slotCount)",
        "return operand < int64(slotCount)",
    ),
    "unchecked-add": (
        "vm.go",
        "case OpAdd:\n\t\tif right > 0 && left > math.MaxInt64-right || right < 0 && left < math.MinInt64-right {\n\t\t\treturn 0, CodeIntegerOverflow\n\t\t}\n\t\treturn left + right, \"\"",
        "case OpAdd:\n\t\treturn left + right, \"\"",
    ),
}


def apply_mutation(candidate, name):
    filename, before, after = MUTATIONS[name]
    path = candidate / filename
    content = path.read_text(encoding="utf-8")
    if content.count(before) != 1:
        raise HarnessError("seed mutation anchor mismatch: {}".format(name))
    path.write_text(content.replace(before, after), encoding="utf-8")


def self_check(scratch, go_executable, timeout):
    good = scratch / "known-good"
    materialize_reference(good)
    good_results = run_candidate(good, scratch, go_executable, timeout, "known-good")
    if any(status != 0 for status in good_results.values()):
        raise HarnessError("known-good reference was not accepted: {}".format(good_results))
    for index, name in enumerate(sorted(MUTATIONS)):
        bad = scratch / ("seeded-bad-" + name)
        shutil.copytree(str(good), str(bad))
        apply_mutation(bad, name)
        results = run_candidate(bad, scratch, go_executable, timeout, "bad-{}-{}".format(index, name))
        if results["sealed"] == 0:
            raise HarnessError("sealed suite did not reject seeded defect: {}".format(name))
    print("PASS known-good accepted and all {} seeded defects rejected".format(len(MUTATIONS)))


def main(argv):
    parser = argparse.ArgumentParser()
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument("--candidate")
    choice.add_argument("--self-check", action="store_true")
    parser.add_argument("--go", default=shutil.which("go"))
    parser.add_argument("--scratch-parent")
    parser.add_argument("--timeout", type=int, default=120)
    args = parser.parse_args(argv)
    if not args.go:
        print("BLOCKED Go executable not found", file=sys.stderr)
        return 2
    if args.timeout < 1 or args.timeout > 600:
        print("FAIL timeout must be between 1 and 600", file=sys.stderr)
        return 2
    try:
        suite_hash = verify_locked_inputs()
        go_executable = str(Path(args.go).resolve(strict=True))
        with tempfile.TemporaryDirectory(prefix="pebble-harness-", dir=args.scratch_parent) as temporary:
            scratch = Path(temporary)
            if args.self_check:
                self_check(scratch, go_executable, args.timeout)
            else:
                results = run_candidate(
                    Path(args.candidate), scratch, go_executable, args.timeout, "candidate"
                )
                if results["public"] != 0 or results["sealed"] != 0:
                    raise HarnessError("harness-controlled suites rejected candidate: {}".format(results))
                print("PASS harness-controlled public and sealed suites accepted candidate")
        print("PASS suite content lock: {}".format(suite_hash))
    except (HarnessError, OSError, subprocess.SubprocessError) as error:
        print("FAIL {}".format(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
