from __future__ import annotations

import json
import math
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from learnfactory.bytecode_slice import PROJECT_ID, generate_bytecode_slice
from learnfactory.db import Database
from learnfactory.jobs import JobRepository
from learnfactory.util import file_sha256, tree_sha256
from learnfactory.validation import ValidationResult, Validator


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = REPOSITORY_ROOT / "migrations"


class BytecodeSliceTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="learnfactory-bytecode-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.database = Database(self.root / "factory.db", MIGRATIONS)
        self.database.migrate()
        self.jobs = JobRepository(self.database)
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                """
                INSERT INTO sources(
                    source_id,type,name,path,upstream_url,commit_hash,license,ingested_at,
                    metadata_json,is_active
                ) VALUES (?,?,?,?,?,?,?,?,?,1)
                """,
                (
                    "source_bytecode_fixture",
                    "build-your-own-x",
                    "Build Your Own X fixture",
                    "/public/build-your-own-x",
                    "https://github.com/codecrafters-io/build-your-own-x",
                    "fixture-commit-aa1743",
                    "CC0-1.0",
                    1.0,
                    "{}",
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
                    "source_bytecode_fixture",
                    "home-grown-bytecode-interpreters",
                    "Home-grown bytecode interpreters fixture",
                    "Emulator / Virtual Machine",
                    "C",
                    "https://example.invalid/bytecode-article",
                    '["instruction sets","virtual machines","interpreters"]',
                    8.0,
                    8.5,
                    "article",
                    1,
                    json.dumps(
                        {
                            "linked_resource_license": "NOASSERTION",
                            "provenance": {"source_file": "README.md", "source_line": 166},
                        }
                    ),
                ),
            )

    def _generate(self, job_id: str, directory: str = "pack"):
        self.jobs.create("bytecode_slice", "test", {}, job_id=job_id)
        workspace = self.root / directory
        workspace.mkdir()
        generated = generate_bytecode_slice(
            workspace,
            {"job_id": job_id, "project_id": PROJECT_ID},
            self.database,
        )
        return workspace, generated

    def test_generation_is_deterministic_provenanced_and_progressively_sealed(self) -> None:
        workspace, generated = self._generate("job_bytecode_generation", "first")

        self.assertEqual("bytecode_vm_challenge_pack", generated.artifact_type)
        self.assertEqual("projects/languages/sprig-bytecode-vm", generated.semantic_path)
        self.assertEqual(PROJECT_ID, generated.metadata["project_id"])
        self.assertEqual(2, generated.metadata["architecture_count"])
        self.assertEqual("NOT_PRODUCTION_READY", generated.metadata["deployment_status"])
        self.assertFalse(generated.metadata["productionized"])
        self.assertNotIn("PRODUCTIONIZED", generated.metadata["validation_targets"])
        self.assertFalse((workspace / "benchmarks/results/smoke.json").exists())
        self.assertFalse((workspace / "reports/fuzz-smoke.json").exists())

        provenance = json.loads((workspace / "PROVENANCE.json").read_text(encoding="utf-8"))
        source = provenance["catalog_source"]
        self.assertEqual(PROJECT_ID, source["project_id"])
        self.assertEqual("source_bytecode_fixture", source["source_id"])
        self.assertEqual("fixture-commit-aa1743", source["commit_hash"])
        self.assertEqual("active database catalog row", source["lookup_status"])
        self.assertEqual("NOASSERTION", source["linked_resource_license"])
        self.assertEqual("README.md:166", source["source_reference"])
        self.assertFalse(provenance["network_used_during_generation"])
        self.assertFalse(provenance["linked_content_copied"])
        self.assertIn("catalog repository metadata only", provenance["license_boundary"])
        self.assertTrue(any("concept tags" in item for item in provenance["derivation"]["inferred"]))
        self.assertFalse(any("concepts" in item for item in provenance["derivation"]["source_derived"]))

        manifest = json.loads((workspace / "MANIFEST.yaml").read_text(encoding="utf-8"))
        self.assertEqual("GENERATED_CANDIDATE", manifest["status"])
        self.assertFalse(manifest["productionized"])
        self.assertEqual(PROJECT_ID, manifest["provenance_project_id"])
        self.assertEqual({"bytecode", "treewalk"}, {item["name"] for item in manifest["architectures"]})

        visible = [
            workspace / name
            for name in (
                "README.md",
                "REQUIREMENTS.md",
                "GRAMMAR.md",
                "BYTECODE.md",
                "CONCEPTS.md",
                "DESIGN_QUESTIONS.md",
            )
        ]
        visible += [path for root in (workspace / "starter", workspace / "public_tests") for path in root.rglob("*") if path.is_file()]
        visible_text = "\n".join(path.read_text(encoding="utf-8") for path in visible)
        for secret_marker in ("EXPECTED_REVIEW", "root-cause.md", "patch.diff", "right = self._term()"):
            self.assertNotIn(secret_marker, visible_text)
        starter_text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in sorted((workspace / "starter/tinyvm").glob("*.py"))
        )
        self.assertIn("NotImplementedError", starter_text)
        for stage in ("stage 1a", "stage 1b", "stage 2", "stage 3"):
            self.assertIn(stage, starter_text)
        self.assertTrue((workspace / "sealed/reference/tinyvm/vm.py").is_file())
        self.assertTrue((workspace / "sealed/reference_tests/test_hidden.py").is_file())

        for common in ("model.py", "lexer.py", "parser.py", "semantics.py"):
            self.assertEqual(
                file_sha256(workspace / "sealed/reference/tinyvm" / common),
                file_sha256(workspace / "alternatives/treewalk/tinyvm" / common),
                f"front end drifted for {common}",
            )
        self.assertNotEqual(
            file_sha256(workspace / "sealed/reference/tinyvm/api.py"),
            file_sha256(workspace / "alternatives/treewalk/tinyvm/api.py"),
        )

        second = self.root / "second"
        second.mkdir()
        generate_bytecode_slice(
            second,
            {"job_id": "job_bytecode_generation", "project_id": PROJECT_ID},
            self.database,
        )
        self.assertEqual(tree_sha256(workspace), tree_sha256(second))

    def test_generation_rejects_dirty_or_mismatched_workspaces_and_boundary_leaks(self) -> None:
        dirty = self.root / "dirty"
        dirty.mkdir()
        (dirty / "stale.txt").write_text("stale retry material\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "must be empty"):
            generate_bytecode_slice(
                dirty,
                {"job_id": "job_bytecode_dirty", "project_id": PROJECT_ID},
                self.database,
            )

        managed = self.root / "managed"
        managed.mkdir()
        (managed / ".factory-workspace").write_text("managed\n", encoding="utf-8")
        generated = generate_bytecode_slice(
            managed,
            {"job_id": "job_bytecode_managed", "project_id": PROJECT_ID},
            self.database,
        )
        self.assertEqual("bytecode_vm_challenge_pack", generated.artifact_type)

        wrong_project = self.root / "wrong-project"
        wrong_project.mkdir()
        with self.assertRaisesRegex(ValueError, "project_id"):
            generate_bytecode_slice(
                wrong_project,
                {"job_id": "job_bytecode_wrong", "project_id": "project_wrong"},
                self.database,
            )

        workspace, _ = self._generate("job_bytecode_boundary_mutation", "boundary")
        shutil.copytree(
            workspace / "sealed/reference/tinyvm",
            workspace / "starter/copied_complete_reference",
        )
        process = subprocess.run(
            [sys.executable, "environment/check_boundaries.py"],
            cwd=workspace,
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
        )
        self.assertNotEqual(0, process.returncode)
        self.assertIn("unexpected learner-visible file", process.stderr)

    def test_every_validator_passes_and_evidence_comes_from_execution(self) -> None:
        job_id = "job_bytecode_all_validators"
        workspace, generated = self._generate(job_id, "validated")
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
                "SELECT COUNT(*) total,SUM(status='PASS') passed FROM validations WHERE job_id=?",
                (job_id,),
            ).fetchone()
        self.assertEqual((len(results), len(results)), tuple(persisted))

        by_name = {result.name: result for result in results}
        for architecture in ("bytecode", "treewalk"):
            self.assertEqual(0, by_name[f"{architecture}-public-contract"].exit_code)
            self.assertEqual(0, by_name[f"{architecture}-withheld-contract"].exit_code)
            hidden_log = by_name[f"{architecture}-withheld-contract"].stderr_path
            self.assertIsNotNone(hidden_log)
            assert hidden_log is not None
            hidden_text = hidden_log.read_text(encoding="utf-8")
            self.assertIn("test_negative_division_and_remainder_truncate_toward_zero", hidden_text)
            self.assertIn("test_overflow_is_not_host_integer_growth", hidden_text)
            self.assertIn("test_signed_minimum_literal_and_bounded_integer_diagnostics", hidden_text)
            self.assertIn("test_documented_ascii_lexical_contract", hidden_text)
            self.assertIn("test_error_order_and_budget_are_architecture_neutral", hidden_text)
        self.assertEqual(0, by_name["bytecode-instruction-contract"].exit_code)
        bytecode_log = by_name["bytecode-instruction-contract"].stderr_path
        assert bytecode_log is not None
        self.assertIn(
            "test_verifier_rejects_malformed_operands_and_instructions",
            bytecode_log.read_text(encoding="utf-8"),
        )
        self.assertEqual(0, by_name["deterministic-differential-fuzz"].exit_code)
        self.assertEqual(1, by_name["debugging-bug-reproduces"].exit_code)
        self.assertEqual(0, by_name["debugging-fix-restores-contract"].exit_code)
        self.assertEqual(0, by_name["debugging-isolated-mutation-integrity"].exit_code)
        self.assertEqual(0, by_name["review-finding-reproduction"].exit_code)
        self.assertFalse(any("PRODUCTIONIZED" in result.claims for result in results))

        bug_log = by_name["debugging-bug-reproduces"].stderr_path
        assert bug_log is not None
        self.assertIn("wanted 12, observed (18,)", bug_log.read_text(encoding="utf-8"))
        fix_log = by_name["debugging-fix-restores-contract"].stdout_path
        assert fix_log is not None
        self.assertIn("left-associative", fix_log.read_text(encoding="utf-8"))
        review_log = by_name["review-finding-reproduction"].stdout_path
        assert review_log is not None
        self.assertIn("eagerly evaluates an unreachable RHS", review_log.read_text(encoding="utf-8"))

        fuzz = json.loads((workspace / "reports/fuzz-smoke.json").read_text(encoding="utf-8"))
        self.assertEqual(7401, fuzz["seed"])
        self.assertEqual(120, fuzz["iterations"])
        self.assertEqual(0, fuzz["failures"])
        self.assertEqual({"bytecode", "treewalk"}, set(fuzz["engines"]))
        self.assertRegex(fuzz["corpus_sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(120, fuzz["coverage"]["programs"])
        self.assertTrue(
            {"declarations", "assignment", "while", "if/else", "division/remainder", "short-circuit"}
            <= set(fuzz["coverage"]["features"])
        )

        benchmark = json.loads((workspace / "benchmarks/results/smoke.json").read_text(encoding="utf-8"))
        self.assertEqual(1, benchmark["schema_version"])
        self.assertEqual("time.perf_counter_ns", benchmark["environment"]["clock"])
        self.assertEqual("not used", benchmark["environment"]["network"])
        self.assertIn("end-to-end", benchmark["hypothesis"])
        self.assertIn("compilation for bytecode", benchmark["measurement_scope"])
        self.assertTrue(benchmark["environment"]["python"])
        self.assertEqual({"bytecode", "treewalk"}, set(benchmark["raw_results"]))
        process_ids = set()
        for engine, measurement in benchmark["raw_results"].items():
            with self.subTest(engine=engine):
                self.assertEqual(engine, measurement["engine"])
                self.assertEqual(7, len(measurement["raw_elapsed_ns"]))
                self.assertTrue(all(isinstance(value, int) and value > 0 for value in measurement["raw_elapsed_ns"]))
                self.assertGreater(measurement["median_elapsed_ns"], 0)
                self.assertLessEqual(measurement["min_elapsed_ns"], measurement["median_elapsed_ns"])
                self.assertLessEqual(measurement["median_elapsed_ns"], measurement["max_elapsed_ns"])
                self.assertTrue(math.isfinite(measurement["median_elapsed_ns"]))
                process_ids.add(measurement["pid"])
        self.assertEqual(2, len(process_ids), "each architecture must be actually run in its own child")
        self.assertEqual(
            ("BENCHMARKED", "PARTIAL"),
            by_name["measured-architecture-benchmark"].claims,
        )
        self.assertIn(
            "benchmarks/results/smoke.json",
            by_name["measured-architecture-benchmark"].evidence["declared_output_changes"],
        )

    @staticmethod
    def _diagnostic(result: ValidationResult) -> str:
        stdout = result.stdout_path.read_text(encoding="utf-8", errors="replace")[-2_000:] if result.stdout_path and result.stdout_path.is_file() else ""
        stderr = result.stderr_path.read_text(encoding="utf-8", errors="replace")[-3_000:] if result.stderr_path and result.stderr_path.is_file() else ""
        return f"{result.name}: {result.status}; evidence={result.evidence!r}; stdout={stdout!r}; stderr={stderr!r}"


if __name__ == "__main__":
    unittest.main()
