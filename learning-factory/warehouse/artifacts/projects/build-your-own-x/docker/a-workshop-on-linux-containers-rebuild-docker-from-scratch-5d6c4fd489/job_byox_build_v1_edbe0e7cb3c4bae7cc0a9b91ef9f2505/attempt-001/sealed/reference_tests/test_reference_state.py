import json
import os
import concurrent.futures
import tempfile
import threading
import unittest
from dataclasses import FrozenInstanceError, is_dataclass
from pathlib import Path
from unittest import mock

from minibox.errors import StateError
from minibox.state import ContainerState, StateStore


class StateStoreReferenceTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.base = Path(self.temporary_directory.name)
        self.state_directory = self.base / "states"
        self.now = [10.0]
        self.store = StateStore(self.state_directory, clock=lambda: self.now[0])

    def advance(self, value):
        self.now[0] = value

    def move_to(self, container_id, status):
        self.store.create(container_id)
        if status == "CREATED":
            return
        self.store.transition(container_id, "CREATED", "RUNNING")
        if status == "RUNNING":
            return
        if status == "EXITED":
            self.store.transition(
                container_id, "RUNNING", "EXITED", exit_code=0
            )
            return
        if status == "FAILED":
            self.store.transition(
                container_id, "RUNNING", "FAILED", error="fixture failure"
            )
            return
        raise AssertionError("unsupported fixture status")

    def test_create_returns_a_frozen_container_state_dataclass(self):
        state = self.store.create("box")

        self.assertTrue(is_dataclass(state))
        self.assertIsInstance(state, ContainerState)
        self.assertEqual(state.container_id, "box")
        self.assertEqual(state.status, "CREATED")
        self.assertEqual(state.revision, 0)
        self.assertEqual(state.created_at, 10.0)
        self.assertEqual(state.updated_at, 10.0)
        self.assertIsNone(state.exit_code)
        self.assertIsNone(state.error)
        with self.assertRaises(FrozenInstanceError):
            state.status = "RUNNING"

    def test_container_id_boundary_and_punctuation(self):
        accepted = ("a", "a.b_c-9", "0", "a" + "b" * 63)
        for container_id in accepted:
            with self.subTest(accepted=container_id):
                self.assertEqual(
                    self.store.create(container_id).container_id, container_id
                )

        rejected = (
            "",
            "A",
            "Upper",
            "_box",
            ".box",
            "-box",
            "a/b",
            "a\\b",
            "a b",
            "a\n",
            "é",
            "a" * 65,
            None,
            1,
            b"box",
        )
        for container_id in rejected:
            with self.subTest(rejected=container_id):
                with self.assertRaises(StateError):
                    self.store.create(container_id)

    def test_duplicate_create_is_rejected_across_store_instances(self):
        expected = self.store.create("same")
        second = StateStore(self.state_directory, clock=lambda: 999.0)

        with self.assertRaises(StateError):
            second.create("same")
        self.assertEqual(second.get("same"), expected)

    def test_running_to_failed_records_error_and_revision(self):
        created = self.store.create("failed")
        self.advance(11.0)
        running = self.store.transition("failed", "CREATED", "RUNNING")
        self.advance(12.0)
        failed = self.store.transition(
            "failed", "RUNNING", "FAILED", error="validator error"
        )

        self.assertEqual(created.revision, 0)
        self.assertEqual(running.revision, 1)
        self.assertEqual(failed.revision, 2)
        self.assertEqual(failed.status, "FAILED")
        self.assertEqual(failed.error, "validator error")
        self.assertIsNone(failed.exit_code)
        self.assertEqual(failed.created_at, 10.0)
        self.assertEqual(failed.updated_at, 12.0)

    def test_only_created_to_running_and_running_to_terminal_are_legal(self):
        illegal_pairs = (
            ("CREATED", "CREATED"),
            ("CREATED", "EXITED"),
            ("CREATED", "FAILED"),
            ("RUNNING", "CREATED"),
            ("RUNNING", "RUNNING"),
            ("EXITED", "CREATED"),
            ("EXITED", "RUNNING"),
            ("EXITED", "EXITED"),
            ("EXITED", "FAILED"),
            ("FAILED", "CREATED"),
            ("FAILED", "RUNNING"),
            ("FAILED", "EXITED"),
            ("FAILED", "FAILED"),
        )
        for index, (source, target) in enumerate(illegal_pairs):
            container_id = "illegal-{}".format(index)
            self.move_to(container_id, source)
            before = self.store.get(container_id)
            kwargs = {}
            if target == "EXITED":
                kwargs["exit_code"] = 1
            if target == "FAILED":
                kwargs["error"] = "failure"
            with self.subTest(source=source, target=target):
                with self.assertRaises(StateError):
                    self.store.transition(
                        container_id, source, target, **kwargs
                    )
                self.assertEqual(self.store.get(container_id), before)

    def test_unknown_statuses_and_missing_containers_are_state_errors(self):
        self.store.create("known")
        with self.assertRaises(StateError):
            self.store.transition("known", "CREATED", "PAUSED")
        with self.assertRaises(StateError):
            self.store.transition("known", "PAUSED", "RUNNING")
        with self.assertRaises(StateError):
            self.store.get("missing")
        with self.assertRaises(StateError):
            self.store.transition("missing", "CREATED", "RUNNING")

    def test_stale_expected_status_cannot_overwrite_terminal_state(self):
        self.move_to("race", "RUNNING")
        first = StateStore(self.state_directory, clock=lambda: 20.0)
        second = StateStore(self.state_directory, clock=lambda: 21.0)

        exited = first.transition("race", "RUNNING", "EXITED", exit_code=4)
        with self.assertRaises(StateError):
            second.transition("race", "RUNNING", "FAILED", error="late")

        self.assertEqual(second.get("race"), exited)
        self.assertEqual(second.get("race").status, "EXITED")
        self.assertEqual(second.get("race").exit_code, 4)

    def test_corrupt_truncated_and_wrong_shape_json_are_not_overwritten(self):
        bad_records = (
            ("invalid-utf8", b"\xff\xfe"),
            ("truncated", b'{"container_id":"truncated"'),
            (
                "wrong-shape",
                (json.dumps({"container_id": "wrong-shape"}) + "\n").encode(
                    "utf-8"
                ),
            ),
            (
                "duplicate-state",
                b'{"container_id":"duplicate-state",'
                b'"container_id":"duplicate-state","status":"CREATED",'
                b'"revision":0,"created_at":10.0,"updated_at":10.0,'
                b'"exit_code":null,"error":null}',
            ),
            (
                "wrong-revision",
                (
                    json.dumps(
                        {
                            "container_id": "wrong-revision",
                            "status": "CREATED",
                            "revision": 9,
                            "created_at": 10.0,
                            "updated_at": 10.0,
                            "exit_code": None,
                            "error": None,
                        }
                    )
                    + "\n"
                ).encode("utf-8"),
            ),
        )
        for container_id, bad_bytes in bad_records:
            with self.subTest(container_id=container_id):
                self.store.create(container_id)
                record_path = self.state_directory / (container_id + ".json")
                record_path.write_bytes(bad_bytes)

                with self.assertRaises(StateError):
                    self.store.get(container_id)
                self.assertEqual(record_path.read_bytes(), bad_bytes)

                with self.assertRaises(StateError):
                    self.store.transition(container_id, "CREATED", "RUNNING")
                self.assertEqual(record_path.read_bytes(), bad_bytes)

    def test_symbolic_link_state_record_is_rejected_without_touching_target(self):
        self.store.create("linked-state")
        record_path = self.state_directory / "linked-state.json"
        target_path = self.base / "outside-state.json"
        target_bytes = record_path.read_bytes()
        target_path.write_bytes(target_bytes)
        record_path.unlink()
        try:
            os.symlink(target_path, record_path)
        except (NotImplementedError, OSError) as exc:
            self.skipTest("symlinks are unavailable: {}".format(exc))

        with self.assertRaises(StateError):
            self.store.get("linked-state")
        with self.assertRaises(StateError):
            self.store.transition("linked-state", "CREATED", "RUNNING")
        self.assertEqual(target_path.read_bytes(), target_bytes)
        self.assertTrue(record_path.is_symlink())

    def test_path_traversal_id_does_not_escape_state_directory(self):
        escaped = self.base / "escaped"

        with self.assertRaises(StateError):
            self.store.create("../escaped")

        self.assertFalse(escaped.exists())

    def test_failed_initial_write_never_publishes_partial_record(self):
        with mock.patch(
            "minibox.state.os.write", side_effect=OSError("injected write failure")
        ):
            with self.assertRaises(StateError):
                self.store.create("fragile")

        self.assertFalse((self.state_directory / "fragile.json").exists())
        self.assertEqual(
            list(self.state_directory.glob(".fragile.create.*.tmp")), []
        )
        self.assertEqual(self.store.create("fragile").status, "CREATED")

    def test_two_same_expectation_transitions_have_one_winner(self):
        self.move_to("contended", "RUNNING")
        first = StateStore(self.state_directory, clock=lambda: 20.0)
        second = StateStore(self.state_directory, clock=lambda: 21.0)
        barrier = threading.Barrier(3)

        def finish(store, target):
            barrier.wait()
            try:
                if target == "EXITED":
                    return store.transition(
                        "contended", "RUNNING", target, exit_code=9
                    )
                return store.transition(
                    "contended", "RUNNING", target, error="concurrent failure"
                )
            except StateError as exc:
                return exc

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(finish, first, "EXITED"),
                executor.submit(finish, second, "FAILED"),
            ]
            barrier.wait()
            outcomes = [future.result(timeout=5) for future in futures]

        states = [value for value in outcomes if isinstance(value, ContainerState)]
        errors = [value for value in outcomes if isinstance(value, StateError)]
        self.assertEqual(len(states), 1)
        self.assertEqual(len(errors), 1)
        self.assertEqual(self.store.get("contended"), states[0])


if __name__ == "__main__":
    unittest.main()
