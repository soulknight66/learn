from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from learnfactory.cli import main
from learnfactory.db import Database
from learnfactory.jobs import JobRepository
from learnfactory.sources import SourceDescriptor


class CliSafetyTests(unittest.TestCase):
    def _config(self, root: Path) -> Path:
        config = root / "factory.toml"
        config.write_text(
            "\n".join(
                [
                    "[factory]",
                    f'database = "{root / "factory.db"}"',
                    f'warehouse = "{root / "warehouse"}"',
                    "[backend]",
                    'model = "gpt-5.6-sol"',
                    'reasoning_effort = "ultra"',
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        return config

    def _run(self, arguments: list[str]) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            result = main(arguments)
        return result, stdout.getvalue(), stderr.getvalue()

    def test_read_only_status_refuses_to_create_or_migrate_a_fresh_database(self) -> None:
        with tempfile.TemporaryDirectory(prefix="learnfactory-cli-") as raw:
            root = Path(raw)
            config = self._config(root)
            result, output, error = self._run(
                ["--config", str(config), "status", "--json"]
            )
            self.assertEqual(2, result)
            self.assertEqual("", output)
            self.assertIn("not initialized", error)
            self.assertFalse((root / "factory.db").exists())

    def test_status_uses_verified_read_only_connections_without_migrating(self) -> None:
        with tempfile.TemporaryDirectory(prefix="learnfactory-cli-") as raw:
            root = Path(raw)
            config = self._config(root)
            self.assertEqual(0, self._run(["--config", str(config), "init"])[0])

            with mock.patch(
                "learnfactory.cli.Database.migrate",
                side_effect=AssertionError("status attempted migration"),
            ):
                result, output, error = self._run(
                    ["--config", str(config), "status", "--json"]
                )

            self.assertEqual(0, result, error)
            self.assertIn('"jobs": {}', output)
            self.assertFalse((root / "factory.db-journal").exists())

    def test_inspect_decodes_human_readable_run_reproducibility(self) -> None:
        with tempfile.TemporaryDirectory(prefix="learnfactory-cli-") as raw:
            root = Path(raw)
            config = self._config(root)
            self.assertEqual(0, self._run(["--config", str(config), "init"])[0])
            database = Database(
                root / "factory.db", Path(__file__).resolve().parents[1] / "migrations"
            )
            jobs = JobRepository(database)
            job_id = jobs.create("fake", "test", {}, job_id="job_inspect_run")
            metadata = {
                "schema": "learnfactory-run-provenance-v2",
                "fingerprint_sha256": "a" * 64,
                "components": {"code_sha256": "b" * 64},
            }
            with database.transaction(immediate=True) as connection:
                connection.execute(
                    """
                    INSERT INTO workers(
                        worker_id,type,state,started_at,last_activity,hostname
                    ) VALUES ('worker-inspect','test','SUCCEEDED',1,2,'fixture')
                    """
                )
                connection.execute(
                    """
                    INSERT INTO job_runs(
                        run_id,job_id,worker_id,attempt_number,backend,started_at,
                        reproducibility_digest,reproducibility_path,reproducibility_json
                    ) VALUES ('run-inspect',?,?,1,'fake',1,?,?,?)
                    """,
                    (
                        job_id,
                        "worker-inspect",
                        "a" * 64,
                        "/logs/RUN_PROVENANCE.json",
                        json.dumps(metadata),
                    ),
                )

            result, output, error = self._run(
                ["--config", str(config), "inspect", job_id]
            )

            self.assertEqual(0, result, error)
            inspected = json.loads(output)
            self.assertEqual(1, len(inspected["runs"]))
            self.assertEqual(metadata, inspected["runs"][0]["reproducibility"])
            self.assertEqual("a" * 64, inspected["runs"][0]["reproducibility_digest"])

    def test_exercise_start_rejects_path_escape_and_unpublished_input(self) -> None:
        with tempfile.TemporaryDirectory(prefix="learnfactory-cli-") as raw:
            root = Path(raw)
            config = self._config(root)
            self.assertEqual(0, self._run(["--config", str(config), "init"])[0])
            challenge = root / "warehouse" / "artifacts" / "challenge"
            challenge.mkdir(parents=True)
            (challenge / "README.md").write_text("start\n", encoding="utf-8")
            outside = root / "outside"
            outside.mkdir()
            (outside / "README.md").write_text("private\n", encoding="utf-8")

            for exercise_id, source in (
                ("../escape", challenge),
                ("absolute", outside),
            ):
                result, _, error = self._run(
                    [
                        "--config",
                        str(config),
                        "exercise-start",
                        exercise_id,
                        str(source),
                        "--student",
                        "student-target",
                    ]
                )
                self.assertEqual(2, result)
                self.assertIn("error:", error)
            self.assertFalse((root / "warehouse" / "learners" / "student-target" / "escape").exists())

            result, output, error = self._run(
                [
                    "--config",
                    str(config),
                    "exercise-start",
                    "safe-exercise",
                    str(challenge),
                    "--student",
                    "student-target",
                ]
            )
            self.assertEqual(0, result, error)
            self.assertTrue(Path(output.strip(), "README.md").is_file())

    def test_ingest_refresh_ids_include_path_commit_and_extractor(self) -> None:
        with tempfile.TemporaryDirectory(prefix="learnfactory-cli-") as raw:
            root = Path(raw)
            config = self._config(root)
            first = root / "one" / "catalog"
            second = root / "two" / "catalog"
            first.mkdir(parents=True)
            second.mkdir(parents=True)

            def descriptor(path: Path) -> SourceDescriptor:
                commit = "1" * 40 if path == first else "2" * 40
                return SourceDescriptor(
                    source_id=f"source-{commit[0]}",
                    source_type="test",
                    name="Test Catalog",
                    path=path,
                    upstream_url=None,
                    commit_hash=commit,
                    license="MIT",
                    metadata={"adapter": "test", "extractor_version": "2.1"},
                )

            with mock.patch(
                "learnfactory.cli.describe_source", side_effect=descriptor
            ):
                self.assertEqual(
                    0,
                    self._run(
                        ["--config", str(config), "ingest", str(first)]
                    )[0],
                )
                # Re-observing the exact path, commit, and extractor is idempotent.
                self.assertEqual(
                    0,
                    self._run(
                        ["--config", str(config), "ingest", str(first)]
                    )[0],
                )
                self.assertEqual(
                    0,
                    self._run(
                        ["--config", str(config), "ingest", str(second)]
                    )[0],
                )
                self.assertEqual(
                    0,
                    self._run(
                        ["--config", str(config), "ingest", str(second)]
                    )[0],
                )
            database = Database(root / "factory.db", Path(__file__).resolve().parents[1] / "migrations")
            with database.connect() as connection:
                jobs = list(
                    connection.execute(
                        "SELECT job_id,payload_json FROM jobs ORDER BY job_id"
                    )
                )
            self.assertEqual(2, len(jobs))
            self.assertTrue(any(row["job_id"] == "job_ingest_catalog" for row in jobs))
            self.assertTrue(
                any("222222222222_v2.1" in row["job_id"] for row in jobs)
            )


if __name__ == "__main__":
    unittest.main()
