from __future__ import annotations

import json
import math
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Callable

from learnfactory.db import Database
from learnfactory.jobs import JobRepository
from learnfactory.validation import ValidationResult, Validator
from learnfactory.vertical_slices import (
    SliceResult,
    generate_course_slice,
    generate_project_slice,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = REPOSITORY_ROOT / "migrations"


class VerticalSliceTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="learnfactory-vertical-slices-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.database = Database(self.root / "factory.db", MIGRATIONS)
        self.database.migrate()
        self.jobs = JobRepository(self.database)

    def _generate_and_validate(
        self,
        name: str,
        generator: Callable[[Path, dict[str, object], Database], SliceResult],
    ) -> tuple[Path, SliceResult, list[ValidationResult]]:
        job_id = f"job_test_{name}_vertical_slice"
        self.jobs.create(
            f"{name}_vertical_slice",
            "test",
            {},
            job_id=job_id,
        )
        workspace = self.root / name
        workspace.mkdir()
        generated = generator(workspace, {"job_id": job_id}, self.database)

        results = Validator(self.database).run(
            job_id,
            workspace,
            generated.validators,
            self.root / "logs" / job_id,
        )
        diagnostics: list[str] = []
        for result in results:
            if result.passed:
                continue
            stdout = (
                result.stdout_path.read_text(encoding="utf-8", errors="replace")
                if result.stdout_path and result.stdout_path.is_file()
                else ""
            )
            stderr = (
                result.stderr_path.read_text(encoding="utf-8", errors="replace")
                if result.stderr_path and result.stderr_path.is_file()
                else ""
            )
            diagnostics.append(
                f"{result.name}: {result.status}; evidence={result.evidence!r}; "
                f"stdout={stdout[-1000:]!r}; stderr={stderr[-1000:]!r}"
            )
        self.assertEqual(
            len(generated.validators),
            len(results),
            "validation stopped before exercising every validator",
        )
        self.assertEqual([], diagnostics, "\n".join(diagnostics))
        with self.database.connect() as connection:
            persisted = connection.execute(
                """
                SELECT COUNT(*) AS total,
                       SUM(status='PASS') AS passed
                FROM validations WHERE job_id=?
                """,
                (job_id,),
            ).fetchone()
        self.assertEqual(
            (len(generated.validators), len(generated.validators)), tuple(persisted)
        )
        return workspace, generated, results

    def test_course_slice_passes_every_returned_validator_and_records_examiner_evidence(self) -> None:
        workspace, generated, results = self._generate_and_validate(
            "course", generate_course_slice
        )

        self.assertEqual("course_vertical_slice", generated.artifact_type)
        self.assertEqual("courses/mit-6-s081/cow-transfer", generated.semantic_path)
        self.assertTrue(generated.evidence["external_validation_required"])
        self.assertEqual(len(results), generated.evidence["validator_count"])
        self.assertEqual(
            "TRANSFER_VERIFIED", generated.metadata["validation_target"]
        )
        report = json.loads(
            (workspace / "evaluations" / "attempt-001.json").read_text(encoding="utf-8")
        )
        self.assertEqual("PASS", report["result"])
        self.assertEqual(8, report["tests_run"])
        self.assertEqual(0, report["failures"])
        self.assertEqual(0, report["errors"])
        self.assertEqual("independent deterministic examiner", report["evaluator"])
        self.assertTrue(any(line.endswith("... ok") for line in report["evidence"]))
        self.assertEqual(
            0,
            next(
                result.exit_code
                for result in results
                if result.name == "independent-transfer-grader"
            ),
        )
        result_by_name = {result.name: result for result in results}
        self.assertEqual(("BUILDS",), result_by_name["course-python-syntax"].claims)
        self.assertEqual(
            ("TESTED", "TRANSFER_VERIFIED"),
            result_by_name["independent-transfer-grader"].claims,
        )

    def test_project_slice_passes_every_returned_validator_and_records_measured_benchmark(self) -> None:
        workspace = self.root / "project"
        job_id = "job_test_project_vertical_slice"
        self.jobs.create("project_vertical_slice", "test", {}, job_id=job_id)
        workspace.mkdir()
        generated = generate_project_slice(workspace, {"job_id": job_id}, self.database)
        benchmark_path = workspace / "benchmarks" / "results" / "smoke.json"
        self.assertFalse(
            benchmark_path.exists(),
            "benchmark evidence must be created by execution, not by slice generation",
        )

        results = Validator(self.database).run(
            job_id,
            workspace,
            generated.validators,
            self.root / "logs" / job_id,
        )
        diagnostics: list[str] = []
        for result in results:
            if not result.passed:
                stderr = (
                    result.stderr_path.read_text(encoding="utf-8", errors="replace")
                    if result.stderr_path and result.stderr_path.is_file()
                    else ""
                )
                diagnostics.append(
                    f"{result.name}: {result.status}; {result.evidence!r}; {stderr[-1000:]}"
                )
        self.assertEqual(len(generated.validators), len(results))
        self.assertEqual([], diagnostics, "\n".join(diagnostics))

        self.assertEqual("project_challenge_pack", generated.artifact_type)
        self.assertEqual("projects/database/durable-bytes-kv", generated.semantic_path)
        self.assertTrue(generated.evidence["external_validation_required"])
        self.assertEqual(len(results), generated.evidence["validator_count"])
        self.assertEqual(
            ["BUILDS", "TESTED", "FUZZED", "BENCHMARKED", "PARTIAL"],
            generated.metadata["validation_targets"],
        )
        self.assertEqual("NOT_PRODUCTION_READY", generated.metadata["deployment_status"])
        self.assertEqual(2, generated.metadata["artifact_revision"])
        self.assertEqual(6, generated.metadata["production_relevance"])
        self.assertEqual("NOT_PRODUCTION_READY", generated.evidence["deployment_status"])
        self.assertEqual(2, generated.evidence["artifact_revision"])

        manifest = (workspace / "MANIFEST.yaml").read_text(encoding="utf-8")
        self.assertIn("schema_version: 2", manifest)
        self.assertIn('deployment_status: "NOT_PRODUCTION_READY"', manifest)
        self.assertIn("productionized: false", manifest)
        self.assertIn("instrumented_variant: true", manifest)
        readme = (workspace / "README.md").read_text(encoding="utf-8")
        self.assertIn("python3 scripts/run_all.py", readme)
        self.assertIn("KVSTORE_IMPL=reference", readme)
        self.assertIn("KVSTORE_IMPL=production", readme)
        self.assertIn("KVSTORE_IMPL=buggy", readme)
        self.assertIn("not a claim of production readiness", readme)
        self.assertTrue((workspace / "scripts" / "run_all.py").is_file())

        for relative in (
            "adversarial/fuzz/model_fuzz.py",
            "adversarial/stress/thread_stress.py",
            "adversarial/fault-injection/torn_tail.py",
        ):
            script = (workspace / relative).read_text(encoding="utf-8")
            self.assertIn('os.environ.get("KVSTORE_IMPL", "reference")', script)
            self.assertIn('"production": ROOT / "production/implementation"', script)

        debugging_source = (
            workspace / "debugging" / "lost-delete" / "buggy" / "kvstore.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("# BUG", debugging_source)
        self.assertNotIn("delete record as a no-op", debugging_source)
        debugging_test = (
            workspace / "debugging" / "lost-delete" / "test_bug.py"
        ).read_text(encoding="utf-8")
        self.assertIn('os.environ.get("KVSTORE_IMPL", "buggy")', debugging_test)
        repair_patch = (
            workspace / "debugging" / "lost-delete" / "sealed" / "patch.diff"
        ).read_text(encoding="utf-8")
        self.assertRegex(repair_patch, r"(?m)^--- a/debugging/lost-delete/buggy/kvstore\.py$")
        self.assertRegex(repair_patch, r"(?m)^\+\+\+ b/debugging/lost-delete/buggy/kvstore\.py$")
        self.assertIsNotNone(re.search(r"(?m)^@@ -\d+(?:,\d+)? \+\d+(?:,\d+)? @@", repair_patch))
        self.assertIn("+                self._data.pop(key, None)", repair_patch)

        production_review = (
            workspace / "production" / "PRODUCTIONIZATION.md"
        ).read_text(encoding="utf-8")
        self.assertIn("not a production-ready database", production_review)
        self.assertIn("`PARTIAL`, not `PRODUCTIONIZED`", production_review)

        result_by_name = {result.name: result for result in results}
        self.assertEqual(("BUILDS",), result_by_name["project-python-syntax"].claims)
        self.assertEqual(("TESTED",), result_by_name["reference-public-tests"].claims)
        self.assertEqual(("TESTED",), result_by_name["reference-hidden-tests"].claims)
        self.assertEqual(("TESTED",), result_by_name["production-public-tests"].claims)
        self.assertEqual(
            ("TESTED", "PARTIAL"), result_by_name["production-hidden-tests"].claims
        )
        self.assertEqual(("FUZZED",), result_by_name["reference-model-fuzz"].claims)
        self.assertEqual(("FUZZED",), result_by_name["production-model-fuzz"].claims)
        self.assertEqual(("BENCHMARKED",), result_by_name["measured-smoke-benchmark"].claims)
        self.assertEqual(1, result_by_name["debugging-bug-reproduces"].exit_code)
        self.assertEqual(0, result_by_name["debugging-reference-regression"].exit_code)
        self.assertFalse(
            any("PRODUCTIONIZED" in result.claims for result in results),
            "bounded validators must not claim production readiness",
        )

        for validator_name in ("reference-hidden-tests", "production-hidden-tests"):
            stderr = result_by_name[validator_name].stderr_path.read_text(encoding="utf-8")
            for test_name in (
                "test_short_writes_are_completed_before_acknowledgement",
                "test_partial_write_failure_poisons_store",
                "test_failed_replace_keeps_original_store_usable",
                "test_directory_fsync_failure_keeps_replacement_usable",
                "test_checksummed_wrong_shape_is_normalized_as_corruption",
            ):
                self.assertIn(test_name, stderr)
        run_all = subprocess.run(
            [sys.executable, "scripts/run_all.py"],
            cwd=workspace,
            text=True,
            capture_output=True,
            timeout=60,
            check=False,
        )
        self.assertEqual(
            0,
            run_all.returncode,
            f"stdout={run_all.stdout[-2000:]!r}\nstderr={run_all.stderr[-2000:]!r}",
        )
        self.assertIn("all bounded validation stages behaved as expected", run_all.stdout)
        self.assertTrue(benchmark_path.is_file())
        benchmark = json.loads(benchmark_path.read_text(encoding="utf-8"))
        self.assertEqual(1, benchmark["schema_version"])
        self.assertTrue(benchmark["hypothesis"])
        self.assertEqual(
            {"operations": 500, "sync": False, "value_bytes": 100},
            benchmark["parameters"],
        )
        self.assertTrue(benchmark["environment"]["python"])
        self.assertTrue(benchmark["environment"]["implementation"])
        self.assertTrue(benchmark["environment"]["platform"])
        self.assertEqual({"production", "reference"}, set(benchmark["raw_results"]))
        for implementation, measurement in benchmark["raw_results"].items():
            with self.subTest(implementation=implementation):
                self.assertEqual(500, measurement["operations"])
                self.assertGreater(measurement["open_ns"], 0)
                self.assertGreater(measurement["write_total_ns"], 0)
                self.assertGreater(measurement["write_ns_per_op"], 0)
                self.assertGreater(measurement["read_total_ns"], 0)
                self.assertGreater(measurement["read_ns_per_op"], 0)
                self.assertGreater(measurement["file_bytes"], 0)
        ratio = benchmark["summary"]["production_to_reference_write_ratio"]
        self.assertTrue(math.isfinite(ratio))
        self.assertGreater(ratio, 0)
        benchmark_validation = next(
            result for result in results if result.name == "measured-smoke-benchmark"
        )
        self.assertEqual(0, benchmark_validation.exit_code)
        self.assertTrue(benchmark_validation.stdout_path.is_file())
        self.assertTrue(benchmark_validation.stdout_path.read_text(encoding="utf-8").strip())
        with self.database.connect() as connection:
            persisted = connection.execute(
                """
                SELECT COUNT(*) AS total,
                       SUM(status='PASS') AS passed
                FROM validations WHERE job_id=?
                """,
                (job_id,),
            ).fetchone()
        self.assertEqual((len(generated.validators), len(generated.validators)), tuple(persisted))


if __name__ == "__main__":
    unittest.main()
