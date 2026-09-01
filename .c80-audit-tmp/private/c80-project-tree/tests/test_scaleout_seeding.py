from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from learnfactory.db import Database
from learnfactory.jobs import JobRepository
from learnfactory.seeding import seed_scaleout_jobs


ROOT = Path(__file__).resolve().parents[1]


class ScaleoutSeedingTests(unittest.TestCase):
    def test_scaleout_jobs_are_idempotent_and_bound_to_active_catalog(self) -> None:
        with tempfile.TemporaryDirectory(prefix="learnfactory-scaleout-") as raw:
            database = Database(Path(raw) / "factory.db", ROOT / "migrations")
            database.migrate()
            with database.transaction(immediate=True) as connection:
                connection.execute(
                    """
                    INSERT INTO sources(
                        source_id,type,name,path,upstream_url,commit_hash,license,ingested_at
                    ) VALUES ('source_csdiy','csdiy','CSDIY','/public/csdiy',
                              'https://example.invalid/csdiy','course-commit','MIT',1)
                    """
                )
                connection.execute(
                    """
                    INSERT INTO sources(
                        source_id,type,name,path,upstream_url,commit_hash,license,ingested_at
                    ) VALUES ('source_byox','build-your-own-x','Build Your Own X','/public/byox',
                              'https://example.invalid/byox','byox-commit','CC0-1.0',1)
                    """
                )
                for project_id, slug, title, category, language in (
                    (
                        "project_62500cd7d143a95230c724df71a56c4a",
                        "allocator",
                        "Allocator",
                        "Memory Allocator",
                        "C",
                    ),
                    (
                        "project_4b7f4b85b17d9b99cf19b3c18d8a914808f",
                        "wrong-id",
                        "Ignored",
                        "Virtual Machine",
                        "C",
                    ),
                    (
                        "project_4b7f4b85b17b06eeba75d235767a898f",
                        "bytecode",
                        "Home-grown bytecode interpreters",
                        "Emulator / Virtual Machine",
                        "C",
                    ),
                ):
                    connection.execute(
                        """
                        INSERT INTO build_projects(
                            project_id,source_id,slug,title,category,implementation_language,
                            upstream_reference,concepts_json,priority_tier
                        ) VALUES (?,?,?,?,?,?,?,'[]',1)
                        """,
                        (
                            project_id,
                            "source_byox",
                            slug,
                            title,
                            category,
                            language,
                            f"https://example.invalid/{slug}",
                        ),
                    )
            jobs = JobRepository(database)
            jobs.create(
                "catalog_synthesis",
                "synthesizer",
                {},
                job_id="job_catalog_synthesis_v1",
            )

            first = seed_scaleout_jobs(database, jobs)
            second = seed_scaleout_jobs(database, jobs)
            self.assertEqual(first, second)
            self.assertEqual(
                {"allocator", "bytecode", "event_service"}, set(first)
            )
            with database.connect() as connection:
                rows = list(
                    connection.execute(
                        """
                        SELECT j.job_id,j.type,j.worker_type,j.payload_json,
                               d.depends_on_job_id
                        FROM jobs j
                        JOIN job_dependencies d ON d.job_id=j.job_id
                        WHERE j.job_id <> 'job_catalog_synthesis_v1'
                        ORDER BY j.job_id
                        """
                    )
                )
            self.assertEqual(3, len(rows))
            self.assertTrue(
                all(row["depends_on_job_id"] == "job_catalog_synthesis_v1" for row in rows)
            )
            self.assertEqual(
                {
                    "allocator_vertical_slice",
                    "bytecode_vertical_slice",
                    "event_service_vertical_slice",
                },
                {row["type"] for row in rows},
            )
            event = jobs.get(first["event_service"])
            assert event is not None
            self.assertEqual(
                ["source_byox", "source_csdiy"],
                sorted(event["payload"]["source_ids"]),
            )


if __name__ == "__main__":
    unittest.main()
