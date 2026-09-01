from __future__ import annotations

import tempfile
import threading
import unittest
from pathlib import Path

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
