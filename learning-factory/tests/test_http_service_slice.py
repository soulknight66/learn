from __future__ import annotations

import json
import math
import tempfile
import threading
import unittest
from pathlib import Path

from learnfactory.db import Database
from learnfactory.config import FactorySettings
from learnfactory.handlers import JobHandlers
from learnfactory.http_service_slice import generate_http_service_slice
from learnfactory.jobs import ClaimedJob, JobRepository
from learnfactory.seeding import seed_http_service_job
from learnfactory.validation import ValidationResult, Validator
from learnfactory.workspace import WorkspaceManager


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = REPOSITORY_ROOT / "migrations"


class HTTPServiceSliceTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="learnfactory-http-service-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.database = Database(self.root / "factory.db", MIGRATIONS)
        self.database.migrate()
        self.jobs = JobRepository(self.database)

    def _generate(self, job_id: str) -> tuple[Path, object]:
        self.jobs.create("http_service_slice", "test", {}, job_id=job_id)
        workspace = self.root / job_id
        workspace.mkdir()
        generated = generate_http_service_slice(
            workspace,
            {
                "job_id": job_id,
                "provenance": {
                    "source": "Payload Build Systems Catalog",
                    "source_id": "source_payload_byox",
                    "commit": "0123456789abcdef",
                    "upstream": "https://example.invalid/public-catalog",
                    "catalog_entry": "https://example.invalid/public-http-entry",
                    "catalog_license": "CC0 payload fixture",
                    "source_reference": "README.md#payload-web-server",
                },
            },
            self.database,
        )
        return workspace, generated

    def test_generation_preserves_payload_provenance_and_progressive_boundaries(self) -> None:
        workspace, generated = self._generate("job_http_generation")

        self.assertEqual("http_service_challenge_pack", generated.artifact_type)
        self.assertEqual(
            "projects/networking/bounded-http-counter-service",
            generated.semantic_path,
        )
        self.assertEqual("NOT_PRODUCTION_READY", generated.metadata["deployment_status"])
        self.assertFalse(generated.metadata["productionized"])
        self.assertEqual(3, generated.metadata["architecture_count"])
        self.assertFalse(
            (workspace / "benchmarks/results/smoke.json").exists(),
            "measured evidence must be created by execution, not generation",
        )

        provenance = json.loads((workspace / "PROVENANCE.json").read_text(encoding="utf-8"))
        source = provenance["catalog_source"]
        self.assertEqual("Payload Build Systems Catalog", source["source_name"])
        self.assertEqual("source_payload_byox", source["source_id"])
        self.assertEqual("0123456789abcdef", source["commit_hash"])
        self.assertEqual(
            "https://example.invalid/public-http-entry", source["external_reference"]
        )
        self.assertEqual("CC0 payload fixture", source["license"])
        self.assertEqual("job provenance", source["lookup_status"])
        self.assertFalse(provenance["network_used_during_generation"])
        self.assertIn("agent_generated", provenance["derivation"])
        self.assertIn("measured", provenance["derivation"])

        manifest = json.loads((workspace / "MANIFEST.yaml").read_text(encoding="utf-8"))
        self.assertEqual("GENERATED_CANDIDATE", manifest["status"])
        self.assertEqual("NOT_PRODUCTION_READY", manifest["deployment_status"])
        self.assertFalse(manifest["productionized"])
        self.assertEqual(2, len(manifest["alternative_architectures"]))
        self.assertNotIn("PRODUCTIONIZED", manifest["validation_targets"])
        self.assertIn("PARTIAL", manifest["validation_targets"])

        starter_files = [path for path in (workspace / "starter").rglob("*") if path.is_file()]
        self.assertTrue(starter_files)
        starter_text = "\n".join(path.read_text(encoding="utf-8") for path in starter_files)
        for forbidden in ("EXPECTED_REVIEW", "root-cause.md", "sealed/reference"):
            self.assertNotIn(forbidden, starter_text)

        command_specs = [
            spec for spec in generated.validators if spec.get("type") == "command"
        ]
        self.assertGreaterEqual(len(command_specs), 10)
        for spec in command_specs:
            with self.subTest(validator=spec["name"]):
                self.assertIsInstance(spec["argv"], list)
                self.assertTrue(spec["argv"])
                self.assertTrue(all(isinstance(item, str) for item in spec["argv"]))
                self.assertNotIn("shell", spec)
                self.assertIn("PARTIAL", spec["claims"])
                self.assertNotIn("PRODUCTIONIZED", spec["claims"])

    def test_handler_dispatch_and_catalog_seed_bind_immutable_provenance(self) -> None:
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                """
                INSERT INTO sources(
                    source_id,type,name,path,upstream_url,commit_hash,license,ingested_at
                ) VALUES ('source_byox','build-your-own-x','Build Your Own X','/public/byox',
                          'https://example.invalid/byox','deadbeef','CC0-1.0',1)
                """
            )
            connection.execute(
                """
                INSERT INTO build_projects(
                    project_id,source_id,slug,title,category,implementation_language,
                    upstream_reference,concepts_json,production_relevance,priority_tier
                ) VALUES ('project_http','source_byox','simple-http','A Simple Web Server',
                          'Web Server','Python','https://example.invalid/tutorial','[]',8.5,1)
                """
            )
        self.jobs.create(
            "catalog_synthesis", "synthesizer", {}, job_id="job_catalog_synthesis_v1"
        )
        job_id = seed_http_service_job(self.database, self.jobs)
        self.assertEqual("job_project_http_service_vertical_v1", job_id)
        seeded = self.jobs.get(job_id or "")
        assert seeded is not None
        self.assertEqual("project_http", seeded["payload"]["project_id"])
        self.assertEqual("deadbeef", seeded["payload"]["provenance"]["commit"])
        with self.database.connect() as connection:
            dependency = connection.execute(
                "SELECT depends_on_job_id FROM job_dependencies WHERE job_id=?",
                (job_id,),
            ).fetchone()[0]
        self.assertEqual("job_catalog_synthesis_v1", dependency)

        workspace = self.root / "handler-workspace"
        workspace.mkdir()
        warehouse = self.root / "warehouse"
        settings = FactorySettings(
            root=REPOSITORY_ROOT,
            database=self.database.path,
            warehouse=warehouse,
        )
        handled = JobHandlers(
            settings, self.database, WorkspaceManager(warehouse, self.database)
        ).execute(
            ClaimedJob(
                job_id=job_id or "",
                type="http_service_vertical_slice",
                worker_type="reference_builder",
                payload=seeded["payload"],
                attempt_count=1,
                workspace=str(workspace),
                model=None,
                reasoning_effort=None,
                lease_token="test-lease",
            ),
            workspace,
            self.root / "handler-logs",
            threading.Event(),
        )
        self.assertEqual("http_service_challenge_pack", handled.artifact_type)
        self.assertEqual(
            "projects/networking/bounded-http-counter-service", handled.semantic_path
        )

    def test_every_validator_passes_and_measured_and_debug_evidence_is_real(self) -> None:
        job_id = "job_http_all_validators"
        workspace, generated = self._generate(job_id)
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
            diagnostics.append(self._diagnostic(result))
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
        for architecture in ("reference", "thread-per-connection", "event-loop"):
            self.assertEqual(0, by_name[f"{architecture}-public-contract"].exit_code)
            self.assertEqual(0, by_name[f"{architecture}-withheld-contract"].exit_code)
            self.assertEqual(
                ("TESTED", "PARTIAL"),
                by_name[f"{architecture}-withheld-contract"].claims,
            )
            hidden_stderr = by_name[f"{architecture}-withheld-contract"].stderr_path
            self.assertIsNotNone(hidden_stderr)
            assert hidden_stderr is not None
            hidden_evidence = hidden_stderr.read_text(encoding="utf-8")
            self.assertIn("test_request_budget_stops_pipelined_dispatch", hidden_evidence)
            self.assertIn(
                "test_idempotency_key_conflict_cannot_cross_resources", hidden_evidence
            )
            self.assertIn(
                "test_close_unblocks_idle_keepalive_before_read_timeout", hidden_evidence
            )
        self.assertEqual(0, by_name["deterministic-parser-adversary"].exit_code)
        self.assertEqual(0, by_name["fault-containment-check"].exit_code)
        self.assertEqual(0, by_name["slow-client-capacity-recovery"].exit_code)
        self.assertEqual(1, by_name["debugging-bug-reproduces"].exit_code)
        self.assertEqual(0, by_name["debugging-reference-regression"].exit_code)
        self.assertEqual(
            ("BENCHMARKED", "PARTIAL"),
            by_name["measured-architecture-benchmark"].claims,
        )
        self.assertFalse(
            any("PRODUCTIONIZED" in result.claims for result in results),
            "bounded evidence must not turn into a deployment claim",
        )

        bug_stderr = by_name["debugging-bug-reproduces"].stderr_path
        self.assertIsNotNone(bug_stderr)
        assert bug_stderr is not None
        self.assertIn(
            "parser emitted a request before Content-Length bytes arrived",
            bug_stderr.read_text(encoding="utf-8"),
        )
        reference_stdout = by_name["debugging-reference-regression"].stdout_path
        self.assertIsNotNone(reference_stdout)
        assert reference_stdout is not None
        self.assertIn(
            "fragmented body remained buffered until complete",
            reference_stdout.read_text(encoding="utf-8"),
        )
        buggy = (workspace / "debugging/partial-body/buggy/http_core.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("# BUG", buggy)
        patch = (workspace / "debugging/partial-body/sealed/patch.diff").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "--- a/debugging/partial-body/buggy/http_core.py", patch
        )
        self.assertIn(
            "+++ b/debugging/partial-body/buggy/http_core.py", patch
        )
        self.assertIn("+                return requests", patch)
        self.assertIn("-                length = len(self._buffer) - header_end", patch)

        benchmark = json.loads(
            (workspace / "benchmarks/results/smoke.json").read_text(encoding="utf-8")
        )
        self.assertEqual(1, benchmark["schema_version"])
        self.assertTrue(benchmark["hypothesis"])
        self.assertEqual(
            {
                "requests_per_workload": 40,
                "concurrency": 4,
                "endpoint": "GET /healthz over a new loopback connection",
            },
            benchmark["parameters"],
        )
        self.assertEqual("IPv4 loopback only", benchmark["environment"]["network"])
        self.assertTrue(benchmark["environment"]["python"])
        self.assertEqual(
            {"worker_pool", "thread_per_connection", "event_loop"},
            set(benchmark["raw_results"]),
        )
        expected_architectures = {
            "worker_pool": "bounded-worker-pool",
            "thread_per_connection": "bounded-thread-per-connection",
            "event_loop": "single-threaded-selector-loop",
        }
        for name, measurements in benchmark["raw_results"].items():
            with self.subTest(benchmark=name):
                self.assertEqual(expected_architectures[name], measurements["architecture"])
                self.assertEqual(40, len(measurements["sequential_latency_ns_raw"]))
                self.assertEqual(40, len(measurements["burst_latency_ns_raw"]))
                self.assertTrue(
                    all(value > 0 for value in measurements["sequential_latency_ns_raw"])
                )
                self.assertTrue(
                    all(value > 0 for value in measurements["burst_latency_ns_raw"])
                )
                self.assertGreater(measurements["burst_total_ns"], 0)
                self.assertTrue(
                    math.isfinite(measurements["burst_requests_per_second"])
                )
                self.assertGreater(measurements["burst_requests_per_second"], 0)

    def _diagnostic(self, result: ValidationResult) -> str:
        stdout = (
            result.stdout_path.read_text(encoding="utf-8", errors="replace")[-2_000:]
            if result.stdout_path and result.stdout_path.is_file()
            else ""
        )
        stderr = (
            result.stderr_path.read_text(encoding="utf-8", errors="replace")[-3_000:]
            if result.stderr_path and result.stderr_path.is_file()
            else ""
        )
        return (
            f"{result.name}: {result.status}; evidence={result.evidence!r}; "
            f"stdout={stdout!r}; stderr={stderr!r}"
        )


if __name__ == "__main__":
    unittest.main()
