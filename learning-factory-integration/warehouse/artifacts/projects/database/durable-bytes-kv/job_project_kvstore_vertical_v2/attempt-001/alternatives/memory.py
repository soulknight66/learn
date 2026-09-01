from __future__ import annotations

import threading


class MemoryStore:
    def __init__(self) -> None:
        self._data: dict[bytes, bytes] = {}
        self._lock = threading.RLock()

    def set(self, key: bytes, value: bytes) -> None:
        with self._lock:
            self._data[key] = value

    def get(self, key: bytes) -> bytes | None:
        with self._lock:
            return self._data.get(key)

    def delete(self, key: bytes) -> bool:
        with self._lock:
            return self._data.pop(key, None) is not None
