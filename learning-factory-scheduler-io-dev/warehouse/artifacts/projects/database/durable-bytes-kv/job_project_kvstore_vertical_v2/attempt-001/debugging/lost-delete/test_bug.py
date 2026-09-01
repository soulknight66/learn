from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
IMPLEMENTATIONS = {
    "buggy": Path(__file__).resolve().parent / "buggy",
    "reference": ROOT / "sealed/reference",
    "production": ROOT / "production/implementation",
}
implementation = os.environ.get("KVSTORE_IMPL", "buggy")
try:
    implementation_path = IMPLEMENTATIONS[implementation]
except KeyError as error:
    raise SystemExit(
        "KVSTORE_IMPL must be 'buggy', 'reference', or 'production'"
    ) from error
sys.path.insert(0, str(implementation_path))
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
