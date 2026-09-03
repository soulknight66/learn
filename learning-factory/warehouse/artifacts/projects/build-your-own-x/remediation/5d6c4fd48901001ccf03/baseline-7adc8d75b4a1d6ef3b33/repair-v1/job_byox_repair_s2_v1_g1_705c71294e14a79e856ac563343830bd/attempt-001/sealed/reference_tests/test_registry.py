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

    def test_database_trigger_rejects_bypass(self):
        self.registry.create(spec(), T0)
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


if __name__ == "__main__":
    unittest.main()
