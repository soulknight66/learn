from __future__ import annotations

import errno
import hashlib
import json
import math
import os
import re
import shutil
import signal
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

from ..retained_logs import (
    DEFAULT_LAST_MESSAGE_LIMIT_BYTES,
    DEFAULT_STREAM_LIMIT_BYTES,
    BoundedBinaryCapture,
    CaptureError,
    sanitize_retained_file,
    write_redacted_bytes,
)
from ..util import redact
from .base import BackendResult


_PROVIDER_ID = re.compile(r"^[A-Za-z0-9_-]+$")
_PERMISSION_PROFILE_ID = re.compile(r"^[A-Za-z0-9_-]+$")

# These features either expose a hosted/non-profile tool surface or import
# operator-level configuration into a worker. Strict config deliberately turns
# a removed/renamed feature into a hard failure on a future CLI upgrade.
_DISABLED_FEATURES = (
    "apps",
    "auth_elicitation",
    "browser_use",
    "browser_use_external",
    "browser_use_full_cdp_access",
    "computer_use",
    "external_agent_memory_import",
    "goals",
    "hooks",
    "image_generation",
    "in_app_browser",
    "in_app_updates",
    "memories",
    "mentions_v2",
    "multi_agent",
    "multi_agent_v2",
    "network_proxy",
    "plugin_sharing",
    "plugins",
    "remote_plugin",
    "request_permissions_tool",
    "shell_snapshot",
    "skill_mcp_dependency_install",
    "skill_search",
    "standalone_web_search",
    "tool_call_mcp_elicitation",
    "tool_suggest",
    "workspace_dependencies",
)

_BROAD_READ_ROOTS = frozenset(
    Path(path)
    for path in (
        "/",
        "/arm",
        "/arm/tools",
        "/dev",
        "/etc",
        "/home",
        "/mnt",
        "/opt",
        "/proc",
        "/projects",
        "/projects/se",
        "/srv",
        "/sys",
        "/tmp",
        "/var",
    )
)

# Factory operators may expose only narrowly versioned tool installations from
# these public tool roots. Arbitrary absolute paths (for example /etc/ssh or a
# project subtree) are never valid merely because they are not an exact broad
# root name.
_APPROVED_TOOLCHAIN_PREFIXES = tuple(
    Path(path)
    for path in (
        "/arm/tools/python",
        "/arm/tools/git/git",
    )
)
_PROTECTED_READ_PREFIXES = (
    Path("/projects"),
    Path("/arm/projectscratch"),
    Path("/arm/ref"),
    Path("/arm/ip"),
)

_LEAF_WORKER_PREFIX = (
    "You are a leaf execution worker inside a deterministic learning-factory job. "
    "Do not spawn, delegate to, or message other agents. Work directly in the "
    "provided workspace. Once the requested files are complete, stop work and "
    "return a concise final response promptly. The orchestrator, not your response, "
    "will independently validate completion.\n\nJOB:\n"
)


def _provider_id(value: str | None) -> str | None:
    if value is None:
        return None
    rendered = value.strip()
    if not rendered:
        return None
    if not _PROVIDER_ID.fullmatch(rendered):
        raise ValueError("Codex provider id must contain only letters, digits, '-' or '_'")
    return rendered


def _permission_profile_id(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError("Codex permission profile id must be text")
    rendered = value.strip()
    if not rendered or not _PERMISSION_PROFILE_ID.fullmatch(rendered):
        raise ValueError(
            "Codex permission profile id must contain only letters, digits, '-' or '_'"
        )
    return rendered


def _toml_string(value: str) -> str:
    """Render a safe TOML basic string for a Codex `--config` value."""
    return json.dumps(value, ensure_ascii=False)


class ExecBackend:
    """Codex CLI JSONL adapter. Candidate output is still subject to external validation."""

    name = "exec"
    DEFAULT_PROMPT_LIMIT_BYTES = 2 * 1024 * 1024

    def __init__(
        self,
        command: str = "codex",
        timeout_seconds: float = 1800,
        *,
        permission_profile: str = "factory-isolated",
        toolchain_read_roots: tuple[str, ...] = (),
        log_limit_bytes: int = DEFAULT_STREAM_LIMIT_BYTES,
        last_message_limit_bytes: int = DEFAULT_LAST_MESSAGE_LIMIT_BYTES,
        prompt_limit_bytes: int = DEFAULT_PROMPT_LIMIT_BYTES,
        provider: str | None = None,
        base_url: str | None = None,
        provider_name: str | None = None,
        requires_openai_auth: bool = True,
        supports_websockets: bool = False,
    ):
        self.command = command
        self.permission_profile = _permission_profile_id(permission_profile)
        if isinstance(toolchain_read_roots, (str, bytes)):
            raise TypeError("Codex toolchain read roots must be a sequence of paths")
        self.toolchain_read_roots = tuple(toolchain_read_roots)
        self.timeout_seconds = timeout_seconds
        self.log_limit_bytes = log_limit_bytes
        self.last_message_limit_bytes = last_message_limit_bytes
        self.prompt_limit_bytes = prompt_limit_bytes
        self.provider = _provider_id(provider)
        self.base_url = base_url.strip() if base_url else None
        self.provider_name = provider_name.strip() if provider_name else None
        self.requires_openai_auth = requires_openai_auth
        self.supports_websockets = supports_websockets
        self._process: subprocess.Popen[bytes] | None = None
        self._status = "IDLE"

    def start_job(
        self,
        prompt: str,
        workspace: Path,
        log_dir: Path,
        *,
        output_schema: Path | None = None,
        model: str | None = None,
        reasoning_effort: str | None = None,
        timeout_seconds: float | None = None,
        cancel_event: threading.Event | None = None,
    ) -> BackendResult:
        return self._run(
            ["exec"], prompt, workspace, log_dir,
            output_schema=output_schema, model=model, reasoning_effort=reasoning_effort,
            timeout_seconds=timeout_seconds, cancel_event=cancel_event,
        )

    def resume_job(
        self,
        session_id: str,
        prompt: str,
        workspace: Path,
        log_dir: Path,
        **kwargs: Any,
    ) -> BackendResult:
        return self._run(["exec", "resume", session_id], prompt, workspace, log_dir, **kwargs)

    def invocation_manifest(
        self,
        workspace: Path,
        *,
        prompt: str,
        output_schema: Path | None = None,
        model: str | None = None,
        reasoning_effort: str | None = None,
        timeout_seconds: float | None = None,
    ) -> dict[str, Any]:
        """Describe the exact secret-free exec invocation before it is launched.

        The inherited output descriptor is the only process-local value unavailable
        at worker start, so its argv position is represented by a stable placeholder.
        `_run` and this record share `_render_exec_argv`; provenance cannot silently
        drift from the command builder used for execution.
        """

        prompt_record = self.prompt_manifest(prompt)
        executable = self._resolve_command()
        permission_overrides = self._permission_overrides(executable)
        effective_timeout = _positive_timeout(
            timeout_seconds if timeout_seconds is not None else self.timeout_seconds
        )
        argv = self._render_exec_argv(
            str(executable),
            ["exec"],
            workspace,
            output_schema=output_schema,
            model=model,
            reasoning_effort=reasoning_effort,
            last_message_target="<INHERITED_OUTPUT_FD>",
            permission_overrides=permission_overrides,
        )
        return {
            "schema_version": 1,
            "backend": self.name,
            "argv": argv,
            "cwd": str(workspace),
            "stdin": "leaf-worker policy envelope plus job prompt bytes",
            "prompt": prompt_record["effective_prompt"],
            "job_prompt": prompt_record["job_prompt"],
            "leaf_worker_policy": prompt_record["leaf_worker_policy"],
            "timeout_seconds": effective_timeout,
            "model": model,
            "reasoning_effort": reasoning_effort,
            "permission_profile": self.permission_profile,
            "toolchain_read_roots": list(self.toolchain_read_roots),
            "dynamic_placeholders": {
                "<INHERITED_OUTPUT_FD>": (
                    "a write-only inherited descriptor allocated immediately before spawn"
                )
            },
        }

    def prompt_manifest(self, prompt: str) -> dict[str, Any]:
        """Fingerprint the effective stdin envelope without retaining its text."""

        job_prompt = _bounded_prompt(prompt, self.prompt_limit_bytes)
        effective_prompt = self._effective_prompt_bytes(prompt)
        leaf_policy = _LEAF_WORKER_PREFIX.encode("utf-8")
        return {
            "effective_prompt": {
                "sha256": hashlib.sha256(effective_prompt).hexdigest(),
                "utf8_bytes": len(effective_prompt),
                "content_stored": False,
                "includes_leaf_worker_policy": True,
            },
            "job_prompt": {
                "sha256": hashlib.sha256(job_prompt).hexdigest(),
                "utf8_bytes": len(job_prompt),
                "content_stored": False,
            },
            "leaf_worker_policy": {
                "sha256": hashlib.sha256(leaf_policy).hexdigest(),
                "utf8_bytes": len(leaf_policy),
                "content_stored": False,
            },
        }

    def _effective_prompt_bytes(self, prompt: str) -> bytes:
        return _bounded_prompt(
            _LEAF_WORKER_PREFIX + prompt,
            self.prompt_limit_bytes,
        )

    def _run(
        self,
        subcommand: list[str],
        prompt: str,
        workspace: Path,
        log_dir: Path,
        *,
        output_schema: Path | None = None,
        model: str | None = None,
        reasoning_effort: str | None = None,
        timeout_seconds: float | None = None,
        cancel_event: threading.Event | None = None,
    ) -> BackendResult:
        log_dir.mkdir(parents=True, exist_ok=True)
        jsonl_path = log_dir / "codex.jsonl"
        stderr_path = log_dir / "codex.stderr.log"
        last_message_path = log_dir / "codex.last-message.txt"
        is_codex_exec = bool(subcommand) and subcommand[0] == "exec"
        try:
            effective_timeout = _positive_timeout(
                timeout_seconds if timeout_seconds is not None else self.timeout_seconds
            )
            prompt_bytes = (
                self._effective_prompt_bytes(prompt)
                if is_codex_exec
                else _bounded_prompt(prompt, self.prompt_limit_bytes)
            )
            resolved_command = self.command
            permission_overrides: list[str] = []
            if is_codex_exec:
                resolved_command = str(self._resolve_command())
                permission_overrides = self._permission_overrides(
                    Path(resolved_command)
                )
        except (TypeError, ValueError) as error:
            self._status = "FAILED"
            message = f"invalid Codex invocation: {error}"
            write_redacted_bytes(
                stderr_path,
                message.encode("utf-8"),
                max_bytes=self.log_limit_bytes,
            )
            return BackendResult(2, "", stderr_tail=redact(message))

        last_read_fd: int | None = None
        last_write_fd: int | None = None
        argv = [resolved_command, *subcommand]
        if is_codex_exec:
            last_read_fd, last_write_fd = os.pipe()
            argv = self._render_exec_argv(
                resolved_command,
                subcommand,
                workspace,
                output_schema=output_schema,
                model=model,
                reasoning_effort=reasoning_effort,
                last_message_target=f"/proc/self/fd/{last_write_fd}",
                permission_overrides=permission_overrides,
            )
        else:
            argv.append("-")
        started = time.monotonic()
        deadline = started + effective_timeout
        self._status = "RUNNING"
        stdout_capture = BoundedBinaryCapture(self.log_limit_bytes)
        stderr_capture = BoundedBinaryCapture(self.log_limit_bytes)
        last_capture = BoundedBinaryCapture(self.last_message_limit_bytes)
        events = _JsonlEventAccumulator()
        process: subprocess.Popen[bytes] | None = None
        try:
            process = subprocess.Popen(
                argv,
                cwd=workspace,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,
                env=os.environ.copy(),
                pass_fds=(last_write_fd,) if last_write_fd is not None else (),
            )
            self._process = process
        except (OSError, ValueError) as error:
            self._status = "FAILED"
            if last_read_fd is not None:
                os.close(last_read_fd)
            if last_write_fd is not None:
                os.close(last_write_fd)
            message = redact(str(error))
            write_redacted_bytes(
                stderr_path,
                message.encode("utf-8"),
                max_bytes=self.log_limit_bytes,
            )
            return BackendResult(127, "", stderr_tail=message)

        timed_out = False
        cancelled = False
        exit_code = 125
        prompt_writer: _StdinWriter | None = None
        runtime_error: Exception | None = None
        try:
            if last_write_fd is not None:
                os.close(last_write_fd)
                last_write_fd = None
            assert process.stdout is not None
            assert process.stderr is not None
            stdout_capture.start(
                process.stdout, observe=events.feed, name="codex-stdout-capture"
            )
            stderr_capture.start(process.stderr, name="codex-stderr-capture")
            if last_read_fd is not None:
                last_stream = os.fdopen(last_read_fd, "rb", buffering=0)
                last_read_fd = None
                last_capture.start(last_stream, name="codex-last-message-capture")
            assert process.stdin is not None
            writer = _StdinWriter(process.stdin, prompt_bytes)
            writer.start()
            prompt_writer = writer
            while process.poll() is None:
                if cancel_event and cancel_event.wait(0.2):
                    cancelled = True
                    self._stop_process(signal.SIGINT)
                    break
                if time.monotonic() >= deadline:
                    timed_out = True
                    self._stop_process(signal.SIGTERM)
                    break
                time.sleep(0.05)
            exit_code = process.wait()
        except Exception as error:
            runtime_error = error
        finally:
            if last_read_fd is not None:
                os.close(last_read_fd)
                last_read_fd = None
            if last_write_fd is not None:
                os.close(last_write_fd)
                last_write_fd = None
            if prompt_writer is None and process.stdin is not None:
                try:
                    process.stdin.close()
                except OSError:
                    pass
            # A successful CLI parent can still leave inherited-fd descendants.
            # Always reconcile the whole process group before retaining logs.
            _terminate_cli_process_group(process, signal.SIGTERM)
        self._process = None
        capture_errors: list[str] = []
        for capture in (stdout_capture, stderr_capture, last_capture):
            try:
                capture.finish()
            except CaptureError as error:
                capture_errors.append(str(error))
        if prompt_writer is not None:
            try:
                prompt_writer.finish()
            except CaptureError as error:
                capture_errors.append(str(error))
        if runtime_error is not None:
            capture_errors.append(f"Codex process supervision failed: {runtime_error}")
        events.finish()
        stdout_capture.persist_redacted(jsonl_path)
        stderr_text = stderr_capture.persist_redacted(stderr_path)
        final_message = last_capture.persist_redacted(last_message_path)
        if capture_errors:
            diagnostic = "\n".join([stderr_text, *capture_errors]).encode("utf-8")
            stderr_text = write_redacted_bytes(
                stderr_path, diagnostic, max_bytes=self.log_limit_bytes
            )
            if exit_code == 0:
                exit_code = 125
        stderr_tail = stderr_text[-20_000:]
        session_id, usage = events.session_id, events.usage
        self._status = "CANCELLED" if cancelled else "TIMED_OUT" if timed_out else "COMPLETED" if exit_code == 0 else "FAILED"
        return BackendResult(
            exit_code,
            final_message,
            session_id=session_id,
            usage=usage,
            timed_out=timed_out,
            cancelled=cancelled,
            stderr_tail=stderr_tail,
        )

    def _resolve_command(self) -> Path:
        resolved = shutil.which(self.command)
        if resolved is None:
            raise ValueError(
                f"Codex command is not executable or was not found: {self.command}"
            )
        try:
            path = Path(resolved).resolve(strict=True)
        except OSError as error:
            raise ValueError(
                f"Codex command cannot be resolved safely: {self.command}: {error}"
            ) from error
        if not path.is_file() or not os.access(path, os.X_OK):
            raise ValueError(f"Codex command is not an executable file: {path}")
        return path

    def _render_exec_argv(
        self,
        resolved_command: str,
        subcommand: list[str],
        workspace: Path,
        *,
        output_schema: Path | None,
        model: str | None,
        reasoning_effort: str | None,
        last_message_target: str,
        permission_overrides: list[str],
    ) -> list[str]:
        """Build the sole argv used by both execution and start-time provenance."""

        argv = [resolved_command, *subcommand, "--json"]
        if subcommand == ["exec"]:
            argv.extend(["--color", "never", "--cd", str(workspace)])
        argv.extend(
            [
                "--skip-git-repo-check",
                "--ephemeral",
                "--ignore-user-config",
                "--ignore-rules",
                "--strict-config",
                "--config",
                'approval_policy="never"',
            ]
        )
        for override in permission_overrides:
            argv.extend(["--config", override])
        for feature in _DISABLED_FEATURES:
            argv.extend(["--disable", feature])
        if self.provider:
            prefix = f"model_providers.{self.provider}"
            argv.extend(
                ["--config", f'model_provider={_toml_string(self.provider)}']
            )
            argv.extend(
                [
                    "--config",
                    f'{prefix}.name={_toml_string(self.provider_name or self.provider)}',
                ]
            )
            if self.base_url:
                argv.extend(
                    ["--config", f'{prefix}.base_url={_toml_string(self.base_url)}']
                )
            argv.extend(
                [
                    "--config",
                    f"{prefix}.requires_openai_auth={str(self.requires_openai_auth).lower()}",
                    "--config",
                    f"{prefix}.supports_websockets={str(self.supports_websockets).lower()}",
                    "--config",
                    f'{prefix}.wire_api="responses"',
                ]
            )
        elif self.base_url:
            argv.extend(
                ["--config", f'openai_base_url={_toml_string(self.base_url)}']
            )
        if output_schema:
            argv.extend(["--output-schema", str(output_schema)])
        argv.extend(["--output-last-message", last_message_target])
        if model:
            argv.extend(["--model", model])
        if reasoning_effort:
            argv.extend(
                ["--config", f'model_reasoning_effort="{reasoning_effort}"']
            )
        argv.append("-")
        return argv

    def _permission_overrides(self, executable: Path) -> list[str]:
        codex_home = Path(
            os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))
        ).resolve(strict=False)
        read_roots: list[Path] = []
        for raw_root in self.toolchain_read_roots:
            root = Path(raw_root)
            if not root.is_absolute():
                raise ValueError(
                    f"Codex toolchain read root must be absolute: {raw_root}"
                )
            try:
                root = root.resolve(strict=True)
            except OSError as error:
                raise ValueError(
                    f"Codex toolchain read root is unavailable: {raw_root}: {error}"
                ) from error
            if root in _BROAD_READ_ROOTS or root == Path.home().resolve(strict=False):
                raise ValueError(f"Codex toolchain read root is too broad: {root}")
            if not any(
                root == prefix or prefix in root.parents
                for prefix in _APPROVED_TOOLCHAIN_PREFIXES
            ):
                raise ValueError(
                    f"Codex toolchain read root is outside approved tool roots: {root}"
                )
            if any(_is_within(root, prefix) for prefix in _PROTECTED_READ_PREFIXES):
                raise ValueError(
                    f"Codex toolchain read root is in a protected source tree: {root}"
                )
            if _paths_overlap(root, codex_home):
                raise ValueError(
                    f"Codex toolchain read root overlaps protected CODEX_HOME: {root}"
                )
            if not root.is_file() and not root.is_dir():
                raise ValueError(
                    "Codex toolchain read root is not a regular file or directory: "
                    f"{root}"
                )
            if root not in read_roots:
                read_roots.append(root)

        filesystem_rules: list[tuple[str, str]] = [
            (":root", "deny"),
            (":minimal", "read"),
            ("/proc", "deny"),
            (str(codex_home), "deny"),
            (str(executable), "read"),
        ]
        filesystem_rules.extend((str(root), "read") for root in read_roots)
        rendered_rules = ",".join(
            f"{_toml_string(path)}={_toml_string(access)}"
            for path, access in filesystem_rules
        )
        rendered_rules += ',":workspace_roots"={"."="write"}'
        filesystem = "{" + rendered_rules + "}"
        profile = f"permissions.{self.permission_profile}"
        return [
            f"default_permissions={_toml_string(self.permission_profile)}",
            f"{profile}.filesystem={filesystem}",
            f"{profile}.network.enabled=false",
            'shell_environment_policy.inherit="none"',
            "shell_environment_policy.ignore_default_excludes=false",
            "tools.web_search=false",
            "mcp_servers={}",
            "analytics.enabled=false",
        ]

    @staticmethod
    def _sanitize_log(path: Path) -> None:
        if path.exists():
            sanitize_retained_file(path, max_bytes=DEFAULT_STREAM_LIMIT_BYTES)

    def _stop_process(self, first_signal: signal.Signals) -> None:
        process = self._process
        if process is None:
            return
        _terminate_cli_process_group(process, first_signal)

    @staticmethod
    def _parse_events(path: Path) -> tuple[str | None, dict[str, object]]:
        accumulator = _JsonlEventAccumulator()
        if not path.exists():
            return None, {}
        with path.open("rb") as stream:
            while chunk := stream.read(64 * 1024):
                accumulator.feed(chunk)
        accumulator.finish()
        return accumulator.session_id, accumulator.usage

    @staticmethod
    def _find_string(value: object, keys: tuple[str, ...]) -> str | None:
        if isinstance(value, dict):
            for key in keys:
                if isinstance(value.get(key), str):
                    return value[key]
            for nested in value.values():
                found = ExecBackend._find_string(nested, keys)
                if found:
                    return found
        elif isinstance(value, list):
            for nested in value:
                found = ExecBackend._find_string(nested, keys)
                if found:
                    return found
        return None

    def interrupt_job(self) -> None:
        self._stop_process(signal.SIGINT)
        self._status = "INTERRUPTED"

    def get_status(self) -> str:
        return self._status

    def terminate_job(self) -> None:
        self._stop_process(signal.SIGTERM)
        self._status = "TERMINATED"


def _positive_timeout(value: object) -> float:
    if isinstance(value, bool):
        raise TypeError("timeout must be a finite positive number")
    try:
        timeout = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as error:
        raise TypeError("timeout must be a finite positive number") from error
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("timeout must be a finite positive number")
    return timeout


def _paths_overlap(left: Path, right: Path) -> bool:
    try:
        left.relative_to(right)
        return True
    except ValueError:
        pass
    try:
        right.relative_to(left)
        return True
    except ValueError:
        return False


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _bounded_prompt(prompt: object, max_bytes: object) -> bytes:
    if not isinstance(prompt, str):
        raise TypeError("prompt must be text")
    if isinstance(max_bytes, bool) or not isinstance(max_bytes, int) or max_bytes <= 0:
        raise TypeError("prompt_limit_bytes must be a positive integer")
    encoded = prompt.encode("utf-8")
    if len(encoded) > max_bytes:
        raise ValueError(
            f"prompt is {len(encoded)} bytes; limit is {max_bytes} bytes"
        )
    return encoded


class _StdinWriter:
    """Feed stdin off the supervision thread so a full pipe cannot block timeout."""

    def __init__(self, stream: Any, value: bytes):
        self._stream = stream
        self._value = value
        self._error: OSError | None = None
        self._thread = threading.Thread(
            target=self._write, name="codex-stdin-writer", daemon=True
        )

    def start(self) -> None:
        self._thread.start()

    def _write(self) -> None:
        view = memoryview(self._value)
        offset = 0
        try:
            descriptor = self._stream.fileno()
            while offset < len(view):
                offset += os.write(descriptor, view[offset : offset + 64 * 1024])
        except BrokenPipeError:
            pass
        except OSError as error:
            if error.errno not in {errno.EPIPE, errno.EBADF}:
                self._error = error
        finally:
            try:
                self._stream.close()
            except OSError:
                pass

    def finish(self, timeout: float = 2.0) -> None:
        self._thread.join(timeout)
        if self._thread.is_alive():
            raise CaptureError("Codex stdin writer did not stop after process-group cleanup")
        if self._error is not None:
            raise CaptureError(f"Codex stdin writer failed: {self._error}")


class _JsonlEventAccumulator:
    _MAX_LINE_BYTES = 1024 * 1024

    def __init__(self) -> None:
        self.session_id: str | None = None
        self.usage: dict[str, object] = {}
        self._pending = bytearray()
        self._discarding_line = False

    def feed(self, chunk: bytes) -> None:
        self._pending.extend(chunk)
        while True:
            newline = self._pending.find(b"\n")
            if newline < 0:
                break
            line = bytes(self._pending[:newline])
            del self._pending[: newline + 1]
            if not self._discarding_line:
                self._parse_line(line)
            self._discarding_line = False
        if len(self._pending) > self._MAX_LINE_BYTES:
            self._pending.clear()
            self._discarding_line = True

    def finish(self) -> None:
        if self._pending and not self._discarding_line:
            self._parse_line(bytes(self._pending))
        self._pending.clear()

    def _parse_line(self, line: bytes) -> None:
        try:
            event = json.loads(line.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return
        self.session_id = self.session_id or ExecBackend._find_string(
            event, ("thread_id", "session_id")
        )
        if isinstance(event, dict) and isinstance(event.get("usage"), dict):
            self.usage.update(event["usage"])


def _terminate_cli_process_group(
    process: subprocess.Popen[bytes], first_signal: signal.Signals
) -> None:
    process_group = process.pid
    try:
        os.killpg(process_group, first_signal)
    except ProcessLookupError:
        if process.poll() is None:
            try:
                process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                pass
        return
    if process.poll() is None:
        try:
            process.wait(timeout=0.25)
        except subprocess.TimeoutExpired:
            pass
    try:
        _wait_process_group(process_group, 0.25)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process_group, signal.SIGKILL)
        except ProcessLookupError:
            pass
    if process.poll() is None:
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            pass


def _wait_process_group(process_group: int, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            os.killpg(process_group, 0)
        except ProcessLookupError:
            return
        time.sleep(0.02)
    raise subprocess.TimeoutExpired("process-group", timeout)
