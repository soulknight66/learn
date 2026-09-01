"""Crash-conscious JSON lifecycle state with guarded transitions."""

from __future__ import annotations

import contextlib
import json
import math
import os
import re
import stat
import tempfile
import time
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Callable, Iterator

from .errors import StateCommitUncertain, StateError

try:
    import fcntl as _fcntl
except ImportError:  # pragma: no cover - exercised on Windows
    _fcntl = None

try:
    import msvcrt as _msvcrt
except ImportError:  # pragma: no cover - exercised on POSIX
    _msvcrt = None

CREATED = "CREATED"
RUNNING = "RUNNING"
EXITED = "EXITED"
FAILED = "FAILED"

_STATUSES = frozenset({CREATED, RUNNING, EXITED, FAILED})
_TRANSITIONS = frozenset(
    {
        (CREATED, RUNNING),
        (RUNNING, EXITED),
        (RUNNING, FAILED),
    }
)
_CONTAINER_ID = re.compile(r"[a-z0-9][a-z0-9_.-]{0,63}\Z", re.ASCII)
_RECORD_KEYS = frozenset(
    {
        "container_id",
        "status",
        "revision",
        "created_at",
        "updated_at",
        "exit_code",
        "error",
    }
)
_MAX_RECORD_BYTES = 65_536


@dataclass(frozen=True)
class ContainerState:
    container_id: str
    status: str
    revision: int
    created_at: float
    updated_at: float
    exit_code: int | None = None
    error: str | None = None


def _validate_id(container_id: str) -> str:
    if not isinstance(container_id, str) or _CONTAINER_ID.fullmatch(container_id) is None:
        raise StateError(
            "container id must match [a-z0-9][a-z0-9_.-]{0,63}"
        )
    return container_id


def _plain_number(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise StateError(f"state field {name} must be numeric")
    converted = float(value)
    if not math.isfinite(converted):
        raise StateError(f"state field {name} must be finite")
    return converted


def _decode_record(raw: object, expected_id: str) -> ContainerState:
    if not isinstance(raw, dict) or frozenset(raw) != _RECORD_KEYS:
        raise StateError("state record has an invalid shape")
    if raw["container_id"] != expected_id:
        raise StateError("state record id does not match its filename")
    status = raw["status"]
    if not isinstance(status, str) or status not in _STATUSES:
        raise StateError("state record has an unknown status")
    revision = raw["revision"]
    if isinstance(revision, bool) or not isinstance(revision, int) or revision < 0:
        raise StateError("state revision must be a non-negative integer")
    created_at = _plain_number(raw["created_at"], "created_at")
    updated_at = _plain_number(raw["updated_at"], "updated_at")
    if updated_at < created_at:
        raise StateError("state updated_at precedes created_at")

    exit_code = raw["exit_code"]
    if exit_code is not None and (
        isinstance(exit_code, bool) or not isinstance(exit_code, int)
    ):
        raise StateError("state exit_code must be an integer or null")
    error = raw["error"]
    if error is not None and (not isinstance(error, str) or not error):
        raise StateError("state error must be a non-empty string or null")

    if status == EXITED:
        if exit_code is None or error is not None:
            raise StateError("EXITED state requires only an exit code")
    elif status == FAILED:
        if error is None or exit_code is not None:
            raise StateError("FAILED state requires only an error")
    elif exit_code is not None or error is not None:
        raise StateError("non-terminal state must not contain result fields")
    expected_revision = {CREATED: 0, RUNNING: 1, EXITED: 2, FAILED: 2}[status]
    if revision != expected_revision:
        raise StateError("state revision is inconsistent with its status")

    return ContainerState(
        container_id=expected_id,
        status=status,
        revision=revision,
        created_at=created_at,
        updated_at=updated_at,
        exit_code=exit_code,
        error=error,
    )


class StateStore:
    def __init__(
        self,
        directory: str | Path,
        *,
        clock: Callable[[], float] | None = None,
    ) -> None:
        requested = Path(directory)
        try:
            requested.mkdir(parents=True, exist_ok=True)
            metadata = os.lstat(requested)
        except OSError as exc:
            raise StateError(f"cannot prepare state directory: {exc.strerror or exc}") from exc
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            raise StateError("state directory must be a real directory, not a symlink")
        absolute = Path(os.path.abspath(requested))
        current = Path(absolute.anchor)
        try:
            for part in absolute.parts[1:]:
                current = current / part
                if stat.S_ISLNK(os.lstat(current).st_mode):
                    raise StateError(
                        "state directory and its parents must not be symlinks"
                    )
        except OSError as exc:
            raise StateError(
                f"cannot inspect state directory: {exc.strerror or exc}"
            ) from exc
        self.directory = absolute
        self.clock = clock if clock is not None else time.time

    def _now(self) -> float:
        try:
            value = self.clock()
        except Exception as exc:
            raise StateError(f"state clock failed: {exc}") from exc
        return _plain_number(value, "clock")

    def _record_path(self, container_id: str) -> Path:
        return self.directory / f"{_validate_id(container_id)}.json"

    @contextlib.contextmanager
    def _locked(self, container_id: str) -> Iterator[None]:
        _validate_id(container_id)
        lock_path = self.directory / f".{container_id}.lock"
        flags = os.O_RDWR | os.O_CREAT
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor: int | None = None
        locked = False
        try:
            descriptor = os.open(lock_path, flags, 0o600)
            if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                raise StateError("state lock is not a regular file")
            if _fcntl is not None:
                _fcntl.flock(descriptor, _fcntl.LOCK_EX)
            elif _msvcrt is not None:  # pragma: no cover - Windows only
                if os.fstat(descriptor).st_size == 0:
                    os.write(descriptor, b"\0")
                    os.fsync(descriptor)
                os.lseek(descriptor, 0, os.SEEK_SET)
                _msvcrt.locking(descriptor, _msvcrt.LK_LOCK, 1)
            else:  # pragma: no cover - no supported Python platform lacks both
                raise StateError("this platform has no supported file-lock API")
            locked = True
        except StateError:
            if descriptor is not None:
                os.close(descriptor)
            raise
        except OSError as exc:
            if descriptor is not None:
                os.close(descriptor)
            raise StateError(f"cannot lock state: {exc.strerror or exc}") from exc
        try:
            yield
        finally:
            try:
                if locked:
                    if _fcntl is not None:
                        _fcntl.flock(descriptor, _fcntl.LOCK_UN)
                    elif _msvcrt is not None:  # pragma: no cover - Windows only
                        os.lseek(descriptor, 0, os.SEEK_SET)
                        _msvcrt.locking(descriptor, _msvcrt.LK_UNLCK, 1)
            finally:
                if descriptor is not None:
                    os.close(descriptor)

    @staticmethod
    def _encoded(state: ContainerState) -> bytes:
        return (
            json.dumps(asdict(state), sort_keys=True, separators=(",", ":")) + "\n"
        ).encode("utf-8")

    def _sync_directory(self) -> None:
        if os.name == "nt":  # Opening a directory for fsync is not supported.
            return
        flags = os.O_RDONLY
        if hasattr(os, "O_DIRECTORY"):
            flags |= os.O_DIRECTORY
        try:
            descriptor = os.open(self.directory, flags)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
        except OSError as exc:
            raise StateError(f"cannot sync state directory: {exc.strerror or exc}") from exc

    def _sync_published(self, state: ContainerState) -> None:
        """Sync a publication or report its deliberately distinct outcome."""

        try:
            self._sync_directory()
        except BaseException as exc:
            raise StateCommitUncertain(state, self.directory, exc) from exc

    def _create_exclusive(self, path: Path, state: ContainerState) -> None:
        data = self._encoded(state)
        descriptor: int | None = None
        temporary: Path | None = None
        try:
            descriptor, temporary_name = tempfile.mkstemp(
                prefix=f".{state.container_id}.create.",
                suffix=".tmp",
                dir=self.directory,
            )
            temporary = Path(temporary_name)
            if hasattr(os, "fchmod"):
                os.fchmod(descriptor, 0o600)
            view = memoryview(data)
            while view:
                written = os.write(descriptor, view)
                if written == 0:
                    raise StateError("short write while creating state")
                view = view[written:]
            os.fsync(descriptor)
            os.close(descriptor)
            descriptor = None
            try:
                os.link(temporary, path)
            except FileExistsError as exc:
                raise StateError(
                    f"container {state.container_id!r} already exists"
                ) from exc
        except StateError:
            raise
        except OSError as exc:
            raise StateError(f"cannot create state: {exc.strerror or exc}") from exc
        finally:
            if descriptor is not None:
                os.close(descriptor)
            if temporary is not None:
                try:
                    temporary.unlink()
                except FileNotFoundError:
                    pass
                except OSError:
                    pass
        self._sync_published(state)

    def _replace(self, path: Path, state: ContainerState) -> None:
        data = self._encoded(state)
        descriptor: int | None = None
        temporary: Path | None = None
        try:
            descriptor, temporary_name = tempfile.mkstemp(
                prefix=f".{state.container_id}.replace.",
                suffix=".tmp",
                dir=self.directory,
            )
            temporary = Path(temporary_name)
            if hasattr(os, "fchmod"):
                os.fchmod(descriptor, 0o600)
            view = memoryview(data)
            while view:
                written = os.write(descriptor, view)
                if written == 0:
                    raise StateError("short write while replacing state")
                view = view[written:]
            os.fsync(descriptor)
            os.close(descriptor)
            descriptor = None
            os.replace(temporary, path)
            temporary = None
        except OSError as exc:
            raise StateError(f"cannot persist state: {exc.strerror or exc}") from exc
        finally:
            if descriptor is not None:
                os.close(descriptor)
            if temporary is not None:
                try:
                    temporary.unlink()
                except FileNotFoundError:
                    pass
                except OSError:
                    pass
        self._sync_published(state)

    def _read(self, path: Path, container_id: str) -> ContainerState:
        flags = os.O_RDONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor: int | None = None
        try:
            path_metadata = os.lstat(path)
            if stat.S_ISLNK(path_metadata.st_mode):
                raise StateError("state path is not a regular, non-symlink file")
            descriptor = os.open(path, flags)
            metadata = os.fstat(descriptor)
            if not stat.S_ISREG(metadata.st_mode):
                raise StateError("state path is not a regular, non-symlink file")
            if metadata.st_size > _MAX_RECORD_BYTES:
                raise StateError("state record is unexpectedly large")
            chunks: list[bytes] = []
            remaining = _MAX_RECORD_BYTES + 1
            while remaining:
                chunk = os.read(descriptor, min(8192, remaining))
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            encoded = b"".join(chunks)
            if len(encoded) > _MAX_RECORD_BYTES:
                raise StateError("state record is unexpectedly large")
            def reject_constant(value: str) -> None:
                raise ValueError(f"non-finite JSON constant {value!r}")

            def reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
                result: dict[str, object] = {}
                for key, value in pairs:
                    if key in result:
                        raise ValueError(f"duplicate JSON key {key!r}")
                    result[key] = value
                return result

            raw = json.loads(
                encoded.decode("utf-8"),
                parse_constant=reject_constant,
                object_pairs_hook=reject_duplicate_keys,
            )
        except FileNotFoundError as exc:
            raise StateError(f"container {container_id!r} does not exist") from exc
        except (OSError, UnicodeError, ValueError) as exc:
            raise StateError(f"cannot decode state record: {exc}") from exc
        finally:
            if descriptor is not None:
                os.close(descriptor)
        return _decode_record(raw, container_id)

    def create(self, container_id: str) -> ContainerState:
        path = self._record_path(container_id)
        with self._locked(container_id):
            now = self._now()
            state = ContainerState(
                container_id=container_id,
                status=CREATED,
                revision=0,
                created_at=now,
                updated_at=now,
            )
            self._create_exclusive(path, state)
            return state

    def get(self, container_id: str) -> ContainerState:
        path = self._record_path(container_id)
        with self._locked(container_id):
            return self._read(path, container_id)

    def recover(self, uncertainty: StateCommitUncertain) -> ContainerState:
        """Reconcile and re-sync one post-publication uncertain commit.

        Recovery succeeds only when this store addresses the same state
        directory and the complete visible record equals the proposal carried
        by ``uncertainty``. A missing, superseded, or different record remains
        evidence requiring caller-level reconciliation and is never rewritten.
        """

        if not isinstance(uncertainty, StateCommitUncertain):
            raise StateError("recover requires a StateCommitUncertain value")
        proposed = uncertainty.proposed_state
        if (
            not isinstance(proposed, ContainerState)
            or uncertainty._directory != self.directory
        ):
            raise StateError("uncertain commit belongs to a different state store")
        path = self._record_path(proposed.container_id)
        with self._locked(proposed.container_id):
            visible = self._read(path, proposed.container_id)
            if visible != proposed:
                raise StateError("visible state does not match the uncertain commit")
            self._sync_published(proposed)
            return visible

    def transition(
        self,
        container_id: str,
        expected: str,
        target: str,
        *,
        exit_code: int | None = None,
        error: str | None = None,
    ) -> ContainerState:
        path = self._record_path(container_id)
        if (
            not isinstance(expected, str)
            or not isinstance(target, str)
            or (expected, target) not in _TRANSITIONS
        ):
            raise StateError(f"illegal state transition {expected!r} -> {target!r}")
        if target == EXITED:
            if isinstance(exit_code, bool) or not isinstance(exit_code, int) or error is not None:
                raise StateError("EXITED transition requires only an integer exit_code")
        elif target == FAILED:
            if not isinstance(error, str) or not error or exit_code is not None:
                raise StateError("FAILED transition requires only a non-empty error")
        elif exit_code is not None or error is not None:
            raise StateError("RUNNING transition cannot carry terminal fields")

        with self._locked(container_id):
            current = self._read(path, container_id)
            if current.status != expected:
                raise StateError(
                    f"expected state {expected!r}, found {current.status!r}"
                )
            now = self._now()
            if now < current.updated_at:
                raise StateError("state clock moved backwards")
            updated = replace(
                current,
                status=target,
                revision=current.revision + 1,
                updated_at=now,
                exit_code=exit_code,
                error=error,
            )
            self._replace(path, updated)
            return updated
