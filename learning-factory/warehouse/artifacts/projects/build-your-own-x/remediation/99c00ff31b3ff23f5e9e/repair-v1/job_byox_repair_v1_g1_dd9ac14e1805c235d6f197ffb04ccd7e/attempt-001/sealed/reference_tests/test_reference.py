#!/usr/bin/env python3
"""Stronger deterministic checks for the sealed Mica reference."""

import os
from pathlib import Path
import random
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
TEMP_PARENT = ROOT / "environment" / ".reference-test-work"


class ReferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        configured = os.environ.get("MICA_BIN")
        if configured:
            candidate = Path(configured)
            cls.mica = candidate if candidate.is_absolute() else ROOT / candidate
        else:
            subprocess.run(
                ["make", "-C", str(ROOT / "sealed" / "reference"), "all"],
                cwd=str(ROOT),
                check=True,
                timeout=30,
            )
            cls.mica = ROOT / "sealed" / "reference" / "mica"
        TEMP_PARENT.mkdir(parents=True, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        try:
            TEMP_PARENT.rmdir()
        except OSError:
            pass

    def setUp(self):
        self.work = Path(tempfile.mkdtemp(prefix="sealed-", dir=str(TEMP_PARENT)))

    def tearDown(self):
        shutil.rmtree(str(self.work))

    def source(self, text, name="case.mica"):
        path = self.work / name
        path.write_text(text, encoding="ascii")
        return path

    def source_bytes(self, content, name="case.mica"):
        path = self.work / name
        path.write_bytes(content)
        return path

    def invoke_path(self, mode, source_path, *tail, timeout=10):
        return subprocess.run(
            [str(self.mica), mode, str(source_path)] + [str(item) for item in tail],
            cwd=str(ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            timeout=timeout,
        )

    def invoke(self, mode, text, *tail, timeout=10):
        return self.invoke_path(mode, self.source(text), *tail, timeout=timeout)

    def invoke_arguments(self, *arguments, timeout=10):
        return subprocess.run(
            [str(self.mica)] + [str(item) for item in arguments],
            cwd=str(ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            timeout=timeout,
        )

    def native(self, text, timeout=10):
        source = self.source(text, "native.mica")
        assembly = self.work / "native.s"
        executable = self.work / "native"
        emitted = self.invoke_path("compile", source, "-o", assembly)
        self.assertEqual(emitted.returncode, 0, emitted.stderr)
        linked = subprocess.run(
            ["cc", "-no-pie", str(assembly), "-o", str(executable)],
            cwd=str(ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            timeout=20,
        )
        self.assertEqual(linked.returncode, 0, linked.stderr)
        return subprocess.run(
            [str(executable)],
            cwd=str(ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            timeout=timeout,
        )

    def assert_differential(self, text):
        interpreted = self.invoke("run", text)
        self.assertEqual(interpreted.returncode, 0, interpreted.stderr)
        compiled = self.native(text)
        self.assertEqual(compiled.returncode, 0, compiled.stderr)
        self.assertEqual(compiled.stdout, interpreted.stdout)
        self.assertEqual(compiled.stderr, interpreted.stderr)

    def test_empty_and_comment_only_programs(self):
        for text in ("", "// no statements", " \n\t// comment\n"):
            result = self.invoke("run", text)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, "")

    def test_usage_failures_are_single_diagnostic_lines(self):
        cases = (
            (),
            ("unknown",),
            ("run",),
            ("compile", "input.mica", "-o"),
            ("compile", "input.mica", "--output", "out.s"),
        )
        for arguments in cases:
            result = self.invoke_arguments(*arguments)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, "")
            self.assertTrue(result.stderr.startswith("mica: usage error:"), result.stderr)
            self.assertEqual(len(result.stderr.splitlines()), 1)

    def test_all_comparisons_and_left_associativity(self):
        text = (
            "print 1 < 2; print 2 <= 2; print 3 > 4; print 4 >= 4;\n"
            "print 5 == 5; print 5 != 5; print 20 - 3 - 2;\n"
        )
        result = self.invoke("run", text)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "1\n1\n0\n1\n1\n0\n15\n")

    def test_minimum_division_overflow_is_defined(self):
        text = (
            "let minimum = -9223372036854775807 - 1;\n"
            "print minimum / -1;\n"
            "print minimum % -1;\n"
        )
        self.assert_differential(text)
        result = self.invoke("run", text)
        self.assertEqual(result.stdout, "-9223372036854775808\n0\n")

    def test_skipped_declaration_has_zero_initialized_storage(self):
        text = (
            "if (0) { let branch_value = 41; }\n"
            "print branch_value;\n"
            "if (0) { let later = 2; } else { later = 9; }\n"
            "print later;\n"
        )
        self.assert_differential(text)
        result = self.invoke("run", text)
        self.assertEqual(result.stdout, "0\n9\n")

    def test_unselected_branch_does_not_evaluate(self):
        text = "if (1) { print 7; } else { print 1 / 0; }\n"
        self.assert_differential(text)

    def test_parse_and_validation_diagnostics(self):
        cases = [
            ("print 1\n", "mica: parse error: 2:1:"),
            ("let x = x;\n", "mica: validation error: 1:9:"),
            ("let x = 1; let x = 2;\n", "mica: validation error: 1:16:"),
            ("x = 1;\n", "mica: validation error: 1:1:"),
        ]
        for text, prefix in cases:
            result = self.invoke("run", text)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(result.stdout, "")
            self.assertTrue(result.stderr.startswith(prefix), result.stderr)

    def test_integer_overflow_and_nul_are_lexical_errors(self):
        overflow = self.invoke("tokens", "print 9223372036854775808;\n")
        self.assertNotEqual(overflow.returncode, 0)
        self.assertIn("outside signed 64-bit range", overflow.stderr)
        nul_path = self.source_bytes(b"print 1;\x00print 2;")
        nul = self.invoke_path("tokens", nul_path)
        self.assertNotEqual(nul.returncode, 0)
        self.assertIn("unexpected byte 0x00", nul.stderr)

    def test_variable_limit_accepts_256_and_rejects_257(self):
        declarations = ["let v{} = {};".format(index, index) for index in range(256)]
        accepted = self.invoke("run", "\n".join(declarations) + "\nprint v255;\n")
        self.assertEqual(accepted.returncode, 0, accepted.stderr)
        self.assertEqual(accepted.stdout, "255\n")
        rejected = self.invoke(
            "run", "\n".join(declarations + ["let overflow = 0;"]) + "\n"
        )
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("variable limit exceeded", rejected.stderr)

    def test_explicit_and_tree_depth_limits(self):
        nested = "print " + "(" * 129 + "1" + ")" * 129 + ";\n"
        nested_result = self.invoke("run", nested)
        self.assertNotEqual(nested_result.returncode, 0)
        self.assertIn("nesting limit exceeded", nested_result.stderr)
        flat = "print " + " + ".join(["1"] * 130) + ";\n"
        flat_result = self.invoke("run", flat)
        self.assertNotEqual(flat_result.returncode, 0)
        self.assertIn("expression tree depth limit exceeded", flat_result.stderr)

    def test_source_size_limit(self):
        path = self.source_bytes(b" " * 1048577, "oversized.mica")
        result = self.invoke_path("tokens", path)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("source exceeds 1048576-byte limit", result.stderr)

    def test_division_by_zero_matches_native_failure_class(self):
        # Nest the failing divide under pending expression temporaries; the
        # shared error path must restore stack alignment before calling libc.
        text = "print 1 + (2 * (9 / 0));\n"
        interpreted = self.invoke("run", text)
        native = self.native(text)
        self.assertNotEqual(interpreted.returncode, 0)
        self.assertNotEqual(native.returncode, 0)
        self.assertIn("mica: runtime error:", interpreted.stderr)
        self.assertEqual(native.stderr,
                         "mica: runtime error: division by zero\n")

    def test_execution_budget_is_enforced_in_both_backends(self):
        text = "while (1) { }\n"
        interpreted = self.invoke("run", text, timeout=5)
        native = self.native(text, timeout=5)
        self.assertNotEqual(interpreted.returncode, 0)
        self.assertNotEqual(native.returncode, 0)
        self.assertIn("execution step limit exceeded", interpreted.stderr)
        self.assertIn("execution step limit exceeded", native.stderr)

    def test_assembly_emission_is_deterministic(self):
        source = self.source("let x = 3; if (x) { print x; }\n")
        first = self.work / "first.s"
        second = self.work / "second.s"
        one = self.invoke_path("compile", source, "-o", first)
        two = self.invoke_path("compile", source, "-o", second)
        self.assertEqual(one.returncode, 0, one.stderr)
        self.assertEqual(two.returncode, 0, two.stderr)
        self.assertEqual(first.read_bytes(), second.read_bytes())

    def test_seeded_expression_corpus_is_differential(self):
        rng = random.Random(20260831)

        def expression(depth):
            if depth == 0 or rng.randrange(4) == 0:
                return str(rng.randrange(0, 1000))
            left = expression(depth - 1)
            right = expression(depth - 1)
            operation = rng.choice(["+", "-", "*", "==", "!=", "<", ">="])
            return "({} {} {})".format(left, operation, right)

        text = "".join("print {};\n".format(expression(4)) for _ in range(80))
        self.assert_differential(text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
