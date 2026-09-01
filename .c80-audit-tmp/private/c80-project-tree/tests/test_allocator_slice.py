from __future__ import annotations

import json
import math
import re
import tempfile
import unittest
from pathlib import Path

from learnfactory.allocator_slice import PROJECT_ID, generate_allocator_slice
from learnfactory.db import Database
from learnfactory.jobs import JobRepository
from learnfactory.util import tree_sha256
from learnfactory.validation import ValidationResult, Validator


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = REPOSITORY_ROOT / "migrations"


class AllocatorSliceTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="learnfactory-allocator-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.database = Database(self.root / "factory.db", MIGRATIONS)
        self.database.migrate()
        self.jobs = JobRepository(self.database)
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                """
                INSERT INTO sources(
                    source_id,type,name,path,upstream_url,commit_hash,license,
                    ingested_at,metadata_json
                ) VALUES (?,?,?,?,?,?,?,?,?)
                """,
                (
                    "source_allocator_fixture",
                    "project_catalog",
                    "Build Your Own X active fixture",
                    "/authorized/public/build-your-own-x",
                    "https://github.com/codecrafters-io/build-your-own-x",
                    "feedface0123456789",
                    "CC0-1.0 fixture",
                    1.0,
                    json.dumps({"linked_resource_license": "NOASSERTION"}),
                ),
            )
            connection.execute(
                """
                INSERT INTO build_projects(
                    project_id,source_id,slug,title,category,implementation_language,
                    upstream_reference,concepts_json,difficulty,production_relevance,
                    source_format,priority_tier,metadata_json
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    PROJECT_ID,
                    "source_allocator_fixture",
                    "malloc-is-not-magic-implementing-your-own-memory-allocator",
                    "Malloc is not magic -- Implementing your own memory allocator",
                    "Memory Allocator",
                    "C",
                    "https://example.invalid/public-allocator-article",
                    '["memory management","fragmentation","systems programming"]',
                    8.0,
                    8.5,
                    "article",
                    1,
                    json.dumps({"linked_resource_license": "NOASSERTION"}),
                ),
            )

    def _generate(self, job_id: str, *, workspace_name: str | None = None):
        self.jobs.create("allocator_slice", "test", {}, job_id=job_id)
        workspace = self.root / (workspace_name or job_id)
        workspace.mkdir()
        generated = generate_allocator_slice(
            workspace,
            {
                "job_id": job_id,
                "project_id": PROJECT_ID,
                # This untrusted payload must not replace authoritative active-source metadata.
                "provenance": {
                    "source": "spoofed source",
                    "commit": "spoofed commit",
                },
            },
            self.database,
        )
        return workspace, generated

    def test_generation_is_deterministic_and_preserves_progressive_boundaries(self) -> None:
        workspace, generated = self._generate("job_allocator_generation")

        self.assertEqual("allocator_challenge_pack", generated.artifact_type)
        self.assertEqual(
            "projects/systems/caller-owned-arena-c-allocator",
            generated.semantic_path,
        )
        self.assertEqual(PROJECT_ID, generated.metadata["source_project_id"])
        self.assertEqual(3, generated.metadata["architecture_count"])
        self.assertEqual(2, generated.metadata["alternative_architecture_count"])
        self.assertEqual("NOT_PRODUCTION_READY", generated.metadata["deployment_status"])
        self.assertFalse(generated.metadata["productionized"])
        self.assertNotIn("PRODUCTIONIZED", generated.metadata["validation_targets"])
        self.assertFalse((workspace / "benchmarks/results/smoke.json").exists())
        self.assertFalse((workspace / "validation-output").exists())

        provenance = json.loads((workspace / "PROVENANCE.json").read_text(encoding="utf-8"))
        source = provenance["catalog_source"]
        self.assertEqual(PROJECT_ID, source["project_id"])
        self.assertEqual("active_database_record", source["lookup_status"])
        self.assertEqual("Build Your Own X active fixture", source["source_name"])
        self.assertEqual("feedface0123456789", source["commit_hash"])
        self.assertEqual("CC0-1.0 fixture", source["catalog_license"])
        self.assertEqual("NOASSERTION", source["linked_resource_license"])
        self.assertEqual(
            "https://example.invalid/public-allocator-article",
            source["external_reference"],
        )
        self.assertNotEqual("spoofed source", source["source_name"])
        self.assertFalse(provenance["network_used_during_generation"])
        self.assertIn("not mirrored", provenance["license_boundary"]["linked_tutorial"])
        self.assertIn("measured", provenance["derivation"])

        manifest = json.loads((workspace / "MANIFEST.yaml").read_text(encoding="utf-8"))
        self.assertEqual("GENERATED_CANDIDATE", manifest["status"])
        self.assertEqual("NOT_PRODUCTION_READY", manifest["deployment_status"])
        self.assertFalse(manifest["productionized"])
        self.assertEqual(3, len(manifest["architectures"]))
        self.assertIn("PARTIAL", manifest["validation_targets"])
        self.assertNotIn("FUZZED", manifest["validation_targets"])
        self.assertNotIn("PRODUCTIONIZED", manifest["validation_targets"])

        readme = (workspace / "README.md").read_text(encoding="utf-8")
        requirements = (workspace / "REQUIREMENTS.md").read_text(encoding="utf-8")
        header = (workspace / "include/allocator.h").read_text(encoding="utf-8")
        tradeoffs = (workspace / "sealed/TRADEOFFS.md").read_text(encoding="utf-8")
        self.assertIn("portable effective-type contract", readme)
        self.assertIn("alignment and a cast do not change its effective type", requirements)
        self.assertIn(
            "casted, declared unsigned char array is outside this portable contract",
            header,
        )
        self.assertIn("known contract boundary, not a runtime-detected property", tradeoffs)
        for relative in (
            "public_tests/contract.c",
            "sealed/reference_tests/contract.c",
            "sealed/reference_tests/segregated_integrity.c",
            "adversarial/model_randomized.c",
            "benchmarks/benchmark.c",
            "debugging/coalesce-span/regression.c",
        ):
            fixture = (workspace / relative).read_text(encoding="utf-8")
            self.assertIn("malloc(", fixture, relative)
            self.assertNotIn("_Alignas", fixture, relative)

        learner_files = [
            *workspace.joinpath("starter").rglob("*"),
            *workspace.joinpath("public_tests").rglob("*"),
            *workspace.joinpath("include").rglob("*"),
        ]
        learner_text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in learner_files
            if path.is_file()
        )
        for forbidden in (
            "root-cause.md",
            "EXPECTED_REVIEW",
            "item->size += HEADER_SIZE + next->size",
            "segregated-size-class-bins",
        ):
            self.assertNotIn(forbidden, learner_text)
        self.assertFalse((workspace / "starter/sealed").exists())
        self.assertFalse((workspace / "public_tests/reference").exists())

        command_specs = [
            spec for spec in generated.validators if spec.get("type") == "command"
        ]
        self.assertGreaterEqual(len(command_specs), 15)
        for spec in command_specs:
            with self.subTest(validator=spec["name"]):
                self.assertIsInstance(spec["argv"], list)
                self.assertTrue(spec["argv"])
                self.assertTrue(all(isinstance(value, str) for value in spec["argv"]))
                self.assertNotIn("shell", spec)
                self.assertIn("PARTIAL", spec["claims"])
                self.assertNotIn("FUZZED", spec["claims"])
                self.assertNotIn("PRODUCTIONIZED", spec["claims"])

        second_workspace = self.root / "deterministic-second"
        second_workspace.mkdir()
        second = generate_allocator_slice(
            second_workspace,
            {"job_id": "job_allocator_generation", "project_id": PROJECT_ID},
            self.database,
        )
        self.assertEqual(generated.evidence["candidate_tree_sha256"], tree_sha256(workspace))
        self.assertEqual(generated.evidence["candidate_tree_sha256"], tree_sha256(second_workspace))
        self.assertEqual(generated.evidence["validator_count"], len(second.validators))

    def test_generation_rejects_a_contaminated_workspace(self) -> None:
        job_id = "job_allocator_contaminated_workspace"
        self.jobs.create("allocator_slice", "test", {}, job_id=job_id)
        workspace = self.root / job_id
        workspace.mkdir()
        starter = workspace / "starter"
        starter.mkdir()
        (starter / "reveal").symlink_to("../sealed")

        with self.assertRaisesRegex(ValueError, "must be empty"):
            generate_allocator_slice(
                workspace,
                {"job_id": job_id, "project_id": PROJECT_ID},
                self.database,
            )

    def test_generation_accepts_the_orchestrator_workspace_marker(self) -> None:
        job_id = "job_allocator_managed_workspace"
        self.jobs.create("allocator_slice", "test", {}, job_id=job_id)
        workspace = self.root / job_id
        workspace.mkdir()
        (workspace / ".factory-workspace").write_text("managed\n", encoding="utf-8")

        generated = generate_allocator_slice(
            workspace,
            {"job_id": job_id, "project_id": PROJECT_ID},
            self.database,
        )

        self.assertEqual("allocator_challenge_pack", generated.artifact_type)

    def test_every_validator_passes_with_executed_benchmark_and_proven_bug(self) -> None:
        job_id = "job_allocator_all_validators"
        workspace, generated = self._generate(job_id)
        self.assertFalse((workspace / "benchmarks/results/smoke.json").exists())

        results = Validator(self.database).run(
            job_id,
            workspace,
            generated.validators,
            self.root / "logs" / job_id,
        )
        diagnostics = [self._diagnostic(result) for result in results if not result.passed]
        self.assertEqual(
            len(generated.validators),
            len(results),
            "validation stopped before exercising every declared validator",
        )
        self.assertEqual([], diagnostics, "\n".join(diagnostics))
        with self.database.connect() as connection:
            persisted = connection.execute(
                """
                SELECT COUNT(*) AS total,SUM(status='PASS') AS passed
                FROM validations WHERE job_id=?
                """,
                (job_id,),
            ).fetchone()
        self.assertEqual(
            (len(generated.validators), len(generated.validators)), tuple(persisted)
        )

        by_name = {result.name: result for result in results}
        for architecture, implementation_name in {
            "reference": "address-ordered-first-fit",
            "best-fit": "address-ordered-best-fit",
            "segregated-bins": "segregated-size-class-bins",
        }.items():
            with self.subTest(architecture=architecture):
                self.assertEqual(0, by_name[f"{architecture}-public-contract"].exit_code)
                hidden = by_name[f"{architecture}-withheld-contract"]
                self.assertEqual(0, hidden.exit_code)
                self.assertEqual(("TESTED", "PARTIAL"), hidden.claims)
                assert hidden.stdout_path is not None
                self.assertIn(
                    implementation_name,
                    hidden.stdout_path.read_text(encoding="utf-8"),
                )
                model = by_name[f"{architecture}-deterministic-model"]
                self.assertEqual(0, model.exit_code)
                self.assertEqual(("TESTED", "PARTIAL"), model.claims)
                assert model.stdout_path is not None
                model_output = model.stdout_path.read_text(encoding="utf-8")
                self.assertIn("seed=0x20260830", model_output)
                self.assertIn("iterations=4000", model_output)
                resize_failures = re.search(r"resize_failures=(\d+)", model_output)
                self.assertIsNotNone(resize_failures)
                assert resize_failures is not None
                self.assertGreater(int(resize_failures.group(1)), 0)

        toolchain = json.loads(
            (workspace / "validation-output/toolchain.json").read_text(encoding="utf-8")
        )
        self.assertIn("gcc", toolchain["compiler"].lower())
        self.assertIn("-Werror", toolchain["strict_flags"])
        self.assertFalse(toolchain["network_used"])
        expected_architectures = {"reference", "best-fit", "segregated-bins"}
        self.assertEqual(
            expected_architectures,
            set(toolchain["sanitizer"]["requested_architectures"]),
        )
        sanitizer = json.loads(
            (workspace / "validation-output/sanitizer-result.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(expected_architectures, set(sanitizer["requested_architectures"]))
        if sanitizer["probe_available"]:
            self.assertEqual("PASS", sanitizer["status"])
            self.assertEqual(0, sanitizer["exit_code"])
            self.assertEqual(expected_architectures, set(sanitizer["architectures"]))
            for architecture, result in sanitizer["architectures"].items():
                with self.subTest(sanitized_architecture=architecture):
                    self.assertEqual(0, result["exit_code"])
                    self.assertIn("deterministic model passed", result["stdout"])
        else:
            self.assertEqual("SKIPPED_UNAVAILABLE", sanitizer["status"])
            self.assertIsNone(sanitizer["exit_code"])
            self.assertEqual({}, sanitizer["architectures"])

        integrity = by_name["segregated-bin-topology-corruption"]
        self.assertEqual(0, integrity.exit_code)
        assert integrity.stdout_path is not None
        self.assertIn(
            "reject missing, inconsistent, duplicate, and extraneous nodes",
            integrity.stdout_path.read_text(encoding="utf-8"),
        )

        buggy_result = by_name["debugging-corruption-reproduces"]
        fixed_result = by_name["debugging-patch-regression"]
        self.assertEqual(1, buggy_result.exit_code)
        self.assertEqual(0, fixed_result.exit_code)
        assert buggy_result.stderr_path is not None
        assert fixed_result.stdout_path is not None
        self.assertIn(
            "detected allocator metadata corruption after adjacent coalescing",
            buggy_result.stderr_path.read_text(encoding="utf-8"),
        )
        self.assertIn(
            "retained the exact physical arena span",
            fixed_result.stdout_path.read_text(encoding="utf-8"),
        )
        buggy_source = (workspace / "debugging/coalesce-span/buggy/allocator.c").read_text(
            encoding="utf-8"
        )
        reference_source = (workspace / "sealed/reference/allocator.c").read_text(
            encoding="utf-8"
        )
        repaired = buggy_source.replace(
            "item->size += (2U * HEADER_SIZE) + next->size;",
            "item->size += HEADER_SIZE + next->size;",
        )
        self.assertEqual(reference_source, repaired, "debug challenge must contain one root cause")
        patch = (workspace / "debugging/coalesce-span/sealed/patch.diff").read_text(
            encoding="utf-8"
        )
        self.assertIn("item->size += (2U * HEADER_SIZE) + next->size;", patch)
        self.assertIn("item->size += HEADER_SIZE + next->size;", patch)

        review = by_name["review-overflow-demonstration"]
        self.assertEqual(0, review.exit_code)
        assert review.stdout_path is not None
        self.assertIn("SIZE_MAX rounded down to zero", review.stdout_path.read_text(encoding="utf-8"))

        benchmark_result = by_name["measured-allocator-benchmark"]
        self.assertEqual(("BENCHMARKED", "PARTIAL"), benchmark_result.claims)
        self.assertIn(
            "benchmarks/results/smoke.json",
            benchmark_result.evidence["declared_output_changes"],
        )
        benchmark = json.loads(
            (workspace / "benchmarks/results/smoke.json").read_text(encoding="utf-8")
        )
        self.assertEqual(1, benchmark["schema_version"])
        self.assertTrue(benchmark["generated_at_utc"])
        self.assertEqual(80000, benchmark["parameters"]["timed_operations"])
        self.assertEqual("not used", benchmark["environment"]["network"])
        self.assertEqual(
            {"reference", "best-fit", "segregated-bins"},
            set(benchmark["raw_results"]),
        )
        expected_names = {
            "reference": "address-ordered-first-fit",
            "best-fit": "address-ordered-best-fit",
            "segregated-bins": "segregated-size-class-bins",
        }
        for architecture, measurement in benchmark["raw_results"].items():
            with self.subTest(benchmark=architecture):
                self.assertEqual(expected_names[architecture], measurement["architecture"])
                self.assertEqual(80000, measurement["timed_operations"])
                self.assertGreater(measurement["elapsed_ns"], 0)
                self.assertTrue(math.isfinite(measurement["operations_per_second"]))
                self.assertGreater(measurement["operations_per_second"], 0)
                fragmentation = measurement["fragmentation_workload"]
                self.assertGreater(fragmentation["free_bytes"], 0)
                self.assertGreater(fragmentation["largest_free_block"], 0)
                self.assertGreaterEqual(fragmentation["external_fragmentation_ratio"], 0.0)
                self.assertLessEqual(fragmentation["external_fragmentation_ratio"], 1.0)
        self.assertFalse(
            any("PRODUCTIONIZED" in result.claims for result in results),
            "bounded local evidence cannot become a deployment claim",
        )

    def _diagnostic(self, result: ValidationResult) -> str:
        stdout = (
            result.stdout_path.read_text(encoding="utf-8", errors="replace")[-3_000:]
            if result.stdout_path and result.stdout_path.is_file()
            else ""
        )
        stderr = (
            result.stderr_path.read_text(encoding="utf-8", errors="replace")[-5_000:]
            if result.stderr_path and result.stderr_path.is_file()
            else ""
        )
        return (
            f"{result.name}: {result.status}; evidence={result.evidence!r}; "
            f"stdout={stdout!r}; stderr={stderr!r}"
        )


if __name__ == "__main__":
    unittest.main()
