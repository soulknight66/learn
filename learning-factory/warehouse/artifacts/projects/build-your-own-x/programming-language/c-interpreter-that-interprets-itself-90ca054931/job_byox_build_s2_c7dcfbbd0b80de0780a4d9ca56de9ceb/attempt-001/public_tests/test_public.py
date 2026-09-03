import os
from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "public_tests" / "cases"
LEXER_ONLY = os.environ.get("EMBER_LEXER_ONLY") == "1"


def interpreter() -> str:
    configured = os.environ.get("MICROC_BIN")
    if configured:
        return configured
    return str(ROOT / "starter" / "build" / "emberc")


def run_ember(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [interpreter(), *arguments],
        cwd=ROOT,
        text=True,
        input="",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=3,
        check=False,
    )


class LexerTests(unittest.TestCase):
    def test_maximal_munch_and_positions(self) -> None:
        result = run_ember("--tokens", str(CASES / "precedence.ec"))
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = result.stdout.splitlines()
        self.assertIn("2:5 PRINT print", lines)
        self.assertIn("2:13 PLUS +", lines)
        self.assertIn("2:17 STAR *", lines)
        self.assertTrue(lines[-1].endswith("EOF "), lines[-1])

    def test_unterminated_comment_is_located(self) -> None:
        result = run_ember("--tokens", str(CASES / "bad_comment.ec"))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("bad_comment.ec:2:3:", result.stderr)


@unittest.skipIf(LEXER_ONLY, "lexer milestone")
class LanguageTests(unittest.TestCase):
    def test_precedence(self) -> None:
        result = run_ember(str(CASES / "precedence.ec"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "14\n20\n1\n")

    def test_loop_and_assignment(self) -> None:
        result = run_ember(str(CASES / "factorial.ec"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "720\n")

    def test_scope_and_short_circuit(self) -> None:
        result = run_ember(str(CASES / "scope_short_circuit.ec"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "9\n3\n7\n")

    def test_arguments_and_heap(self) -> None:
        result = run_ember(
            str(CASES / "arguments_heap.ec"), "--", "12", "30"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "42\n0\n")

    def test_check_mode(self) -> None:
        result = run_ember("--check", str(CASES / "factorial.ec"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")

    def test_duplicate_declaration_is_rejected(self) -> None:
        result = run_ember("--check", str(CASES / "bad_duplicate.ec"))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("bad_duplicate.ec:3:9:", result.stderr)

    def test_runtime_overflow_is_rejected(self) -> None:
        result = run_ember(str(CASES / "bad_overflow.ec"))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("runtime error:", result.stderr)


if __name__ == "__main__":
    unittest.main()
