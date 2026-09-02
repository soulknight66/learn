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


if __name__ == "__main__":
    unittest.main()
