from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import learnfactory.handlers as handlers
from learnfactory.db import Database
from learnfactory.handlers import (
    _examiner_text_projection,
    _materialize_csdiy_examiner_result,
)
from learnfactory.util import tree_sha256
from learnfactory.workspace import WorkspaceError
from learnfactory.jobs import JobRepository
from learnfactory.seeding import reconcile_legacy_csdiy_examiners


EVALUATION_SCHEMA = {
    "type": "object",
    "properties": {
        "result": {"type": "string", "enum": ["PASS", "REVISE", "FAIL"]},
        "score": {"type": "number", "minimum": 0, "maximum": 100},
        "evidence": {"type": "array", "items": {"type": "string"}},
        "transfer_gaps": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["result", "score", "evidence", "transfer_gaps"],
    "additionalProperties": False,
}


class ExaminerProjectionTests(unittest.TestCase):
    def test_projection_is_deterministic_text_and_binds_tree_checksum(self) -> None:
        with tempfile.TemporaryDirectory(prefix="lf-examiner-projection-") as raw:
            root = Path(raw) / "candidate"
            (root / "src").mkdir(parents=True)
            (root / "src/main.py").write_text("print('ok')\n", encoding="utf-8")
            (root / "README.md").write_text("design\n", encoding="utf-8")

            first, evidence = _examiner_text_projection(
                root, Path("STUDENT_SUBMISSION")
            )
            second, second_evidence = _examiner_text_projection(
                root, Path("STUDENT_SUBMISSION")
            )

            self.assertEqual(first, second)
            self.assertEqual(evidence["projection_sha256"], second_evidence["projection_sha256"])
            self.assertEqual("tree-sha256-v2", evidence["source_checksum_algorithm"])
            self.assertEqual(tree_sha256(root), evidence["source_checksum"])
            value = json.loads(first)
            self.assertEqual("learnfactory-examiner-text-projection-v1", value["schema"])
            self.assertEqual(
                ["README.md", "src/main.py"],
                [item["path"] for item in value["files"]],
            )

    def test_projection_rejects_symlink_hardlink_invalid_text_nul_and_limits(self) -> None:
        with tempfile.TemporaryDirectory(prefix="lf-examiner-invalid-") as raw:
            base = Path(raw)
            cases: list[tuple[str, Path]] = []
            symlink_root = base / "symlink"
            symlink_root.mkdir()
            (symlink_root / "target").write_text("safe", encoding="utf-8")
            (symlink_root / "alias").symlink_to("target")
            cases.append(("symlink", symlink_root))
            hardlink_root = base / "hardlink"
            hardlink_root.mkdir()
            (hardlink_root / "one").write_text("same", encoding="utf-8")
            os.link(hardlink_root / "one", hardlink_root / "two")
            cases.append(("hardlink", hardlink_root))
            invalid = base / "invalid"
            invalid.write_bytes(b"\xff")
            cases.append(("invalid-utf8", invalid))
            nul = base / "nul"
            nul.write_bytes(b"before\x00after")
            cases.append(("nul", nul))
            oversized = base / "oversized"
            oversized.write_bytes(
                b"x" * (handlers._EXAMINER_PROJECTION_MAX_FILE_BYTES + 1)
            )
            cases.append(("oversized", oversized))
            for name, source in cases:
                with self.subTest(name=name), self.assertRaises(WorkspaceError):
                    _examiner_text_projection(source, Path("INPUT"))

    def test_projection_rejects_named_entry_rename_to_symlink_race(self) -> None:
        with tempfile.TemporaryDirectory(prefix="lf-examiner-race-") as raw:
            root = Path(raw) / "candidate"
            root.mkdir()
            candidate = root / "answer.txt"
            candidate.write_text("learner", encoding="utf-8")
            secret = Path(raw) / "secret.txt"
            secret.write_text("sealed", encoding="utf-8")
            original = handlers._projection_file_record

            def swap_after_read(descriptor: int, before: os.stat_result, relative: str):
                result = original(descriptor, before, relative)
                if relative == "answer.txt":
                    candidate.rename(root / "old-answer.txt")
                    candidate.symlink_to(secret)
                return result

            with mock.patch.object(
                handlers, "_projection_file_record", side_effect=swap_after_read
            ), self.assertRaises(WorkspaceError):
                _examiner_text_projection(root, Path("STUDENT_SUBMISSION"))

    def test_projection_rejects_depth_and_aggregate_overflow_without_truncation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="lf-examiner-bounds-") as raw:
            root = Path(raw)
            (root / "a.txt").write_text("abcd", encoding="utf-8")
            (root / "b.txt").write_text("efgh", encoding="utf-8")
            with mock.patch.object(
                handlers, "_EXAMINER_PROJECTION_MAX_RAW_BYTES", 7
            ), self.assertRaisesRegex(WorkspaceError, "raw bytes"):
                _examiner_text_projection(root, Path("INPUT"))
            deep = root / "deep"
            for index in range(3):
                deep /= str(index)
            deep.mkdir(parents=True)
            with mock.patch.object(
                handlers, "_EXAMINER_PROJECTION_MAX_DEPTH", 2
            ), self.assertRaisesRegex(WorkspaceError, "depth"):
                _examiner_text_projection(root, Path("INPUT"))

    def test_projection_entry_limit_never_retains_or_reads_4097th(self) -> None:
        with tempfile.TemporaryDirectory(prefix="lf-examiner-entry-bound-") as raw:
            root = Path(raw)
            for index in range(handlers._EXAMINER_PROJECTION_MAX_ENTRIES + 1):
                (root / f"entry-{index:04d}.txt").touch()

            admitted: list[str] = []
            original_path_record = handlers._projection_path_record

            def observe_path(relative: str):
                result = original_path_record(relative)
                if relative != ".":
                    admitted.append(relative)
                return result

            with mock.patch.object(
                handlers, "_projection_path_record", side_effect=observe_path
            ), mock.patch.object(
                handlers,
                "_projection_file_record",
                wraps=handlers._projection_file_record,
            ) as read_file, self.assertRaisesRegex(WorkspaceError, "maximum entries"):
                _examiner_text_projection(root, Path("STUDENT_SUBMISSION"))

            self.assertEqual(
                handlers._EXAMINER_PROJECTION_MAX_ENTRIES, len(admitted)
            )
            self.assertEqual(len(admitted), len(set(admitted)))
            read_file.assert_not_called()

    def test_projection_detects_root_and_directory_rename_races(self) -> None:
        with tempfile.TemporaryDirectory(prefix="lf-examiner-directory-race-") as raw:
            base = Path(raw)
            for race in ("root", "directory"):
                root = base / race / "candidate"
                nested = root / "nested"
                nested.mkdir(parents=True)
                (nested / "answer.txt").write_text("learner\n", encoding="utf-8")
                original = handlers._projection_file_record
                raced = False

                def rename_after_read(
                    descriptor: int, before: os.stat_result, relative: str
                ):
                    nonlocal raced
                    result = original(descriptor, before, relative)
                    if not raced:
                        raced = True
                        target = root if race == "root" else nested
                        target.rename(target.with_name(target.name + "-retired"))
                        target.mkdir()
                    return result

                with self.subTest(race=race), mock.patch.object(
                    handlers,
                    "_projection_file_record",
                    side_effect=rename_after_read,
                ), self.assertRaises(WorkspaceError):
                    _examiner_text_projection(root, Path("STUDENT_SUBMISSION"))
                self.assertTrue(raced)


class ExaminerResultPublicationTests(unittest.TestCase):
    def test_every_invalid_result_class_publishes_neither_file(self) -> None:
        valid_evaluation = {
            "result": "PASS",
            "score": 90,
            "evidence": ["observed"],
            "transfer_gaps": [],
        }
        cases = {
            "malformed": "{",
            "partial": json.dumps({"evaluation": valid_evaluation}),
            "trailing": json.dumps(
                {"evaluation": valid_evaluation, "feedback": "ok"}
            )
            + " trailing",
            "duplicate": (
                '{"evaluation":{},"evaluation":{},"feedback":"forged"}'
            ),
            "schema-invalid": json.dumps(
                {
                    "evaluation": {**valid_evaluation, "score": "100"},
                    "feedback": "forged",
                }
            ),
            "nonstandard-number": (
                '{"evaluation":{"result":"PASS","score":NaN,'
                '"evidence":[],"transfer_gaps":[]},"feedback":"forged"}'
            ),
            "overflow-number": (
                '{"evaluation":{"result":"PASS","score":1e999,'
                '"evidence":[],"transfer_gaps":[]},"feedback":"forged"}'
            ),
            "nul-text": json.dumps(
                {"evaluation": valid_evaluation, "feedback": "forged\x00text"}
            ),
            "invalid-unicode": (
                '{"evaluation":{"result":"PASS","score":90,'
                '"evidence":["\\ud800"],"transfer_gaps":[]},"feedback":"forged"}'
            ),
            "deep": "[" * 2_000 + "0" + "]" * 2_000,
            "oversized": "x" * (1024 * 1024 + 1),
        }
        with tempfile.TemporaryDirectory(prefix="lf-examiner-publication-") as raw:
            base = Path(raw)
            for name, final_message in cases.items():
                workspace = base / name
                workspace.mkdir()
                with self.subTest(name=name), self.assertRaises(ValueError):
                    _materialize_csdiy_examiner_result(
                        workspace, final_message, EVALUATION_SCHEMA
                    )
                self.assertFalse((workspace / "evaluation.json").exists())
                self.assertFalse((workspace / "feedback.md").exists())


class LegacyExaminerReconciliationTests(unittest.TestCase):
    def test_reconciliation_is_global_atomic_idempotent_and_history_safe(self) -> None:
        with tempfile.TemporaryDirectory(prefix="lf-examiner-reconcile-") as raw:
            database = Database(
                Path(raw) / "factory.db",
                Path(__file__).resolve().parents[1] / "migrations",
            )
            database.migrate()
            jobs = JobRepository(database, secret_value_provider=lambda: ())

            def payload(*, bound: bool = False) -> dict[str, object]:
                value: dict[str, object] = {
                    "seed_policy": {
                        "kind": "csdiy_course_progression",
                        "role": "examiner",
                    }
                }
                if bound:
                    value["student_submission_binding"] = {"present": True}
                return value

            identifiers = {
                name: jobs.create(
                    "codex_task", "examiner", payload(bound=name == "bound"),
                    job_id=f"job_reconcile_{name}",
                )
                for name in (
                    "discovered",
                    "ready",
                    "active",
                    "attempted",
                    "terminal",
                    "bound",
                )
            }
            with database.transaction(immediate=True) as connection:
                for name in ("ready", "active", "attempted", "bound"):
                    connection.execute(
                        "UPDATE jobs SET state='READY' WHERE job_id=?",
                        (identifiers[name],),
                    )
                connection.execute(
                    """
                    UPDATE jobs SET state='CLAIMED',owner='worker',lease_token='lease',
                        lease_expires_at=9999999999,attempt_count=1
                    WHERE job_id=?
                    """,
                    (identifiers["active"],),
                )
                connection.execute(
                    """
                    UPDATE jobs SET state='CLAIMED',owner='worker',lease_token='lease',
                        lease_expires_at=9999999999,attempt_count=1
                    WHERE job_id=?
                    """,
                    (identifiers["attempted"],),
                )
                connection.execute(
                    """
                    UPDATE jobs SET state='RETRY_WAIT',owner=NULL,lease_token=NULL,
                        lease_expires_at=NULL,retry_at=9999999999
                    WHERE job_id=?
                    """,
                    (identifiers["attempted"],),
                )
                connection.execute(
                    "UPDATE jobs SET state='CANCELLED',cancel_requested=1 WHERE job_id=?",
                    (identifiers["terminal"],),
                )

            first = reconcile_legacy_csdiy_examiners(database)
            second = reconcile_legacy_csdiy_examiners(database)
            self.assertEqual(
                [
                    identifiers["attempted"],
                    identifiers["discovered"],
                    identifiers["ready"],
                ],
                first["job_ids"],
            )
            self.assertEqual([identifiers["active"]], first["cancel_requested_job_ids"])
            self.assertEqual(
                {
                    "cancelled": 0,
                    "job_ids": [],
                    "cancel_requested": 0,
                    "cancel_requested_job_ids": [],
                },
                second,
            )
            self.assertEqual("CLAIMED", jobs.get(identifiers["active"])["state"])
            self.assertEqual(1, jobs.get(identifiers["active"])["cancel_requested"])
            self.assertEqual("CANCELLED", jobs.get(identifiers["attempted"])["state"])
            self.assertEqual("CANCELLED", jobs.get(identifiers["terminal"])["state"])
            self.assertEqual("READY", jobs.get(identifiers["bound"])["state"])
            with database.connect() as connection:
                events = connection.execute(
                    """
                    SELECT COUNT(*) FROM events
                    WHERE type='CSDIY_EXAMINER_ISOLATION_SUPERSEDED'
                    """
                ).fetchone()[0]
            self.assertEqual(3, events)

    def test_reconciliation_rejects_ambiguous_persisted_examiner_json(self) -> None:
        cases: dict[str, object] = {
            "duplicate-nested-key": (
                '{"seed_policy":{"kind":"csdiy_course_cohort",'
                '"role":"examiner","role":"reviewer"}}'
            ),
            "nan": '{"seed_policy":{"kind":"csdiy_course_cohort",'
            '"role":"examiner"},"value":NaN}',
            "overflow-to-infinity": '{"seed_policy":{"kind":"csdiy_course_cohort",'
            '"role":"examiner"},"value":1e999}',
            "deep": "[" * 2_000 + "0" + "]" * 2_000,
            "invalid-utf8": b"\xff",
            "oversized": " " * (2 * 1024 * 1024 + 1),
        }
        for name, ambiguous in cases.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory(
                prefix="lf-examiner-ambiguous-"
            ) as raw:
                database = Database(
                    Path(raw) / "factory.db",
                    Path(__file__).resolve().parents[1] / "migrations",
                )
                database.migrate()
                jobs = JobRepository(database, secret_value_provider=lambda: ())
                job_id = jobs.create(
                    "codex_task",
                    "examiner",
                    {
                        "seed_policy": {
                            "kind": "csdiy_course_cohort",
                            "role": "examiner",
                        }
                    },
                )
                with database.transaction(immediate=True) as connection:
                    connection.execute(
                        "UPDATE jobs SET payload_json=? WHERE job_id=?",
                        (ambiguous, job_id),
                    )
                with self.assertRaisesRegex(
                    RuntimeError, "ambiguous persisted payload"
                ):
                    reconcile_legacy_csdiy_examiners(database)
                with database.connect() as connection:
                    state = connection.execute(
                        "SELECT state FROM jobs WHERE job_id=?", (job_id,)
                    ).fetchone()["state"]
                self.assertEqual("DISCOVERED", state)


if __name__ == "__main__":
    unittest.main()
