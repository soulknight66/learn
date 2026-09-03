import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from minictr.errors import TransitionError, ValidationError
from minictr.registry import Registry
from minictr.spec import ContainerSpec

T0 = "2026-01-02T03:04:05Z"
T1 = "2026-01-02T03:04:06+00:00"
T2 = "2026-01-02T03:04:07Z"
NON_RFC3339 = (
    "2026-W01-1T03:04:05+00:00",
    "20260102T030405+00:00",
    "2026-01-02Q03:04:05+00:00",
)


def spec(root="/tmp/root", container_id="dbbox"):
    return ContainerSpec.from_mapping({"id": container_id, "rootfs": root, "command": ["/bin/true"]})


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.path = Path(self.temporary.name) / "state.sqlite3"
        self.registry = Registry(self.path)

    def tearDown(self):
        self.registry.close()
        self.temporary.cleanup()

    def test_success_lifecycle_and_canonical_spec(self):
        created = self.registry.create(spec(), T0)
        self.assertEqual(created.state, "CREATED")
        self.assertEqual(json.loads(created.spec_json)["id"], "dbbox")
        running = self.registry.claim_start("dbbox", 123, T1)
        self.assertEqual((running.state, running.pid), ("RUNNING", 123))
        exited = self.registry.finish("dbbox", 0, "/tmp/dbbox.log", T2)
        self.assertEqual((exited.state, exited.exit_code), ("EXITED", 0))

    def test_failure_is_durable_after_reopen(self):
        self.registry.create(spec(), T0)
        self.registry.claim_start("dbbox", 321, T1)
        self.registry.finish("dbbox", 17, "/tmp/failure.log", T2)
        self.registry.close()
        self.registry = Registry(self.path)
        record = self.registry.get("dbbox")
        self.assertEqual((record.state, record.exit_code, record.log_path), ("FAILED", 17, "/tmp/failure.log"))

    def test_only_one_connection_can_claim(self):
        self.registry.create(spec(), T0)
        contender = Registry(self.path)
        try:
            first = self.registry.claim_start("dbbox", 100, T1)
            self.assertEqual(first.pid, 100)
            with self.assertRaises(TransitionError):
                contender.claim_start("dbbox", 200, T2)
            self.assertEqual(contender.get("dbbox").pid, 100)
        finally:
            contender.close()

    def test_duplicate_and_invalid_method_transitions_fail(self):
        self.registry.create(spec(), T0)
        with self.assertRaises(TransitionError):
            self.registry.create(spec(), T1)
        with self.assertRaises(TransitionError):
            self.registry.finish("dbbox", 0, "/tmp/log", T2)

    def test_database_trigger_rejects_policy_tampering_and_bypass(self):
        self.registry.create(spec(), T0)
        with self.assertRaises(sqlite3.OperationalError):
            self.registry.connection.execute(
                "INSERT INTO allowed_transitions(old_state, new_state) VALUES (?, ?)",
                ("CREATED", "EXITED"),
            )
        with self.assertRaises(sqlite3.IntegrityError):
            self.registry.connection.execute(
                "UPDATE containers SET state = ? WHERE id = ?", ("EXITED", "dbbox")
            )
        self.assertEqual(self.registry.get("dbbox").state, "CREATED")

    def test_numbered_migration_replaces_legacy_mutable_policy(self):
        self.registry.create(spec(), T0)
        self.registry.close()
        legacy = sqlite3.connect(self.path)
        try:
            legacy.execute("PRAGMA user_version = 0")
            legacy.execute("DROP TRIGGER enforce_container_transition")
            legacy.execute(
                "CREATE TABLE allowed_transitions ("
                "old_state TEXT NOT NULL, new_state TEXT NOT NULL, "
                "PRIMARY KEY (old_state, new_state))"
            )
            legacy.executemany(
                "INSERT INTO allowed_transitions(old_state, new_state) VALUES (?, ?)",
                [
                    ("CREATED", "RUNNING"),
                    ("RUNNING", "EXITED"),
                    ("RUNNING", "FAILED"),
                    ("CREATED", "EXITED"),
                ],
            )
            legacy.execute(
                "CREATE TRIGGER enforce_container_transition "
                "BEFORE UPDATE OF state ON containers WHEN OLD.state <> NEW.state BEGIN "
                "SELECT CASE WHEN NOT EXISTS (SELECT 1 FROM allowed_transitions "
                "WHERE old_state = OLD.state AND new_state = NEW.state) "
                "THEN RAISE(ABORT, 'invalid container state transition') END; END"
            )
            legacy.commit()
        finally:
            legacy.close()

        self.registry = Registry(self.path)
        version = self.registry.connection.execute("PRAGMA user_version").fetchone()[0]
        policy_table = self.registry.connection.execute(
            "SELECT name FROM sqlite_master WHERE type = ? AND name = ?",
            ("table", "allowed_transitions"),
        ).fetchone()
        self.assertEqual(version, 1)
        self.assertIsNone(policy_table)
        with self.assertRaises(sqlite3.IntegrityError):
            self.registry.connection.execute(
                "UPDATE containers SET state = ? WHERE id = ?", ("EXITED", "dbbox")
            )
        self.assertEqual(self.registry.get("dbbox").state, "CREATED")

    def test_validates_pid_exit_code_and_timestamp(self):
        self.registry.create(spec(), T0)
        for pid in (True, 0, -1, "12"):
            with self.subTest(pid=pid), self.assertRaises(ValidationError):
                self.registry.claim_start("dbbox", pid, T1)
        with self.assertRaises(ValidationError):
            self.registry.claim_start("dbbox", 12, "2026-01-02 03:04:05")

    def test_rejects_non_rfc3339_forms_at_every_timestamp_boundary(self):
        for index, timestamp in enumerate(NON_RFC3339):
            with self.subTest(operation="create", timestamp=timestamp), self.assertRaises(ValidationError):
                self.registry.create(spec(container_id=f"create{index}"), timestamp)

        self.registry.create(spec(), T0)
        for timestamp in NON_RFC3339:
            with self.subTest(operation="claim_start", timestamp=timestamp), self.assertRaises(ValidationError):
                self.registry.claim_start("dbbox", 123, timestamp)
        self.assertEqual(self.registry.get("dbbox").state, "CREATED")

        self.registry.claim_start("dbbox", 123, T1)
        for timestamp in NON_RFC3339:
            with self.subTest(operation="finish", timestamp=timestamp), self.assertRaises(ValidationError):
                self.registry.finish("dbbox", 0, "/tmp/dbbox.log", timestamp)
        self.assertEqual(self.registry.get("dbbox").state, "RUNNING")

    def test_accepts_rfc3339_fraction_and_numeric_offset(self):
        timestamp = "2026-01-02T03:04:05.123456+05:30"
        created = self.registry.create(spec(), timestamp)
        self.assertEqual(created.created_at, timestamp)

    def test_rejects_leap_second_spellings_by_declared_policy(self):
        timestamps = (
            "2026-01-02T03:04:60Z",
            "2016-12-31T23:59:60Z",
            "2017-01-01T00:59:60+01:00",
        )
        for index, timestamp in enumerate(timestamps):
            with self.subTest(timestamp=timestamp), self.assertRaises(ValidationError):
                self.registry.create(spec(container_id=f"leap{index}"), timestamp)


if __name__ == "__main__":
    unittest.main()
