from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import learnfactory.byox_gate_backfill as backfill
from learnfactory.byox_gate_backfill import (
    BYOX_CODE_AUDIT_SCOPE,
    ByoxGateBackfillError,
    revalidate_archived_byox_artifacts,
)
from learnfactory.byox_jobs import (
    BYOX_CODE_PRESENCE_VALIDATOR,
    byox_runtime_safety_validators,
)
from learnfactory.cli import build_parser, main
from learnfactory.db import Database
from learnfactory.util import canonical_json, tree_sha256
from learnfactory.validation import byox_code_policy_digest, evaluate_byox_code_presence


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = REPOSITORY_ROOT / "migrations"


class ByoxGateBackfillTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="learnfactory-byox-backfill-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.warehouse = self.root / "warehouse"
        (self.warehouse / "artifacts").mkdir(parents=True)
        self.database = Database(self.root / "factory.db", MIGRATIONS)
        self.database.migrate()
        self.counter = 0

    @staticmethod
    def _code_tree(path: Path, marker: str = "base") -> None:
        files = {
            "sealed/reference/main.py": f"def answer(): return {marker!r}\n",
            "starter/main.py": "def answer(): raise NotImplementedError\n",
            "public_tests/test_main.py": "def test_contract(): assert True\n",
        }
        for relative, content in files.items():
            target = path / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")

    def _artifact(
        self,
        *,
        artifact_type: str = "byox-challenge-pack",
        policy_kind: str = "byox_reference_build",
        marker: str | None = None,
        job_id: str | None = None,
        attempt: int = 1,
    ) -> tuple[str, str, Path]:
        self.counter += 1
        suffix = str(self.counter)
        job_id = job_id or f"job_byox_backfill_{suffix}"
        artifact_id = f"artifact_byox_backfill_{suffix}"
        path = (
            self.warehouse
            / "artifacts"
            / "projects"
            / "build-your-own-x"
            / job_id
            / f"attempt-{attempt:03d}-{suffix}"
        )
        path.mkdir(parents=True)
        self._code_tree(path, marker or suffix)
        payload = {
            "seed_policy": {"kind": policy_kind, "version": 1, "role": "builder"},
            "project_id": f"project-{suffix}",
            "artifact_type": artifact_type,
        }
        checksum = tree_sha256(path)
        with self.database.transaction(immediate=True) as connection:
            if connection.execute(
                "SELECT 1 FROM jobs WHERE job_id=?", (job_id,)
            ).fetchone() is None:
                connection.execute(
                    """
                    INSERT INTO jobs(
                        job_id,type,worker_type,state,priority,payload_json,
                        attempt_count,max_attempts,created_at,finished_at
                    ) VALUES (?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        job_id,
                        "codex_task",
                        "reference_builder",
                        "SUCCEEDED",
                        1.0,
                        canonical_json(payload),
                        attempt,
                        2,
                        1.0,
                        2.0,
                    ),
                )
            connection.execute(
                """
                INSERT INTO artifacts(
                    artifact_id,job_id,type,path,checksum,metadata_json,created_at,
                    validation_status,attempt_number,checksum_algorithm,integrity_status
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    artifact_id,
                    job_id,
                    artifact_type,
                    str(path),
                    checksum,
                    "{}",
                    float(self.counter),
                    "GENERATED+PARTIAL",
                    attempt,
                    "tree-sha256-v2",
                    "VERIFIED_V2",
                ),
            )
        return artifact_id, job_id, path

    def _validation(
        self,
        job_id: str,
        *,
        evidence: dict[str, object],
        status: str = "PASS",
        claims: list[str] | None = None,
        suffix: str = "1",
    ) -> None:
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                """
                INSERT INTO validations(
                    validation_id,job_id,validator,status,evidence_json,
                    started_at,finished_at,attempt_number,claims_json
                ) VALUES (?,?,?,?,?,?,?,?,?)
                """,
                (
                    f"validation_backfill_{self.counter}_{suffix}",
                    job_id,
                    BYOX_CODE_PRESENCE_VALIDATOR,
                    status,
                    canonical_json(evidence),
                    1.0,
                    2.0,
                    1,
                    canonical_json(["PARTIAL"] if claims is None else claims),
                ),
            )

    def _table(self, table: str) -> list[tuple[object, ...]]:
        with self.database.connect() as connection:
            columns = [
                str(row[1])
                for row in connection.execute(f"PRAGMA table_info({table})")
            ]
            return [
                tuple(row[column] for column in columns)
                for row in connection.execute(f"SELECT * FROM {table} ORDER BY rowid")
            ]

    def test_absent_evidence_pass_is_append_only_idempotent_and_non_promoting(self) -> None:
        artifact_id, job_id, _ = self._artifact()
        protected = {
            table: self._table(table)
            for table in ("jobs", "artifacts", "validations", "artifact_validation_labels")
        }

        first = revalidate_archived_byox_artifacts(
            self.database, self.warehouse, artifact_ids=[artifact_id]
        )
        second = revalidate_archived_byox_artifacts(
            self.database, self.warehouse, artifact_ids=[artifact_id]
        )

        self.assertEqual(1, first["inserted"])
        self.assertEqual(0, first["already_recorded"])
        self.assertEqual({"PASS": 1}, first["effective_outcomes"])
        self.assertEqual("ABSENT", first["records"][0]["controller_evidence_category"])
        self.assertFalse(first["builds_or_tested_claimed"])
        self.assertEqual([], first["semantic_claims_added"])
        self.assertEqual(0, second["inserted"])
        self.assertEqual(1, second["already_recorded"])
        self.assertEqual(first["records"][0]["audit_id"], second["records"][0]["audit_id"])
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM byox_code_presence_audits WHERE artifact_id=?",
                (artifact_id,),
            ).fetchone()
            self.assertEqual("PASS", row["outcome"])
            self.assertEqual("PASS", row["gate_status"])
            self.assertEqual(BYOX_CODE_AUDIT_SCOPE, row["scope"])
            self.assertEqual("[]", row["semantic_claims_json"])
            self.assertEqual(job_id, row["job_id"])
            with self.assertRaisesRegex(sqlite3.IntegrityError, "append-only"):
                connection.execute(
                    "UPDATE byox_code_presence_audits SET outcome='FAIL' WHERE audit_id=?",
                    (row["audit_id"],),
                )
            with self.assertRaisesRegex(sqlite3.IntegrityError, "append-only"):
                connection.execute(
                    "DELETE FROM byox_code_presence_audits WHERE audit_id=?",
                    (row["audit_id"],),
                )
        for table, before in protected.items():
            self.assertEqual(before, self._table(table), table)

    def test_legacy_unbound_and_exact_final_policy_evidence_are_distinguished(self) -> None:
        legacy_id, legacy_job, _ = self._artifact()
        self._validation(
            legacy_job,
            evidence={"scope": "code-presence-structure-only", "schema_version": 1},
        )
        legacy = revalidate_archived_byox_artifacts(
            self.database, self.warehouse, artifact_ids=[legacy_id]
        )
        self.assertEqual(
            "LEGACY_SCHEMA_ONLY",
            legacy["records"][0]["controller_evidence_category"],
        )
        self.assertEqual({"PASS": 1}, legacy["effective_outcomes"])

        current_id, current_job, current_path = self._artifact()
        specification = next(
            value
            for value in byox_runtime_safety_validators()
            if value["name"] == BYOX_CODE_PRESENCE_VALIDATOR
        )
        gate = evaluate_byox_code_presence(
            current_path, specification, name=BYOX_CODE_PRESENCE_VALIDATOR
        )
        self.assertEqual("PASS", gate.status)
        self._validation(current_job, evidence=gate.evidence, suffix="current")

        current = revalidate_archived_byox_artifacts(
            self.database, self.warehouse, artifact_ids=[current_id]
        )
        self.assertEqual(
            "FINAL_POLICY_MATCH",
            current["records"][0]["controller_evidence_category"],
        )
        self.assertEqual({"PASS": 1}, current["effective_outcomes"])

    def test_checksum_drift_appends_failure_without_running_gate(self) -> None:
        artifact_id, _, path = self._artifact()
        (path / "starter/main.py").write_text("changed = True\n", encoding="utf-8")

        result = revalidate_archived_byox_artifacts(
            self.database, self.warehouse, artifact_ids=[artifact_id]
        )

        self.assertEqual({"FAIL": 1}, result["effective_outcomes"])
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT gate_status,observed_checksum,evidence_json FROM byox_code_presence_audits"
            ).fetchone()
        self.assertEqual("NOT_RUN", row["gate_status"])
        evidence = json.loads(row["evidence_json"])["observation"]
        self.assertIn("checksum-drift", evidence["reason_codes"])
        self.assertNotEqual(evidence["artifact"]["artifact_checksum"], row["observed_checksum"])

    def test_mutation_during_gate_is_caught_by_post_gate_checksum(self) -> None:
        artifact_id, _, path = self._artifact()
        evaluate = backfill.evaluate_byox_code_manifest

        def mutate_after_gate(*args: object, **kwargs: object):
            result = evaluate(*args, **kwargs)
            (path / "changed-during-gate.txt").write_text("drift\n", encoding="utf-8")
            return result

        with patch(
            "learnfactory.byox_gate_backfill.evaluate_byox_code_manifest",
            side_effect=mutate_after_gate,
        ):
            result = revalidate_archived_byox_artifacts(
                self.database, self.warehouse, artifact_ids=[artifact_id]
            )

        self.assertEqual({"FAIL": 1}, result["effective_outcomes"])
        with self.database.connect() as connection:
            evidence = json.loads(
                connection.execute(
                    "SELECT evidence_json FROM byox_code_presence_audits"
                ).fetchone()[0]
            )["observation"]
        self.assertIn("tree-changed-during-policy-replay", evidence["reason_codes"])

    def test_transient_source_mutation_cannot_change_private_snapshot_gate(self) -> None:
        artifact_id, _, path = self._artifact()
        starter = path / "starter/main.py"
        starter.unlink()
        checksum = tree_sha256(path)
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                "UPDATE artifacts SET checksum=? WHERE artifact_id=?",
                (checksum, artifact_id),
            )
        specification = next(
            value
            for value in byox_runtime_safety_validators()
            if value["name"] == BYOX_CODE_PRESENCE_VALIDATOR
        )
        self.assertEqual(
            "FAIL",
            evaluate_byox_code_presence(
                path, specification, name=BYOX_CODE_PRESENCE_VALIDATOR
            ).status,
        )
        evaluate = backfill.evaluate_byox_code_manifest
        evaluated_paths: list[Path] = []

        def transient_source_insert(*args: object, **kwargs: object):
            scratch = self.warehouse / backfill._SNAPSHOT_PARENT_NAME
            snapshot = next(scratch.iterdir())
            evaluated_paths.append(snapshot)
            self.assertNotEqual(path, snapshot)
            self.assertEqual(0o700, snapshot.stat().st_mode & 0o777)
            starter.write_text("def answer(): return 'transient'\n", encoding="utf-8")
            try:
                self.assertEqual(
                    "PASS",
                    evaluate_byox_code_presence(
                        path, specification, name=BYOX_CODE_PRESENCE_VALIDATOR
                    ).status,
                )
                return evaluate(*args, **kwargs)
            finally:
                starter.unlink()

        with patch(
            "learnfactory.byox_gate_backfill.evaluate_byox_code_manifest",
            side_effect=transient_source_insert,
        ):
            result = revalidate_archived_byox_artifacts(
                self.database, self.warehouse, artifact_ids=[artifact_id]
            )

        self.assertEqual({"FAIL": 1}, result["effective_outcomes"])
        self.assertTrue(evaluated_paths)
        self.assertEqual(
            "FAIL",
            evaluate_byox_code_presence(
                path, specification, name=BYOX_CODE_PRESENCE_VALIDATOR
            ).status,
        )
        scratch = self.warehouse / backfill._SNAPSHOT_PARENT_NAME
        self.assertTrue(scratch.is_dir())
        self.assertEqual([], list(scratch.iterdir()))
        with self.database.connect() as connection:
            evidence = json.loads(
                connection.execute(
                    "SELECT evidence_json FROM byox_code_presence_audits"
                ).fetchone()[0]
            )["observation"]
        self.assertEqual("FAIL", evidence["gate"]["status"])
        self.assertEqual(
            backfill.BYOX_CODE_AUDIT_PROTOCOL,
            evidence["archive_tree"]["audit_protocol"],
        )
        self.assertNotIn(str(evaluated_paths[0]), canonical_json(evidence))

    def test_transient_snapshot_mutation_cannot_change_manifest_gate(self) -> None:
        artifact_id, _, path = self._artifact()
        (path / "starter/main.py").unlink()
        checksum = tree_sha256(path)
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                "UPDATE artifacts SET checksum=? WHERE artifact_id=?",
                (checksum, artifact_id),
            )
        specification = next(
            value
            for value in byox_runtime_safety_validators()
            if value["name"] == BYOX_CODE_PRESENCE_VALIDATOR
        )
        evaluate_manifest = backfill.evaluate_byox_code_manifest

        def transient_snapshot_insert(*args: object, **kwargs: object):
            scratch = self.warehouse / backfill._SNAPSHOT_PARENT_NAME
            snapshot = next(scratch.iterdir())
            starter = snapshot / "starter/main.py"
            starter.write_text("def answer(): return 'transient'\n", encoding="utf-8")
            try:
                self.assertEqual(
                    "PASS",
                    evaluate_byox_code_presence(
                        snapshot,
                        specification,
                        name=BYOX_CODE_PRESENCE_VALIDATOR,
                    ).status,
                )
                return evaluate_manifest(*args, **kwargs)
            finally:
                starter.unlink()

        with patch(
            "learnfactory.byox_gate_backfill.evaluate_byox_code_manifest",
            side_effect=transient_snapshot_insert,
        ):
            result = revalidate_archived_byox_artifacts(
                self.database, self.warehouse, artifact_ids=[artifact_id]
            )

        self.assertEqual({"FAIL": 1}, result["effective_outcomes"])
        with self.database.connect() as connection:
            evidence = json.loads(
                connection.execute(
                    "SELECT evidence_json FROM byox_code_presence_audits"
                ).fetchone()[0]
            )["observation"]
        self.assertEqual("FAIL", evidence["gate"]["status"])
        self.assertEqual("CHECKED", evidence["archive_tree"]["status"])
        self.assertEqual(
            evidence["archive_tree"]["policy_manifest_digest"],
            evidence["gate"]["evidence"]["manifest_digest"],
        )
        self.assertEqual(
            [],
            list((self.warehouse / backfill._SNAPSHOT_PARENT_NAME).iterdir()),
        )

    def test_snapshot_copy_failure_is_cleaned_without_running_gate(self) -> None:
        artifact_id, _, _ = self._artifact()
        with patch(
            "learnfactory.byox_gate_backfill._copy_regular_file_from_directory",
            side_effect=backfill._TreeAuditFailure("injected-copy-failure"),
        ), patch(
            "learnfactory.byox_gate_backfill.evaluate_byox_code_manifest"
        ) as evaluate:
            result = revalidate_archived_byox_artifacts(
                self.database, self.warehouse, artifact_ids=[artifact_id]
            )

        self.assertEqual({"FAIL": 1}, result["effective_outcomes"])
        evaluate.assert_not_called()
        scratch = self.warehouse / backfill._SNAPSHOT_PARENT_NAME
        self.assertTrue(scratch.is_dir())
        self.assertEqual([], list(scratch.iterdir()))

    def test_private_snapshot_mutation_is_rejected_and_cleaned(self) -> None:
        artifact_id, _, _ = self._artifact()
        evaluate = backfill.evaluate_byox_code_manifest
        observed_snapshot: list[Path] = []

        def mutate_snapshot(*args: object, **kwargs: object):
            scratch = self.warehouse / backfill._SNAPSHOT_PARENT_NAME
            snapshot = next(scratch.iterdir())
            observed_snapshot.append(snapshot)
            result = evaluate(*args, **kwargs)
            (snapshot / "transient-output.txt").write_text("drift\n", encoding="utf-8")
            return result

        with patch(
            "learnfactory.byox_gate_backfill.evaluate_byox_code_manifest",
            side_effect=mutate_snapshot,
        ):
            result = revalidate_archived_byox_artifacts(
                self.database, self.warehouse, artifact_ids=[artifact_id]
            )

        self.assertEqual({"FAIL": 1}, result["effective_outcomes"])
        self.assertTrue(observed_snapshot)
        self.assertFalse(observed_snapshot[0].exists())
        with self.database.connect() as connection:
            evidence = json.loads(
                connection.execute(
                    "SELECT evidence_json FROM byox_code_presence_audits"
                ).fetchone()[0]
            )["observation"]
        self.assertIn(
            "private-snapshot-changed-during-policy-replay",
            evidence["reason_codes"],
        )
        replay = revalidate_archived_byox_artifacts(
            self.database, self.warehouse, artifact_ids=[artifact_id]
        )
        self.assertEqual({"CONFLICT": 1}, replay["effective_outcomes"])

    def test_tree_checksum_never_follows_a_queued_directory_replacement(self) -> None:
        tree = self.root / "queued-directory-tree"
        nested = tree / "starter"
        nested.mkdir(parents=True)
        displaced = tree / "starter-before-swap"
        outside = self.root / "queued-directory-outside"
        outside.mkdir()
        outside_content = b"outside checksum material\n"
        (outside / "external.py").write_bytes(outside_content)

        control = self.root / "queued-directory-control"
        (control / "starter").mkdir(parents=True)
        (control / "starter/external.py").write_bytes(outside_content)
        outside_checksum = backfill._bounded_tree_checksum(control).checksum

        real_open = backfill.os.open
        real_push = backfill.heapq.heappush
        swapped = False

        def perform_swap() -> None:
            nonlocal swapped
            if swapped:
                return
            nested.rename(displaced)
            nested.symlink_to(outside, target_is_directory=True)
            swapped = True

        def race_directory_open(
            path: object, flags: int, *args: object, **kwargs: object
        ) -> int:
            if path == "starter" and kwargs.get("dir_fd") is not None:
                perform_swap()
            return real_open(path, flags, *args, **kwargs)  # type: ignore[arg-type]

        def race_queued_path(heap: list[object], item: object) -> None:
            real_push(heap, item)
            if (
                isinstance(item, tuple)
                and len(item) == 2
                and Path(item[1]) == nested
            ):
                perform_swap()

        with (
            patch.object(backfill.os, "open", side_effect=race_directory_open),
            patch.object(backfill.heapq, "heappush", side_effect=race_queued_path),
        ):
            with self.assertRaises(backfill._TreeAuditFailure):
                observed = backfill._bounded_tree_checksum(tree)
                self.assertNotEqual(outside_checksum, observed.checksum)

        self.assertTrue(swapped)

    def test_tree_checksum_never_follows_a_replaced_root_component(self) -> None:
        parent = self.root / "root-component-parent"
        tree = parent / "tree"
        tree.mkdir(parents=True)
        (tree / "inside.txt").write_text("inside\n", encoding="utf-8")
        displaced = self.root / "root-component-parent-before-swap"
        outside_parent = self.root / "root-component-outside"
        (outside_parent / "tree").mkdir(parents=True)
        (outside_parent / "tree/outside.txt").write_text(
            "outside\n", encoding="utf-8"
        )

        real_open = backfill.os.open
        swapped = False

        def race_root_component(
            path: object, flags: int, *args: object, **kwargs: object
        ) -> int:
            nonlocal swapped
            if (
                not swapped
                and path == parent.name
                and kwargs.get("dir_fd") is not None
            ):
                parent.rename(displaced)
                parent.symlink_to(outside_parent, target_is_directory=True)
                swapped = True
            return real_open(path, flags, *args, **kwargs)  # type: ignore[arg-type]

        with patch.object(backfill.os, "open", side_effect=race_root_component):
            with self.assertRaises(backfill._TreeAuditFailure):
                backfill._bounded_tree_checksum(tree)

        self.assertTrue(swapped)

    def test_private_copy_is_authority_when_source_changes_after_early_read(self) -> None:
        tree = self.root / "source-changing-during-copy"
        (tree / "a").mkdir(parents=True)
        (tree / "z").mkdir()
        early = tree / "a/early.txt"
        original = b"early\n"
        early.write_bytes(original)
        (tree / "z/late.txt").write_text("late\n", encoding="utf-8")
        destination = self.root / "detached-copy"
        destination.mkdir()
        original_copy = backfill._copy_regular_file_from_directory
        swapped = False

        def replace_after_late_file(*args: object, **kwargs: object) -> str:
            nonlocal swapped
            digest = original_copy(*args, **kwargs)
            if args[1] == "late.txt":
                early.write_text("replacement\n", encoding="utf-8")
                swapped = True
            return digest

        with patch.object(
            backfill,
            "_copy_regular_file_from_directory",
            side_effect=replace_after_late_file,
        ):
            copied = backfill._copy_bounded_tree(tree, destination)

        self.assertTrue(swapped)
        self.assertEqual(original, (destination / "a/early.txt").read_bytes())
        self.assertNotEqual(early.read_bytes(), (destination / "a/early.txt").read_bytes())
        self.assertEqual(copied.tree.checksum, copied.manifest_tree_checksum)
        self.assertEqual(copied.tree.checksum, tree_sha256(destination))

    def test_external_hardlink_is_rejected_even_when_stored_checksum_matches(self) -> None:
        artifact_id, _, path = self._artifact()
        external = self.root / "external-hardlink.py"
        external.write_text("def external(): return True\n", encoding="utf-8")
        os.link(external, path / "starter/external.py")
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                "UPDATE artifacts SET checksum=? WHERE artifact_id=?",
                (tree_sha256(path), artifact_id),
            )

        result = revalidate_archived_byox_artifacts(
            self.database, self.warehouse, artifact_ids=[artifact_id]
        )

        self.assertEqual({"FAIL": 1}, result["effective_outcomes"])
        with self.database.connect() as connection:
            observation = json.loads(
                connection.execute(
                    "SELECT evidence_json FROM byox_code_presence_audits"
                ).fetchone()[0]
            )["observation"]
        self.assertIn("hardlink-entry", observation["reason_codes"])

    def test_checksum_and_snapshot_copy_share_an_exact_depth_bound(self) -> None:
        def tree_at(path: Path, depth: int) -> None:
            path.mkdir()
            current = path
            for _ in range(depth):
                current = current / "d"
                current.mkdir()
            (current / "leaf.txt").write_text("leaf\n", encoding="utf-8")

        exact = self.root / "backfill-depth-exact"
        tree_at(exact, backfill.BYOX_TREE_MAX_DEPTH)
        exact_checksum = backfill._bounded_tree_checksum(exact)
        exact_copy = self.root / "backfill-depth-exact-copy"
        exact_copy.mkdir()
        copied = backfill._copy_bounded_tree(exact, exact_copy)

        over = self.root / "backfill-depth-over"
        tree_at(over, backfill.BYOX_TREE_MAX_DEPTH + 1)
        over_copy = self.root / "backfill-depth-over-copy"
        over_copy.mkdir()

        self.assertEqual(1, exact_checksum.files)
        self.assertEqual(exact_checksum.checksum, copied.tree.checksum)
        with self.assertRaisesRegex(backfill._TreeAuditFailure, "max-depth-exceeded"):
            backfill._bounded_tree_checksum(over)
        with self.assertRaisesRegex(backfill._TreeAuditFailure, "max-depth-exceeded"):
            backfill._copy_bounded_tree(over, over_copy)

    def test_checksum_directory_fd_closes_when_initial_fstat_raises(self) -> None:
        tree = self.root / "checksum-fstat-failure"
        (tree / "nested").mkdir(parents=True)
        original_open_tree = backfill._open_tree_directory
        original_fstat = backfill.os.fstat
        returned_descriptors: list[int] = []
        fail_descriptors: set[int] = set()

        def mark_returned(*args: object, **kwargs: object) -> int:
            descriptor = original_open_tree(*args, **kwargs)
            if not fail_descriptors:
                returned_descriptors.append(descriptor)
                fail_descriptors.add(descriptor)
            return descriptor

        def fail_initial_fstat(descriptor: int):
            if descriptor in fail_descriptors:
                fail_descriptors.remove(descriptor)
                raise OSError("injected checksum fstat failure")
            return original_fstat(descriptor)

        try:
            with (
                patch.object(
                    backfill,
                    "_open_tree_directory",
                    side_effect=mark_returned,
                ),
                patch.object(backfill.os, "fstat", side_effect=fail_initial_fstat),
            ):
                with self.assertRaisesRegex(OSError, "injected checksum fstat"):
                    backfill._bounded_tree_checksum(tree)
            self.assertTrue(returned_descriptors)
            for descriptor in returned_descriptors:
                with self.assertRaises(OSError):
                    os.fstat(descriptor)
        finally:
            for descriptor in returned_descriptors:
                try:
                    os.close(descriptor)
                except OSError:
                    pass

    def test_symlink_and_special_file_fail_closed_even_with_stored_tree_hash(self) -> None:
        for entry_type in ("symlink", "fifo"):
            artifact_id, _, path = self._artifact(marker=entry_type)
            unsafe = path / f"unsafe-{entry_type}"
            if entry_type == "symlink":
                unsafe.symlink_to("starter/main.py")
            else:
                os.mkfifo(unsafe)
            with self.database.transaction(immediate=True) as connection:
                connection.execute(
                    "UPDATE artifacts SET checksum=? WHERE artifact_id=?",
                    (tree_sha256(path), artifact_id),
                )

            result = revalidate_archived_byox_artifacts(
                self.database, self.warehouse, artifact_ids=[artifact_id]
            )

            self.assertEqual({"FAIL": 1}, result["effective_outcomes"])
            with self.database.connect() as connection:
                evidence = json.loads(
                    connection.execute(
                        "SELECT evidence_json FROM byox_code_presence_audits WHERE artifact_id=?",
                        (artifact_id,),
                    ).fetchone()[0]
                )["observation"]
            expected = "symlink-entry" if entry_type == "symlink" else "special-file-entry"
            self.assertIn(expected, evidence["reason_codes"])

    def test_ambiguous_job_attempt_artifacts_fail_closed(self) -> None:
        first_id, job_id, _ = self._artifact()
        self._artifact(marker="second", job_id=job_id)

        result = revalidate_archived_byox_artifacts(
            self.database, self.warehouse, artifact_ids=[first_id]
        )

        self.assertEqual({"FAIL": 1}, result["effective_outcomes"])
        with self.database.connect() as connection:
            evidence = json.loads(
                connection.execute(
                    "SELECT evidence_json FROM byox_code_presence_audits WHERE artifact_id=?",
                    (first_id,),
                ).fetchone()[0]
            )["observation"]
        self.assertIn("ambiguous-job-attempt-artifacts", evidence["identity_errors"])

    def test_ambiguity_added_after_observation_aborts_inside_write_transaction(self) -> None:
        artifact_id, job_id, _ = self._artifact()
        observe = backfill._observe_artifact

        def add_ambiguous_artifact(*args: object, **kwargs: object):
            observation = observe(*args, **kwargs)
            self._artifact(marker="racing", job_id=job_id)
            return observation

        with patch(
            "learnfactory.byox_gate_backfill._observe_artifact",
            side_effect=add_ambiguous_artifact,
        ):
            with self.assertRaisesRegex(ByoxGateBackfillError, "identity changed"):
                revalidate_archived_byox_artifacts(
                    self.database, self.warehouse, artifact_ids=[artifact_id]
                )
        with self.database.connect() as connection:
            self.assertEqual(
                0,
                connection.execute(
                    "SELECT COUNT(*) FROM byox_code_presence_audits"
                ).fetchone()[0],
            )

    def test_lexical_path_aliases_make_each_binding_ambiguous(self) -> None:
        first_id, _, first_path = self._artifact()
        second_id, _, _ = self._artifact()
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                "UPDATE artifacts SET path=? WHERE artifact_id=?",
                (str(first_path) + "/.", second_id),
            )

        result = revalidate_archived_byox_artifacts(
            self.database,
            self.warehouse,
            artifact_ids=[first_id, second_id],
        )

        self.assertEqual({"FAIL": 2}, result["effective_outcomes"])
        with self.database.connect() as connection:
            observations = [
                json.loads(row[0])["observation"]
                for row in connection.execute(
                    "SELECT evidence_json FROM byox_code_presence_audits ORDER BY artifact_id"
                )
            ]
        self.assertTrue(
            all(
                "ambiguous-normalized-artifact-path" in item["identity_errors"]
                for item in observations
            )
        )

    def test_normalized_alias_scan_includes_non_byox_artifact_types(self) -> None:
        artifact_id, _, path = self._artifact()
        other_id, _, _ = self._artifact()
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                "UPDATE artifacts SET type='unrelated-artifact',path=? WHERE artifact_id=?",
                (str(path) + "/.", other_id),
            )

        result = revalidate_archived_byox_artifacts(
            self.database, self.warehouse, artifact_ids=[artifact_id]
        )

        self.assertEqual({"FAIL": 1}, result["effective_outcomes"])
        with self.database.connect() as connection:
            observation = json.loads(
                connection.execute(
                    "SELECT evidence_json FROM byox_code_presence_audits"
                ).fetchone()[0]
            )["observation"]
        self.assertIn(
            "ambiguous-normalized-artifact-path", observation["identity_errors"]
        )

    def test_conflicting_current_policy_controller_evidence_is_not_accepted(self) -> None:
        artifact_id, job_id, _ = self._artifact()
        self._validation(
            job_id,
            evidence={"policy_digest": byox_code_policy_digest(), "fabricated": True},
        )

        result = revalidate_archived_byox_artifacts(
            self.database, self.warehouse, artifact_ids=[artifact_id]
        )

        self.assertEqual({"CONFLICT": 1}, result["effective_outcomes"])
        self.assertEqual("CONFLICT", result["records"][0]["controller_evidence_category"])
        with self.database.connect() as connection:
            labels = connection.execute(
                "SELECT COUNT(*) FROM artifact_validation_labels WHERE artifact_id=?",
                (artifact_id,),
            ).fetchone()[0]
        self.assertEqual(0, labels)

    def test_matching_current_policy_failure_expects_no_claims(self) -> None:
        artifact_id, job_id, path = self._artifact()
        (path / "starter/main.py").unlink()
        checksum = tree_sha256(path)
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                "UPDATE artifacts SET checksum=? WHERE artifact_id=?",
                (checksum, artifact_id),
            )
        specification = next(
            value
            for value in byox_runtime_safety_validators()
            if value["name"] == BYOX_CODE_PRESENCE_VALIDATOR
        )
        gate = evaluate_byox_code_presence(
            path, specification, name=BYOX_CODE_PRESENCE_VALIDATOR
        )
        self.assertEqual("FAIL", gate.status)
        self._validation(
            job_id,
            evidence=gate.evidence,
            status="FAIL",
            claims=[],
            suffix="matching-fail",
        )

        result = revalidate_archived_byox_artifacts(
            self.database, self.warehouse, artifact_ids=[artifact_id]
        )

        self.assertEqual({"FAIL": 1}, result["effective_outcomes"])
        self.assertEqual(
            "FINAL_POLICY_MATCH",
            result["records"][0]["controller_evidence_category"],
        )

    def test_changed_observation_is_appended_once_and_effectively_conflicting(self) -> None:
        artifact_id, _, path = self._artifact()
        initial = revalidate_archived_byox_artifacts(
            self.database, self.warehouse, artifact_ids=[artifact_id]
        )
        self.assertEqual({"PASS": 1}, initial["effective_outcomes"])
        (path / "README.md").write_text("later mutation\n", encoding="utf-8")

        changed = revalidate_archived_byox_artifacts(
            self.database, self.warehouse, artifact_ids=[artifact_id]
        )
        repeated = revalidate_archived_byox_artifacts(
            self.database, self.warehouse, artifact_ids=[artifact_id]
        )

        self.assertEqual(1, changed["inserted"])
        self.assertEqual({"CONFLICT": 1}, changed["effective_outcomes"])
        self.assertEqual(0, repeated["inserted"])
        self.assertEqual({"CONFLICT": 1}, repeated["effective_outcomes"])
        with self.database.connect() as connection:
            self.assertEqual(
                2,
                connection.execute(
                    "SELECT COUNT(*) FROM byox_code_presence_audits WHERE artifact_id=?",
                    (artifact_id,),
                ).fetchone()[0],
            )

    def test_default_scan_is_bounded_and_advances_past_audited_rows(self) -> None:
        first_id, _, _ = self._artifact()
        second_id, _, _ = self._artifact()

        first = revalidate_archived_byox_artifacts(
            self.database, self.warehouse, max_artifacts=1
        )
        second = revalidate_archived_byox_artifacts(
            self.database, self.warehouse, max_artifacts=1
        )

        self.assertEqual([first_id], [row["artifact_id"] for row in first["records"]])
        self.assertEqual([second_id], [row["artifact_id"] for row in second["records"]])
        self.assertEqual(1, first["remaining_unaudited"])
        self.assertEqual(0, second["remaining_unaudited"])

    def test_invocation_byte_budget_stops_without_misgrading_and_resumes(self) -> None:
        first_id, _, first_path = self._artifact()
        second_id, _, second_path = self._artifact()
        first_bytes = backfill._bounded_tree_checksum(first_path).total_bytes
        second_bytes = backfill._bounded_tree_checksum(second_path).total_bytes
        # A successful replay reads three source hashes, one source copy, and
        # two private-snapshot hashes.  The aggregate limit accounts for all
        # six reads rather than only a completed first pass.
        one_artifact_budget = 6 * max(first_bytes, second_bytes)

        first = revalidate_archived_byox_artifacts(
            self.database,
            self.warehouse,
            max_artifacts=2,
            max_total_bytes=one_artifact_budget,
        )

        self.assertEqual([first_id], [row["artifact_id"] for row in first["records"]])
        self.assertEqual("max_total_bytes", first["stopped_reason"])
        self.assertEqual(second_id, first["stopped_artifact_id"])
        self.assertEqual(1, first["processed"])
        self.assertEqual(
            6 * first_bytes, first["budget"]["consumed_total_bytes"]
        )
        self.assertEqual(1, first["remaining_unaudited"])
        with self.database.connect() as connection:
            self.assertEqual(
                0,
                connection.execute(
                    "SELECT count(*) FROM byox_code_presence_audits WHERE artifact_id=?",
                    (second_id,),
                ).fetchone()[0],
            )

        second = revalidate_archived_byox_artifacts(
            self.database,
            self.warehouse,
            max_artifacts=2,
            max_total_bytes=one_artifact_budget,
        )
        self.assertEqual([second_id], [row["artifact_id"] for row in second["records"]])
        self.assertIsNone(second["stopped_reason"])
        self.assertEqual(0, second["remaining_unaudited"])

    def test_wall_budget_stops_before_observation_without_artifact_failure(self) -> None:
        artifact_id, _, _ = self._artifact()

        with patch(
            "learnfactory.byox_gate_backfill._monotonic",
            side_effect=[0.0, 2.0],
        ):
            result = revalidate_archived_byox_artifacts(
                self.database,
                self.warehouse,
                max_wall_seconds=1.0,
            )

        self.assertEqual([], result["records"])
        self.assertEqual("max_wall_seconds", result["stopped_reason"])
        self.assertEqual(artifact_id, result["stopped_artifact_id"])
        self.assertEqual(0, result["processed"])
        self.assertEqual(1, result["remaining_unaudited"])
        with self.database.connect() as connection:
            self.assertEqual(
                0,
                connection.execute(
                    "SELECT count(*) FROM byox_code_presence_audits"
                ).fetchone()[0],
            )

    def test_wall_budget_expiring_after_observation_never_appends_a_row(self) -> None:
        artifact_id, _, _ = self._artifact()

        with (
            patch(
                "learnfactory.byox_gate_backfill._monotonic",
                side_effect=[0.0, 0.5, 2.0],
            ),
            patch(
                "learnfactory.byox_gate_backfill._observe_artifact",
                return_value={},
            ),
        ):
            result = revalidate_archived_byox_artifacts(
                self.database,
                self.warehouse,
                max_wall_seconds=1.0,
            )

        self.assertEqual([], result["records"])
        self.assertEqual("max_wall_seconds", result["stopped_reason"])
        self.assertEqual(artifact_id, result["stopped_artifact_id"])
        with self.database.connect() as connection:
            self.assertEqual(
                0,
                connection.execute(
                    "SELECT count(*) FROM byox_code_presence_audits"
                ).fetchone()[0],
            )

    def test_wall_budget_expiring_inside_append_rolls_back_and_is_resumable(self) -> None:
        artifact_id, _, _ = self._artifact()
        policy = backfill._current_policy()
        snapshot = backfill._select_artifacts(
            self.database, policy, 1, (artifact_id,)
        )[0]
        observation = backfill._observe_artifact(
            self.database,
            self.warehouse,
            snapshot,
            policy,
            backfill._InvocationBudget(
                max_total_bytes=backfill.MAX_AUDIT_TOTAL_BYTES,
                deadline=float("inf"),
            ),
        )

        with (
            patch(
                "learnfactory.byox_gate_backfill._monotonic",
                side_effect=[0.0, 0.1, 0.2, 2.0],
            ),
            patch(
                "learnfactory.byox_gate_backfill._observe_artifact",
                return_value=observation,
            ),
        ):
            result = revalidate_archived_byox_artifacts(
                self.database,
                self.warehouse,
                max_wall_seconds=1.0,
                artifact_ids=[artifact_id],
            )

        self.assertEqual([], result["records"])
        self.assertEqual("max_wall_seconds", result["stopped_reason"])
        self.assertEqual(artifact_id, result["stopped_artifact_id"])
        self.assertEqual(1, result["remaining_unaudited"])
        with self.database.connect() as connection:
            self.assertEqual(
                0,
                connection.execute(
                    "SELECT count(*) FROM byox_code_presence_audits"
                ).fetchone()[0],
            )

    def test_budget_exhaustion_is_not_masked_by_snapshot_cleanup_failure(self) -> None:
        artifact_id, _, path = self._artifact()
        one_source_pass = backfill._bounded_tree_checksum(path).total_bytes
        real_discard = backfill._discard_private_snapshot

        def discard_then_report_failure(snapshot: Path) -> None:
            real_discard(snapshot)
            raise OSError("injected cleanup report")

        with patch(
            "learnfactory.byox_gate_backfill._discard_private_snapshot",
            side_effect=discard_then_report_failure,
        ):
            result = revalidate_archived_byox_artifacts(
                self.database,
                self.warehouse,
                max_total_bytes=one_source_pass,
                artifact_ids=[artifact_id],
            )

        self.assertEqual([], result["records"])
        self.assertEqual("max_total_bytes", result["stopped_reason"])
        self.assertEqual(artifact_id, result["stopped_artifact_id"])
        self.assertEqual(one_source_pass, result["budget"]["consumed_total_bytes"])
        with self.database.connect() as connection:
            self.assertEqual(
                0,
                connection.execute(
                    "SELECT count(*) FROM byox_code_presence_audits"
                ).fetchone()[0],
            )

    def test_empty_explicit_artifact_selection_never_defaults_to_all(self) -> None:
        self._artifact()

        result = revalidate_archived_byox_artifacts(
            self.database, self.warehouse, artifact_ids=[]
        )

        self.assertEqual(0, result["selected"])
        self.assertEqual(0, result["processed"])
        self.assertEqual([], result["records"])
        self.assertEqual(1, result["remaining_unaudited"])
        with self.database.connect() as connection:
            self.assertEqual(
                0,
                connection.execute(
                    "SELECT count(*) FROM byox_code_presence_audits"
                ).fetchone()[0],
            )

    def test_failed_trees_charge_bytes_read_before_late_unsafe_entry(self) -> None:
        artifacts: list[tuple[str, Path]] = []
        external = self.root / "late-unsafe-target"
        external.write_text("outside\n", encoding="utf-8")
        for _ in range(3):
            artifact_id, _, path = self._artifact(marker="same")
            (path / "starter/zz-unsafe").symlink_to(external)
            with self.database.transaction(immediate=True) as connection:
                connection.execute(
                    "UPDATE artifacts SET checksum=? WHERE artifact_id=?",
                    (tree_sha256(path), artifact_id),
                )
            artifacts.append((artifact_id, path))
        one_failed_tree_bytes = sum(
            candidate.stat().st_size
            for candidate in artifacts[0][1].rglob("*")
            if candidate.is_file() and not candidate.is_symlink()
        )

        result = revalidate_archived_byox_artifacts(
            self.database,
            self.warehouse,
            max_artifacts=3,
            max_total_bytes=one_failed_tree_bytes,
        )

        self.assertEqual(1, result["processed"])
        self.assertEqual({"FAIL": 1}, result["effective_outcomes"])
        self.assertEqual("max_total_bytes", result["stopped_reason"])
        self.assertEqual(artifacts[1][0], result["stopped_artifact_id"])
        self.assertEqual(
            one_failed_tree_bytes, result["budget"]["consumed_total_bytes"]
        )
        with self.database.connect() as connection:
            self.assertEqual(
                1,
                connection.execute(
                    "SELECT count(*) FROM byox_code_presence_audits"
                ).fetchone()[0],
            )

    def test_incoherent_direct_sql_audit_cannot_make_default_scan_skip_work(self) -> None:
        artifact_id, job_id, _ = self._artifact()
        specification = next(
            value
            for value in byox_runtime_safety_validators()
            if value["name"] == BYOX_CODE_PRESENCE_VALIDATOR
        )
        specification_json = canonical_json(specification)
        with self.database.transaction(immediate=True) as connection:
            artifact = connection.execute(
                "SELECT * FROM artifacts WHERE artifact_id=?", (artifact_id,)
            ).fetchone()
            job = connection.execute(
                "SELECT * FROM jobs WHERE job_id=?", (job_id,)
            ).fetchone()
            connection.execute(
                """
                INSERT INTO byox_code_presence_audits(
                    audit_id,artifact_id,job_id,artifact_attempt,artifact_type,
                    artifact_path,artifact_checksum,checksum_algorithm,integrity_status,
                    job_state,job_attempt_count,job_payload_sha256,
                    policy_name,policy_digest,policy_spec_sha256,policy_spec_json,
                    observation_sha256,outcome,gate_status,scope,semantic_claims_json,
                    observed_checksum,controller_evidence_sha256,evidence_sha256,
                    evidence_json,created_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    "fabricated_audit",
                    artifact_id,
                    job_id,
                    artifact["attempt_number"],
                    artifact["type"],
                    artifact["path"],
                    artifact["checksum"],
                    artifact["checksum_algorithm"],
                    artifact["integrity_status"],
                    job["state"],
                    job["attempt_count"],
                    "0" * 64,
                    BYOX_CODE_PRESENCE_VALIDATOR,
                    byox_code_policy_digest(),
                    hashlib.sha256(specification_json.encode()).hexdigest(),
                    specification_json,
                    "1" * 64,
                    "PASS",
                    "PASS",
                    BYOX_CODE_AUDIT_SCOPE,
                    "[]",
                    artifact["checksum"],
                    "2" * 64,
                    "3" * 64,
                    "{}",
                    3.0,
                ),
            )

        with self.assertRaisesRegex(ByoxGateBackfillError, "payload binding"):
            revalidate_archived_byox_artifacts(self.database, self.warehouse)

    def test_explicit_selection_chunks_one_thousand_ids_for_sqlite_326(self) -> None:
        identifiers: list[str] = []
        payload = canonical_json(
            {
                "seed_policy": {
                    "kind": "byox_reference_build",
                    "version": 1,
                    "role": "builder",
                },
                "project_id": "bulk",
                "artifact_type": "byox-challenge-pack",
            }
        )
        with self.database.transaction(immediate=True) as connection:
            for index in range(1000):
                job_id = f"job_bulk_{index:04d}"
                artifact_id = f"artifact_bulk_{index:04d}"
                identifiers.append(artifact_id)
                connection.execute(
                    """
                    INSERT INTO jobs(
                        job_id,type,worker_type,state,priority,payload_json,
                        attempt_count,max_attempts,created_at,finished_at
                    ) VALUES (?, 'codex_task','reference_builder','SUCCEEDED',1,?,1,1,1,2)
                    """,
                    (job_id, payload),
                )
                connection.execute(
                    """
                    INSERT INTO artifacts(
                        artifact_id,job_id,type,path,checksum,metadata_json,created_at,
                        validation_status,attempt_number,checksum_algorithm,integrity_status
                    ) VALUES (?,?,'byox-challenge-pack',?,?,'{}',1,'GENERATED+PARTIAL',1,
                              'tree-sha256-v2','VERIFIED_V2')
                    """,
                    (
                        artifact_id,
                        job_id,
                        str(self.warehouse / "artifacts" / artifact_id),
                        f"{index:064x}"[-64:],
                    ),
                )
        policy = backfill._current_policy()

        selected = backfill._select_artifacts(
            self.database, policy, 1000, tuple(identifiers)
        )

        self.assertEqual(1000, len(selected))

    def test_regular_file_open_uses_nonblocking_no_follow_flags(self) -> None:
        path = self.root / "ordinary.py"
        path.write_text("value = 1\n", encoding="utf-8")
        actual_open = os.open
        seen_flags: list[int] = []

        def record_flags(*args: object, **kwargs: object) -> int:
            seen_flags.append(int(args[1]))
            return actual_open(*args, **kwargs)

        parent_descriptor = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY)
        try:
            with patch(
                "learnfactory.byox_gate_backfill.os.open", side_effect=record_flags
            ):
                backfill._hash_regular_file_at(
                    parent_descriptor,
                    path.name,
                    path.stat(),
                    "ordinary.py",
                )
        finally:
            os.close(parent_descriptor)

        self.assertTrue(seen_flags)
        if hasattr(os, "O_NONBLOCK"):
            self.assertTrue(seen_flags[0] & os.O_NONBLOCK)
        if hasattr(os, "O_NOFOLLOW"):
            self.assertTrue(seen_flags[0] & os.O_NOFOLLOW)

    def test_cli_defaults_and_bounds_are_explicit(self) -> None:
        parsed = build_parser().parse_args(["revalidate-byox-code"])
        self.assertEqual(100, parsed.max_artifacts)
        self.assertIsNone(parsed.artifact_id)
        with self.assertRaisesRegex(ByoxGateBackfillError, "1 through 1000"):
            revalidate_archived_byox_artifacts(
                self.database, self.warehouse, max_artifacts=1001
            )
        with self.assertRaisesRegex(ByoxGateBackfillError, "max_total_bytes"):
            revalidate_archived_byox_artifacts(
                self.database, self.warehouse, max_total_bytes=0
            )
        with self.assertRaisesRegex(ByoxGateBackfillError, "max_wall_seconds"):
            revalidate_archived_byox_artifacts(
                self.database, self.warehouse, max_wall_seconds=float("inf")
            )

    def test_cli_executes_bounded_audit_and_prints_non_promoting_scope(self) -> None:
        artifact_id, _, _ = self._artifact()
        config = self.root / "factory.toml"
        config.write_text(
            "\n".join(
                (
                    "[factory]",
                    f'database = "{self.database.path}"',
                    f'warehouse = "{self.warehouse}"',
                    "[backend]",
                    'model = "gpt-5.6-sol"',
                    'reasoning_effort = "ultra"',
                )
            )
            + "\n",
            encoding="utf-8",
        )
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            exit_code = main(
                [
                    "--config",
                    str(config),
                    "revalidate-byox-code",
                    "--max-artifacts",
                    "1",
                    "--artifact-id",
                    artifact_id,
                ]
            )

        self.assertEqual(0, exit_code, stderr.getvalue())
        output = json.loads(stdout.getvalue())
        self.assertEqual(BYOX_CODE_AUDIT_SCOPE, output["scope"])
        self.assertEqual([], output["semantic_claims_added"])
        self.assertFalse(output["builds_or_tested_claimed"])

if __name__ == "__main__":
    unittest.main()
