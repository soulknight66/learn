from __future__ import annotations

import base64
import json
import os
import threading
import time
from collections import Counter
import zlib
from pathlib import Path
from typing import Iterable


class CorruptLogError(RuntimeError):
    pass


class KVStore:
    MAX_KEY_BYTES = 1024
    MAX_VALUE_BYTES = 1024 * 1024
    MAX_RECORD_BYTES = 4 * 1024 * 1024

    def __init__(self, path: str | Path, *, sync: bool = True) -> None:
        self.path = Path(path)
        self.sync = bool(sync)
        self._lock = threading.RLock()
        self._closed = False
        self._poisoned = False
        self._data: dict[bytes, bytes] = {}
        self._metrics: Counter[str] = Counter()
        self._opened_at = time.monotonic()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._replay()
        self._file = self.path.open("ab", buffering=0)

    @staticmethod
    def _b64(value: bytes) -> str:
        return base64.b64encode(value).decode("ascii")

    @staticmethod
    def _unb64(value: object) -> bytes:
        if not isinstance(value, str):
            raise CorruptLogError("encoded bytes must be a string")
        try:
            return base64.b64decode(value, validate=True)
        except (ValueError, TypeError) as error:
            raise CorruptLogError("invalid base64 in log") from error

    def _check_open(self) -> None:
        if self._closed:
            raise RuntimeError("store is closed")
        if self._poisoned:
            raise RuntimeError("store is unavailable after a persistence failure")

    @staticmethod
    def _write_all(stream: object, data: bytes) -> None:
        remaining = memoryview(data)
        while remaining:
            written = stream.write(remaining)
            if not isinstance(written, int) or written <= 0 or written > len(remaining):
                raise OSError("write returned an invalid byte count")
            remaining = remaining[written:]

    def _poison(self) -> None:
        self._poisoned = True
        try:
            self._file.close()
        except Exception:
            pass

    @staticmethod
    def _discard_temporary(path: Path) -> None:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass

    def _check_key(self, key: bytes) -> None:
        if not isinstance(key, bytes):
            raise TypeError("keys must be bytes")
        if not key or len(key) > self.MAX_KEY_BYTES:
            raise ValueError("key length is out of bounds")

    def _check_value(self, value: bytes) -> None:
        if not isinstance(value, bytes):
            raise TypeError("values must be bytes")
        if len(value) > self.MAX_VALUE_BYTES:
            raise ValueError("value length is out of bounds")

    def _encode(self, operations: list[tuple[str, bytes, bytes | None]]) -> bytes:
        body = json.dumps(
            {
                "version": 1,
                "ops": [
                    {"op": op, "key": self._b64(key), "value": self._b64(value) if value is not None else None}
                    for op, key, value in operations
                ],
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        envelope = json.dumps(
            {"body": body.decode("utf-8"), "crc32": f"{zlib.crc32(body) & 0xffffffff:08x}"},
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8") + b"\n"
        if len(envelope) > self.MAX_RECORD_BYTES:
            raise ValueError("batch is too large")
        return envelope

    def _decode(self, raw: bytes, line_number: int) -> list[tuple[str, bytes, bytes | None]]:
        try:
            envelope = json.loads(raw)
            body_text = envelope["body"]
            if not isinstance(body_text, str):
                raise TypeError("body is not text")
            body = body_text.encode("utf-8")
            if envelope["crc32"] != f"{zlib.crc32(body) & 0xffffffff:08x}":
                raise CorruptLogError("checksum mismatch")
            decoded = json.loads(body)
            if not isinstance(decoded, dict):
                raise CorruptLogError("record body must be an object")
            if decoded.get("version") != 1 or not isinstance(decoded.get("ops"), list):
                raise CorruptLogError("unsupported record")
            result: list[tuple[str, bytes, bytes | None]] = []
            for item in decoded["ops"]:
                op = item["op"]
                key = self._unb64(item["key"])
                value = self._unb64(item["value"]) if item.get("value") is not None else None
                if op not in {"set", "delete"} or (op == "set") != (value is not None):
                    raise CorruptLogError("invalid operation")
                self._check_key(key)
                if value is not None:
                    self._check_value(value)
                result.append((op, key, value))
            return result
        except CorruptLogError:
            raise
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            raise CorruptLogError(f"invalid complete record at line {line_number}") from error

    def _apply(self, operations: Iterable[tuple[str, bytes, bytes | None]]) -> None:
        for op, key, value in operations:
            if op == "set":
                assert value is not None
                self._data[key] = value
                self._metrics["logical_sets"] += 1
            else:
                self._data.pop(key, None)
                self._metrics["logical_deletes"] += 1

    def _replay(self) -> None:
        if not self.path.exists():
            return
        raw = self.path.read_bytes()
        lines = raw.splitlines(keepends=True)
        valid_bytes = 0
        for index, line in enumerate(lines, start=1):
            if not line.endswith(b"\n"):
                if index == len(lines):
                    with self.path.open("r+b") as stream:
                        stream.truncate(valid_bytes)
                        stream.flush()
                        if self.sync:
                            os.fsync(stream.fileno())
                    break
                raise CorruptLogError(f"unterminated non-tail record at line {index}")
            if len(line) > self.MAX_RECORD_BYTES:
                raise CorruptLogError(f"oversized record at line {index}")
            self._apply(self._decode(line, index))
            valid_bytes += len(line)

    def _append(self, operations: list[tuple[str, bytes, bytes | None]]) -> None:
        record = self._encode(operations)
        completed = False
        try:
            self._write_all(self._file, record)
            if self.sync:
                os.fsync(self._file.fileno())
            completed = True
        finally:
            if not completed:
                self._poison()

    def set(self, key: bytes, value: bytes) -> None:
        self.batch([("set", key, value)])

    def get(self, key: bytes) -> bytes | None:
        self._check_key(key)
        with self._lock:
            self._check_open()
            return self._data.get(key)

    def delete(self, key: bytes) -> bool:
        self._check_key(key)
        with self._lock:
            self._check_open()
            if key not in self._data:
                return False
            self._append([("delete", key, None)])
            self._data.pop(key)
            self._metrics["logical_deletes"] += 1
            return True

    def batch(self, operations: Iterable[tuple[str, bytes, bytes | None]]) -> None:
        normalized = list(operations)
        for op, key, value in normalized:
            if op not in {"set", "delete"}:
                raise ValueError(f"unknown operation: {op}")
            self._check_key(key)
            if op == "set":
                if value is None:
                    raise ValueError("set requires a value")
                self._check_value(value)
            elif value is not None:
                raise ValueError("delete value must be None")
        with self._lock:
            self._check_open()
            if not normalized:
                return
            self._append(normalized)
            self._apply(normalized)

    def keys(self) -> list[bytes]:
        with self._lock:
            self._check_open()
            return sorted(self._data)

    def compact(self) -> None:
        with self._lock:
            self._check_open()
            operations = [("set", key, value) for key, value in sorted(self._data.items())]
            temporary = self.path.with_name(self.path.name + ".compact.tmp")
            record = self._encode(operations) if operations else b""
            replaced = False
            try:
                with temporary.open("wb", buffering=0) as stream:
                    self._write_all(stream, record)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary, self.path)
                replaced = True
                try:
                    replacement = self.path.open("ab", buffering=0)
                except BaseException:
                    self._poison()
                    raise
                previous = self._file
                self._file = replacement
                previous.close()
                if hasattr(os, "O_DIRECTORY"):
                    directory_fd = os.open(self.path.parent, os.O_RDONLY | os.O_DIRECTORY)
                    try:
                        os.fsync(directory_fd)
                    finally:
                        os.close(directory_fd)
            finally:
                if not replaced:
                    self._discard_temporary(temporary)

    def metrics(self) -> dict[str, int | float]:
        with self._lock:
            return {
                **dict(self._metrics),
                "live_keys": len(self._data),
                "uptime_seconds": time.monotonic() - self._opened_at,
            }

    def health(self) -> dict[str, object]:
        with self._lock:
            if self._closed:
                status = "closed"
            elif self._poisoned:
                status = "degraded"
            else:
                status = "ok"
            return {"status": status, "path": str(self.path)}

    def close(self) -> None:
        with self._lock:
            if not self._closed:
                try:
                    self._file.close()
                finally:
                    self._closed = True

    def __enter__(self) -> "KVStore":
        self._check_open()
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
