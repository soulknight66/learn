from __future__ import annotations

from pathlib import Path
import tempfile
import threading
import unittest

from minibox.errors import ContainerNotFound, InvalidTransition, StateConflict
from minibox.models import ContainerSpec, ContainerState
from minibox.state import StateStore


class ReferenceStateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.database = Path(self.temporary.name) / "state.sqlite3"
        self.store = StateStore(self.database, clock_ns=lambda: 5)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def create(self, container_id: str = "one") -> None:
        self.store.create(ContainerSpec(container_id, "base", ("/bin/true",)))

    def test_unknown_ids_are_distinct_errors(self) -> None:
        with self.assertRaises(ContainerNotFound):
            self.store.get("missing")
        with self.assertRaises(ContainerNotFound):
            self.store.events("missing")
        with self.assertRaises(ContainerNotFound):
            self.store.transition("missing", ContainerState.CREATED, ContainerState.RUNNING)

    def test_exit_code_contract_and_monotonic_timestamp(self) -> None:
        self.create()
        initial = self.store.get("one")
        running = self.store.transition("one", ContainerState.CREATED, ContainerState.RUNNING)
        with self.assertRaises(InvalidTransition):
            self.store.transition("one", ContainerState.RUNNING, ContainerState.EXITED)
        with self.assertRaises(InvalidTransition):
            self.store.transition(
                "one", ContainerState.RUNNING, ContainerState.FAILED, exit_code=2
            )
        exited = self.store.transition(
            "one", ContainerState.RUNNING, ContainerState.EXITED, exit_code=-9
        )
        self.assertLess(initial.updated_ns, running.updated_ns)
        self.assertLess(running.updated_ns, exited.updated_ns)
        self.assertEqual(len(self.store.events("one")), 3)

    def test_two_claimants_produce_one_winner(self) -> None:
        self.create()
        barrier = threading.Barrier(3)
        outcomes: list[str] = []
        outcome_lock = threading.Lock()

        def claim() -> None:
            barrier.wait()
            try:
                self.store.transition("one", ContainerState.CREATED, ContainerState.RUNNING)
                value = "won"
            except StateConflict:
                value = "stale"
            with outcome_lock:
                outcomes.append(value)

        threads = [threading.Thread(target=claim) for _ in range(2)]
        for thread in threads:
            thread.start()
        barrier.wait()
        for thread in threads:
            thread.join(timeout=5)
        self.assertTrue(all(not thread.is_alive() for thread in threads))
        self.assertCountEqual(outcomes, ["won", "stale"])
        self.assertEqual(self.store.get("one").state, ContainerState.RUNNING)
        self.assertEqual(len(self.store.events("one")), 2)

    def test_deleted_is_terminal(self) -> None:
        self.create()
        self.store.transition("one", ContainerState.CREATED, ContainerState.DELETED)
        with self.assertRaises(InvalidTransition):
            self.store.transition("one", ContainerState.DELETED, ContainerState.RUNNING)


if __name__ == "__main__":
    unittest.main()
