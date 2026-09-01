from __future__ import annotations

import tempfile
from pathlib import Path

from kvstore import KVStore


def main() -> int:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "fault.log"
        with KVStore(path) as store:
            store.set(b"committed", b"survives")
        with path.open("ab") as stream:
            stream.write(b'{"body":"torn tail without newline')
        with KVStore(path) as recovered:
            assert recovered.get(b"committed") == b"survives"
            recovered.set(b"after", b"recovery")
        # Compaction removes the ignored torn bytes before another append/reopen cycle.
        with KVStore(path) as recovered:
            recovered.compact()
        with KVStore(path) as final:
            assert final.get(b"committed") == b"survives"
            assert final.get(b"after") == b"recovery"
    print("torn-tail recovery and post-recovery compaction passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
