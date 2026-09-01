import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from contextlib import redirect_stderr, redirect_stdout
import io


ROOT = Path(__file__).resolve().parents[1]


def valid_document():
    return {
        "budget": 1.0,
        "items": [
            {"id": "api", "weight": 1.0, "target": 0.8},
            {"id": "batch", "weight": 2.0, "target": 0.4},
            {"id": "search", "weight": 4.0, "target": 0.3},
        ],
        "solver": {"tolerance": 1e-9, "max_iterations": 10000},
    }


def run_cli(raw, timeout=5.0):
    with tempfile.TemporaryDirectory() as temporary:
        input_path = Path(temporary) / "input.json"
        input_path.write_bytes(raw)
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(ROOT / "src")
        process = subprocess.Popen(
            [sys.executable, "-m", "allocation_solver", str(input_path)],
            cwd=ROOT,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        try:
            stdout, stderr = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            stdout, stderr = process.communicate()
            raise AssertionError(
                f"CLI exceeded {timeout} seconds; stdout={stdout!r}, stderr={stderr!r}"
            )
        return process.returncode, stdout, stderr


def encode(document):
    return json.dumps(document, separators=(",", ":"), allow_nan=True).encode("utf-8")


class CliSuccessTests(unittest.TestCase):
    def test_converged_output_has_exact_schema_order_and_provenance(self):
        raw = encode(valid_document())
        returncode, stdout, stderr = run_cli(raw)
        self.assertEqual(returncode, 0)
        self.assertEqual(stderr, b"")
        result = json.loads(stdout)
        self.assertEqual(
            list(result),
            ["status", "allocations", "objective", "diagnostics", "provenance"],
        )
        self.assertEqual(result["status"], "CONVERGED")
        self.assertEqual(
            [allocation["id"] for allocation in result["allocations"]],
            ["api", "batch", "search"],
        )
        self.assertTrue(
            all(set(allocation) == {"id", "amount"} for allocation in result["allocations"])
        )
        self.assertEqual(
            set(result["diagnostics"]),
            {"iterations", "tolerance", "fixed_point_residual", "feasibility_residual"},
        )
        self.assertEqual(
            set(result["provenance"]),
            {"course_id", "unit_id", "input_sha256", "algorithm", "validation_label"},
        )
        self.assertEqual(result["provenance"]["input_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(
            result["provenance"]["validation_label"],
            "LEARNER_GENERATED_NOT_INDEPENDENTLY_VALIDATED",
        )
        self.assertEqual(stdout.count(b"\n"), 1)

    def test_identical_runs_produce_identical_bytes(self):
        raw = encode(valid_document())
        first = run_cli(raw)
        second = run_cli(raw)
        self.assertEqual(first, second)

    def test_raw_formatting_changes_hash_without_normalization(self):
        compact = encode(valid_document())
        spaced = json.dumps(valid_document(), indent=2).encode("utf-8")
        compact_result = json.loads(run_cli(compact)[1])
        spaced_result = json.loads(run_cli(spaced)[1])
        self.assertNotEqual(
            compact_result["provenance"]["input_sha256"],
            spaced_result["provenance"]["input_sha256"],
        )


class CliFailureTests(unittest.TestCase):
    def assert_invalid(self, raw, expected_code):
        returncode, stdout, stderr = run_cli(raw)
        self.assertEqual(returncode, 2)
        self.assertEqual(stdout, b"")
        error = json.loads(stderr)
        self.assertEqual(set(error), {"status", "error"})
        self.assertEqual(error["status"], "INVALID_INPUT")
        self.assertEqual(error["error"]["code"], expected_code)
        self.assertEqual(set(error["error"]), {"code", "message"})
        self.assertNotIn(b"Traceback", stderr)
        self.assertEqual(stderr.count(b"\n"), 1)

    def test_malformed_json(self):
        self.assert_invalid(b"{", "INVALID_JSON")

    def test_valid_json_number_that_overflows_binary64_is_invalid_numeric(self):
        raw = (
            b'{"budget":1e309,"items":[{"id":"x","weight":1,"target":0}],'
            b'"solver":{"tolerance":1e-9,"max_iterations":1}}'
        )
        self.assert_invalid(raw, "INVALID_NUMERIC")

    def test_validation_categories_including_nonstandard_nonfinite_number(self):
        cases = []
        document = valid_document()
        document["items"] = []
        cases.append((document, "INVALID_STRUCTURE"))
        document = valid_document()
        document["items"][0]["target"] = float("nan")
        cases.append((document, "INVALID_NUMERIC"))
        document = valid_document()
        document["budget"] = -1
        cases.append((document, "INVALID_RANGE"))
        document = valid_document()
        document["items"][1]["id"] = "api"
        cases.append((document, "INVALID_ITEM_ID"))
        for document, code in cases:
            with self.subTest(code=code):
                self.assert_invalid(encode(document), code)

    def test_finite_overflow_prone_input_is_numerical_failure(self):
        document = {
            "budget": 1e308,
            "items": [
                {"id": "left", "weight": 1e308, "target": -1e308},
                {"id": "right", "weight": 1e308, "target": 1e308},
            ],
            "solver": {"tolerance": 1e-9, "max_iterations": 2},
        }
        returncode, stdout, stderr = run_cli(encode(document))
        self.assertEqual(returncode, 4)
        self.assertEqual(stdout, b"")
        self.assertEqual(
            json.loads(stderr),
            {
                "status": "NUMERICAL_FAILURE",
                "error": {
                    "code": "NONFINITE_INTERMEDIATE",
                    "message": "numerical result is not finite",
                },
            },
        )
        self.assertNotIn(b"Traceback", stderr)

    def test_exhaustion_is_result_on_stdout_with_exit_three(self):
        document = {
            "budget": 1.0,
            "items": [
                {"id": "slow", "weight": 1.0, "target": 1.0},
                {"id": "fast", "weight": 100.0, "target": 0.0},
            ],
            "solver": {"tolerance": 1e-12, "max_iterations": 1},
        }
        returncode, stdout, stderr = run_cli(encode(document))
        self.assertEqual(returncode, 3)
        self.assertEqual(stderr, b"")
        result = json.loads(stdout)
        self.assertEqual(result["status"], "MAX_ITERATIONS")
        self.assertEqual(result["diagnostics"]["iterations"], 1)
        self.assertEqual(
            result["provenance"]["validation_label"],
            "LEARNER_GENERATED_NOT_INDEPENDENTLY_VALIDATED",
        )

    def test_unexpected_failure_maps_to_stable_internal_error(self):
        from allocation_solver import cli

        stdout = io.StringIO()
        stderr = io.StringIO()
        with mock.patch.object(cli.Path, "read_bytes", return_value=b"{}"):
            with mock.patch.object(cli, "parse_input_bytes", side_effect=RuntimeError("private")):
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    returncode = cli.main(["ignored.json"])
        self.assertEqual(returncode, 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(
            json.loads(stderr.getvalue()),
            {
                "status": "INTERNAL_ERROR",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "internal solver failure",
                },
            },
        )
        self.assertNotIn("private", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
