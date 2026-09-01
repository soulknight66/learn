from __future__ import annotations

import argparse
import random
import tempfile
from pathlib import Path

from kvstore import KVStore


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--operations", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=20260830)
    args = parser.parse_args()
    randomizer = random.Random(args.seed)
    model: dict[bytes, bytes] = {}
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "fuzz.log"
        store = KVStore(path, sync=False)
        for step in range(args.operations):
            key = f"key-{randomizer.randrange(40)}".encode()
            choice = randomizer.randrange(5)
            if choice < 3:
                value = randomizer.randbytes(randomizer.randrange(0, 80))
                store.set(key, value)
                model[key] = value
            elif choice == 3:
                observed = store.delete(key)
                expected = key in model
                model.pop(key, None)
                assert observed == expected
            else:
                assert store.get(key) == model.get(key)
            if step and step % 137 == 0:
                store.close()
                store = KVStore(path, sync=False)
                assert store.keys() == sorted(model)
        store.close()
        with KVStore(path) as reopened:
            assert reopened.keys() == sorted(model)
            for key, value in model.items():
                assert reopened.get(key) == value
    print(f"model fuzz passed: seed={args.seed} operations={args.operations}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
