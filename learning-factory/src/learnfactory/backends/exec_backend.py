from __future__ import annotations

import errno
import ctypes
import hashlib
import json
import math
import os
import re
import shutil
import signal
import stat
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..sandbox_policy import SandboxRuleManifest, build_sandbox_rule_manifest
from ..retained_logs import (
    DEFAULT_LAST_MESSAGE_LIMIT_BYTES,
    DEFAULT_STREAM_LIMIT_BYTES,
    BoundedBinaryCapture,
    CaptureError,
    sanitize_retained_file,
    write_redacted_bytes,
)
from ..result_channel import (
    RESULT_ALIAS_DIRECTORY,
    RESULT_CHANNEL_ALIAS,
    RESULT_CHANNEL_DIRECTORY,
    RESULT_TRANSPORT_DIRECTORY,
    default_result_transport_root,
    fresh_result_channel,
    lexical_absolute,
    result_channel_contract,
)
from ..util import redact
from .base import BackendResult


_PROVIDER_ID = re.compile(r"^[A-Za-z0-9_-]+$")
_PERMISSION_PROFILE_ID = re.compile(r"^[A-Za-z0-9_-]+$")
_RESULT_FD_PLACEHOLDER = "<controller-result-file-capability>"

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

# CSDIY examiners receive every verified input as a bounded textual projection
# on stdin.  They have no legitimate local tool use.  Keep this list explicit
# so a Codex upgrade that removes or renames one of these capabilities fails
# under --strict-config instead of silently restoring an execution surface.
_NO_TOOL_FEATURES = (
    "artifact",
    "code_mode",
    "code_mode_buffered_exec",
    "code_mode_host",
    "code_mode_only",
    "deferred_executor",
    "executor_capability_discovery",
    "shell_tool",
    "shell_zsh_fork",
    "unified_exec",
    "unified_exec_zsh_fork",
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
        "/arm/tools/adoptopenjdk/openjdk",
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

_LEAF_WORKER_PREAMBLE = (
    "You are a leaf execution worker inside a deterministic learning-factory job. "
    "Do not spawn, delegate to, or message other agents. Work directly in the "
    "provided workspace. Once the requested files are complete, stop work and "
    "return a concise final response promptly. The orchestrator, not your response, "
    "will independently validate completion.\n\n"
)


def _leaf_worker_policy(
    toolchain_read_roots: tuple[str, ...], *, tools_enabled: bool
) -> str:
    toolchain_note = ""
    if tools_enabled and toolchain_read_roots:
        unique_roots: list[str] = []
        seen: set[str] = set()
        for raw_root in toolchain_read_roots:
            root = os.fspath(raw_root)
            if not isinstance(root, str):
                raise TypeError("Codex toolchain read root must resolve to text")
            if root not in seen:
                seen.add(root)
                unique_roots.append(root)
        rendered_roots = "\n".join(
            f"- {json.dumps(root, ensure_ascii=True)}" for root in unique_roots
        )
        toolchain_note = (
            "Configured read-only toolchain roots are available at the exact "
            "JSON-quoted paths below. They are intentionally not added to PATH; "
            "invoke a useful binary by absolute path and record its exact path "
            "and version in validation evidence.\n"
            f"{rendered_roots}\n\n"
        )
    return _LEAF_WORKER_PREAMBLE + toolchain_note + "JOB:\n"


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
        sandbox_manifest: SandboxRuleManifest | None = None,
    ) -> BackendResult:
        return self._run(
            ["exec"], prompt, workspace, log_dir,
            output_schema=output_schema, model=model, reasoning_effort=reasoning_effort,
            timeout_seconds=timeout_seconds, cancel_event=cancel_event,
            sandbox_manifest=sandbox_manifest,
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
        sandbox_manifest: SandboxRuleManifest,
    ) -> dict[str, Any]:
        """Describe the exact secret-free exec invocation before it is launched.

        The randomized private path is never part of this record. Both execution
        and provenance name only the fixed outer-CLI alias, while the manifest
        persists a nonce-free channel contract.
        """

        prompt_record = self.prompt_manifest(
            prompt, tools_enabled=sandbox_manifest.tools_enabled
        )
        executable = self._resolve_command()
        self._validate_sandbox_manifest(workspace, sandbox_manifest)
        permission_overrides = self._permission_overrides(executable, sandbox_manifest)
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
            last_message_target=_RESULT_FD_PLACEHOLDER,
            permission_overrides=permission_overrides,
            tools_enabled=sandbox_manifest.tools_enabled,
        )
        return {
            "schema_version": 1,
            "backend": self.name,
            "argv": argv,
            "cwd": (
                sandbox_manifest.result_alias_directory
                if not sandbox_manifest.tools_enabled
                else str(workspace)
            ),
            "stdin": "leaf-worker policy envelope plus job prompt bytes",
            "prompt": prompt_record["effective_prompt"],
            "job_prompt": prompt_record["job_prompt"],
            "leaf_worker_policy": prompt_record["leaf_worker_policy"],
            "timeout_seconds": effective_timeout,
            "model": model,
            "reasoning_effort": reasoning_effort,
            "permission_profile": self.permission_profile,
            "sandbox_rules": sandbox_manifest.as_dict(),
            "toolchain_read_roots": (
                list(self.toolchain_read_roots)
                if sandbox_manifest.tools_enabled
                else []
            ),
            "result_channel": result_channel_contract(),
            "dynamic_placeholders": {
                _RESULT_FD_PLACEHOLDER: {
                    "kind": "parent-held-fixed-alias-file-descriptor",
                    "runtime_value_stored": False,
                    "descriptor_inherited_by_codex": False,
                    "private_path_exposed": False,
                }
            },
        }

    def prompt_manifest(
        self, prompt: str, *, tools_enabled: bool = True
    ) -> dict[str, Any]:
        """Fingerprint the effective stdin envelope without retaining its text."""

        job_prompt = _bounded_prompt(prompt, self.prompt_limit_bytes)
        effective_prompt = self._effective_prompt_bytes(
            prompt, tools_enabled=tools_enabled
        )
        leaf_policy = _leaf_worker_policy(
            self.toolchain_read_roots, tools_enabled=tools_enabled
        ).encode("utf-8")
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

    def _effective_prompt_bytes(
        self, prompt: str, *, tools_enabled: bool = True
    ) -> bytes:
        return _bounded_prompt(
            _leaf_worker_policy(
                self.toolchain_read_roots, tools_enabled=tools_enabled
            )
            + prompt,
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
        sandbox_manifest: SandboxRuleManifest | None = None,
    ) -> BackendResult:
        owner = _ResultChannelOwner()
        try:
            return self._run_owned(
                subcommand,
                prompt,
                workspace,
                log_dir,
                output_schema=output_schema,
                model=model,
                reasoning_effort=reasoning_effort,
                timeout_seconds=timeout_seconds,
                cancel_event=cancel_event,
                sandbox_manifest=sandbox_manifest,
                result_owner=owner,
            )
        finally:
            owner.cleanup()

    def _run_owned(
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
        sandbox_manifest: SandboxRuleManifest | None = None,
        result_owner: _ResultChannelOwner,
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
            resolved_command = self.command
            permission_overrides: list[str] = []
            if is_codex_exec:
                resolved_command = str(self._resolve_command())
                if sandbox_manifest is None:
                    result_channel = fresh_result_channel(
                        default_result_transport_root(log_dir)
                    )
                    sandbox_manifest = build_sandbox_rule_manifest(
                        workspace=workspace,
                        log_dir=log_dir,
                        worker_type="standalone",
                        payload={},
                        result_channel=result_channel,
                    )
                self._validate_sandbox_manifest(workspace, sandbox_manifest)
                permission_overrides = self._permission_overrides(
                    Path(resolved_command), sandbox_manifest
                )
                prompt_bytes = self._effective_prompt_bytes(
                    prompt, tools_enabled=sandbox_manifest.tools_enabled
                )
            else:
                prompt_bytes = _bounded_prompt(prompt, self.prompt_limit_bytes)
        except (TypeError, ValueError) as error:
            self._status = "FAILED"
            message = f"invalid Codex invocation: {error}"
            write_redacted_bytes(
                stderr_path,
                message.encode("utf-8"),
                max_bytes=self.log_limit_bytes,
            )
            return BackendResult(2, "", stderr_tail=redact(message))

        argv = [resolved_command, *subcommand]
        launch_cwd = workspace
        result_alias: Path | None = None
        result_transport_root: Path | None = None
        result_alias_directory: Path | None = None
        result_alias_binding: tuple[int, int, int, int] | None = None
        result_state: _ResultChannelState | None = None
        if is_codex_exec:
            assert sandbox_manifest is not None
            channel_path = Path(sandbox_manifest.result_channel)
            result_transport_root = channel_path.parent.parent
            result_alias_directory = Path(sandbox_manifest.result_alias_directory)
            try:
                if result_alias_directory != (
                    lexical_absolute(log_dir) / RESULT_ALIAS_DIRECTORY
                ):
                    raise ValueError(
                        "controller result alias is outside the fixed launch namespace"
                    )
                result_state = _prepare_result_channel_state(
                    channel_path,
                    result_alias_directory / RESULT_CHANNEL_ALIAS,
                )
                result_owner.acquire(result_state)
                _recover_stale_result_channels(result_state)
                self._prepare_result_channel(result_state)
            except (OSError, ValueError) as error:
                if result_state is not None:
                    _discard_result_channel(result_state)
                    _discard_empty_result_directories(
                        result_state.transport_root,
                        result_state.alias_directory,
                    )
                    try:
                        result_state.close()
                    except OSError:
                        pass
                    else:
                        result_owner.release(result_state)
                self._status = "FAILED"
                message = "cannot prepare controller result channel: " + _channel_safe_error(
                    error, channel_path
                )
                write_redacted_bytes(
                    stderr_path,
                    message.encode("utf-8"),
                    max_bytes=self.log_limit_bytes,
                )
                return BackendResult(2, "", stderr_tail=redact(message))
            result_alias = result_alias_directory / RESULT_CHANNEL_ALIAS
            try:
                assert result_state is not None
                result_alias_binding = self._prepare_result_alias(result_state)
                output_descriptor = _open_result_output_descriptor(result_state)
            except (OSError, ValueError) as error:
                if result_state is not None:
                    _discard_result_alias(result_state)
                    _discard_result_channel(result_state)
                    _discard_empty_result_directories(
                        result_state.transport_root,
                        result_state.alias_directory,
                    )
                    try:
                        result_state.close()
                    except OSError:
                        pass
                    else:
                        result_owner.release(result_state)
                self._status = "FAILED"
                message = "cannot prepare controller result alias: " + _channel_safe_error(
                    error, channel_path
                )
                write_redacted_bytes(
                    stderr_path,
                    message.encode("utf-8"),
                    max_bytes=self.log_limit_bytes,
                )
                return BackendResult(2, "", stderr_tail=redact(message))
            if not sandbox_manifest.tools_enabled:
                launch_cwd = _held_directory_process_path(
                    result_state.alias_directory
                )
            last_message_target = str(
                _parent_process_descriptor_path(output_descriptor)
            )
            argv = self._render_exec_argv(
                resolved_command,
                subcommand,
                workspace,
                output_schema=output_schema,
                model=model,
                reasoning_effort=reasoning_effort,
                last_message_target=last_message_target,
                permission_overrides=permission_overrides,
                tools_enabled=sandbox_manifest.tools_enabled,
            )
        else:
            argv.append("-")
        if result_state is not None:
            try:
                result_state.park_private_descriptors()
            except (OSError, ValueError) as error:
                try:
                    result_state.close_output_descriptor()
                except OSError:
                    pass
                try:
                    result_state.restore_private_descriptors()
                except (OSError, ValueError):
                    pass
                _discard_result_alias(result_state)
                _discard_result_channel(result_state)
                _discard_empty_result_directories(
                    result_state.transport_root,
                    result_state.alias_directory,
                )
                try:
                    result_state.close()
                except OSError:
                    pass
                else:
                    result_owner.release(result_state)
                self._status = "FAILED"
                message = (
                    "cannot park controller result descriptors: "
                    + _channel_safe_error(error, result_state.channel_path)
                )
                write_redacted_bytes(
                    stderr_path,
                    message.encode("utf-8"),
                    max_bytes=self.log_limit_bytes,
                )
                return BackendResult(2, "", stderr_tail=redact(message))
        started = time.monotonic()
        deadline = started + effective_timeout
        self._status = "RUNNING"
        stdout_capture = BoundedBinaryCapture(self.log_limit_bytes)
        stderr_capture = BoundedBinaryCapture(self.log_limit_bytes)
        events = _JsonlEventAccumulator()
        process: subprocess.Popen[bytes] | None = None
        descendant_reaper: _DescendantReaper | None = None
        try:
            descendant_reaper = _DescendantReaper.install()
            process = subprocess.Popen(
                argv,
                cwd=launch_cwd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,
                env=os.environ.copy(),
            )
            self._process = process
        except (OSError, TypeError, ValueError) as error:
            self._status = "FAILED"
            restoration_error: OSError | None = None
            if descendant_reaper is not None:
                try:
                    descendant_reaper.close()
                except OSError as close_error:
                    restoration_error = close_error
            if result_state is not None:
                try:
                    result_state.close_output_descriptor()
                except OSError:
                    pass
                try:
                    result_state.restore_private_descriptors()
                except (OSError, ValueError):
                    pass
                _discard_result_alias(result_state)
                _discard_result_channel(result_state)
                if result_transport_root is not None and result_alias_directory is not None:
                    _discard_empty_result_directories(
                        result_state.transport_root,
                        result_state.alias_directory,
                    )
                try:
                    result_state.close()
                except OSError:
                    pass
                else:
                    result_owner.release(result_state)
            message = redact(str(error))
            if restoration_error is not None:
                message += (
                    "; child-subreaper restoration also failed: "
                    + redact(str(restoration_error), 500)
                )
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
            assert process.stdout is not None
            assert process.stderr is not None
            stdout_capture.start(
                process.stdout, observe=events.feed, name="codex-stdout-capture"
            )
            stderr_capture.start(process.stderr, name="codex-stderr-capture")
            assert process.stdin is not None
            writer = _StdinWriter(process.stdin, prompt_bytes)
            writer.start()
            prompt_writer = writer
            while process.poll() is None:
                # Detached grandchildren are adopted by this worker as the
                # subreaper. Collect exited adoptees throughout a long Codex
                # run so they cannot accumulate as zombies. The Popen-owned
                # primary is explicitly excluded; only Popen may consume its
                # wait status.
                descendant_reaper.reap_exited_descendants(
                    primary_pid=process.pid
                )
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
            if prompt_writer is None and process.stdin is not None:
                try:
                    process.stdin.close()
                except OSError:
                    pass
            # A successful CLI parent can still leave detached descendants.
            # Always reconcile the process tree before accepting its result.
            try:
                _terminate_cli_process_group(process, signal.SIGTERM)
            except (OSError, subprocess.TimeoutExpired) as error:
                runtime_error = runtime_error or error
            primary_reaped = process.poll() is not None
            if descendant_reaper is not None:
                if not primary_reaped:
                    # Never let the generic descendant waitpid path consume
                    # the Popen primary's status. Keep subreaper containment
                    # installed when primary termination could not be proved.
                    runtime_error = runtime_error or subprocess.TimeoutExpired(
                        "primary Codex process", 0, output=str(process.pid)
                    )
                else:
                    try:
                        descendant_reaper.terminate_new_descendants()
                    except (OSError, subprocess.TimeoutExpired) as error:
                        runtime_error = runtime_error or error
                    finally:
                        try:
                            descendant_reaper.close(primary_process=process)
                        except (OSError, subprocess.TimeoutExpired) as error:
                            runtime_error = runtime_error or error
        self._process = None
        capture_errors: list[str] = []
        if result_state is not None:
            try:
                result_state.close_output_descriptor()
            except OSError as error:
                capture_errors.append(
                    "controller result output capability cleanup failed: "
                    + _channel_safe_error(error, result_state.channel_path)
                )
        for capture in (stdout_capture, stderr_capture):
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
        final_bytes = b""
        if result_state is not None:
            channel = Path(sandbox_manifest.result_channel)
            try:
                result_state.restore_private_descriptors()
                if result_alias is not None:
                    if result_alias_binding is None:
                        raise ValueError("controller result alias binding is missing")
                    self._remove_result_alias(
                        result_state, result_alias_binding
                    )
                if result_alias_binding is None:
                    raise ValueError("controller result channel binding is missing")
                final_bytes = self._read_result_channel(
                    result_state, result_alias_binding
                )
            except (OSError, ValueError) as error:
                capture_errors.append(
                    "controller result channel is invalid: "
                    + _channel_safe_error(error, channel)
                )
            finally:
                try:
                    _remove_result_channel(result_state)
                    if (
                        result_transport_root is not None
                        and result_alias_directory is not None
                    ):
                        _discard_empty_result_directories(
                            result_state.transport_root,
                            result_state.alias_directory,
                        )
                except OSError as error:
                    capture_errors.append(
                        "controller result channel cleanup failed: "
                        + _channel_safe_error(error, channel)
                    )
                except ValueError as error:
                    capture_errors.append(
                        "controller result channel cleanup failed: "
                        + _channel_safe_error(error, channel)
                    )
                finally:
                    try:
                        result_state.close()
                    except OSError as error:
                        capture_errors.append(
                            "controller result channel descriptor cleanup failed: "
                            + _channel_safe_error(error, channel)
                        )
                    else:
                        result_owner.release(result_state)
        final_message = write_redacted_bytes(
            last_message_path,
            final_bytes,
            max_bytes=self.last_message_limit_bytes,
        )
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
        tools_enabled: bool,
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
        disabled_features = (
            (*_DISABLED_FEATURES, *_NO_TOOL_FEATURES)
            if not tools_enabled
            else _DISABLED_FEATURES
        )
        for feature in dict.fromkeys(disabled_features):
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

    def _permission_overrides(
        self, executable: Path, sandbox_manifest: SandboxRuleManifest
    ) -> list[str]:
        codex_home = Path(
            os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))
        ).resolve(strict=False)
        read_roots: list[Path] = []
        configured_read_roots = (
            self.toolchain_read_roots if sandbox_manifest.tools_enabled else ()
        )
        for raw_root in configured_read_roots:
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

        filesystem_rules: list[tuple[str, str]] = [(":root", "deny")]
        if sandbox_manifest.tools_enabled:
            filesystem_rules.extend(
                [
                    (":minimal", "read"),
                    ("/proc", "deny"),
                    (str(codex_home), "deny"),
                    (str(executable), "read"),
                ]
            )
        else:
            # No inner command may run for a prompt-only examiner.  These
            # explicit denies remain defense in depth for any unexpected
            # always-on read/view capability.
            filesystem_rules.extend(
                [("/proc", "deny"), (str(codex_home), "deny")]
            )
        filesystem_rules.extend((str(root), "read") for root in read_roots)
        filesystem_rules.extend(
            (rule.path, rule.access) for rule in sandbox_manifest.rules
        )
        rendered_rules = ",".join(
            f"{_toml_string(path)}={_toml_string(access)}"
            for path, access in filesystem_rules
        )
        rendered_rules += (
            ',":workspace_roots"={"."='
            + _toml_string(sandbox_manifest.workspace_access)
            + "}"
        )
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
    def _validate_sandbox_manifest(
        workspace: Path, manifest: SandboxRuleManifest
    ) -> None:
        if manifest.schema_version != 1:
            raise ValueError("unsupported sandbox rule manifest")
        if str(lexical_absolute(workspace)) != manifest.workspace:
            raise ValueError("sandbox manifest workspace does not match invocation")
        if manifest.workspace_access not in {"deny", "read", "write"}:
            raise ValueError("invalid sandbox workspace access")
        if not manifest.result_channel:
            raise ValueError("sandbox manifest has no controller result channel")
        if not manifest.result_alias_directory:
            raise ValueError("sandbox manifest has no fixed result alias directory")
        if not isinstance(manifest.tools_enabled, bool):
            raise ValueError("sandbox tools_enabled must be boolean")
        if not manifest.tools_enabled and (
            manifest.workspace_access != "deny" or manifest.rules
        ):
            raise ValueError("no-tool sandbox must deny an empty workspace")
        result_path = Path(manifest.result_channel)
        result_root = result_path.parent.parent
        alias_directory = Path(manifest.result_alias_directory)
        if (
            not result_path.is_absolute()
            or result_path != lexical_absolute(result_path)
            or not RESULT_CHANNEL_DIRECTORY.fullmatch(result_path.parent.name)
            or result_path.name != "result.json"
            or result_root.parts.count(RESULT_TRANSPORT_DIRECTORY) != 1
            or result_root.name == RESULT_TRANSPORT_DIRECTORY
        ):
            raise ValueError("controller result channel has an invalid private topology")
        if (
            not alias_directory.is_absolute()
            or alias_directory != lexical_absolute(alias_directory)
            or alias_directory.name != RESULT_ALIAS_DIRECTORY
        ):
            raise ValueError("controller result alias has an invalid launch topology")
        if _paths_overlap(Path(manifest.workspace), result_root):
            raise ValueError("controller result channel overlaps worker workspace")
        if _paths_overlap(alias_directory, result_root):
            raise ValueError("controller result transport overlaps fixed launch namespace")
        for rule in manifest.rules:
            rule_path = Path(rule.path)
            if (
                rule.access not in {"read", "write"}
                or not rule_path.is_absolute()
                or rule_path != lexical_absolute(rule_path)
            ):
                raise ValueError("sandbox rules must be absolute read/write paths")
            if _paths_overlap(rule_path, result_root):
                raise ValueError("controller result channel may not enter inner sandbox rules")

    @staticmethod
    def _prepare_result_channel(state: _ResultChannelState) -> None:
        path = state.channel_path
        if (
            path.name != "result.json"
            or not RESULT_CHANNEL_DIRECTORY.fullmatch(path.parent.name)
            or path.parent.parent != state.transport_root.path
            or state.channel_directory is not None
            or state.result_binding is not None
        ):
            raise ValueError("controller result channel has an invalid private name")
        channel_directory = _open_or_create_private_child(
            state.transport_root, path.parent.name, require_absent=True
        )
        state.channel_directory = channel_directory
        channel_directory.verify()
        with os.scandir(channel_directory.fileno()) as entries:
            if next(iter(entries), None) is not None:
                raise ValueError("controller result channel namespace is not empty")
        channel_directory.verify()
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(
            path.name, flags | os.O_CLOEXEC, 0o600,
            dir_fd=channel_directory.fileno(),
        )
        try:
            info = os.fstat(descriptor)
            if (
                not stat.S_ISREG(info.st_mode)
                or stat.S_IMODE(info.st_mode) != 0o600
                or info.st_nlink != 1
                or info.st_uid != os.getuid()
            ):
                raise ValueError("controller result channel is not a fresh regular file")
            os.fchmod(descriptor, 0o600)
            info = os.fstat(descriptor)
            named = os.stat(
                path.name,
                dir_fd=channel_directory.fileno(),
                follow_symlinks=False,
            )
            if (
                _result_inode_binding(info) != _result_inode_binding(named)
                or info.st_nlink != 1
                or named.st_nlink != 1
            ):
                raise ValueError("controller result channel raced during creation")
            state.result_binding = _result_inode_binding(info)
        finally:
            os.close(descriptor)
        channel_directory.verify()

    @staticmethod
    def _prepare_result_alias(
        state: _ResultChannelState,
    ) -> tuple[int, int, int, int]:
        channel = state.channel_path
        alias = state.alias_path
        if (
            alias.name != RESULT_CHANNEL_ALIAS
            or alias.parent.name != RESULT_ALIAS_DIRECTORY
            or _paths_overlap(alias.parent, channel.parent.parent)
            or state.channel_directory is None
            or state.result_binding is None
            or state.alias_active
        ):
            raise ValueError("controller result alias is outside its fixed contract")
        channel_directory = state.channel_directory
        alias_directory = state.alias_directory
        alias_created = False
        try:
            channel_directory.verify()
            alias_directory.verify()
            alias_entries: list[str] = []
            with os.scandir(alias_directory.fileno()) as entries:
                for entry in entries:
                    alias_entries.append(entry.name)
                    if len(alias_entries) > 1:
                        break
            if alias_entries:
                raise ValueError(
                    "controller result launch namespace is not empty"
                )
            channel_info = os.stat(
                channel.name,
                dir_fd=channel_directory.fileno(),
                follow_symlinks=False,
            )
            binding = _result_inode_binding(channel_info)
            if (
                binding != state.result_binding
                or not stat.S_ISREG(channel_info.st_mode)
                or stat.S_IMODE(channel_info.st_mode) != 0o600
                or channel_info.st_uid != os.getuid()
                or channel_info.st_nlink != 1
            ):
                raise ValueError("controller result channel is not private and unaliased")
            try:
                os.stat(
                    alias.name,
                    dir_fd=alias_directory.fileno(),
                    follow_symlinks=False,
                )
            except FileNotFoundError:
                pass
            else:
                raise ValueError("controller result alias already exists")
            channel_directory.verify()
            alias_directory.verify()
            os.link(
                channel.name,
                alias.name,
                src_dir_fd=channel_directory.fileno(),
                dst_dir_fd=alias_directory.fileno(),
                follow_symlinks=False,
            )
            alias_created = True
            state.alias_active = True
            channel_after = os.stat(
                channel.name,
                dir_fd=channel_directory.fileno(),
                follow_symlinks=False,
            )
            alias_info = os.stat(
                alias.name,
                dir_fd=alias_directory.fileno(),
                follow_symlinks=False,
            )
            if (
                _result_inode_binding(channel_after) != binding
                or _result_inode_binding(alias_info) != binding
                or channel_after.st_nlink != 2
                or alias_info.st_nlink != 2
            ):
                raise ValueError("controller result alias did not bind the channel inode")
            channel_directory.verify()
            alias_directory.verify()
            return binding
        except BaseException:
            if alias_created:
                try:
                    _discard_result_alias(state)
                except (OSError, ValueError):
                    pass
            raise

    @staticmethod
    def _remove_result_alias(
        state: _ResultChannelState,
        binding: tuple[int, int, int, int],
    ) -> None:
        if (
            state.result_binding != binding
            or not state.alias_active
            or state.output_descriptor is not None
        ):
            raise ValueError("controller result alias binding is missing")
        channel_directory = state.channel_directory
        if channel_directory is None:
            raise ValueError("controller result channel descriptor is missing")
        alias_directory = state.alias_directory
        channel_directory.verify()
        alias_directory.verify()
        alias_entries: list[str] = []
        with os.scandir(alias_directory.fileno()) as entries:
            for entry in entries:
                alias_entries.append(entry.name)
                if len(alias_entries) > 1:
                    break
        if alias_entries != [state.alias_path.name]:
            raise ValueError(
                "controller result launch namespace changed during execution"
            )
        channel_info = os.stat(
            state.channel_path.name,
            dir_fd=channel_directory.fileno(),
            follow_symlinks=False,
        )
        alias_info = os.stat(
            state.alias_path.name,
            dir_fd=alias_directory.fileno(),
            follow_symlinks=False,
        )
        if (
            _result_inode_binding(channel_info) != binding
            or _result_inode_binding(alias_info) != binding
            or channel_info.st_nlink != 2
            or alias_info.st_nlink != 2
        ):
            raise ValueError("controller result alias changed during execution")
        channel_directory.verify()
        alias_directory.verify()
        channel_confirm = os.stat(
            state.channel_path.name,
            dir_fd=channel_directory.fileno(),
            follow_symlinks=False,
        )
        alias_confirm = os.stat(
            state.alias_path.name,
            dir_fd=alias_directory.fileno(),
            follow_symlinks=False,
        )
        if (
            _result_inode_binding(channel_confirm) != binding
            or _result_inode_binding(alias_confirm) != binding
            or channel_confirm.st_nlink != 2
            or alias_confirm.st_nlink != 2
        ):
            raise ValueError("controller result alias raced before removal")
        os.unlink(state.alias_path.name, dir_fd=alias_directory.fileno())
        state.alias_active = False
        try:
            os.stat(
                state.alias_path.name,
                dir_fd=alias_directory.fileno(),
                follow_symlinks=False,
            )
        except FileNotFoundError:
            pass
        else:
            raise ValueError("controller result alias survived removal")
        with os.scandir(alias_directory.fileno()) as entries:
            if next(iter(entries), None) is not None:
                raise ValueError(
                    "controller result launch namespace did not become empty"
                )
        channel_after = os.stat(
            state.channel_path.name,
            dir_fd=channel_directory.fileno(),
            follow_symlinks=False,
        )
        if (
            _result_inode_binding(channel_after) != binding
            or channel_after.st_nlink != 1
        ):
            raise ValueError("controller result channel did not become unaliased")
        channel_directory.verify()
        alias_directory.verify()

    def _read_result_channel(
        self,
        state: _ResultChannelState,
        expected_binding: tuple[int, int, int, int],
    ) -> bytes:
        path = state.channel_path
        parent = state.channel_directory
        if parent is None or state.result_binding != expected_binding:
            raise ValueError("controller result channel binding is missing")
        parent.verify()
        names: list[str] = []
        with os.scandir(parent.fileno()) as entries:
            for entry in entries:
                names.append(entry.name)
                if len(names) > 1:
                    break
        if names != [path.name]:
            raise ValueError(
                "controller result channel contains unexpected entries"
            )
        before = os.stat(
            path.name,
            dir_fd=parent.fileno(),
            follow_symlinks=False,
        )
        if (
            not stat.S_ISREG(before.st_mode)
            or stat.S_IMODE(before.st_mode) != 0o600
            or before.st_uid != os.getuid()
            or before.st_nlink != 1
        ):
            raise ValueError(
                "controller result channel changed type or link count"
            )
        if before.st_size > self.last_message_limit_bytes:
            raise ValueError("controller result exceeds retained-message limit")
        flags = os.O_RDONLY | os.O_CLOEXEC
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(path.name, flags, dir_fd=parent.fileno())
        try:
            opened = os.fstat(descriptor)
            binding = _result_inode_binding(before)
            if (
                binding != expected_binding
                or _result_inode_binding(opened) != expected_binding
                or opened.st_nlink != 1
                or not stat.S_ISREG(opened.st_mode)
                or opened.st_size > self.last_message_limit_bytes
            ):
                raise ValueError("controller result channel raced during capture")
            value = bytearray()
            while len(value) <= self.last_message_limit_bytes:
                chunk = os.read(
                    descriptor,
                    self.last_message_limit_bytes + 1 - len(value),
                )
                if not chunk:
                    break
                value.extend(chunk)
            after = os.fstat(descriptor)
            if (
                _result_inode_binding(after) != binding
                or after.st_nlink != 1
                or after.st_size != opened.st_size
                or after.st_mtime_ns != opened.st_mtime_ns
                or after.st_ctime_ns != opened.st_ctime_ns
            ):
                raise ValueError("controller result channel changed during capture")
            if len(value) > self.last_message_limit_bytes:
                raise ValueError("controller result exceeds retained-message limit")
            parent.verify()
            return bytes(value)
        finally:
            os.close(descriptor)

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


class _DescendantReaper:
    """Contain CLI descendants that escape the original process group.

    A worker runs one backend subprocess at a time. On Linux it temporarily
    becomes a child subreaper, so ``setsid`` and double-fork descendants are
    reparented here when the CLI tree is terminated and can be killed/reaped
    before its result channel is trusted.
    """

    _PR_SET_CHILD_SUBREAPER = 36
    _PR_GET_CHILD_SUBREAPER = 37

    def __init__(self, previous: int, baseline: frozenset[int]):
        self._previous = previous
        self._baseline = baseline
        self._closed = False

    @classmethod
    def install(cls) -> _DescendantReaper:
        if not sys.platform.startswith("linux"):
            raise OSError("detached-descendant containment requires Linux subreaper support")
        libc = ctypes.CDLL(None, use_errno=True)
        previous = ctypes.c_int()
        if libc.prctl(cls._PR_GET_CHILD_SUBREAPER, ctypes.byref(previous), 0, 0, 0) != 0:
            error = ctypes.get_errno()
            raise OSError(error, os.strerror(error))
        baseline = frozenset(_direct_child_pids())
        if baseline:
            raise OSError(
                "Codex backend requires an otherwise childless worker process"
            )
        if libc.prctl(cls._PR_SET_CHILD_SUBREAPER, 1, 0, 0, 0) != 0:
            error = ctypes.get_errno()
            raise OSError(error, os.strerror(error))
        return cls(previous.value, baseline)

    def reap_exited_descendants(self, *, primary_pid: int) -> None:
        """Collect exited adoptees without consuming the primary's status."""

        self._new_children(excluded_pid=primary_pid)

    def terminate_new_descendants(self) -> None:
        self._signal_until_quiet(signal.SIGTERM, timeout=0.25)
        self._signal_until_quiet(signal.SIGKILL, timeout=1.0)
        survivors = self._new_children()
        if survivors:
            raise subprocess.TimeoutExpired(
                "detached Codex descendants", 1.25, output=str(sorted(survivors))
            )

    def _signal_until_quiet(
        self,
        value: signal.Signals,
        *,
        timeout: float,
    ) -> None:
        deadline = time.monotonic() + timeout
        while True:
            children = self._new_children()
            if not children:
                return
            for pid in children:
                try:
                    os.kill(pid, value)
                except ProcessLookupError:
                    pass
            for pid in children:
                try:
                    os.waitpid(pid, os.WNOHANG)
                except ChildProcessError:
                    pass
            if time.monotonic() >= deadline:
                return
            time.sleep(0.02)

    def _new_children(self, *, excluded_pid: int | None = None) -> set[int]:
        children = _direct_child_pids() - set(self._baseline)
        if excluded_pid is not None:
            # subprocess.Popen owns this wait status. Exclude the primary
            # before any waitpid call, including if it exits immediately after
            # poll(). Terminal cleanup has already reaped it and excludes no
            # PID, so a rapidly reused number cannot hide an adopted survivor.
            children.discard(excluded_pid)
        alive: set[int] = set()
        for pid in children:
            try:
                waited, _status = os.waitpid(pid, os.WNOHANG)
            except ChildProcessError:
                continue
            if waited == 0:
                alive.add(pid)
        return alive

    def close(
        self,
        *,
        primary_process: subprocess.Popen[bytes] | None = None,
    ) -> None:
        if self._closed:
            return
        if primary_process is not None and primary_process.poll() is None:
            # Restoration would hand a still-live detached tree back to the
            # system reaper. Popen retains exclusive ownership of this wait
            # status; keep subreaper containment installed and fail closed.
            raise subprocess.TimeoutExpired(
                "primary Codex process", 0, output=str(primary_process.pid)
            )
        self._closed = True
        libc = ctypes.CDLL(None, use_errno=True)
        if libc.prctl(
            self._PR_SET_CHILD_SUBREAPER, self._previous, 0, 0, 0
        ) != 0:
            error = ctypes.get_errno()
            raise OSError(error, os.strerror(error))


def _direct_child_pids() -> set[int]:
    path = Path(f"/proc/{os.getpid()}/task/{os.getpid()}/children")
    try:
        rendered = path.read_text(encoding="ascii").strip()
    except (FileNotFoundError, PermissionError) as error:
        raise OSError("cannot enumerate worker child processes") from error
    if not rendered:
        return set()
    try:
        return {int(value) for value in rendered.split()}
    except ValueError as error:
        raise OSError("kernel child-process inventory is malformed") from error


def _channel_safe_error(error: BaseException, channel: Path) -> str:
    """Render an error without persisting a private channel path or nonce."""

    rendered = str(error)
    private_values: set[str] = {
        str(channel),
        str(channel.parent),
        str(channel.parent.parent),
        channel.parent.name,
    }
    transport_root = channel.parent.parent
    bases = [
        candidate
        for candidate in (transport_root, *transport_root.parents)
        if candidate.name == RESULT_TRANSPORT_DIRECTORY
    ]
    if len(bases) == 1:
        base = bases[0]
        if base.parent.name.startswith(".learnfactory-controller-"):
            private_values.add(str(base.parent))
            private_values.add(base.parent.name)
        current = transport_root
        while True:
            private_values.add(str(current))
            if current != base:
                private_values.add(current.name)
            if current == base:
                break
            current = current.parent
    nonce = channel.parent.name.removeprefix(".codex-final-")
    private_values.add(nonce)
    for value in tuple(private_values):
        if value:
            private_values.add(hashlib.sha256(value.encode("utf-8")).hexdigest())
    for value in sorted(private_values, key=len, reverse=True):
        if value:
            rendered = rendered.replace(value, "<controller-result-channel>")
    rendered = re.sub(
        r"\.codex-final-[A-Za-z0-9_.-]+",
        "<controller-result-channel>",
        rendered,
    )
    return redact(rendered, 2_000)


def _controller_transport_base(path: Path) -> Path:
    matches = [
        candidate
        for candidate in (path, *path.parents)
        if candidate.name == RESULT_TRANSPORT_DIRECTORY
    ]
    if len(matches) != 1 or path == matches[0]:
        raise ValueError("invalid controller result transport root")
    return matches[0]


_DirectoryBinding = tuple[int, int, int, int, int]
_ResultBinding = tuple[int, int, int, int]


def _directory_binding(value: os.stat_result) -> _DirectoryBinding:
    return (
        int(value.st_dev),
        int(value.st_ino),
        int(value.st_mode),
        int(value.st_uid),
        int(value.st_nlink),
    )


def _directory_open_flags() -> int:
    if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY"):
        raise ValueError("safe controller directory operations are unavailable")
    return os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NOFOLLOW


def _validate_directory_info(
    value: os.stat_result, *, private: bool, message: str
) -> None:
    if not stat.S_ISDIR(value.st_mode) or value.st_nlink < 1:
        raise ValueError(message)
    if private and (
        stat.S_IMODE(value.st_mode) not in {0o700, stat.S_ISGID | 0o700}
        or value.st_uid != os.getuid()
    ):
        raise ValueError(message)


@dataclass
class _HeldDirectory:
    """A directory capability whose optional parent is also kept open.

    Paths are diagnostic metadata only. All namespace access and mutation uses
    ``descriptor`` or the retained parent descriptor.
    """

    path: Path
    descriptor: int | None
    binding: _DirectoryBinding
    private: bool
    strict_links: bool = True
    parent: _HeldDirectory | None = None
    name: str | None = None

    def fileno(self) -> int:
        if self.descriptor is None:
            raise ValueError("controller result directory descriptor is closed")
        return self.descriptor

    def verify(self, *, entry: bool = True) -> os.stat_result:
        descriptor = self.fileno()
        current = os.fstat(descriptor)
        _validate_directory_info(
            current,
            private=self.private,
            message="controller result directory changed",
        )
        current_binding = _directory_binding(current)
        if (
            current_binding[:4] != self.binding[:4]
            or (self.strict_links and current_binding[4] != self.binding[4])
        ):
            raise ValueError("controller result directory binding changed")
        if entry and self.parent is not None:
            self.parent.verify()
            assert self.name is not None
            named = os.stat(
                self.name,
                dir_fd=self.parent.fileno(),
                follow_symlinks=False,
            )
            named_binding = _directory_binding(named)
            if (
                named_binding[:4] != self.binding[:4]
                or (self.strict_links and named_binding[4] != self.binding[4])
            ):
                raise ValueError("controller result directory entry changed")
        return current

    def refresh_after_child_change(self, expected_links: int) -> None:
        current = os.fstat(self.fileno())
        _validate_directory_info(
            current,
            private=self.private,
            message="controller result directory changed during mutation",
        )
        prior_identity = self.binding[:4]
        current_binding = _directory_binding(current)
        if current_binding[:4] != prior_identity:
            raise ValueError("controller result directory raced during mutation")
        if current.st_nlink != expected_links:
            raise ValueError("controller result directory link count raced")
        self.binding = current_binding
        if self.parent is not None:
            assert self.name is not None
            named = os.stat(
                self.name,
                dir_fd=self.parent.fileno(),
                follow_symlinks=False,
            )
            named_binding = _directory_binding(named)
            if (
                named_binding[:4] != self.binding[:4]
                or (self.strict_links and named_binding[4] != self.binding[4])
            ):
                raise ValueError("controller result directory entry raced")

    def close_self(self) -> None:
        descriptor = self.descriptor
        self.descriptor = None
        if descriptor is not None:
            os.close(descriptor)

    def reopen(self) -> None:
        if self.descriptor is not None:
            self.verify()
            return
        if self.parent is None or self.name is None:
            raise ValueError("controller result anchor descriptor was lost")
        self.parent.reopen()
        self.parent.verify()
        before = os.stat(
            self.name,
            dir_fd=self.parent.fileno(),
            follow_symlinks=False,
        )
        before_binding = _directory_binding(before)
        if (
            before_binding[:4] != self.binding[:4]
            or (self.strict_links and before_binding[4] != self.binding[4])
        ):
            raise ValueError("controller result directory changed while parked")
        descriptor = os.open(
            self.name,
            _directory_open_flags(),
            dir_fd=self.parent.fileno(),
        )
        try:
            opened = os.fstat(descriptor)
            after = os.stat(
                self.name,
                dir_fd=self.parent.fileno(),
                follow_symlinks=False,
            )
            opened_binding = _directory_binding(opened)
            if not (
                opened_binding
                == _directory_binding(before)
                == _directory_binding(after)
            ) or (
                opened_binding[:4] != self.binding[:4]
                or (self.strict_links and opened_binding[4] != self.binding[4])
            ):
                raise ValueError("controller result directory raced while restoring")
            _validate_directory_info(
                opened,
                private=self.private,
                message="controller result directory changed while parked",
            )
            if not self.strict_links:
                self.binding = opened_binding
            self.descriptor = descriptor
        except BaseException:
            os.close(descriptor)
            raise

    def close_chain(self) -> None:
        error: OSError | None = None
        current: _HeldDirectory | None = self
        while current is not None:
            parent = current.parent
            current.parent = None
            try:
                current.close_self()
            except OSError as close_error:
                error = error or close_error
            current = parent
        if error is not None:
            raise error


def _validate_path_for_descriptor_walk(path: Path) -> Path:
    normalized = lexical_absolute(path)
    if not path.is_absolute() or path != normalized:
        raise ValueError("controller directory path must be normalized and absolute")
    return normalized


def _open_nofollow_directory(path: Path) -> int:
    """Open an absolute directory one component at a time without symlinks."""

    normalized = _validate_path_for_descriptor_walk(path)
    flags = _directory_open_flags()
    descriptor = os.open("/", flags)
    try:
        current = os.fstat(descriptor)
        _validate_directory_info(
            current, private=False, message="controller directory anchor changed"
        )
        for component in normalized.parts[1:]:
            before_parent = _directory_binding(os.fstat(descriptor))
            before = os.stat(
                component, dir_fd=descriptor, follow_symlinks=False
            )
            child = os.open(component, flags, dir_fd=descriptor)
            try:
                opened = os.fstat(child)
                after = os.stat(
                    component, dir_fd=descriptor, follow_symlinks=False
                )
                if (
                    _directory_binding(os.fstat(descriptor)) != before_parent
                    or _directory_binding(before) != _directory_binding(opened)
                    or _directory_binding(after) != _directory_binding(opened)
                ):
                    raise ValueError(
                        "controller directory changed during component walk"
                    )
                _validate_directory_info(
                    opened,
                    private=False,
                    message="controller path component is not a directory",
                )
            except BaseException:
                os.close(child)
                raise
            previous = descriptor
            descriptor = child
            os.close(previous)
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _open_existing_anchor(path: Path, *, private: bool) -> _HeldDirectory:
    descriptor = _open_nofollow_directory(path)
    try:
        info = os.fstat(descriptor)
        _validate_directory_info(
            info,
            private=private,
            message="controller result directory is not private",
        )
        return _HeldDirectory(
            path=path,
            descriptor=descriptor,
            binding=_directory_binding(info),
            private=private,
            strict_links=False,
        )
    except BaseException:
        os.close(descriptor)
        raise


def _open_or_create_private_child(
    parent: _HeldDirectory,
    name: str,
    *,
    require_absent: bool = False,
) -> _HeldDirectory:
    if not name or name in {".", ".."} or "/" in name:
        raise ValueError("invalid controller result directory component")
    parent.verify()
    parent_links = parent.binding[4]
    try:
        existing = os.stat(name, dir_fd=parent.fileno(), follow_symlinks=False)
    except FileNotFoundError:
        parent.verify()
        try:
            os.mkdir(name, mode=0o700, dir_fd=parent.fileno())
        except FileExistsError as error:
            raise ValueError(
                "controller result directory raced during creation"
            ) from error
        parent.refresh_after_child_change(parent_links + 1)
    else:
        if require_absent:
            raise ValueError("controller result directory already exists")
        _validate_directory_info(
            existing,
            private=True,
            message="controller result directory is not private",
        )
    parent.verify()
    before = os.stat(name, dir_fd=parent.fileno(), follow_symlinks=False)
    descriptor = os.open(name, _directory_open_flags(), dir_fd=parent.fileno())
    try:
        opened = os.fstat(descriptor)
        after = os.stat(name, dir_fd=parent.fileno(), follow_symlinks=False)
        _validate_directory_info(
            opened,
            private=True,
            message="controller result directory is not private",
        )
        if not (
            _directory_binding(before)
            == _directory_binding(opened)
            == _directory_binding(after)
        ):
            raise ValueError("controller result directory raced while opening")
        child = _HeldDirectory(
            path=parent.path / name,
            descriptor=descriptor,
            binding=_directory_binding(opened),
            private=True,
            parent=parent,
            name=name,
        )
        child.verify()
        return child
    except BaseException:
        os.close(descriptor)
        # A newly-created directory is deliberately retained on uncertainty.
        # The caller can only remove it after obtaining a bound descriptor.
        raise


def _detach_private_anchor(directory: _HeldDirectory) -> _HeldDirectory:
    """Make an opened private directory the stable root of a held subtree."""

    directory.verify()
    parent = directory.parent
    directory.parent = None
    directory.name = None
    directory.strict_links = False
    if parent is not None:
        try:
            parent.close_chain()
        except BaseException:
            directory.close_self()
            raise
    return directory


def _prepare_result_transport_root(path: Path) -> _HeldDirectory:
    """Create and hold the exact controller-owned recovery namespace."""

    path = _validate_path_for_descriptor_walk(path)
    base = _controller_transport_base(path)
    container = base.parent
    if container.name.startswith(".learnfactory-controller-"):
        container_parent = _open_existing_anchor(container.parent, private=False)
        try:
            container_handle = _open_or_create_private_child(
                container_parent, container.name
            )
        except BaseException:
            container_parent.close_chain()
            raise
        container_handle = _detach_private_anchor(container_handle)
    else:
        container_handle = _open_existing_anchor(container, private=False)
    try:
        base_handle = _open_or_create_private_child(container_handle, base.name)
    except BaseException:
        container_handle.close_chain()
        raise
    base_handle = _detach_private_anchor(base_handle)
    current = base_handle
    try:
        for component in path.relative_to(base).parts:
            current = _open_or_create_private_child(current, component)
        current.strict_links = True
        ancestor = current.parent
        while ancestor is not None:
            ancestor.strict_links = False
            ancestor = ancestor.parent
        current.verify()
        return current
    except BaseException:
        current.close_chain()
        raise


def _prepare_result_alias_directory(path: Path) -> _HeldDirectory:
    """Create and hold the disclosed fixed launch namespace."""

    path = _validate_path_for_descriptor_walk(path)
    if path.name != RESULT_ALIAS_DIRECTORY:
        raise ValueError("controller result alias directory has an invalid name")
    parent = _open_existing_anchor(path.parent, private=False)
    try:
        return _open_or_create_private_child(parent, path.name)
    except BaseException:
        parent.close_chain()
        raise


def _remove_empty_bound_directory(directory: _HeldDirectory) -> None:
    """Remove an empty bound directory through its retained parent only."""

    directory.verify()
    if directory.parent is None or directory.name is None:
        raise ValueError("controller result directory has no retained parent")
    parent = directory.parent
    with os.scandir(directory.fileno()) as entries:
        if next(iter(entries), None) is not None:
            raise OSError(errno.ENOTEMPTY, "controller result directory is not empty")
    target_binding = directory.binding
    parent.verify()
    named = os.stat(
        directory.name, dir_fd=parent.fileno(), follow_symlinks=False
    )
    if _directory_binding(named) != target_binding:
        raise ValueError("controller result directory changed before removal")
    parent_links = parent.binding[4]
    directory.close_self()
    parent.verify()
    named = os.stat(
        directory.name, dir_fd=parent.fileno(), follow_symlinks=False
    )
    if _directory_binding(named) != target_binding:
        raise ValueError("controller result directory changed before removal")
    os.rmdir(directory.name, dir_fd=parent.fileno())
    try:
        os.stat(directory.name, dir_fd=parent.fileno(), follow_symlinks=False)
    except FileNotFoundError:
        pass
    else:
        raise ValueError("controller result directory survived removal")
    parent.refresh_after_child_change(parent_links - 1)


def _discard_empty_result_directories(
    transport_root: _HeldDirectory | None,
    alias_directory: _HeldDirectory | None,
) -> None:
    """Best-effort descriptor-relative removal of exact empty leaf roots."""

    for directory in (transport_root, alias_directory):
        if directory is None or directory.descriptor is None:
            continue
        try:
            _remove_empty_bound_directory(directory)
        except (OSError, ValueError):
            # A non-empty or uncertain namespace is retained as evidence.
            pass


@dataclass
class _ResultChannelState:
    channel_path: Path
    alias_path: Path
    transport_root: _HeldDirectory
    alias_directory: _HeldDirectory
    channel_directory: _HeldDirectory | None = None
    result_binding: _ResultBinding | None = None
    alias_active: bool = False
    output_descriptor: int | None = None

    def close_output_descriptor(self) -> None:
        descriptor = self.output_descriptor
        self.output_descriptor = None
        if descriptor is not None:
            os.close(descriptor)

    def park_private_descriptors(self) -> None:
        """Hide nonce-bearing descriptor paths while the outer CLI executes."""

        if self.channel_directory is not None:
            self.channel_directory.close_self()
        current = self.transport_root
        while current.parent is not None:
            current.close_self()
            current = current.parent
        current.verify()

    def restore_private_descriptors(self) -> None:
        self.transport_root.reopen()
        if self.channel_directory is not None:
            self.channel_directory.reopen()

    def close(self) -> None:
        error: OSError | None = None
        try:
            self.close_output_descriptor()
        except OSError as close_error:
            error = close_error
        if self.channel_directory is not None:
            try:
                self.channel_directory.close_self()
            except OSError as close_error:
                error = error or close_error
        for directory in (self.transport_root, self.alias_directory):
            try:
                directory.close_chain()
            except OSError as close_error:
                error = error or close_error
        if error is not None:
            raise error


def _parent_process_descriptor_path(descriptor: int) -> Path:
    if descriptor <= 2:
        raise ValueError("controller result capability descriptor is invalid")
    return Path(f"/proc/{os.getpid()}/fd/{descriptor}")


def _open_result_output_descriptor(state: _ResultChannelState) -> int:
    """Hold the fixed alias inode read-only for outer-CLI output by procfd."""

    if (
        not state.alias_active
        or state.result_binding is None
        or state.channel_directory is None
        or state.output_descriptor is not None
    ):
        raise ValueError("controller result output capability is not ready")
    state.channel_directory.verify()
    state.alias_directory.verify()
    alias_info = os.stat(
        state.alias_path.name,
        dir_fd=state.alias_directory.fileno(),
        follow_symlinks=False,
    )
    channel_info = os.stat(
        state.channel_path.name,
        dir_fd=state.channel_directory.fileno(),
        follow_symlinks=False,
    )
    if (
        _result_inode_binding(alias_info) != state.result_binding
        or _result_inode_binding(channel_info) != state.result_binding
        or alias_info.st_nlink != 2
        or channel_info.st_nlink != 2
        or not stat.S_ISREG(alias_info.st_mode)
        or stat.S_IMODE(alias_info.st_mode) != 0o600
        or alias_info.st_uid != os.getuid()
    ):
        raise ValueError("controller result output capability changed")
    flags = os.O_RDONLY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(
        state.alias_path.name,
        flags,
        dir_fd=state.alias_directory.fileno(),
    )
    try:
        opened = os.fstat(descriptor)
        capability = _parent_process_descriptor_path(descriptor)
        through_proc = capability.stat()
        if (
            _result_inode_binding(opened) != state.result_binding
            or _result_inode_binding(through_proc) != state.result_binding
            or opened.st_nlink != 2
            or through_proc.st_nlink != 2
            or os.get_inheritable(descriptor)
        ):
            raise ValueError("controller result output capability raced")
        state.output_descriptor = descriptor
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _held_directory_process_path(directory: _HeldDirectory) -> Path:
    """Name a held cwd capability through the controller's procfd table."""

    directory.verify()
    capability = _parent_process_descriptor_path(directory.fileno())
    info = capability.stat()
    if _directory_binding(info) != directory.binding:
        raise ValueError("controller result launch capability changed")
    return capability


class _ResultChannelOwner:
    """Idempotent whole-lifetime cleanup for one prepared result channel."""

    def __init__(self) -> None:
        self._state: _ResultChannelState | None = None

    def acquire(self, state: _ResultChannelState) -> None:
        if self._state is not None:
            raise ValueError("controller result owner already has a state")
        self._state = state

    def release(self, state: _ResultChannelState) -> None:
        if self._state is state:
            self._state = None

    def cleanup(self) -> None:
        state = self._state
        self._state = None
        if state is None:
            return
        try:
            try:
                state.close_output_descriptor()
            except OSError:
                pass
            try:
                state.restore_private_descriptors()
            except (OSError, ValueError):
                pass
            _discard_result_alias(state)
            _discard_result_channel(state)
            _discard_empty_result_directories(
                state.transport_root, state.alias_directory
            )
        finally:
            try:
                state.close()
            except (OSError, ValueError):
                pass


def _prepare_result_channel_state(
    channel_path: Path, alias_path: Path
) -> _ResultChannelState:
    transport: _HeldDirectory | None = None
    alias: _HeldDirectory | None = None
    try:
        transport = _prepare_result_transport_root(channel_path.parent.parent)
        alias = _prepare_result_alias_directory(alias_path.parent)
        return _ResultChannelState(channel_path, alias_path, transport, alias)
    except BaseException:
        _discard_empty_result_directories(transport, alias)
        for directory in (transport, alias):
            if directory is not None:
                try:
                    directory.close_chain()
                except OSError:
                    pass
        raise


@dataclass
class _RecoveryCandidate:
    name: str
    directory: _HeldDirectory
    result_binding: _ResultBinding | None
    result_links: int | None

    def close(self) -> None:
        """Relinquish ownership before close so an exception cannot double-close."""

        self.directory.close_self()


def _open_existing_private_child(
    parent: _HeldDirectory, name: str
) -> _HeldDirectory:
    parent.verify()
    before = os.stat(name, dir_fd=parent.fileno(), follow_symlinks=False)
    _validate_directory_info(
        before,
        private=True,
        message="controller result directory is not private",
    )
    descriptor = os.open(name, _directory_open_flags(), dir_fd=parent.fileno())
    try:
        opened = os.fstat(descriptor)
        after = os.stat(name, dir_fd=parent.fileno(), follow_symlinks=False)
        if not (
            _directory_binding(before)
            == _directory_binding(opened)
            == _directory_binding(after)
        ):
            raise ValueError("controller result directory raced while opening")
        child = _HeldDirectory(
            path=parent.path / name,
            descriptor=descriptor,
            binding=_directory_binding(opened),
            private=True,
            parent=parent,
            name=name,
        )
        child.verify()
        return child
    except BaseException:
        os.close(descriptor)
        raise


def _recover_stale_result_channels(state: _ResultChannelState) -> None:
    """Remove only exact crash-leftover private-channel structures.

    A malformed alias or directory is never guessed at or recursively removed.
    Recovery scans exactly one attempt root and its fixed launch directory, so
    an active channel belonging to another job or attempt is never a target.
    """

    transport = state.transport_root
    alias_directory = state.alias_directory
    candidates: list[_RecoveryCandidate] = []
    try:
        transport.verify()
        alias_directory.verify()
        alias_names: list[str] = []
        with os.scandir(alias_directory.fileno()) as entries:
            for entry in entries:
                alias_names.append(entry.name)
                if (
                    len(alias_names) > 1
                    or entry.name != RESULT_CHANNEL_ALIAS
                ):
                    raise ValueError(
                        "fixed controller launch directory has an unexpected entry"
                    )
        alias_info: os.stat_result | None
        try:
            alias_info = os.stat(
                RESULT_CHANNEL_ALIAS,
                dir_fd=alias_directory.fileno(),
                follow_symlinks=False,
            )
        except FileNotFoundError:
            alias_info = None
        if alias_info is not None and (
            not stat.S_ISREG(alias_info.st_mode)
            or stat.S_IMODE(alias_info.st_mode) != 0o600
            or alias_info.st_uid != os.getuid()
            or alias_info.st_nlink != 2
        ):
            raise ValueError("stale controller result alias is not recoverable")

        scanned = 0
        with os.scandir(transport.fileno()) as entries:
            for entry in entries:
                scanned += 1
                if scanned > 10_000:
                    raise ValueError("result transport root exceeds recovery scan limit")
                name = entry.name
                if not name.startswith(".codex-final-"):
                    continue
                # Production capabilities use a 256-bit random token. Similar
                # human-owned names are outside the recovery namespace and
                # must never become cleanup targets.
                if not RESULT_CHANNEL_DIRECTORY.fullmatch(name):
                    continue
                if len(candidates) >= 128:
                    raise ValueError("too many stale controller result channels")
                directory_info = os.stat(
                    name, dir_fd=transport.fileno(), follow_symlinks=False
                )
                _validate_directory_info(
                    directory_info,
                    private=True,
                    message="stale controller result directory is not recoverable",
                )
                if directory_info.st_nlink != 2:
                    raise ValueError(
                        "stale controller result directory is not recoverable"
                    )
                directory = _open_existing_private_child(transport, name)
                try:
                    contents: list[str] = []
                    with os.scandir(directory.fileno()) as children:
                        for child in children:
                            if contents:
                                raise ValueError(
                                    "stale controller result directory has extra entries"
                                )
                            contents.append(child.name)
                    if not contents:
                        candidates.append(
                            _RecoveryCandidate(
                                name=name,
                                directory=directory,
                                result_binding=None,
                                result_links=None,
                            )
                        )
                        directory = None
                        continue
                    if contents != ["result.json"]:
                        raise ValueError(
                            "stale controller result directory has an unexpected entry"
                        )
                    result_info = os.stat(
                        "result.json",
                        dir_fd=directory.fileno(),
                        follow_symlinks=False,
                    )
                    if (
                        not stat.S_ISREG(result_info.st_mode)
                        or stat.S_IMODE(result_info.st_mode) != 0o600
                        or result_info.st_uid != os.getuid()
                        or result_info.st_nlink not in {1, 2}
                    ):
                        raise ValueError(
                            "stale controller result file is not recoverable"
                        )
                    candidates.append(
                        _RecoveryCandidate(
                            name=name,
                            directory=directory,
                            result_binding=_result_inode_binding(result_info),
                            result_links=int(result_info.st_nlink),
                        )
                    )
                    directory = None
                finally:
                    if directory is not None:
                        directory.close_self()

        alias_binding = (
            _result_inode_binding(alias_info) if alias_info is not None else None
        )
        matching = [
            item for item in candidates if item.result_binding == alias_binding
        ] if alias_binding is not None else []
        if alias_binding is not None and len(matching) != 1:
            raise ValueError("stale controller result alias binding is ambiguous")
        transport.verify()
        alias_directory.verify()
        for candidate in candidates:
            candidate.directory.verify()
            if candidate.result_binding is None:
                continue
            current = os.stat(
                "result.json",
                dir_fd=candidate.directory.fileno(),
                follow_symlinks=False,
            )
            if (
                _result_inode_binding(current) != candidate.result_binding
                or current.st_nlink != candidate.result_links
            ):
                raise ValueError("stale controller result file changed")
        for candidate in candidates:
            directory = candidate.directory
            binding = candidate.result_binding
            if binding is not None:
                directory.verify()
                current = os.stat(
                    "result.json",
                    dir_fd=directory.fileno(),
                    follow_symlinks=False,
                )
                if (
                    _result_inode_binding(current) != binding
                    or current.st_nlink != candidate.result_links
                ):
                    raise ValueError("stale controller result file changed")
                if binding == alias_binding:
                    if current.st_nlink != 2:
                        raise ValueError("stale controller result link count changed")
                    alias_directory.verify()
                    current_alias = os.stat(
                        RESULT_CHANNEL_ALIAS,
                        dir_fd=alias_directory.fileno(),
                        follow_symlinks=False,
                    )
                    if (
                        _result_inode_binding(current_alias) != binding
                        or current_alias.st_nlink != 2
                    ):
                        raise ValueError("stale controller result alias changed")
                    os.unlink(
                        RESULT_CHANNEL_ALIAS,
                        dir_fd=alias_directory.fileno(),
                    )
                    try:
                        os.stat(
                            RESULT_CHANNEL_ALIAS,
                            dir_fd=alias_directory.fileno(),
                            follow_symlinks=False,
                        )
                    except FileNotFoundError:
                        pass
                    else:
                        raise ValueError("stale controller result alias survived")
                    current = os.stat(
                        "result.json",
                        dir_fd=directory.fileno(),
                        follow_symlinks=False,
                    )
                if current.st_nlink != 1:
                    raise ValueError(
                        "stale controller result has an external hard-link alias"
                    )
                directory.verify()
                confirmed = os.stat(
                    "result.json",
                    dir_fd=directory.fileno(),
                    follow_symlinks=False,
                )
                if (
                    _result_inode_binding(confirmed) != binding
                    or confirmed.st_nlink != 1
                ):
                    raise ValueError("stale controller result file raced")
                os.unlink("result.json", dir_fd=directory.fileno())
                try:
                    os.stat(
                        "result.json",
                        dir_fd=directory.fileno(),
                        follow_symlinks=False,
                    )
                except FileNotFoundError:
                    pass
                else:
                    raise ValueError("stale controller result file survived")
        for candidate in candidates:
            _remove_empty_bound_directory(candidate.directory)
        try:
            os.stat(
                RESULT_CHANNEL_ALIAS,
                dir_fd=alias_directory.fileno(),
                follow_symlinks=False,
            )
        except FileNotFoundError:
            pass
        else:
            raise ValueError("stale controller result alias survived recovery")
    except BaseException as error:
        for candidate in candidates:
            try:
                candidate.close()
            except OSError:
                pass
        if isinstance(error, ValueError):
            raise
        raise ValueError("stale controller result recovery failed") from error


def _remove_result_channel(state: _ResultChannelState) -> None:
    if state.alias_active:
        raise ValueError("controller result alias is still active")
    directory = state.channel_directory
    if directory is None:
        return
    directory.verify()
    if state.result_binding is not None:
        current = os.stat(
            state.channel_path.name,
            dir_fd=directory.fileno(),
            follow_symlinks=False,
        )
        if (
            _result_inode_binding(current) != state.result_binding
            or not stat.S_ISREG(current.st_mode)
            or stat.S_IMODE(current.st_mode) != 0o600
            or current.st_uid != os.getuid()
            or current.st_nlink != 1
        ):
            raise ValueError("controller result channel changed before removal")
        directory.verify()
        confirmed = os.stat(
            state.channel_path.name,
            dir_fd=directory.fileno(),
            follow_symlinks=False,
        )
        if (
            _result_inode_binding(confirmed) != state.result_binding
            or confirmed.st_nlink != 1
        ):
            raise ValueError("controller result channel raced before removal")
        os.unlink(state.channel_path.name, dir_fd=directory.fileno())
        try:
            os.stat(
                state.channel_path.name,
                dir_fd=directory.fileno(),
                follow_symlinks=False,
            )
        except FileNotFoundError:
            state.result_binding = None
        else:
            raise ValueError("controller result channel survived removal")
    _remove_empty_bound_directory(directory)


def _discard_result_channel(state: _ResultChannelState) -> None:
    try:
        _remove_result_channel(state)
    except (OSError, ValueError):
        # The caller already reports the primary spawn/capture failure. Unknown
        # entries are deliberately not recursively deleted.
        pass


def _result_inode_binding(value: os.stat_result) -> tuple[int, int, int, int]:
    return (
        int(value.st_dev),
        int(value.st_ino),
        int(value.st_mode),
        int(value.st_uid),
    )


def _discard_result_alias(state: _ResultChannelState) -> None:
    if not state.alias_active or state.result_binding is None:
        return
    try:
        ExecBackend._remove_result_alias(state, state.result_binding)
    except (OSError, ValueError):
        # A mismatched alias is evidence, not a cleanup target.
        pass


def _terminate_cli_process_group(
    process: subprocess.Popen[bytes], first_signal: signal.Signals
) -> None:
    process_group = process.pid
    try:
        try:
            os.killpg(process_group, first_signal)
        except ProcessLookupError:
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
    finally:
        # Group signaling can fail independently (for example with EPERM).
        # Always make a Popen-owned attempt to terminate and reap the primary;
        # if it succeeds, Python re-raises the original group error unchanged.
        _terminate_and_reap_cli_primary(process)


def _terminate_and_reap_cli_primary(process: subprocess.Popen[bytes]) -> None:
    """Leave the Popen-owned primary neither live nor unreaped."""

    if process.poll() is not None:
        return
    try:
        process.wait(timeout=2)
        return
    except subprocess.TimeoutExpired:
        try:
            process.kill()
        except ProcessLookupError:
            pass
    # Do not swallow this timeout. Live-loop descendant reconciliation excludes
    # this PID so only Popen consumes its status, and the no-exclusion terminal
    # scan is unsafe until that ownership has reached a terminal state.
    process.wait(timeout=2)


def _wait_process_group(process_group: int, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            os.killpg(process_group, 0)
        except ProcessLookupError:
            return
        time.sleep(0.02)
    raise subprocess.TimeoutExpired("process-group", timeout)
