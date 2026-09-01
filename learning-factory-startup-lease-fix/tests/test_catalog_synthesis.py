from __future__ import annotations

import json
import tempfile
import threading
import unittest
from pathlib import Path

from learnfactory.catalog_synthesis import (
    build_catalog_documents,
    generate_catalog_synthesis,
    validate_catalog_synthesis,
)
from learnfactory.config import FactorySettings
from learnfactory.db import Database
from learnfactory.handlers import JobHandlers
from learnfactory.jobs import ClaimedJob, JobRepository
from learnfactory.scoring import DEFAULT_WEIGHTS, priority_score
from learnfactory.seeding import (
    CATALOG_SYNTHESIS_JOB_ID,
    SOURCE_INGESTION_JOB_IDS,
    seed_catalog_synthesis_job,
)
from learnfactory.util import canonical_json
from learnfactory.validation import Validator
from learnfactory.workspace import WorkspaceManager


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = REPOSITORY_ROOT / "migrations"


class CatalogSynthesisTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="learnfactory-catalog-synthesis-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.database = Database(self.root / "factory.db", MIGRATIONS)
        self.database.migrate()
        self.jobs = JobRepository(self.database)
        self._populate_catalog()

    def _populate_catalog(self) -> None:
        with self.database.transaction(immediate=True) as connection:
            connection.executemany(
                """
                INSERT INTO sources(
                    source_id,type,name,path,upstream_url,commit_hash,license,
                    ingested_at,metadata_json
                ) VALUES (?,?,?,?,?,?,?,?,?)
                """,
                [
                    (
                        "source_csdi",
                        "csdiy",
                        "CSDIY",
                        "/snapshots/csdiy/1111111",
                        "https://github.com/pkuflyingpig/cs-self-learning",
                        "1" * 40,
                        "CC-BY-SA-4.0",
                        100.0,
                        canonical_json(
                            {
                                "adapter": "csdiy",
                                "extractor_version": 2,
                                "tree_hash": "a" * 64,
                            }
                        ),
                    ),
                    (
                        "source_byox",
                        "build-your-own-x",
                        "Build Your Own X",
                        "/snapshots/byox/2222222",
                        "https://github.com/codecrafters-io/build-your-own-x",
                        "2" * 40,
                        "CC-BY-SA-4.0",
                        200.0,
                        canonical_json(
                            {
                                "adapter": "build-your-own-x",
                                "extractor_version": 2,
                                "tree_hash": "b" * 64,
                            }
                        ),
                    ),
                ],
            )
            connection.executemany(
                """
                INSERT INTO courses(
                    course_id,source_id,slug,institution,title,topic,description,
                    prerequisites_json,estimated_human_hours,difficulty,
                    source_metadata_json,status
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                [
                    (
                        "course_mit_6s081",
                        "source_csdi",
                        "mit-6-s081",
                        "MIT",
                        "MIT 6.S081 Operating System Engineering",
                        "Operating Systems",
                        "Kernel implementation and systems debugging.",
                        canonical_json(["Computer Architecture", "C"]),
                        160.0,
                        9.0,
                        canonical_json(
                            {
                                "languages": ["C"],
                                "provenance": {
                                    "source_file": "docs/系统基础/mit6s081.md",
                                    "content_sha256": "c" * 64,
                                },
                            }
                        ),
                        "MATERIALS_INGESTED",
                    ),
                    (
                        "course_engineering",
                        "source_csdi",
                        "software-engineering",
                        "UC Berkeley",
                        "Software Engineering",
                        "Software Engineering",
                        "Testing, maintenance, design, and team practices.",
                        canonical_json(["Programming Foundations"]),
                        80.0,
                        7.0,
                        canonical_json(
                            {
                                "languages": ["Python"],
                                "provenance": {
                                    "source_file": "docs/software-engineering.md",
                                    "content_sha256": "d" * 64,
                                },
                            }
                        ),
                        "METADATA_COMPLETE",
                    ),
                ],
            )
            connection.executemany(
                """
                INSERT INTO course_units(
                    unit_id,course_id,type,unit_order,title,dependencies_json,
                    source_reference,metadata_json
                ) VALUES (?,?,?,?,?,?,?,?)
                """,
                [
                    (
                        "unit_vm",
                        "course_mit_6s081",
                        "lab",
                        1,
                        "Virtual memory",
                        "[]",
                        "https://pdos.csail.mit.edu/6.S081/",
                        canonical_json({"availability": "LINKED"}),
                    ),
                    (
                        "unit_fs",
                        "course_mit_6s081",
                        "lab",
                        2,
                        "File system",
                        canonical_json(["unit_vm"]),
                        "https://pdos.csail.mit.edu/6.S081/",
                        canonical_json({"availability": "DESCRIBED"}),
                    ),
                    (
                        "unit_testing",
                        "course_engineering",
                        "project",
                        1,
                        "Testing and maintenance",
                        "[]",
                        "https://example.edu/software-engineering",
                        canonical_json({"availability": "LINKED"}),
                    ),
                ],
            )
            connection.execute(
                """
                INSERT INTO curriculum_edges(
                    from_course_id,to_course_id,relation,evidence,inferred
                ) VALUES (?,?,?,?,?)
                """,
                (
                    "course_engineering",
                    "course_mit_6s081",
                    "recommended-before",
                    "inferred from prerequisites and implementation scope",
                    1,
                ),
            )
            connection.executemany(
                """
                INSERT INTO build_projects(
                    project_id,source_id,slug,title,category,
                    implementation_language,upstream_reference,concepts_json,
                    difficulty,production_relevance,source_format,priority_tier,
                    metadata_json
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                [
                    (
                        "project_database",
                        "source_byox",
                        "database",
                        "Build a Database",
                        "Database",
                        "Rust",
                        "https://cstack.github.io/db_tutorial/",
                        canonical_json(["storage", "indexing", "B+ tree"]),
                        9.0,
                        9.0,
                        "article",
                        1,
                        canonical_json(
                            {
                                "languages": ["Rust"],
                                "linked_resource_license": "NOASSERTION",
                                "provenance": {"content_sha256": "e" * 64},
                            }
                        ),
                    ),
                    (
                        "project_http",
                        "source_byox",
                        "http-server",
                        "Build an HTTP Server",
                        "Web Server",
                        "Python",
                        "https://example.org/http-server",
                        canonical_json(["networking", "HTTP", "sockets"]),
                        7.0,
                        9.0,
                        "article",
                        2,
                        canonical_json(
                            {
                                "languages": ["Python"],
                                "linked_resource_license": "MIT",
                                "provenance": {"content_sha256": "f" * 64},
                            }
                        ),
                    ),
                    (
                        "project_compiler",
                        "source_byox",
                        "compiler",
                        "Build a Compiler",
                        "Compiler",
                        "C++",
                        "https://example.org/compiler",
                        canonical_json(["parser", "AST", "code generation"]),
                        8.0,
                        7.0,
                        "repository",
                        1,
                        canonical_json(
                            {
                                "languages": ["C++"],
                                "linked_resource_license": "MIT",
                                "provenance": {"content_sha256": "0" * 64},
                            }
                        ),
                    ),
                ],
            )

    def test_generation_is_deterministic_complete_ranked_and_provenanced(self) -> None:
        first = build_catalog_documents(
            self.database, manual_overrides={"project_http": 3.25}
        )
        second = build_catalog_documents(
            self.database, manual_overrides={"project_http": 3.25}
        )
        self.assertEqual(first, second)

        workspace = self.root / "synthesis"
        workspace.mkdir()
        generated = generate_catalog_synthesis(
            workspace,
            {"manual_overrides": {"project_http": 3.25}},
            self.database,
        )
        backlog = json.loads((workspace / "BACKLOG.json").read_text(encoding="utf-8"))
        concept_map = json.loads(
            (workspace / "CONCEPT_MAP.json").read_text(encoding="utf-8")
        )
        provenance = json.loads(
            (workspace / "PROVENANCE.json").read_text(encoding="utf-8")
        )

        self.assertEqual("catalog-synthesis", generated.artifact_type)
        self.assertEqual("synthesis/catalog-v1", generated.semantic_path)
        self.assertEqual(
            {"sources": 2, "courses": 2, "projects": 3, "total_items": 5},
            {
                name: backlog["summary"][name]
                for name in ("sources", "courses", "projects", "total_items")
            },
        )
        self.assertEqual(list(range(1, 6)), [item["rank"] for item in backlog["items"]])
        ordering = [
            (
                -item["score"],
                item["kind"],
                item["title"].casefold(),
                item["record_id"],
            )
            for item in backlog["items"]
        ]
        self.assertEqual(sorted(ordering), ordering)
        for item in backlog["items"]:
            expected = round(
                priority_score(item["score_components"], backlog["policy"]["weights"])
                + item["manual_priority_delta"],
                4,
            )
            self.assertEqual(expected, item["score"])
            self.assertIn(item["record_id"], (workspace / "BACKLOG.md").read_text())
            self.assertTrue(item["provenance"]["source_id"])
            self.assertTrue(item["provenance"]["source_commit"])
            self.assertTrue(item["provenance"]["source_license"])
            self.assertTrue(item["provenance"]["source_reference"])
            self.assertIn("source-derived", item["provenance"]["classification"])
        self.assertEqual(3.25, backlog["policy"]["manual_overrides"]["project_http"])
        self.assertEqual(2, len(provenance["sources"]))
        self.assertTrue(all(source["commit_hash"] for source in provenance["sources"]))
        self.assertGreater(concept_map["summary"]["concepts"], 5)
        valid_ids = {item["record_id"] for item in backlog["items"]}
        referenced_ids = {
            identifier
            for node in concept_map["nodes"]
            for identifier in [*node["course_ids"], *node["project_ids"]]
        }
        self.assertEqual(valid_ids, referenced_ids)
        self.assertEqual(
            backlog["catalog_snapshot_sha256"],
            concept_map["catalog_snapshot_sha256"],
        )

    def test_external_replay_is_only_tested_claim_and_detects_tampering(self) -> None:
        job_id = self.jobs.create(
            "catalog_synthesis", "synthesizer", {}, job_id="job_catalog_validate"
        )
        workspace = self.root / "validated"
        workspace.mkdir()
        generated = generate_catalog_synthesis(workspace, {}, self.database)
        results = Validator(self.database).run(
            job_id,
            workspace,
            generated.validators,
            self.root / "logs" / job_id,
        )
        diagnostics = [
            f"{result.name}: {result.status} {result.evidence!r}"
            for result in results
            if not result.passed
        ]
        self.assertEqual(len(generated.validators), len(results))
        self.assertEqual([], diagnostics)
        claims = {result.name: result.claims for result in results}
        self.assertEqual(("TESTED",), claims["authoritative-catalog-replay"])
        self.assertTrue(
            all(
                not labels
                for name, labels in claims.items()
                if name != "authoritative-catalog-replay"
            )
        )
        self.assertNotIn(
            "REVIEWED", {label for labels in claims.values() for label in labels}
        )

        backlog_path = workspace / "BACKLOG.json"
        backlog = json.loads(backlog_path.read_text(encoding="utf-8"))
        backlog["items"][0]["score"] += 1
        backlog_path.write_text(
            json.dumps(backlog, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        errors = validate_catalog_synthesis(
            workspace,
            self.database,
            expected_policy_sha256=generated.evidence["policy_sha256"],
        )
        self.assertIn(
            "BACKLOG.json: differs from authoritative deterministic replay", errors
        )

        backlog["policy"]["weights"]["systems_depth"] += 1
        backlog_path.write_text(
            json.dumps(backlog, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        errors = validate_catalog_synthesis(
            workspace,
            self.database,
            expected_policy_sha256=generated.evidence["policy_sha256"],
        )
        self.assertEqual(
            ["BACKLOG.json: embedded policy differs from the job-authorized policy"],
            errors,
        )

    def test_external_replay_rejects_boolean_in_place_of_numeric_rank(self) -> None:
        workspace = self.root / "typed-replay"
        workspace.mkdir()
        generated = generate_catalog_synthesis(workspace, {}, self.database)
        backlog_path = workspace / "BACKLOG.json"
        backlog = json.loads(backlog_path.read_text(encoding="utf-8"))
        self.assertEqual(1, backlog["items"][0]["rank"])
        backlog["items"][0]["rank"] = True
        backlog_path.write_text(
            json.dumps(backlog, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

        self.assertIn(
            "BACKLOG.json: differs from authoritative deterministic replay",
            validate_catalog_synthesis(
                workspace,
                self.database,
                expected_policy_sha256=generated.evidence["policy_sha256"],
            ),
        )

    def test_handler_dispatches_catalog_synthesis_without_probabilistic_worker(self) -> None:
        warehouse = self.root / "warehouse"
        settings = FactorySettings(
            root=REPOSITORY_ROOT,
            database=self.database.path,
            warehouse=warehouse,
        )
        manager = WorkspaceManager(warehouse, self.database)
        manager.initialize()
        workspace = self.root / "handler-workspace"
        workspace.mkdir()
        result = JobHandlers(settings, self.database, manager).execute(
            ClaimedJob(
                job_id="job_catalog_handler",
                type="catalog_synthesis",
                worker_type="synthesizer",
                payload={},
                attempt_count=1,
                workspace=str(workspace),
                model=None,
                reasoning_effort=None,
                lease_token="lease-test",
            ),
            workspace,
            self.root / "handler-logs",
            threading.Event(),
        )
        self.assertEqual("catalog-synthesis", result.artifact_type)
        self.assertEqual("synthesis/catalog-v1", result.semantic_path)
        self.assertEqual("generate_catalog_synthesis", result.evidence["handler"])
        self.assertTrue((workspace / "CONCEPT_MAP.json").is_file())

    def test_seed_is_idempotent_and_depends_on_both_ingestion_jobs(self) -> None:
        for identifier in SOURCE_INGESTION_JOB_IDS:
            self.jobs.create(
                "source_ingest", "ingestion", {}, job_id=identifier, priority=100
            )

        first = seed_catalog_synthesis_job(self.database, self.jobs)
        second = seed_catalog_synthesis_job(self.database, self.jobs)
        self.assertEqual(CATALOG_SYNTHESIS_JOB_ID, first)
        self.assertEqual(first, second)
        record = self.jobs.get(first)
        assert record is not None
        self.assertEqual("catalog_synthesis", record["type"])
        self.assertEqual("synthesizer", record["worker_type"])
        self.assertEqual("DISCOVERED", record["state"])
        self.assertEqual(DEFAULT_WEIGHTS, record["payload"]["weights"])
        with self.database.connect() as connection:
            dependencies = [
                row["depends_on_job_id"]
                for row in connection.execute(
                    """
                    SELECT depends_on_job_id FROM job_dependencies
                    WHERE job_id=? ORDER BY depends_on_job_id
                    """,
                    (first,),
                )
            ]
            job_count = connection.execute(
                "SELECT COUNT(*) FROM jobs WHERE job_id=?", (first,)
            ).fetchone()[0]
        self.assertEqual(sorted(SOURCE_INGESTION_JOB_IDS), dependencies)
        self.assertEqual(1, job_count)


if __name__ == "__main__":
    unittest.main()
