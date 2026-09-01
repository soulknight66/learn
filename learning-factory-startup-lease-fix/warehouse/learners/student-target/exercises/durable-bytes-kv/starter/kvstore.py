from __future__ import annotations

from pathlib import Path
from typing import Iterable


class KVStore:
    MAX_KEY_BYTES = 1024
    MAX_VALUE_BYTES = 1024 * 1024

    def __init__(self, path: str | Path, *, sync: bool = True) -> None:
        self.path = Path(path)
        self.sync = sync
        self._data: dict[bytes, bytes] = {}
        # TODO: create/replay the append log and initialize lifecycle synchronization.

    def set(self, key: bytes, value: bytes) -> None:
        raise NotImplementedError

    def get(self, key: bytes) -> bytes | None:
        return self._data.get(key)

    def delete(self, key: bytes) -> bool:
        raise NotImplementedError

    def batch(self, operations: Iterable[tuple[str, bytes, bytes | None]]) -> None:
        raise NotImplementedError

    def keys(self) -> list[bytes]:
        return sorted(self._data)

    def compact(self) -> None:
        raise NotImplementedError

    def close(self) -> None:
        raise NotImplementedError

    def __enter__(self) -> "KVStore":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
