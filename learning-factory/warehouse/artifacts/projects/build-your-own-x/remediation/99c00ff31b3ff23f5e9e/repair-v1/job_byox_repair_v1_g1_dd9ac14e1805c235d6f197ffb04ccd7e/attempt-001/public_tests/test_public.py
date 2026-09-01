#!/usr/bin/env python3
"""Deterministic black-box tests for the learner-visible Mica contract."""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
TEMP_PARENT = ROOT / "environment" / ".test-work"


class MicaPublicTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        configured = os.environ.get("MICA_BIN")
        if configured:
            candidate = Path(configured)
            cls.mica = candidate if candidate.is_absolute() else ROOT / candidate
        else:
            subprocess.run(
                ["make", "-C", str(ROOT / "starter"), "all"],
                cwd=str(ROOT),
                check=True,
                timeout=30,
            )
            cls.mica = ROOT / "starter" / "mica"
        TEMP_PARENT.mkdir(parents=True, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        try:
            TEMP_PARENT.rmdir()
        except OSError:
            pass

    def setUp(self):
        self.work = Path(tempfile.mkdtemp(prefix="public-", dir=str(TEMP_PARENT)))

    def tearDown(self):
        shutil.rmtree(str(self.work))

    def source(self, text, name="program.mica"):
        path = self.work / name
        path.write_text(text, encoding="ascii")
        return path

    def source_bytes(self, content, name="program.mica"):
        path = self.work / name
        path.write_bytes(content)
        return path

    def invoke(self, *arguments, timeout=10):
        return subprocess.run(
            [str(self.mica)] + [str(item) for item in arguments],
            cwd=str(ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            timeout=timeout,
        )

    def compile_and_run(self, text):
        source = self.source(text)
        assembly = self.work / "program.s"
        executable = self.work / "program"
        compiled = self.invoke("compile", source, "-o", assembly)
        self.assertEqual(compiled.returncode, 0, compiled.stderr)
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
            timeout=10,
        )

    def test_tokens_include_positions_comments_and_longest_match(self):
        source = self.source("let score=12;\n// ignored\nprint score<=20;\n")
        result = self.invoke("tokens", source)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout,
            "1:1 LET let\n"
            "1:5 IDENTIFIER score\n"
            "1:10 ASSIGN =\n"
            "1:11 INTEGER 12\n"
            "1:13 SEMICOLON ;\n"
            "3:1 PRINT print\n"
            "3:7 IDENTIFIER score\n"
            "3:12 LESS_EQUAL <=\n"
            "3:14 INTEGER 20\n"
            "3:16 SEMICOLON ;\n"
            "4:1 EOF -\n",
        )

    def test_lexical_error_has_phase_and_location(self):
        source = self.source("print 1 ! 2;\n")
        result = self.invoke("tokens", source)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertIn("mica: lexical error: 1:9:", result.stderr)

    def test_ascii_whitespace_bytes_and_columns(self):
        accepted = self.invoke(
            "tokens", self.source_bytes(b"print \t\r1;\n", "accepted.mica")
        )
        self.assertEqual(accepted.returncode, 0, accepted.stderr)
        self.assertEqual(
            accepted.stdout,
            "1:1 PRINT print\n"
            "1:9 INTEGER 1\n"
            "1:10 SEMICOLON ;\n"
            "2:1 EOF -\n",
        )
        for byte, name in ((b"\x0b", "vertical-tab"), (b"\x0c", "form-feed")):
            result = self.invoke(
                "tokens", self.source_bytes(b"print" + byte + b"1;", name + ".mica")
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(result.stdout, "")
            self.assertTrue(
                result.stderr.startswith("mica: lexical error: 1:6:"), result.stderr
            )
            self.assertEqual(len(result.stderr.splitlines()), 1)

    def test_invalid_usage_is_one_phase_prefixed_line(self):
        result = self.invoke()
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertTrue(result.stderr.startswith("mica: usage error:"), result.stderr)
        self.assertEqual(len(result.stderr.splitlines()), 1)

    def test_interpreter_precedence_wrap_and_signed_division(self):
        source = self.source(
            "print 2 + 3 * 4;\n"
            "print (2 + 3) * 4;\n"
            "print -7 / 3;\n"
            "print -7 % 3;\n"
            "print 9223372036854775807 + 1;\n"
        )
        result = self.invoke("run", source)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "14\n20\n-2\n-1\n-9223372036854775808\n")

    def test_control_flow_and_assignment(self):
        source = self.source(
            "let i = 0;\n"
            "let total = 0;\n"
            "while (i < 6) { total = total + i; i = i + 1; }\n"
            "if (total == 15) { print total; } else { print 0; }\n"
        )
        result = self.invoke("run", source)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "15\n")

    def test_undeclared_name_is_validation_error(self):
        result = self.invoke("run", self.source("print missing;\n"))
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertIn("mica: validation error: 1:7:", result.stderr)

    def test_division_by_zero_is_runtime_error(self):
        result = self.invoke("run", self.source("print 9 / (3 - 3);\n"))
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertIn("mica: runtime error:", result.stderr)
        self.assertIn("division by zero", result.stderr)

    def test_compiled_output_matches_interpreter(self):
        text = (
            "let n = 7; let product = 1;\n"
            "while (n > 1) { product = product * n; n = n - 1; }\n"
            "print product;\n"
            "print product >= 5040;\n"
        )
        interpreted = self.invoke("run", self.source(text, "interpreted.mica"))
        self.assertEqual(interpreted.returncode, 0, interpreted.stderr)
        native = self.compile_and_run(text)
        self.assertEqual(native.returncode, 0, native.stderr)
        self.assertEqual(native.stdout, interpreted.stdout)
        self.assertEqual(native.stderr, "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
