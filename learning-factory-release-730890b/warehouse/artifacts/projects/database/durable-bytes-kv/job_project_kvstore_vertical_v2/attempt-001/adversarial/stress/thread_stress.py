from __future__ import annotations

import argparse
import os
import sys
import tempfile
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
IMPLEMENTATIONS = {
    "reference": ROOT / "sealed/reference",
    "production": ROOT / "production/implementation",
}
implementation = os.environ.get("KVSTORE_IMPL", "reference")
try:
    implementation_path = IMPLEMENTATIONS[implementation]
except KeyError as error:
    raise SystemExit("KVSTORE_IMPL must be 'reference' or 'production'") from error
sys.path.insert(0, str(implementation_path))
from kvstore import KVStore


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--threads", type=int, default=8)
    parser.add_argument("--operations", type=int, default=200)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "stress.log"
        with KVStore(path, sync=False) as store:
            errors: list[BaseException] = []

            def writer(worker: int) -> None:
                try:
                    for item in range(args.operations):
                        store.set(f"{worker}:{item}".encode(), str(item).encode())
                except BaseException as error:
                    errors.append(error)

            threads = [threading.Thread(target=writer, args=(worker,)) for worker in range(args.threads)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
            if errors:
                raise errors[0]
            assert len(store.keys()) == args.threads * args.operations
        with KVStore(path) as reopened:
            assert len(reopened.keys()) == args.threads * args.operations
    print(
        f"thread stress passed: implementation={implementation} "
        f"threads={args.threads} operations={args.operations}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
