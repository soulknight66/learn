from __future__ import annotations

import os
import tempfile
import threading
from pathlib import Path
from typing import BinaryIO, Callable

from .util import redact


DEFAULT_STREAM_LIMIT_BYTES = 1024 * 1024
DEFAULT_LAST_MESSAGE_LIMIT_BYTES = 64 * 1024
_READ_SIZE = 64 * 1024
_MINIMUM_LIMIT = 256
_OMISSION_MARKER_RESERVE = 128


class CaptureError(RuntimeError):
    """A subprocess stream could not be drained safely."""


class BoundedBinaryCapture:
    """Drain an untrusted binary stream while retaining bounded head and tail data.

    Raw bytes remain in bounded process memory. Only a decoded, credential-redacted,
    size-capped representation is ever written by :meth:`persist_redacted`.
    """

    def __init__(self, max_bytes: int = DEFAULT_STREAM_LIMIT_BYTES):
        if isinstance(max_bytes, bool) or not isinstance(max_bytes, int):
            raise ValueError("capture max_bytes must be an integer")
        if max_bytes < _MINIMUM_LIMIT:
            raise ValueError(f"capture max_bytes must be at least {_MINIMUM_LIMIT}")
        self.max_bytes = max_bytes
        payload_limit = max_bytes - _OMISSION_MARKER_RESERVE
        self._head_limit = payload_limit // 2
        self._tail_limit = payload_limit - self._head_limit
        self._head = bytearray()
        self._tail = bytearray()
        self._total_bytes = 0
        self._thread: threading.Thread | None = None
        self._stream: BinaryIO | None = None
        self._error: BaseException | None = None

    @property
    def total_bytes(self) -> int:
        return self._total_bytes

    @property
    def omitted_bytes(self) -> int:
        return max(0, self._total_bytes - len(self._head) - len(self._tail))

    def feed(self, chunk: bytes) -> None:
        if not isinstance(chunk, bytes):
            raise TypeError("capture chunks must be bytes")
        if not chunk:
            return
        self._total_bytes += len(chunk)
        head_room = self._head_limit - len(self._head)
        if head_room > 0:
            self._head.extend(chunk[:head_room])
            chunk = chunk[head_room:]
        if chunk:
            self._tail.extend(chunk)
            overflow = len(self._tail) - self._tail_limit
            if overflow > 0:
                del self._tail[:overflow]

    def start(
        self,
        stream: BinaryIO,
        *,
        observe: Callable[[bytes], None] | None = None,
        name: str = "bounded-stream-capture",
    ) -> None:
        if self._thread is not None:
            raise CaptureError("capture already started")
        self._stream = stream

        def drain() -> None:
            try:
                while True:
                    read = getattr(stream, "read1", stream.read)
                    chunk = read(_READ_SIZE)
                    if not chunk:
                        break
                    self.feed(chunk)
                    if observe is not None:
                        observe(chunk)
            except BaseException as error:
                self._error = error
            finally:
                try:
                    stream.close()
                except OSError:
                    pass

        self._thread = threading.Thread(target=drain, name=name, daemon=True)
        self._thread.start()

    def finish(self, timeout: float = 5.0) -> None:
        if self._thread is None:
            return
        self._thread.join(timeout)
        if self._thread.is_alive():
            raise CaptureError("subprocess stream did not close after process-group cleanup")
        if self._error is not None:
            raise CaptureError(f"subprocess stream capture failed: {self._error}")

    def snapshot(self) -> bytes:
        if not self.omitted_bytes:
            return bytes(self._head + self._tail)
        marker = (
            f"\n[learnfactory: {self.omitted_bytes} bytes omitted from retained log]\n"
        ).encode("ascii")
        return bytes(self._head) + marker + bytes(self._tail)

    def persist_redacted(self, path: Path) -> str:
        return write_redacted_bytes(path, self.snapshot(), max_bytes=self.max_bytes)


def _bounded_utf8(text: str, max_bytes: int) -> bytes:
    encoded = text.encode("utf-8")
    if len(encoded) <= max_bytes:
        return encoded
    marker = b"\n[learnfactory: sanitized retained log truncated]\n"
    budget = max_bytes - len(marker)
    if budget <= 0:
        return marker[:max_bytes]
    head_size = budget // 2
    tail_size = budget - head_size
    head = encoded[:head_size].decode("utf-8", errors="ignore").encode("utf-8")
    tail = encoded[-tail_size:].decode("utf-8", errors="ignore").encode("utf-8")
    return head + marker + tail


def write_redacted_bytes(path: Path, value: bytes, *, max_bytes: int) -> str:
    """Atomically persist a bounded redacted rendering of untrusted bytes."""

    if max_bytes < _MINIMUM_LIMIT:
        raise ValueError(f"max_bytes must be at least {_MINIMUM_LIMIT}")
    rendered = value.decode("utf-8", errors="replace")
    sanitized = redact(rendered, limit=None)
    durable = _bounded_utf8(sanitized, max_bytes)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(durable)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()
    return durable.decode("utf-8", errors="strict")


def sanitize_retained_file(
    source: Path,
    *,
    destination: Path | None = None,
    max_bytes: int = DEFAULT_STREAM_LIMIT_BYTES,
) -> str:
    """Bound and redact an existing file without reading it all into memory."""

    capture = BoundedBinaryCapture(max_bytes)
    if source.exists():
        with source.open("rb") as stream:
            while chunk := stream.read(_READ_SIZE):
                capture.feed(chunk)
    return capture.persist_redacted(destination or source)
