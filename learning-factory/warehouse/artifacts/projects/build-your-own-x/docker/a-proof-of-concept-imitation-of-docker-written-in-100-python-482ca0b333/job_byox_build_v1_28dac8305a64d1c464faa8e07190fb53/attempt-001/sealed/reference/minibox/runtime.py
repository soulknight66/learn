"""Linux namespace planning and bounded process execution."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import signal
import stat
import subprocess
import threading
from typing import BinaryIO, Callable, Protocol

from .errors import BackendUnavailable, RunError, StateConflict
from .models import ContainerSpec, ContainerState
from .state import StateStore


class RuntimeBackend(Protocol):
    def build_argv(self, rootfs: Path, spec: ContainerSpec) -> tuple[str, ...]: ...


@dataclass(frozen=True)
class RunResult:
    container_id: str
    argv: tuple[str, ...]
    returncode: int | None
    stdout: bytes
    stderr: bytes
    timed_out: bool
    output_truncated: bool


class LinuxNamespaceBackend:
    def __init__(self, executable: str = "unshare") -> None:
        if not isinstance(executable, str) or not executable or "\x00" in executable:
            raise BackendUnavailable("unshare executable must be a non-empty NUL-free string")
        self.executable = executable

    def build_argv(self, rootfs: Path, spec: ContainerSpec) -> tuple[str, ...]:
        if not isinstance(spec, ContainerSpec):
            raise TypeError("spec must be a ContainerSpec")
        root = Path(rootfs).absolute()
        try:
            mode = root.lstat().st_mode
        except (OSError, ValueError) as exc:
            raise BackendUnavailable(f"container rootfs is unavailable: {root}") from exc
        if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode):
            raise BackendUnavailable(f"container rootfs is not a real directory: {root}")

        options = [
            self.executable,
            "--fork",
            "--pid",
            "--mount",
            "--uts",
            "--ipc",
            "--user",
            "--map-root-user",
        ]
        if spec.network:
            options.append("--net")
        options.extend(
            (
                "--mount-proc=/proc",
                f"--root={root}",
                f"--wd={spec.working_dir}",
                "--",
                *spec.argv,
            )
        )
        return tuple(options)


def _drain(stream: BinaryIO, limit: int, output: bytearray, truncated: list[bool]) -> None:
    try:
        while True:
            chunk = stream.read(64 * 1024)
            if not chunk:
                break
            remaining = limit - len(output)
            if remaining > 0:
                output.extend(chunk[:remaining])
            if len(chunk) > remaining:
                truncated[0] = True
    finally:
        stream.close()


class Runner:
    _BASE_ENVIRONMENT = {
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
    }

    def __init__(
        self,
        state: StateStore,
        rootfs_for: Callable[[str], Path],
        *,
        backend: RuntimeBackend | None = None,
        timeout: float = 10.0,
        max_output: int = 1024 * 1024,
    ) -> None:
        if not isinstance(state, StateStore):
            raise TypeError("state must be a StateStore")
        if not callable(rootfs_for):
            raise TypeError("rootfs_for must be callable")
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or timeout <= 0:
            raise ValueError("timeout must be positive")
        if type(max_output) is not int or max_output <= 0:
            raise ValueError("max_output must be a positive integer")
        self.state = state
        self.rootfs_for = rootfs_for
        self.backend = backend if backend is not None else LinuxNamespaceBackend()
        self.timeout = float(timeout)
        self.max_output = max_output

    def run(self, container_id: str) -> RunResult:
        record = self.state.get(container_id)
        if record.state not in (ContainerState.CREATED, ContainerState.EXITED, ContainerState.FAILED):
            raise StateConflict(f"container cannot run from state {record.state.value}")
        rootfs = self.rootfs_for(record.container_id)
        argv = self.backend.build_argv(rootfs, record.spec)
        if not isinstance(argv, tuple) or not argv or any(not isinstance(item, str) for item in argv):
            raise BackendUnavailable("backend must return a non-empty tuple of strings")

        self.state.transition(record.container_id, record.state, ContainerState.RUNNING)
        environment = dict(self._BASE_ENVIRONMENT)
        environment.update(record.spec.env)
        try:
            process = subprocess.Popen(
                argv,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=environment,
                shell=False,
                start_new_session=True,
                close_fds=True,
            )
        except OSError as exc:
            self.state.transition(
                record.container_id, ContainerState.RUNNING, ContainerState.FAILED
            )
            raise RunError(f"could not launch runtime backend: {exc}") from exc

        assert process.stdout is not None
        assert process.stderr is not None
        stdout = bytearray()
        stderr = bytearray()
        stdout_truncated = [False]
        stderr_truncated = [False]
        readers = (
            threading.Thread(
                target=_drain,
                args=(process.stdout, self.max_output, stdout, stdout_truncated),
                name="minibox-stdout",
                daemon=True,
            ),
            threading.Thread(
                target=_drain,
                args=(process.stderr, self.max_output, stderr, stderr_truncated),
                name="minibox-stderr",
                daemon=True,
            ),
        )
        for reader in readers:
            reader.start()

        timed_out = False
        try:
            process.wait(timeout=self.timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            except OSError:
                process.kill()
            try:
                process.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()

        for reader in readers:
            reader.join(timeout=2.0)
        for reader, stream in zip(readers, (process.stdout, process.stderr)):
            if reader.is_alive():
                stream.close()
                reader.join(timeout=1.0)

        if timed_out:
            self.state.transition(
                record.container_id, ContainerState.RUNNING, ContainerState.FAILED
            )
        else:
            if process.returncode is None:
                raise RunError("payload ended without a return code")
            self.state.transition(
                record.container_id,
                ContainerState.RUNNING,
                ContainerState.EXITED,
                exit_code=process.returncode,
            )

        return RunResult(
            container_id=record.container_id,
            argv=argv,
            returncode=process.returncode,
            stdout=bytes(stdout),
            stderr=bytes(stderr),
            timed_out=timed_out,
            output_truncated=stdout_truncated[0] or stderr_truncated[0],
        )
