from __future__ import annotations

import sqlite3
import threading
from pathlib import Path


class SQLiteStore:
    def __init__(self, path: str | Path) -> None:
        self._connection = sqlite3.connect(path, check_same_thread=False)
        self._connection.execute("PRAGMA synchronous=FULL")
        self._connection.execute("CREATE TABLE IF NOT EXISTS kv(key BLOB PRIMARY KEY,value BLOB NOT NULL)")
        self._lock = threading.RLock()

    def set(self, key: bytes, value: bytes) -> None:
        with self._lock, self._connection:
            self._connection.execute(
                "INSERT INTO kv(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, value),
            )

    def get(self, key: bytes) -> bytes | None:
        with self._lock:
            row = self._connection.execute("SELECT value FROM kv WHERE key=?", (key,)).fetchone()
            return bytes(row[0]) if row else None

    def delete(self, key: bytes) -> bool:
        with self._lock, self._connection:
            return self._connection.execute("DELETE FROM kv WHERE key=?", (key,)).rowcount == 1

    def close(self) -> None:
        with self._lock:
            self._connection.close()
