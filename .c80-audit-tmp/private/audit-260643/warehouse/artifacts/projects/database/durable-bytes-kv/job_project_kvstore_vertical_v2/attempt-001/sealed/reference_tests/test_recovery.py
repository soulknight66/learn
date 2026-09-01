from __future__ import annotations

import json
import os
import tempfile
import threading
import unittest
import zlib
from pathlib import Path
from unittest import mock

import kvstore
from kvstore import CorruptLogError, KVStore


class RecoveryAndBoundsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.path = Path(self.temporary.name) / "store.log"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_truncated_tail_is_ignored(self) -> None:
        with KVStore(self.path) as store:
            store.set(b"safe", b"committed")
        with self.path.open("ab") as stream:
            stream.write(b'{"body":"interrupted')
        with KVStore(self.path) as store:
            self.assertEqual(store.get(b"safe"), b"committed")

    def test_complete_corruption_is_rejected(self) -> None:
        with KVStore(self.path) as store:
            store.set(b"safe", b"committed")
        data = bytearray(self.path.read_bytes())
        data[data.index(b"crc32") + 9] = ord("f") if data[data.index(b"crc32") + 9] != ord("f") else ord("e")
        self.path.write_bytes(data)
        with self.assertRaises(CorruptLogError):
            KVStore(self.path)

    def test_checksummed_wrong_shape_is_normalized_as_corruption(self) -> None:
        body = b"[]"
        envelope = json.dumps(
            {
                "body": body.decode("ascii"),
                "crc32": f"{zlib.crc32(body) & 0xffffffff:08x}",
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8") + b"\n"
        self.path.write_bytes(envelope)
        with self.assertRaises(CorruptLogError):
            KVStore(self.path)

    def test_batch_validation_happens_before_append(self) -> None:
        with KVStore(self.path) as store:
            store.set(b"existing", b"value")
            before = self.path.stat().st_size
            with self.assertRaises(ValueError):
                store.batch([("set", b"valid", b"x"), ("invalid", b"bad", None)])
            self.assertEqual(self.path.stat().st_size, before)
            self.assertIsNone(store.get(b"valid"))

    def test_bounds_and_closed_lifecycle(self) -> None:
        store = KVStore(self.path)
        with self.assertRaises(ValueError):
            store.set(b"", b"x")
        with self.assertRaises(ValueError):
            store.set(b"k", b"x" * (store.MAX_VALUE_BYTES + 1))
        store.close()
        with self.assertRaises(RuntimeError):
            store.get(b"k")
        with self.assertRaises(RuntimeError):
            store.batch([])

    def test_short_writes_are_completed_before_acknowledgement(self) -> None:
        store = KVStore(self.path)
        underlying = store._file

        class ShortWriter:
            calls = 0

            def write(self, data: object) -> int:
                chunk = bytes(data)
                self.calls += 1
                return underlying.write(chunk[:max(1, len(chunk) // 3)])

            def fileno(self) -> int:
                return underlying.fileno()

            def close(self) -> None:
                underlying.close()

        writer = ShortWriter()
        store._file = writer
        store.set(b"short", b"complete")
        self.assertGreater(writer.calls, 1)
        store.close()
        with KVStore(self.path) as reopened:
            self.assertEqual(b"complete", reopened.get(b"short"))

    def test_partial_write_failure_poisons_store(self) -> None:
        store = KVStore(self.path, sync=False)
        underlying = store._file

        class FailingWriter:
            attempted = False

            def write(self, data: object) -> int:
                if not self.attempted:
                    self.attempted = True
                    underlying.write(bytes(data)[:7])
                raise OSError("injected append failure")

            def fileno(self) -> int:
                return underlying.fileno()

            def close(self) -> None:
                underlying.close()

        store._file = FailingWriter()
        with self.assertRaisesRegex(OSError, "injected append failure"):
            store.set(b"uncertain", b"value")
        with self.assertRaisesRegex(RuntimeError, "persistence failure"):
            store.get(b"uncertain")
        store.close()
        with KVStore(self.path) as reopened:
            self.assertIsNone(reopened.get(b"uncertain"))

    def test_failed_replace_keeps_original_store_usable(self) -> None:
        store = KVStore(self.path, sync=False)
        store.set(b"before", b"value")
        with mock.patch.object(kvstore.os, "replace", side_effect=OSError("injected replace failure")):
            with self.assertRaisesRegex(OSError, "injected replace failure"):
                store.compact()
        self.assertFalse(self.path.with_name(self.path.name + ".compact.tmp").exists())
        store.set(b"after", b"value")
        store.close()
        with KVStore(self.path) as reopened:
            self.assertEqual([b"after", b"before"], reopened.keys())

    @unittest.skipUnless(hasattr(os, "O_DIRECTORY"), "directory fsync requires POSIX O_DIRECTORY")
    def test_directory_fsync_failure_keeps_replacement_usable(self) -> None:
        store = KVStore(self.path, sync=False)
        store.set(b"before", b"value")
        real_fsync = kvstore.os.fsync
        calls = 0

        def fail_second_fsync(file_descriptor: int) -> None:
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("injected directory fsync failure")
            real_fsync(file_descriptor)

        with mock.patch.object(kvstore.os, "fsync", side_effect=fail_second_fsync):
            with self.assertRaisesRegex(OSError, "injected directory fsync failure"):
                store.compact()
        store.set(b"after", b"value")
        store.close()
        with KVStore(self.path) as reopened:
            self.assertEqual([b"after", b"before"], reopened.keys())

    def test_concurrent_unique_writes_survive_replay(self) -> None:
        with KVStore(self.path, sync=False) as store:
            def writer(worker: int) -> None:
                for item in range(50):
                    key = f"{worker}:{item}".encode()
                    store.set(key, b"value")

            threads = [threading.Thread(target=writer, args=(worker,)) for worker in range(6)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
            self.assertEqual(len(store.keys()), 300)
        with KVStore(self.path) as store:
            self.assertEqual(len(store.keys()), 300)


if __name__ == "__main__":
    unittest.main()
