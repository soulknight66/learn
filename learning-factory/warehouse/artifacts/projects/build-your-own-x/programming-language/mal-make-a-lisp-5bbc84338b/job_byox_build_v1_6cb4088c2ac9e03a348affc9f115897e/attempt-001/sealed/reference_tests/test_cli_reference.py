import os
import subprocess
import sys
import unittest


class CliBoundaryTests(unittest.TestCase):
    def run_cli(self, arguments, input_text=None):
        return subprocess.run(
            [sys.executable, "-m", "sprig"] + arguments,
            input=input_text,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )

    def test_blank_expression_produces_no_output(self):
        result = self.run_cli(["-e", " ; blank"])
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, "", ""))

    def test_mutually_exclusive_inputs_are_an_argument_error(self):
        result = self.run_cli(["-e", "1", "file.sp"])
        self.assertEqual(result.returncode, 2)
        self.assertIn("mutually exclusive", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_disassembly_requires_vm(self):
        result = self.run_cli(["--disassemble", "-e", "1"])
        self.assertEqual(result.returncode, 2)
        self.assertIn("requires --engine vm", result.stderr)

    def test_missing_file_has_stable_error(self):
        path = "definitely-not-a-sprig-source-{0}.sp".format(os.getpid())
        result = self.run_cli([path])
        self.assertEqual(result.returncode, 2)
        self.assertIn("CLI_FILE", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_repl_retains_definitions_between_lines(self):
        result = self.run_cli([], "(def x 5)\n(+ x 2)\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("5\n", result.stdout)
        self.assertTrue(result.stdout.endswith("7\nsprig> "))

    def test_repl_language_error_exits_two_without_traceback(self):
        result = self.run_cli([], "missing\n")
        self.assertEqual(result.returncode, 2)
        self.assertIn("NAME_UNBOUND", result.stderr)
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
