from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from kvstore import KVStore


class PublicContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.path = Path(self.temporary.name) / "store.log"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_round_trip_and_reopen(self) -> None:
        with KVStore(self.path) as store:
            store.set(b"alpha", b"one")
            store.set(b"binary\x00key", b"binary\xffvalue")
            self.assertEqual(store.get(b"alpha"), b"one")
        with KVStore(self.path) as store:
            self.assertEqual(store.get(b"alpha"), b"one")
            self.assertEqual(store.get(b"binary\x00key"), b"binary\xffvalue")

    def test_delete_result_and_persistence(self) -> None:
        with KVStore(self.path) as store:
            self.assertFalse(store.delete(b"missing"))
            store.set(b"doomed", b"value")
            self.assertTrue(store.delete(b"doomed"))
            self.assertIsNone(store.get(b"doomed"))
        with KVStore(self.path) as store:
            self.assertIsNone(store.get(b"doomed"))

    def test_atomic_batch_and_sorted_keys(self) -> None:
        with KVStore(self.path) as store:
            store.set(b"remove", b"x")
            store.batch([
                ("set", b"z", b"last"),
                ("set", b"a", b"first"),
                ("delete", b"remove", None),
            ])
            self.assertEqual(store.keys(), [b"a", b"z"])

    def test_compaction_preserves_state(self) -> None:
        with KVStore(self.path) as store:
            for number in range(30):
                store.set(b"key", str(number).encode())
            before = self.path.stat().st_size
            store.compact()
            after = self.path.stat().st_size
            self.assertLess(after, before)
        with KVStore(self.path) as store:
            self.assertEqual(store.get(b"key"), b"29")


if __name__ == "__main__":
    unittest.main()
