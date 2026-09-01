import tempfile
import unittest
from pathlib import Path

from minibox.errors import StateError
from minibox.state import StateStore


class StateStorePublicTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.state_directory = Path(self.temporary_directory.name) / "states"
        self.now = [1000.0]
        self.store = StateStore(self.state_directory, clock=lambda: self.now[0])

    def test_create_and_transition_through_successful_lifecycle(self):
        created = self.store.create("box-1")
        self.assertEqual(created.container_id, "box-1")
        self.assertEqual(created.status, "CREATED")
        self.assertEqual(created.revision, 0)
        self.assertEqual(created.created_at, 1000.0)
        self.assertEqual(created.updated_at, 1000.0)
        self.assertIsNone(created.exit_code)
        self.assertIsNone(created.error)

        self.now[0] = 1001.0
        running = self.store.transition("box-1", "CREATED", "RUNNING")
        self.assertEqual(running.status, "RUNNING")
        self.assertEqual(running.revision, 1)
        self.assertEqual(running.created_at, 1000.0)
        self.assertEqual(running.updated_at, 1001.0)

        self.now[0] = 1002.0
        exited = self.store.transition(
            "box-1", "RUNNING", "EXITED", exit_code=7
        )
        self.assertEqual(exited.status, "EXITED")
        self.assertEqual(exited.revision, 2)
        self.assertEqual(exited.exit_code, 7)
        self.assertIsNone(exited.error)
        self.assertEqual(exited.updated_at, 1002.0)

    def test_get_reads_durable_state_from_a_new_store(self):
        expected = self.store.create("durable")

        reopened = StateStore(self.state_directory, clock=lambda: 9999.0)
        actual = reopened.get("durable")

        self.assertEqual(actual, expected)

    def test_duplicate_ids_and_stale_expected_status_are_rejected(self):
        self.store.create("box")
        with self.assertRaises(StateError):
            self.store.create("box")

        with self.assertRaises(StateError):
            self.store.transition("box", "RUNNING", "EXITED", exit_code=0)
        self.assertEqual(self.store.get("box").status, "CREATED")
        self.assertEqual(self.store.get("box").revision, 0)

    def test_unsafe_container_ids_are_rejected(self):
        for container_id in ("", "../escape", "/absolute", "has space", "UPPER"):
            with self.subTest(container_id=container_id):
                with self.assertRaises(StateError):
                    self.store.create(container_id)


if __name__ == "__main__":
    unittest.main()
