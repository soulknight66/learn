from __future__ import annotations

import sqlite3
from pathlib import Path
import tempfile
import unittest

from minibox.errors import ContainerExists, InvalidTransition, StateConflict
from minibox.models import ContainerSpec, ContainerState
from minibox.state import StateStore


class StateStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.database = Path(self.temporary.name) / "state.sqlite3"
        ticks = iter(range(100, 1000))
        self.store = StateStore(self.database, clock_ns=lambda: next(ticks))
        self.spec = ContainerSpec("demo", "base", ("/bin/true",))

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_create_transition_and_history(self) -> None:
        created = self.store.create(self.spec)
        running = self.store.transition("demo", ContainerState.CREATED, ContainerState.RUNNING)
        exited = self.store.transition("demo", ContainerState.RUNNING, ContainerState.EXITED, exit_code=7)

        self.assertEqual(created.state, ContainerState.CREATED)
        self.assertGreater(running.updated_ns, created.updated_ns)
        self.assertEqual(exited.exit_code, 7)
        events = self.store.events("demo")
        self.assertEqual([event.to_state for event in events], [
            ContainerState.CREATED,
            ContainerState.RUNNING,
            ContainerState.EXITED,
        ])
        self.assertIsNone(events[0].from_state)

    def test_duplicate_stale_and_invalid_operations_do_not_append(self) -> None:
        self.store.create(self.spec)
        with self.assertRaises(ContainerExists):
            self.store.create(self.spec)
        with self.assertRaises(StateConflict):
            self.store.transition("demo", ContainerState.EXITED, ContainerState.RUNNING)
        with self.assertRaises(InvalidTransition):
            self.store.transition("demo", ContainerState.CREATED, ContainerState.EXITED, exit_code=0)
        self.assertEqual(len(self.store.events("demo")), 1)

    def test_database_trigger_rejects_bypassed_transition(self) -> None:
        self.store.create(self.spec)
        connection = sqlite3.connect(self.database)
        try:
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "UPDATE containers SET state = ?, exit_code = ?, updated_ns = ? WHERE container_id = ?",
                    ("EXITED", 0, 999, "demo"),
                )
        finally:
            connection.close()
        self.assertEqual(self.store.get("demo").state, ContainerState.CREATED)


if __name__ == "__main__":
    unittest.main()
