from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent / "buggy"))
from kvstore import KVStore


class LostDeleteRegression(unittest.TestCase):
    def test_delete_survives_restart(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "store.log"
            with KVStore(path) as store:
                store.set(b"session", b"active")
                store.delete(b"session")
                self.assertIsNone(store.get(b"session"))
            with KVStore(path) as reopened:
                self.assertIsNone(reopened.get(b"session"))


if __name__ == "__main__":
    unittest.main()
