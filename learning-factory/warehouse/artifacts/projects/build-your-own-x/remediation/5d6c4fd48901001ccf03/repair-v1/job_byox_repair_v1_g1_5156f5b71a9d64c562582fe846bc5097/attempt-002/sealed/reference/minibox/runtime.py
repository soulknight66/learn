"""Runtime coordination plus an optional real Linux namespace backend."""

from __future__ import annotations

import json
import os
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .config import ContainerSpec
from .errors import BackendError, BackendTimeout, BackendUnavailable
from .plan import build_plan
from .rootfs import resolve_executable
from .state import CREATED, EXITED, FAILED, RUNNING, StateStore


@dataclass(frozen=True)
class ExecutionResult:
    exit_code: int
    stdout: bytes
    stderr: bytes


class ExecutionBackend(Protocol):
    def run(self, spec: ContainerSpec) -> ExecutionResult: ...


class Runtime:
    def __init__(self, store: StateStore, backend: ExecutionBackend) -> None:
        self.store = store
        self.backend = backend

    def run(self, spec: ContainerSpec, container_id: str) -> ExecutionResult:
        self.store.create(container_id)
        self.store.transition(container_id, CREATED, RUNNING)
        try:
            result = self.backend.run(spec)
            if not isinstance(result, ExecutionResult):
                raise BackendError("backend returned an invalid result object")
            if (
                isinstance(result.exit_code, bool)
                or not isinstance(result.exit_code, int)
                or not isinstance(result.stdout, bytes)
                or not isinstance(result.stderr, bytes)
            ):
                raise BackendError("backend returned invalid result fields")
        except Exception as exc:
            message = f"{type(exc).__name__}: {exc}"[:4096]
            try:
                self.store.transition(container_id, RUNNING, FAILED, error=message)
            except Exception as state_error:
                if hasattr(exc, "add_note"):
                    exc.add_note(
                        "Minibox also failed to persist FAILED state: "
                        f"{type(state_error).__name__}: {state_error}"
                    )
            raise
        self.store.transition(
            container_id,
            RUNNING,
            EXITED,
            exit_code=result.exit_code,
        )
        return result


def _program_path(configured: str | None, fallback_name: str) -> str | None:
    if configured is None:
        return shutil.which(fallback_name)
    if not isinstance(configured, str) or not configured or "\x00" in configured:
        raise BackendUnavailable(f"invalid path configured for {fallback_name}")
    return configured


def _require_executable(path: str | None, name: str) -> str:
    if path is None:
        raise BackendUnavailable(f"{name} was not found on PATH")
    if not isinstance(path, str) or not path or "\x00" in path:
        raise BackendUnavailable(f"invalid path configured for {name}")
    candidate = Path(path)
    if not candidate.is_absolute():
        raise BackendUnavailable(f"{name} path must be absolute")
    try:
        metadata = os.stat(candidate, follow_symlinks=True)
    except OSError as exc:
        raise BackendUnavailable(f"cannot inspect {name}: {exc.strerror or exc}") from exc
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_mode & 0o111 == 0:
        raise BackendUnavailable(f"{name} is not an executable regular file")
    return str(candidate)


def _bounded_read(stream: object, limit: int) -> bytes:
    stream.seek(0)
    data = stream.read(limit + 1)
    if len(data) <= limit:
        return data
    return data[:limit] + b"\n[minibox: output truncated]\n"


def _read_status(descriptor: int) -> bytes:
    chunks: list[bytes] = []
    remaining = 4097
    while remaining:
        try:
            chunk = os.read(descriptor, remaining)
        except BlockingIOError as exc:
            raise BackendError("child status pipe remained open after launcher exit") from exc
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def _terminate_process_group(process: subprocess.Popen[bytes]) -> None:
    group_error: OSError | None = None
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    except OSError as exc:
        group_error = exc
        try:
            process.kill()
        except OSError:
            pass
    try:
        process.communicate(timeout=5)
    except subprocess.TimeoutExpired as exc:
        try:
            process.kill()
        except OSError:
            pass
        try:
            process.communicate(timeout=5)
        except subprocess.TimeoutExpired as final_exc:
            raise BackendError("namespace launcher could not be reaped") from final_exc
    if group_error is not None:
        raise BackendError(f"cannot kill namespace process group: {group_error}")


class LinuxSubprocessBackend:
    """Launch the child helper using util-linux ``unshare``.

    Construction performs no host mutation.  ``run`` validates all programs
    and the rootfs command before starting a process group.  Captured output is
    spooled to temporary files and read back with a fixed upper bound.
    """

    def __init__(
        self,
        *,
        unshare_path: str | None = None,
        python_path: str | None = None,
        max_output_bytes: int = 1_048_576,
    ) -> None:
        if (
            isinstance(max_output_bytes, bool)
            or not isinstance(max_output_bytes, int)
            or max_output_bytes <= 0
            or max_output_bytes > 16_777_216
        ):
            raise ValueError("max_output_bytes must be an integer from 1 to 16777216")
        self.unshare_path = _program_path(unshare_path, "unshare")
        self.python_path = (
            _program_path(python_path, "python")
            if python_path is not None
            else sys.executable
        )
        self.max_output_bytes = max_output_bytes

    def run(self, spec: ContainerSpec) -> ExecutionResult:
        if sys.platform != "linux":
            raise BackendUnavailable("the namespace backend requires Linux")
        unshare = _require_executable(self.unshare_path, "unshare")
        python = _require_executable(self.python_path, "python")
        host_executable = resolve_executable(spec)
        container_executable = "/" + host_executable.relative_to(spec.rootfs).as_posix()
        plan = build_plan(spec, unshare_path=unshare, python_path=python)
        payload = {
            "argv": list(spec.argv),
            "env": dict(spec.env),
            "executable": container_executable,
            "hostname": spec.hostname,
            "rootfs": str(spec.rootfs),
            "schema_version": 1,
        }
        encoded = (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode(
            "utf-8"
        )

        package_root = str(Path(__file__).resolve(strict=True).parent.parent)
        try:
            status_read, status_write = os.pipe()
            os.set_inheritable(status_read, False)
            os.set_inheritable(status_write, False)
        except OSError as exc:
            for descriptor in locals().get("status_read"), locals().get("status_write"):
                if isinstance(descriptor, int):
                    try:
                        os.close(descriptor)
                    except OSError:
                        pass
            raise BackendError(f"cannot create child status pipe: {exc}") from exc

        with (
            os.fdopen(status_read, "rb", buffering=0) as status_reader,
            os.fdopen(status_write, "wb", buffering=0) as status_writer,
            tempfile.TemporaryFile() as stdout_file,
            tempfile.TemporaryFile() as stderr_file,
        ):
            launcher_environment = {
                "LC_ALL": "C",
                "MINIBOX_STATUS_FD": str(status_writer.fileno()),
                "PATH": "/usr/bin:/bin",
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONHASHSEED": "0",
                "PYTHONNOUSERSITE": "1",
                "PYTHONPATH": package_root,
            }
            try:
                process = subprocess.Popen(
                    list(plan.argv),
                    stdin=subprocess.PIPE,
                    stdout=stdout_file,
                    stderr=stderr_file,
                    close_fds=True,
                    env=launcher_environment,
                    pass_fds=(status_writer.fileno(),),
                    start_new_session=True,
                )
            except Exception as exc:
                error_type = BackendUnavailable if isinstance(exc, OSError) else BackendError
                detail = exc.strerror or exc if isinstance(exc, OSError) else exc
                raise error_type(f"cannot start namespace launcher: {detail}") from exc
            status_writer.close()
            try:
                process.communicate(input=encoded, timeout=spec.timeout_seconds)
            except subprocess.TimeoutExpired as exc:
                try:
                    _terminate_process_group(process)
                except BackendError as cleanup_error:
                    raise BackendError(
                        "container timed out and process-group cleanup failed"
                    ) from cleanup_error
                raise BackendTimeout(
                    f"container exceeded {spec.timeout_seconds:g} seconds"
                ) from exc
            except OSError as exc:
                try:
                    _terminate_process_group(process)
                except BackendError as cleanup_error:
                    if hasattr(exc, "add_note"):
                        exc.add_note(f"process cleanup also failed: {cleanup_error}")
                raise BackendError(f"namespace launcher I/O failed: {exc.strerror or exc}") from exc
            except BaseException as exc:
                try:
                    _terminate_process_group(process)
                except BackendError as cleanup_error:
                    if hasattr(exc, "add_note"):
                        exc.add_note(f"Minibox process cleanup also failed: {cleanup_error}")
                raise

            try:
                os.set_blocking(status_reader.fileno(), False)
                setup_status = _read_status(status_reader.fileno())
            except OSError as exc:
                raise BackendError(f"cannot read child setup status: {exc}") from exc
            if setup_status != b"READY\n":
                if not setup_status:
                    detail = "launcher exited before the child reported readiness"
                elif len(setup_status) > 4096:
                    detail = "child status exceeded its bound"
                else:
                    detail = setup_status.decode("utf-8", errors="replace").strip()
                raise BackendError(
                    f"namespace setup failed (launcher exit {process.returncode}): {detail}"
                )

            return ExecutionResult(
                exit_code=process.returncode,
                stdout=_bounded_read(stdout_file, self.max_output_bytes),
                stderr=_bounded_read(stderr_file, self.max_output_bytes),
            )
