"""Bounded, argv-only subprocess execution."""

from __future__ import annotations

import math
import os
import re
import signal
import subprocess
import tempfile
from collections.abc import Mapping as MappingABC
from pathlib import Path
from typing import BinaryIO, Mapping, Sequence

from .errors import InvalidProcess
from .models import ExecutionResult


_ENV_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
_TRUNCATED = b"\n...[truncated]\n"
_MEDIUM_TRUNCATED = b"[trunc]"
_SHORT_TRUNCATED = b"[...]"


class ProcessRunner:
    def __init__(
        self, max_output_bytes: int = 64 * 1024, scratch_dir: Path | None = None
    ) -> None:
        if (
            not isinstance(max_output_bytes, int)
            or isinstance(max_output_bytes, bool)
            or max_output_bytes < 0
        ):
            raise ValueError("max_output_bytes must be a non-negative integer")
        self.max_output_bytes = max_output_bytes
        try:
            self.scratch_dir = None if scratch_dir is None else Path(scratch_dir)
        except TypeError as exc:
            raise ValueError("scratch_dir must be a filesystem path or None") from exc

    @staticmethod
    def _validate(
        argv: Sequence[str], cwd: Path, env: Mapping[str, str] | None, timeout: float
    ) -> tuple[list[str], Path, dict[str, str], float]:
        if isinstance(argv, (str, bytes)):
            raise InvalidProcess("argv must be a sequence of strings")
        arguments = list(argv)
        if not arguments or any(not isinstance(value, str) or "\0" in value for value in arguments):
            raise InvalidProcess("argv must contain NUL-free strings")
        if not arguments[0]:
            raise InvalidProcess("executable argument must not be empty")

        directory = Path(cwd)
        if directory.is_symlink() or not directory.is_dir():
            raise InvalidProcess("process cwd must be a real directory")
        directory = directory.resolve(strict=True)

        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
            raise InvalidProcess("timeout must be a finite positive number")
        timeout_value = float(timeout)
        if not math.isfinite(timeout_value) or timeout_value <= 0:
            raise InvalidProcess("timeout must be a finite positive number")

        if env is not None and not isinstance(env, MappingABC):
            raise InvalidProcess("environment must be a mapping")
        additions = {} if env is None else dict(env)
        for key, value in additions.items():
            if not isinstance(key, str) or not _ENV_NAME.fullmatch(key):
                raise InvalidProcess(f"invalid environment name: {key!r}")
            if not isinstance(value, str) or "\0" in value:
                raise InvalidProcess(f"invalid environment value for {key}")
        child_env = {"LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "PATH": os.defpath}
        child_env.update(additions)
        return arguments, directory, child_env, timeout_value

    @staticmethod
    def _decode_with_budget(data: bytes, budget: int) -> str:
        decoded = data.decode("utf-8", errors="replace")
        result: list[str] = []
        used = 0
        for character in decoded:
            width = len(character.encode("utf-8"))
            if used + width > budget:
                break
            result.append(character)
            used += width
        return "".join(result)

    @staticmethod
    def _truncation_marker(limit: int) -> bytes:
        if limit >= len(_TRUNCATED):
            return _TRUNCATED
        if limit >= len(_MEDIUM_TRUNCATED):
            return _MEDIUM_TRUNCATED
        if limit >= len(_SHORT_TRUNCATED):
            return _SHORT_TRUNCATED
        return b"!" if limit else b""

    def _read_log(self, stream: BinaryIO) -> str:
        stream.seek(0)
        data = stream.read(self.max_output_bytes + 1)
        truncated = len(data) > self.max_output_bytes
        if not truncated:
            text = data.decode("utf-8", errors="replace")
            if len(text.encode("utf-8")) <= self.max_output_bytes:
                return text

        marker = self._truncation_marker(self.max_output_bytes)
        content_budget = self.max_output_bytes - len(marker)
        prefix = self._decode_with_budget(data[:content_budget], content_budget)
        return prefix + marker.decode("ascii")

    def run(
        self,
        argv: Sequence[str],
        cwd: Path,
        env: Mapping[str, str] | None = None,
        timeout: float = 5.0,
    ) -> ExecutionResult:
        arguments, directory, child_env, timeout_value = self._validate(argv, cwd, env, timeout)
        log_directory = directory
        if self.scratch_dir is not None:
            if self.scratch_dir.is_symlink() or not self.scratch_dir.is_dir():
                raise InvalidProcess("scratch_dir must be a real directory")
            log_directory = self.scratch_dir.resolve(strict=True)
        timed_out = False
        with tempfile.TemporaryFile(
            mode="w+b", dir=log_directory
        ) as stdout_file, tempfile.TemporaryFile(mode="w+b", dir=log_directory) as stderr_file:
            process = subprocess.Popen(
                arguments,
                cwd=directory,
                env=child_env,
                stdin=subprocess.DEVNULL,
                stdout=stdout_file,
                stderr=stderr_file,
                shell=False,
                start_new_session=True,
                close_fds=True,
            )
            try:
                process.wait(timeout=timeout_value)
                exit_code = int(process.returncode)
            except subprocess.TimeoutExpired:
                timed_out = True
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait()
                exit_code = 124

            stdout = self._read_log(stdout_file)
            stderr = self._read_log(stderr_file)
        return ExecutionResult(exit_code, stdout, stderr, timed_out)
