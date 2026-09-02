from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from pydocklet import (
    Conflict,
    ContainerState,
    Docklet,
    ExecutionResult,
    InvalidLayer,
    InvalidName,
    InvalidTransition,
    PathEscape,
    StateStore,
)

from sealed.reference_tests.helpers import write_regular_layer


class PrivateImageTests(unittest.TestCase):
    def test_layer_order_participates_in_digest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            first = write_regular_layer(work / "first.tar", [("value", b"first", 0o644)])
            second = write_regular_layer(work / "second.tar", [("value", b"second", 0o644)])
            engine = Docklet(work / "runtime")
            forward = engine.import_image("forward", [first, second])
            reverse = engine.import_image("reverse", [second, first])
            self.assertNotEqual(forward.digest, reverse.digest)
            self.assertEqual((forward.rootfs / "value").read_bytes(), b"second")
            self.assertEqual((reverse.rootfs / "value").read_bytes(), b"first")

    def test_identical_content_can_have_two_tags(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            layer = write_regular_layer(work / "layer.tar", [("value", b"same", 0o644)])
            engine = Docklet(work / "runtime")
            one = engine.import_image("one", [layer])
            two = engine.import_image("two", [layer])
            self.assertEqual(one.digest, two.digest)
            self.assertEqual(one.rootfs, two.rootfs)

    def test_tag_rebind_is_rejected_before_second_publish(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            one = write_regular_layer(work / "one.tar", [("value", b"one", 0o644)])
            two = write_regular_layer(work / "two.tar", [("value", b"two", 0o644)])
            engine = Docklet(work / "runtime")
            engine.import_image("fixed", [one])
            with self.assertRaises(Conflict):
                engine.import_image("fixed", [two])
            image_dirs = [path for path in (work / "runtime" / "images").iterdir() if path.is_dir()]
            self.assertEqual(len(image_dirs), 1)

    def test_invalid_name_and_invalid_layer_leave_no_build_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            valid = write_regular_layer(work / "valid.tar", [("value", b"ok", 0o644)])
            engine = Docklet(work / "runtime")
            with self.assertRaises(InvalidName):
                engine.import_image("Uppercase", [valid])

            bad = write_regular_layer(work / "bad.tar", [("../../outside", b"no", 0o644)])
            with self.assertRaises((InvalidLayer, PathEscape)):
                engine.import_image("bad", [bad])
            leftovers = [path.name for path in (work / "runtime" / "images").iterdir()]
            self.assertEqual(leftovers, [])


class PrivateStateTests(unittest.TestCase):
    _IMAGE_DIGEST = "sha256:" + "1" * 64
    _LAYER_DIGEST = "sha256:" + "2" * 64

    def _store_with_image(self, root: Path) -> StateStore:
        store = StateStore(root)
        rootfs = root / "images" / ("1" * 64) / "rootfs"
        rootfs.mkdir(parents=True)
        store.register_image("demo", self._IMAGE_DIGEST, rootfs, [self._LAYER_DIGEST])
        return store

    def _container(self, store: StateStore, suffix: str = "one"):
        rootfs = store.root / "containers" / suffix / "rootfs"
        rootfs.mkdir(parents=True)
        return store.create_container(self._IMAGE_DIGEST, ["tool", "arg"], {"B": "2", "A": "1"}, rootfs)

    def test_database_trigger_rejects_illegal_transition(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = self._store_with_image(Path(temporary))
            record = self._container(store)
            connection = sqlite3.connect(store.db_path)
            try:
                with self.assertRaises(sqlite3.IntegrityError):
                    connection.execute(
                        "UPDATE containers SET state = 'EXITED' WHERE container_id = ?",
                        (record.container_id,),
                    )
            finally:
                connection.rollback()
                connection.close()
            self.assertEqual(store.get_container(record.container_id).state, ContainerState.CREATED)

    def test_two_racing_claims_have_exactly_one_winner(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = self._store_with_image(Path(temporary))
            record = self._container(store)

            def claim() -> str:
                try:
                    store.claim_start(record.container_id)
                    return "won"
                except InvalidTransition:
                    return "lost"

            with ThreadPoolExecutor(max_workers=2) as pool:
                outcomes = list(pool.map(lambda _: claim(), range(2)))
            self.assertCountEqual(outcomes, ["won", "lost"])
            running = store.get_container(record.container_id)
            self.assertEqual(running.state, ContainerState.RUNNING)
            store.finish(record.container_id, ExecutionResult(0, "", "", False))

    def test_ids_are_monotonic_and_environment_json_is_canonical(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = self._store_with_image(Path(temporary))
            first = self._container(store, "first")
            second = self._container(store, "second")
            self.assertEqual((first.container_id, second.container_id), ("c000001", "c000002"))
            connection = sqlite3.connect(store.db_path)
            try:
                raw = connection.execute(
                    "SELECT env_json FROM containers WHERE container_id = ?", (first.container_id,)
                ).fetchone()[0]
            finally:
                connection.close()
            self.assertEqual(raw, '{"A":"1","B":"2"}')

    def test_corrupt_json_is_not_returned_as_a_typed_record(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = self._store_with_image(Path(temporary))
            record = self._container(store)
            connection = sqlite3.connect(store.db_path)
            try:
                connection.execute(
                    "UPDATE containers SET command_json = ? WHERE container_id = ?",
                    (json.dumps({"wrong": True}), record.container_id),
                )
                connection.commit()
            finally:
                connection.close()
            with self.assertRaises(Conflict):
                store.get_container(record.container_id)


if __name__ == "__main__":
    unittest.main()
