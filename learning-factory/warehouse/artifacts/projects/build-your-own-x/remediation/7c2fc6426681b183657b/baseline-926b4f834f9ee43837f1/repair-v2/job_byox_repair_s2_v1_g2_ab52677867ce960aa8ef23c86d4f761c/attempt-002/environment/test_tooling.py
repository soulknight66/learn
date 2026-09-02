"""Deterministic regression tests for the pack's build and audit helpers."""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
BUILD_HELPER = ROOT / "environment" / "build.py"
AUDIT_HELPER = ROOT / "environment" / "audit.py"
ASSEMBLER = Path("/usr/bin/as")
LINKER = Path("/usr/bin/ld.bfd")
TIMEOUT_SECONDS = 30

FUNCTIONAL_FILES = (
    "starter/forth.S",
    "starter/Makefile",
    "public_tests/test_cinder.py",
    "environment/build.py",
    "environment/audit.py",
    "environment/test_tooling.py",
    "sealed/reference/forth.S",
    "sealed/reference_tests/test_reference.py",
    "benchmarks/run.py",
)

MINIMAL_ASSEMBLY = """\
.global _start
.section .text
_start:
    mov $60, %rax
    xor %rdi, %rdi
    syscall
"""


def load_audit_module():
    spec = importlib.util.spec_from_file_location("cinder_pack_audit", AUDIT_HELPER)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load audit helper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


AUDIT = load_audit_module()


def run_process(argv: list[str]) -> subprocess.CompletedProcess[bytes]:
    process = subprocess.Popen(
        argv,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    try:
        stdout, stderr = process.communicate(timeout=TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.communicate()
        raise
    return subprocess.CompletedProcess(argv, process.returncode, stdout, stderr)


class BuildHelperRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        for kind, path in (("assembler", ASSEMBLER), ("linker", LINKER)):
            if not path.is_file() or path.is_symlink():
                raise unittest.SkipTest(f"regular system {kind} unavailable: {path}")

    def invoke_build(
        self, source: Path, output: Path, *extra_arguments: str
    ) -> subprocess.CompletedProcess[bytes]:
        return run_process(
            [
                sys.executable,
                str(BUILD_HELPER),
                str(source),
                "-o",
                str(output),
                *extra_arguments,
            ]
        )

    def make_source(self, directory: Path) -> Path:
        source = directory / "minimal.S"
        source.write_text(MINIMAL_ASSEMBLY, encoding="ascii")
        return source

    def test_repeated_builds_are_byte_identical(self) -> None:
        with tempfile.TemporaryDirectory(prefix=".tooling-test-", dir=ROOT / "environment") as raw:
            temporary = Path(raw)
            source = self.make_source(temporary)
            first = temporary / "first-elf"
            second = temporary / "second-elf"

            first_result = self.invoke_build(source, first)
            second_result = self.invoke_build(source, second)
            self.assertEqual(first_result.returncode, 0, first_result.stderr)
            self.assertEqual(second_result.returncode, 0, second_result.stderr)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertNotIn(b"cinder-build-", first.read_bytes())
            self.assertNotIn(str(ROOT).encode("utf-8"), first.read_bytes())

    def assert_symlink_rejected(self, kind: str) -> None:
        with tempfile.TemporaryDirectory(prefix=".tooling-test-", dir=ROOT / "environment") as raw:
            temporary = Path(raw)
            source = self.make_source(temporary)
            output = temporary / "result-elf"
            arguments: list[str] = []

            if kind == "source":
                source_link = temporary / "source-link.S"
                source_link.symlink_to(source)
                source = source_link
            elif kind == "assembler":
                assembler_link = temporary / "assembler-link"
                assembler_link.symlink_to(ASSEMBLER)
                arguments = ["--assembler", str(assembler_link)]
            elif kind == "linker":
                linker_link = temporary / "linker-link"
                linker_link.symlink_to(LINKER)
                arguments = ["--linker", str(linker_link)]
            else:
                self.fail(f"unknown input kind: {kind}")

            result = self.invoke_build(source, output, *arguments)
            self.assertEqual(result.returncode, 2, result)
            self.assertIn(
                f"{kind} must be a regular non-symlink file".encode("ascii"), result.stderr
            )
            self.assertFalse(output.exists())

    def test_rejects_source_symlink(self) -> None:
        self.assert_symlink_rejected("source")

    def test_rejects_assembler_symlink(self) -> None:
        self.assert_symlink_rejected("assembler")

    def test_rejects_linker_symlink(self) -> None:
        self.assert_symlink_rejected("linker")


class AuditRegressionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(
            prefix=".audit-test-", dir=ROOT / "environment"
        )
        self.fixture = Path(self.temporary.name)
        for relative in AUDIT.REQUIRED:
            path = self.fixture / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"fixture\n")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_missing_functional_files_each_fail_the_audit(self) -> None:
        for relative in FUNCTIONAL_FILES:
            path = self.fixture / relative
            original = path.read_bytes()
            path.unlink()
            try:
                with self.subTest(relative=relative):
                    with self.assertRaisesRegex(
                        RuntimeError,
                        re.escape(f"missing regular required file: {relative}"),
                    ):
                        AUDIT.audit_pack(self.fixture)
            finally:
                path.write_bytes(original)

    def test_complete_provenance_object_is_bound(self) -> None:
        AUDIT.validate_metadata(ROOT)
        (self.fixture / "MANIFEST.yaml").write_bytes((ROOT / "MANIFEST.yaml").read_bytes())
        original = json.loads((ROOT / "PROVENANCE.json").read_text(encoding="utf-8"))
        mutations = (
            (("license_boundary", "linked_content_copied"), True),
            (("project", "upstream_reference"), "https://invalid.example/changed"),
            (("source", "commit_hash"), "0" * 40),
        )
        for keys, replacement in mutations:
            changed = json.loads(json.dumps(original))
            target = changed
            for key in keys[:-1]:
                target = target[key]
            target[keys[-1]] = replacement
            (self.fixture / "PROVENANCE.json").write_text(
                json.dumps(changed), encoding="utf-8"
            )
            with self.subTest(field=".".join(keys)):
                with self.assertRaisesRegex(
                    RuntimeError, "authoritative complete object"
                ):
                    AUDIT.validate_metadata(self.fixture)


if __name__ == "__main__":
    unittest.main()
