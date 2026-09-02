from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import tempfile
import threading
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
    LayerApplier,
    PathEscape,
    StateStore,
)
from pydocklet.image import ImageStore

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

    def test_hash_and_apply_use_the_same_staged_layer_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            layer = write_regular_layer(work / "layer.tar", [("value", b"hashed", 0o644)])
            replacement = write_regular_layer(
                work / "replacement.tar", [("value", b"changed", 0o644)]
            )
            expected_layer_digest = f"sha256:{hashlib.sha256(layer.read_bytes()).hexdigest()}"

            class MutatingApplier(LayerApplier):
                def apply(self, archive_path: Path, destination: Path) -> None:
                    layer.write_bytes(replacement.read_bytes())
                    super().apply(archive_path, destination)

            engine = Docklet(work / "runtime")
            engine.images.applier = MutatingApplier()
            image = engine.import_image("demo", [layer])
            self.assertEqual(image.layer_digests, (expected_layer_digest,))
            self.assertEqual((image.rootfs / "value").read_bytes(), b"hashed")

    def test_published_content_is_read_only_and_verified_before_copy(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            layer = write_regular_layer(work / "layer.tar", [("value", b"original", 0o644)])
            engine = Docklet(work / "runtime")
            image = engine.import_image("demo", [layer])
            published = image.rootfs / "value"
            self.assertEqual(published.stat().st_mode & 0o222, 0)

            os.chmod(published, 0o644)
            published.write_bytes(b"tampered")
            with self.assertRaises(Conflict):
                engine.create("demo", ["tool"])

    def test_racing_different_imports_leave_only_the_winner_object(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            first = write_regular_layer(work / "first.tar", [("value", b"first", 0o644)])
            second = write_regular_layer(work / "second.tar", [("value", b"second", 0o644)])
            engine = Docklet(work / "runtime")
            barrier = threading.Barrier(2, timeout=3)
            stage_layer = engine.images._stage_layer

            def coordinated_stage(source: Path, destination: Path) -> str:
                result = stage_layer(source, destination)
                barrier.wait()
                return result

            engine.images._stage_layer = coordinated_stage  # type: ignore[method-assign]

            def import_layer(path: Path) -> str:
                try:
                    engine.import_image("fixed", [path])
                    return "success"
                except Conflict:
                    return "conflict"

            with ThreadPoolExecutor(max_workers=2) as pool:
                outcomes = list(pool.map(import_layer, (first, second)))
            self.assertCountEqual(outcomes, ["success", "conflict"])
            image_dirs = [
                path for path in (work / "runtime" / "images").iterdir() if path.is_dir()
            ]
            self.assertEqual(len(image_dirs), 1)

    def test_losing_published_object_is_removed_after_atomic_tag_claim(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            first = write_regular_layer(work / "first.tar", [("value", b"first", 0o644)])
            second = write_regular_layer(work / "second.tar", [("value", b"second", 0o644)])
            barrier = threading.Barrier(2, timeout=3)

            class CoordinatedState(StateStore):
                def register_image(self, *args, **kwargs):  # type: ignore[no-untyped-def]
                    barrier.wait()
                    return super().register_image(*args, **kwargs)

            state = CoordinatedState(work / "runtime")
            images = ImageStore(state.root, state)

            def import_layer(path: Path) -> str:
                try:
                    images.import_image("fixed", [path])
                    return "success"
                except Conflict:
                    return "conflict"

            with ThreadPoolExecutor(max_workers=2) as pool:
                outcomes = list(pool.map(import_layer, (first, second)))
            self.assertCountEqual(outcomes, ["success", "conflict"])
            image_dirs = [
                path for path in (work / "runtime" / "images").iterdir() if path.is_dir()
            ]
            self.assertEqual(len(image_dirs), 1)


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
