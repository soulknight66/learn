from __future__ import annotations

import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from learnfactory.db import Database
from learnfactory.event_service_slice import generate_event_service_slice
from learnfactory.jobs import JobRepository
from learnfactory.util import tree_sha256
from learnfactory.validation import ValidationResult, Validator


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = REPOSITORY_ROOT / "migrations"


class EventServiceSliceTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="learnfactory-event-slice-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.database = Database(self.root / "factory.db", MIGRATIONS)
        self.database.migrate()
        self.jobs = JobRepository(self.database)

    @staticmethod
    def _diagnostics(results: list[ValidationResult]) -> list[str]:
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
                f"stdout={stdout[-1500:]!r}; stderr={stderr[-2500:]!r}"
            )
        return diagnostics

    def test_deep_pack_passes_independent_validation_and_records_real_evidence(self) -> None:
        job_id = "job_test_event_service_slice"
        self.jobs.create("event_service_slice", "test", {}, job_id=job_id)
        workspace = self.root / "event-service"
        workspace.mkdir()
        generated = generate_event_service_slice(
            workspace,
            {
                "job_id": job_id,
                "untrusted_secret": "MUST_NOT_BE_ARCHIVED",
            },
            self.database,
        )

        benchmark_path = workspace / "benchmarks" / "results" / "smoke.json"
        self.assertFalse(
            benchmark_path.exists(),
            "benchmark evidence must originate from the validator's real execution",
        )
        self.assertEqual("event_service_challenge_pack", generated.artifact_type)
        self.assertEqual(
            "projects/production-services/durable-event-processing-service",
            generated.semantic_path,
        )
        self.assertTrue(generated.evidence["external_validation_required"])
        self.assertTrue(generated.evidence["benchmark_generated_during_validation"])
        self.assertEqual("NOT_PRODUCTION_READY", generated.evidence["deployment_status"])
        self.assertEqual("NOT_PRODUCTION_READY", generated.metadata["deployment_status"])
        self.assertFalse(generated.metadata["productionized"])
        self.assertEqual(1, generated.metadata["debugging_challenges"])
        self.assertEqual(1, generated.metadata["review_exercises"])
        self.assertEqual(
            "agent-generated cross-source synthesis",
            generated.metadata["provenance"]["derivation"],
        )
        self.assertEqual(
            generated.evidence["candidate_tree_sha256"],
            generated.evidence["pre_validation_tree_sha256"],
        )
        self.assertIn(
            "event-pack-tree-checksum",
            generated.evidence["final_tree_sha256_evidence"],
        )

        provenance_text = (workspace / "PROVENANCE.json").read_text(encoding="utf-8")
        self.assertNotIn("MUST_NOT_BE_ARCHIVED", provenance_text)
        provenance = json.loads(provenance_text)
        self.assertEqual("agent-generated cross-source synthesis", provenance["derivation"])
        self.assertEqual("INCOMPLETE", provenance["catalog_context"]["provenance_status"])
        self.assertFalse(provenance["tutorial_code_copied"])
        self.assertFalse(provenance["network_used_during_generation"])
        self.assertEqual([], provenance["external_dependencies"])

        results = Validator(self.database).run(
            job_id,
            workspace,
            generated.validators,
            self.root / "logs" / job_id,
        )
        self.assertEqual(
            len(generated.validators),
            len(results),
            "a failure stopped validation before every independent check ran",
        )
        self.assertEqual([], self._diagnostics(results))
        self.assertEqual(len(results), generated.evidence["validator_count"])
        self.assertNotEqual(
            generated.evidence["pre_validation_tree_sha256"],
            tree_sha256(workspace),
            "validation-produced benchmark must be outside the pre-validation tree hash",
        )
        result_by_name = {result.name: result for result in results}

        self.assertEqual(("BUILDS", "PARTIAL"), result_by_name["event-python-syntax"].claims)
        self.assertEqual(
            ("TESTED", "PARTIAL"),
            result_by_name["reference-withheld-contract"].claims,
        )
        self.assertEqual(
            ("TESTED", "FUZZED", "PARTIAL"),
            result_by_name["concurrent-ingest-and-claims"].claims,
        )
        self.assertEqual(
            ("FUZZED", "PARTIAL"),
            result_by_name["deterministic-queue-model-fuzz"].claims,
        )
        self.assertEqual(
            ("BENCHMARKED", "PARTIAL"),
            result_by_name["measured-event-service-benchmark"].claims,
        )
        self.assertEqual(
            ("TESTED", "REVIEWED", "PARTIAL"),
            result_by_name["review-race-demonstration"].claims,
        )
        self.assertFalse(
            any("PRODUCTIONIZED" in result.claims for result in results),
            "bounded evidence must never make a deployment-readiness claim",
        )
        crash_stdout = result_by_name["crash-after-effect-before-ack"].stdout_path
        self.assertIsNotNone(crash_stdout)
        assert crash_stdout is not None
        self.assertIn(
            "child-process death after durable effect",
            crash_stdout.read_text(encoding="utf-8"),
        )
        self.assertEqual(23, result_by_name["dead-letter-bug-reproduces"].exit_code)
        self.assertEqual(0, result_by_name["dead-letter-reference-repairs"].exit_code)
        review_stdout = result_by_name["review-race-demonstration"].stdout_path
        self.assertIsNotNone(review_stdout)
        assert review_stdout is not None
        self.assertIn(
            "two callers returning ownership of one message",
            review_stdout.read_text(encoding="utf-8"),
        )

        hidden_stderr = result_by_name["reference-withheld-contract"].stderr_path
        self.assertIsNotNone(hidden_stderr)
        assert hidden_stderr is not None
        hidden_evidence = hidden_stderr.read_text(encoding="utf-8")
        for test_name in (
            "test_concurrent_claim_has_one_winner",
            "test_expired_lease_recovers_after_process_crash",
            "test_stale_same_owner_delivery_is_fenced_from_new_claim",
            "test_expired_release_is_rejected",
            "test_heartbeat_never_shortens_a_live_lease",
            "test_repeated_crash_expiry_exhausts_attempt_budget",
            "test_crash_after_side_effect_before_ack_does_not_duplicate_effect",
            "test_retry_schedule_and_poison_dead_letter_boundary",
            "test_bounded_prefetch_structured_observability_and_graceful_drain",
            "test_claim_on_demand_survives_slow_sequential_handlers",
        ):
            self.assertIn(test_name, hidden_evidence)

        self.assertTrue(benchmark_path.is_file())
        benchmark = json.loads(benchmark_path.read_text(encoding="utf-8"))
        self.assertEqual(1, benchmark["schema_version"])
        self.assertEqual(
            {
                "messages": 80,
                "repetitions": 2,
                "capacities": [1, 8],
                "dispatch_policy": "claim_on_demand_one_outstanding",
                "payload_bytes_approximate": 75,
            },
            benchmark["parameters"],
        )
        self.assertTrue(benchmark["hypothesis"])
        self.assertTrue(benchmark["interpretation_boundary"])
        self.assertTrue(benchmark["environment"]["python"])
        self.assertTrue(benchmark["environment"]["platform"])
        self.assertTrue(benchmark["environment"]["sqlite"])
        self.assertIn("sealed/reference/event_service.py", benchmark["environment"]["implementation"])
        self.assertEqual(64, len(benchmark["environment"]["implementation_sha256"]))
        self.assertGreater(benchmark["measured_at_unix_ns"], 0)
        self.assertEqual(4, len(benchmark["raw_samples"]))
        self.assertEqual({1, 8}, {row["capacity"] for row in benchmark["raw_samples"]})
        for sample in benchmark["raw_samples"]:
            self.assertEqual(80, sample["messages"])
            self.assertEqual(1, sample["effective_outstanding_limit"])
            self.assertGreater(sample["ingest_ns"], 0)
            self.assertGreater(sample["delivery_ns"], 0)
            self.assertGreater(sample["total_ns"], 0)
            self.assertGreater(sample["database_bytes"], 0)
            self.assertTrue(math.isfinite(sample["messages_per_second"]))
            self.assertGreater(sample["messages_per_second"], 0)

        repeated_results = Validator(self.database).run(
            job_id,
            workspace,
            generated.validators,
            self.root / "logs" / f"{job_id}-repeat",
        )
        self.assertEqual([], self._diagnostics(repeated_results))
        self.assertEqual(len(generated.validators), len(repeated_results))
        repeated_benchmark = json.loads(benchmark_path.read_text(encoding="utf-8"))
        self.assertGreater(
            repeated_benchmark["measured_at_unix_ns"], benchmark["measured_at_unix_ns"]
        )

        with self.database.connect() as connection:
            persisted = connection.execute(
                """
                SELECT COUNT(*) AS total,SUM(status='PASS') AS passed
                FROM validations WHERE job_id=?
                """,
                (job_id,),
            ).fetchone()
        expected_validation_rows = len(results) + len(repeated_results)
        self.assertEqual(
            (expected_validation_rows, expected_validation_rows), tuple(persisted)
        )

    def test_regeneration_discards_stale_measured_output(self) -> None:
        workspace = self.root / "regenerated-pack"
        workspace.mkdir()
        first = generate_event_service_slice(
            workspace, {"job_id": "job_regeneration"}, self.database
        )
        benchmark_path = workspace / "benchmarks" / "results" / "smoke.json"
        benchmark_path.write_text('{"stale":true}\n', encoding="utf-8")

        second = generate_event_service_slice(
            workspace, {"job_id": "job_regeneration"}, self.database
        )

        self.assertFalse(benchmark_path.exists())
        self.assertEqual(len(first.validators), len(second.validators))
        self.assertEqual(
            second.evidence["candidate_tree_sha256"],
            second.evidence["pre_validation_tree_sha256"],
        )

    def test_progressive_view_and_exercise_answers_are_structurally_separate(self) -> None:
        job_id = "job_test_event_boundaries"
        self.jobs.create("event_service_slice", "test", {}, job_id=job_id)
        workspace = self.root / "boundary-pack"
        workspace.mkdir()
        generated = generate_event_service_slice(
            workspace, {"job_id": job_id}, self.database
        )
        catalog_entry = json.loads(
            (workspace / "CATALOG_ENTRY.json").read_text(encoding="utf-8")
        )
        self.assertEqual(["GENERATED", "PARTIAL"], catalog_entry["validation_status"])
        self.assertIn("BENCHMARKED", catalog_entry["validation_targets"])
        self.assertNotIn("BENCHMARKED", catalog_entry["validation_status"])

        student_view = self.root / "materialized-student"
        completed = subprocess.run(
            [
                sys.executable,
                str(workspace / "environment" / "materialize_student_view.py"),
                str(student_view),
            ],
            cwd=workspace,
            text=True,
            capture_output=True,
            timeout=20,
            check=False,
        )
        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertTrue((student_view / "starter" / "event_service.py").is_file())
        self.assertTrue((student_view / "public_tests" / "test_public_contract.py").is_file())
        for forbidden in (
            "sealed",
            "production",
            "adversarial",
            "debugging",
            "review_exercises",
            "benchmarks",
        ):
            self.assertFalse((student_view / forbidden).exists())
        all_student_text = "\n".join(
            path.read_text(encoding="utf-8", errors="replace")
            for path in student_view.rglob("*")
            if path.is_file()
        )
        self.assertNotIn("EXPECTED_REVIEW", all_student_text)
        self.assertNotIn("if attempts >= self.max_attempts", all_student_text)

        injected_link = workspace / "starter" / "answer-leak"
        injected_link.symlink_to(workspace / "sealed", target_is_directory=True)
        rejected_view = self.root / "rejected-student-view"
        rejected = subprocess.run(
            [
                sys.executable,
                str(workspace / "environment" / "materialize_student_view.py"),
                str(rejected_view),
            ],
            cwd=workspace,
            text=True,
            capture_output=True,
            timeout=20,
            check=False,
        )
        self.assertNotEqual(0, rejected.returncode)
        self.assertIn("contains a symlink", rejected.stderr)
        injected_link.unlink()

        buggy = (
            workspace
            / "debugging"
            / "dead-letter-off-by-one"
            / "buggy"
            / "event_service.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("# BUG", buggy)
        self.assertIn("if attempts > self.max_attempts", buggy)
        patch = (
            workspace
            / "debugging"
            / "dead-letter-off-by-one"
            / "sealed"
            / "patch.diff"
        ).read_text(encoding="utf-8")
        self.assertIn("-            if attempts > self.max_attempts:", patch)
        self.assertIn("+            if attempts >= self.max_attempts:", patch)
        self.assertEqual(1, patch.count("@@") // 2)

        production_review = (
            workspace / "production" / "PRODUCTIONIZATION.md"
        ).read_text(encoding="utf-8")
        self.assertIn("not a production-ready event service", production_review)
        self.assertIn("`PARTIAL`, never `PRODUCTIONIZED`", production_review)
        self.assertEqual(
            [
                "BUILDS",
                "TESTED",
                "FUZZED",
                "BENCHMARKED",
                "REVIEWED",
                "PARTIAL",
            ],
            generated.metadata["validation_targets"],
        )

    def test_generator_rejects_a_symlink_workspace(self) -> None:
        actual = self.root / "actual"
        actual.mkdir()
        alias = self.root / "alias"
        alias.symlink_to(actual, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "existing real directory"):
            generate_event_service_slice(alias, {}, self.database)


if __name__ == "__main__":
    unittest.main()
