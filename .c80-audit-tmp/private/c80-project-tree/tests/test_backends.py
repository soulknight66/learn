from __future__ import annotations

import errno
import hashlib
import json
import math
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from dataclasses import replace
from pathlib import Path
from unittest import mock

from learnfactory.backends.exec_backend import (
    ExecBackend,
    _DescendantReaper,
    _ResultChannelState,
    _discard_empty_result_directories,
    _open_nofollow_directory,
    _open_result_output_descriptor,
    _prepare_result_channel_state,
    _recover_stale_result_channels,
    _remove_result_channel,
)
from learnfactory.config import load_settings
from learnfactory.retained_logs import BoundedBinaryCapture
from learnfactory.result_channel import (
    RESULT_ALIAS_DIRECTORY,
    RESULT_CHANNEL_ALIAS,
    RESULT_TRANSPORT_DIRECTORY,
    default_result_transport_root,
    result_channel_contract,
)
from learnfactory.sandbox_policy import build_sandbox_rule_manifest
from learnfactory.workspace import WorkspaceError


ROOT = Path(__file__).resolve().parents[1]


def _private_result_channel(
    root: Path, namespace: str, nonce_seed: str = "current"
) -> Path:
    transport = default_result_transport_root(root / namespace)
    nonce = hashlib.sha256(nonce_seed.encode("utf-8")).hexdigest()
    return transport / (".codex-final-" + nonce) / "result.json"


def _scoped_result_channel(
    root: Path, namespace: str, nonce_seed: str = "current"
) -> tuple[Path, Path]:
    """Return a worker-shaped channel and its swappable outer container."""

    container = root / ("controller-" + namespace)
    container.mkdir()
    job = hashlib.sha256(namespace.encode("utf-8")).hexdigest()
    nonce = hashlib.sha256(nonce_seed.encode("utf-8")).hexdigest()
    channel = (
        container
        / RESULT_TRANSPORT_DIRECTORY
        / job
        / "attempt-001"
        / (".codex-final-" + nonce)
        / "result.json"
    )
    return channel, container


def _result_alias(logs: Path) -> Path:
    return logs / RESULT_ALIAS_DIRECTORY / RESULT_CHANNEL_ALIAS


def _prepared_result_state(
    backend: ExecBackend, channel: Path, alias: Path
) -> _ResultChannelState:
    state = _prepare_result_channel_state(channel, alias)
    backend._prepare_result_channel(state)
    return state


def _clean_result_state(
    backend: ExecBackend,
    state: _ResultChannelState,
    binding: tuple[int, int, int, int] | None = None,
) -> None:
    if state.alias_active:
        expected = binding if binding is not None else state.result_binding
        if expected is None:
            raise AssertionError("active result alias has no binding")
        backend._remove_result_alias(
            state, expected
        )
    _remove_result_channel(state)
    _discard_empty_result_directories(
        state.transport_root, state.alias_directory
    )
    state.close()


class ExecBackendTests(unittest.TestCase):
    def test_csdiy_examiner_manifest_is_no_tool_no_mount_and_no_channel_rule(self) -> None:
        with tempfile.TemporaryDirectory(prefix="learnfactory-examiner-manifest-") as raw:
            root = Path(raw)
            workspace = root / "workspace"
            logs = root / "logs"
            workspace.mkdir()
            manifest = build_sandbox_rule_manifest(
                workspace=workspace,
                log_dir=logs,
                worker_type="examiner",
                payload={
                    "seed_policy": {
                        "kind": "csdiy_course_progression",
                        "role": "examiner_revision",
                    },
                    "artifact_type": "independent-course-unit-evaluation",
                    "inputs_from_dependencies": [
                        {
                            "job_id": "job-material",
                            "subpath": "examiner_only/RUBRIC.md",
                            "destination": "RUBRIC.md",
                            "prompt_context": True,
                        },
                        {
                            "job_id": "job-student",
                            "student_submission_root": True,
                            "destination": "STUDENT_SUBMISSION",
                        },
                    ],
                },
                result_channel=_private_result_channel(root, "manifest", "first"),
            )

            self.assertEqual("deny", manifest.workspace_access)
            self.assertFalse(manifest.tools_enabled)
            self.assertEqual((), manifest.staged_inputs)
            self.assertEqual((), manifest.declared_outputs)
            self.assertNotIn("RUBRIC.md", json.dumps(manifest.as_dict()))
            self.assertNotIn(
                Path(manifest.result_channel).parent.name,
                json.dumps(manifest.as_dict()),
            )
            self.assertEqual(
                result_channel_contract(),
                manifest.as_dict()["result_channel"],
            )
            self.assertEqual((), manifest.rules)
            self.assertNotIn(str(logs), json.dumps([r.as_dict() for r in manifest.rules]))
            durable_manifest = json.dumps(manifest.as_dict(), sort_keys=True)
            private_channel = Path(manifest.result_channel)
            private_nonce = private_channel.parent.name.removeprefix(
                ".codex-final-"
            )
            for forbidden in (
                str(private_channel),
                str(private_channel.parent.parent),
                private_channel.parent.name,
                private_nonce,
                hashlib.sha256(str(private_channel).encode()).hexdigest(),
                hashlib.sha256(private_nonce.encode()).hexdigest(),
            ):
                self.assertNotIn(forbidden, durable_manifest)
            alternate = build_sandbox_rule_manifest(
                workspace=workspace,
                log_dir=logs,
                worker_type="examiner",
                payload={
                    "seed_policy": {
                        "kind": "csdiy_course_progression",
                        "role": "examiner_revision",
                    },
                    "artifact_type": "independent-course-unit-evaluation",
                    "inputs_from_dependencies": [
                        {
                            "job_id": "job-material",
                            "subpath": "examiner_only/RUBRIC.md",
                            "destination": "RUBRIC.md",
                            "prompt_context": True,
                        },
                        {
                            "job_id": "job-student",
                            "student_submission_root": True,
                            "destination": "STUDENT_SUBMISSION",
                        },
                    ],
                },
                result_channel=_private_result_channel(root, "manifest", "second"),
            )
            self.assertNotEqual(manifest.result_channel, alternate.result_channel)
            self.assertEqual(manifest.as_dict(), alternate.as_dict())

    def test_sandbox_manifest_rejects_disclosed_or_overlapping_transport(self) -> None:
        with tempfile.TemporaryDirectory(prefix="learnfactory-result-policy-") as raw:
            root = Path(raw)
            workspace = root / "workspace"
            logs = root / "logs"
            workspace.mkdir()
            nonce = ".codex-final-" + "a1" * 32
            for transport in (
                logs / RESULT_TRANSPORT_DIRECTORY / "attempt-001",
                workspace / RESULT_TRANSPORT_DIRECTORY / "attempt-001",
            ):
                with self.subTest(transport=transport):
                    with self.assertRaisesRegex(
                        WorkspaceError, "transport root"
                    ):
                        build_sandbox_rule_manifest(
                            workspace=workspace,
                            log_dir=logs,
                            worker_type="student",
                            payload={},
                            result_channel=transport / nonce / "result.json",
                        )

            valid = build_sandbox_rule_manifest(
                workspace=workspace,
                log_dir=logs,
                worker_type="student",
                payload={},
                result_channel=_private_result_channel(root, "policy", "valid"),
            )
            forged = replace(
                valid,
                result_alias_directory=str(
                    Path(valid.result_channel).parent.parent
                    / RESULT_ALIAS_DIRECTORY
                ),
            )
            with self.assertRaisesRegex(ValueError, "transport overlaps"):
                ExecBackend._validate_sandbox_manifest(workspace, forged)
            private = Path(valid.result_channel)
            traversing = replace(
                valid,
                result_channel=str(
                    private.parent.parent
                    / "discarded"
                    / ".."
                    / private.parent.name
                    / private.name
                ),
            )
            with self.assertRaisesRegex(ValueError, "invalid private topology"):
                ExecBackend._validate_sandbox_manifest(workspace, traversing)

    def test_no_tool_examiner_hides_channel_from_proc_and_outer_cli_writes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="learnfactory-no-tool-proc-") as raw:
            root = Path(raw)
            workspace = root / "workspace"
            logs = root / "logs"
            workspace.mkdir()
            executable = root / "fake-codex"
            scanner = root / "scanner.py"
            scanner.write_text(
                """import glob, hashlib, json, os, pathlib, re, sys
pattern = re.compile(rb'\\.codex-final-([0-9a-f]{64})')
matches = []
derived = []
def inspect(value):
    for match in pattern.finditer(value):
        raw = match.group(0)
        matches.append(raw.decode('ascii'))
        derived.extend((hashlib.sha256(raw).hexdigest(), hashlib.sha256(match.group(1)).hexdigest()))
for process in glob.glob('/proc/[0-9]*'):
    for name in ('cmdline', 'environ'):
        try:
            value = open(process + '/' + name, 'rb').read()
        except OSError:
            continue
        inspect(value)
    for descriptor in glob.glob(process + '/fd/*'):
        try:
            value = os.readlink(descriptor).encode('utf-8', 'surrogateescape')
        except OSError:
            continue
        inspect(value)
    for name in ('cwd', 'root'):
        try:
            value = os.readlink(process + '/' + name).encode('utf-8', 'surrogateescape')
        except OSError:
            continue
        inspect(value)
cwd = pathlib.Path.cwd()
ancestors = []
for index, candidate in enumerate((cwd, *cwd.parents)):
    try:
        names = sorted(item.name for item in candidate.iterdir())
    except OSError:
        names = []
    rendered = str(candidate)
    inspect(rendered.encode())
    inspect('\\0'.join(names).encode())
    ancestors.append({
        'path': rendered,
        'entry_count': len(names),
        'entries': names if index < 3 else [],
    })
inspect('\\0'.join(sys.argv).encode())
for key, value in os.environ.items():
    inspect((key + '=' + value).encode('utf-8', 'surrogateescape'))
print(json.dumps({'matches': matches, 'derived': derived, 'ancestors': ancestors}))
""",
                encoding="utf-8",
            )
            executable.write_text(
                "#!/usr/bin/env python3\n"
                "import json,pathlib,subprocess,sys\n"
                f"scan=subprocess.run([sys.executable,{str(scanner)!r}],"
                "capture_output=True,text=True,check=True)\n"
                "target=pathlib.Path(sys.argv[sys.argv.index('--output-last-message')+1]).absolute()\n"
                "payload=json.dumps({'proc_matches':json.loads(scan.stdout)})\n"
                "print(payload)\n"
                "print(payload,file=sys.stderr)\n"
                "target.write_text(payload)\n",
                encoding="utf-8",
            )
            executable.chmod(0o755)
            channel = _private_result_channel(root, "proc", "proc-secret-unit")
            manifest = build_sandbox_rule_manifest(
                workspace=workspace,
                log_dir=logs,
                worker_type="examiner",
                payload={
                    "seed_policy": {
                        "kind": "csdiy_course_cohort",
                        "role": "examiner",
                    },
                    "artifact_type": "independent-course-evaluation",
                },
                result_channel=channel,
            )
            backend = ExecBackend(str(executable), timeout_seconds=5)
            invocation = backend.invocation_manifest(
                workspace,
                prompt="static input only",
                sandbox_manifest=manifest,
            )
            argv = invocation["argv"]
            self.assertEqual(
                "<controller-result-file-capability>",
                argv[argv.index("--output-last-message") + 1],
            )
            self.assertEqual(
                "parent-held-fixed-alias-file-descriptor",
                invocation["dynamic_placeholders"][
                    "<controller-result-file-capability>"
                ]["kind"],
            )
            self.assertNotIn(channel.parent.name, json.dumps(argv))
            self.assertNotIn(str(channel.parent.parent), json.dumps(argv))
            self.assertIn('\":root\"=\"deny\"', " ".join(argv))
            self.assertEqual(
                str(logs / RESULT_ALIAS_DIRECTORY), invocation["cwd"]
            )
            self.assertEqual([], invocation["toolchain_read_roots"])
            result = backend.start_job(
                "static input only",
                workspace,
                logs,
                sandbox_manifest=manifest,
            )
            self.assertEqual(0, result.exit_code, result.stderr_tail)
            observed = json.loads(result.final_message)["proc_matches"]
            self.assertEqual([], observed["matches"])
            self.assertEqual([], observed["derived"])
            rendered_observations = json.dumps(observed, sort_keys=True)
            nonce = channel.parent.name.removeprefix(".codex-final-")
            for secret in (
                str(channel),
                str(channel.parent),
                channel.parent.name,
                nonce,
                hashlib.sha256(str(channel).encode()).hexdigest(),
                hashlib.sha256(nonce.encode()).hexdigest(),
            ):
                self.assertNotIn(secret, rendered_observations)
                for retained_path in logs.rglob("*"):
                    if retained_path.is_file():
                        self.assertNotIn(secret.encode(), retained_path.read_bytes())
            self.assertIn(
                RESULT_CHANNEL_ALIAS,
                observed["ancestors"][0]["entries"],
            )
            self.assertNotIn(
                channel.parent.name,
                observed["ancestors"][1]["entries"],
            )
            self.assertFalse(channel.exists())
            for feature in (
                "artifact",
                "code_mode",
                "code_mode_host",
                "deferred_executor",
                "executor_capability_discovery",
                "shell_tool",
                "unified_exec",
            ):
                self.assertIn(
                    ["--disable", feature],
                    [argv[index : index + 2] for index in range(len(argv) - 1)],
                )

    def test_result_alias_rejects_replacement_and_extra_hardlink(self) -> None:
        with tempfile.TemporaryDirectory(prefix="learnfactory-result-alias-") as raw:
            root = Path(raw)
            logs = root / "logs"
            logs.mkdir()
            backend = ExecBackend("codex")
            for attack in ("replacement", "extra-link", "extra-entry"):
                with self.subTest(attack=attack):
                    channel = _private_result_channel(root, attack, attack)
                    alias = _result_alias(logs)
                    state = _prepared_result_state(backend, channel, alias)
                    binding = backend._prepare_result_alias(state)
                    extra = logs / f"extra-{attack}"
                    if attack == "replacement":
                        alias.unlink()
                        alias.write_text("forged", encoding="utf-8")
                        alias.chmod(0o600)
                    elif attack == "extra-link":
                        os.link(channel, extra)
                    else:
                        extra = alias.parent / "unexpected"
                        extra.write_text("forged", encoding="utf-8")
                    with self.assertRaisesRegex(
                        ValueError, "(?:alias changed|launch namespace changed)"
                    ):
                        backend._remove_result_alias(state, binding)
                    self.assertTrue(alias.exists())
                    if attack == "replacement":
                        self.assertEqual("forged", alias.read_text(encoding="utf-8"))
                        alias.unlink()
                        state.alias_active = False
                    else:
                        extra.unlink()
                        backend._remove_result_alias(state, binding)
                    _clean_result_state(backend, state, binding)

    def test_channel_creation_is_anchored_when_transport_ancestor_is_swapped(self) -> None:
        with tempfile.TemporaryDirectory(prefix="learnfactory-create-swap-") as raw:
            root = Path(raw)
            logs = root / "logs"
            logs.mkdir()
            channel, container = _scoped_result_channel(root, "create", "nonce")
            alias = _result_alias(logs)
            backend = ExecBackend("codex")
            state = _prepare_result_channel_state(channel, alias)

            moved = container.with_name(container.name + "-moved")
            container.rename(moved)
            container.mkdir()
            victim = channel
            victim.parent.mkdir(parents=True)
            victim.write_text("victim", encoding="utf-8")
            victim.chmod(0o600)

            backend._prepare_result_channel(state)
            held_result = moved / channel.relative_to(container)
            self.assertTrue(held_result.exists())
            self.assertEqual("victim", victim.read_text(encoding="utf-8"))
            _clean_result_state(backend, state)
            self.assertEqual("victim", victim.read_text(encoding="utf-8"))

    def test_spawn_error_cleanup_cannot_follow_swapped_transport_ancestor(self) -> None:
        with tempfile.TemporaryDirectory(prefix="learnfactory-spawn-swap-") as raw:
            root = Path(raw)
            workspace = root / "workspace"
            logs = root / "logs"
            workspace.mkdir()
            logs.mkdir()
            channel, container = _scoped_result_channel(root, "spawn", "nonce")
            executable = root / "fake-codex"
            executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            executable.chmod(0o755)
            manifest = build_sandbox_rule_manifest(
                workspace=workspace,
                log_dir=logs,
                worker_type="student",
                payload={},
                result_channel=channel,
            )
            moved = container.with_name(container.name + "-moved")

            def swap_then_fail(*_args: object, **_kwargs: object) -> None:
                container.rename(moved)
                container.mkdir()
                channel.parent.mkdir(parents=True)
                channel.write_text("victim", encoding="utf-8")
                channel.chmod(0o600)
                raise OSError("injected spawn failure")

            with mock.patch(
                "learnfactory.backends.exec_backend.subprocess.Popen",
                side_effect=swap_then_fail,
            ):
                result = ExecBackend(
                    str(executable), timeout_seconds=5
                ).start_job("work", workspace, logs, sandbox_manifest=manifest)

            self.assertEqual(127, result.exit_code)
            self.assertEqual("victim", channel.read_text(encoding="utf-8"))
            held_result = moved / channel.relative_to(container)
            self.assertFalse(held_result.exists())

    def test_post_read_cleanup_cannot_follow_swapped_transport_ancestor(self) -> None:
        with tempfile.TemporaryDirectory(prefix="learnfactory-read-swap-") as raw:
            root = Path(raw)
            workspace = root / "workspace"
            logs = root / "logs"
            workspace.mkdir()
            channel, container = _scoped_result_channel(root, "read", "nonce")
            executable = root / "fake-codex"
            executable.write_text(
                "#!/usr/bin/env python3\n"
                "import pathlib,sys\n"
                "args=sys.argv[1:]\n"
                "pathlib.Path(args[args.index('--output-last-message')+1]).write_text('trusted')\n",
                encoding="utf-8",
            )
            executable.chmod(0o755)
            manifest = build_sandbox_rule_manifest(
                workspace=workspace,
                log_dir=logs,
                worker_type="student",
                payload={},
                result_channel=channel,
            )
            moved = container.with_name(container.name + "-moved")

            class SwapAfterReadBackend(ExecBackend):
                def _read_result_channel(
                    self,
                    state: _ResultChannelState,
                    expected_binding: tuple[int, int, int, int],
                ) -> bytes:
                    value = super()._read_result_channel(state, expected_binding)
                    container.rename(moved)
                    container.mkdir()
                    channel.parent.mkdir(parents=True)
                    channel.write_text("victim", encoding="utf-8")
                    channel.chmod(0o600)
                    return value

            result = SwapAfterReadBackend(
                str(executable), timeout_seconds=5
            ).start_job("work", workspace, logs, sandbox_manifest=manifest)

            self.assertEqual(0, result.exit_code, result.stderr_tail)
            self.assertEqual("trusted", result.final_message)
            self.assertEqual("victim", channel.read_text(encoding="utf-8"))
            held_result = moved / channel.relative_to(container)
            self.assertFalse(held_result.exists())

    def test_spawn_cleanup_cannot_follow_swapped_alias_ancestor(self) -> None:
        with tempfile.TemporaryDirectory(prefix="learnfactory-alias-swap-") as raw:
            root = Path(raw)
            workspace = root / "workspace"
            logs = root / "logs"
            workspace.mkdir()
            logs.mkdir()
            channel, _container = _scoped_result_channel(root, "alias", "nonce")
            executable = root / "fake-codex"
            executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            executable.chmod(0o755)
            manifest = build_sandbox_rule_manifest(
                workspace=workspace,
                log_dir=logs,
                worker_type="student",
                payload={},
                result_channel=channel,
            )
            moved_logs = logs.with_name("logs-moved")
            victim_alias = _result_alias(logs)

            def swap_then_fail(*_args: object, **_kwargs: object) -> None:
                logs.rename(moved_logs)
                victim_alias.parent.mkdir(parents=True, mode=0o700)
                victim_alias.write_text("victim-alias", encoding="utf-8")
                victim_alias.chmod(0o600)
                raise OSError("injected spawn failure")

            with mock.patch(
                "learnfactory.backends.exec_backend.subprocess.Popen",
                side_effect=swap_then_fail,
            ):
                result = ExecBackend(
                    str(executable), timeout_seconds=5
                ).start_job("work", workspace, logs, sandbox_manifest=manifest)

            self.assertEqual(127, result.exit_code)
            self.assertEqual(
                "victim-alias", victim_alias.read_text(encoding="utf-8")
            )
            self.assertFalse(_result_alias(moved_logs).exists())

    def test_real_spawn_binds_output_and_no_tool_cwd_across_alias_ancestor_swap(self) -> None:
        for tools_enabled in (False, True):
            with self.subTest(tools_enabled=tools_enabled), tempfile.TemporaryDirectory(
                prefix="learnfactory-real-launch-swap-"
            ) as raw:
                root = Path(raw)
                workspace = root / "workspace"
                logs = root / "logs"
                workspace.mkdir()
                logs.mkdir()
                channel, _container = _scoped_result_channel(
                    root, f"real-launch-{tools_enabled}", "nonce"
                )
                executable = root / "fake-codex"
                executable.write_text(
                    "#!/usr/bin/env python3\n"
                    "import glob,json,os,pathlib,sys\n"
                    "args=sys.argv[1:]\n"
                    "target=pathlib.Path(args[args.index('--output-last-message')+1])\n"
                    "links=[]\n"
                    "for candidate in glob.glob('/proc/self/fd/*'):\n"
                    "  try: links.append(os.readlink(candidate))\n"
                    "  except OSError: pass\n"
                    "target.write_text(json.dumps({'cwd':str(pathlib.Path.cwd()),"
                    "'target':str(target),'fd_links':links}))\n",
                    encoding="utf-8",
                )
                executable.chmod(0o755)
                payload = (
                    {"sandbox_writable_paths": ["OUTPUT"]}
                    if tools_enabled
                    else {
                        "seed_policy": {
                            "kind": "csdiy_course_progression",
                            "role": "examiner",
                        },
                        "artifact_type": "independent-course-unit-evaluation",
                    }
                )
                manifest = build_sandbox_rule_manifest(
                    workspace=workspace,
                    log_dir=logs,
                    worker_type="student" if tools_enabled else "examiner",
                    payload=payload,
                    result_channel=channel,
                )
                moved_logs = logs.with_name("logs-moved")
                victim_alias = _result_alias(logs)
                real_popen = subprocess.Popen
                swapped = False
                launch_targets: list[str] = []

                def swap_then_spawn(
                    *args: object, **kwargs: object
                ) -> subprocess.Popen[bytes]:
                    nonlocal swapped
                    launch_argv = args[0]
                    if not isinstance(launch_argv, list):
                        raise AssertionError("expected argv list")
                    launch_targets.append(
                        launch_argv[
                            launch_argv.index("--output-last-message") + 1
                        ]
                    )
                    if not swapped:
                        swapped = True
                        logs.rename(moved_logs)
                        victim_alias.parent.mkdir(parents=True, mode=0o700)
                        victim_alias.write_text("victim-alias", encoding="utf-8")
                        victim_alias.chmod(0o600)
                    return real_popen(*args, **kwargs)

                with mock.patch(
                    "learnfactory.backends.exec_backend.subprocess.Popen",
                    side_effect=swap_then_spawn,
                ):
                    result = ExecBackend(
                        str(executable), timeout_seconds=5
                    ).start_job(
                        "work", workspace, logs, sandbox_manifest=manifest
                    )

                self.assertTrue(swapped)
                self.assertEqual(0, result.exit_code, result.stderr_tail)
                self.assertEqual(1, len(launch_targets))
                self.assertRegex(
                    launch_targets[0], r"^/proc/[0-9]+/fd/[0-9]+$"
                )
                observed = json.loads(result.final_message)
                self.assertEqual(
                    "<redacted-runtime-fd-capability>", observed["target"]
                )
                expected_cwd = (
                    workspace
                    if tools_enabled
                    else moved_logs / RESULT_ALIAS_DIRECTORY
                )
                self.assertEqual(str(expected_cwd), observed["cwd"])
                self.assertEqual(
                    "victim-alias", victim_alias.read_text(encoding="utf-8")
                )
                for link in observed["fd_links"]:
                    self.assertNotIn(RESULT_ALIAS_DIRECTORY, link)
                    self.assertNotIn(RESULT_TRANSPORT_DIRECTORY, link)

    def test_empty_root_cleanup_cannot_rmdir_swapped_victim_directories(self) -> None:
        with tempfile.TemporaryDirectory(prefix="learnfactory-root-swap-") as raw:
            root = Path(raw)
            logs = root / "logs"
            logs.mkdir()
            channel, container = _scoped_result_channel(root, "roots", "nonce")
            alias = _result_alias(logs)
            state = _prepare_result_channel_state(channel, alias)
            moved_container = container.with_name(container.name + "-moved")
            moved_logs = logs.with_name("logs-moved")
            container.rename(moved_container)
            logs.rename(moved_logs)

            victim_transport = channel.parent.parent
            victim_transport.mkdir(parents=True)
            victim_alias_directory = alias.parent
            victim_alias_directory.mkdir(parents=True, mode=0o700)
            _discard_empty_result_directories(
                state.transport_root, state.alias_directory
            )
            state.close()

            self.assertTrue(victim_transport.is_dir())
            self.assertTrue(victim_alias_directory.is_dir())
            held_transport = moved_container / victim_transport.relative_to(container)
            self.assertFalse(held_transport.exists())
            self.assertFalse((moved_logs / RESULT_ALIAS_DIRECTORY).exists())

    def test_transport_preparation_mkdir_is_rooted_in_held_parent(self) -> None:
        with tempfile.TemporaryDirectory(prefix="learnfactory-prepare-transport-") as raw:
            root = Path(raw)
            logs = root / "logs"
            logs.mkdir()
            channel, container = _scoped_result_channel(
                root, "prepare-transport", "nonce"
            )
            alias = _result_alias(logs)
            moved = container.with_name(container.name + "-moved")
            victim_marker = container / RESULT_TRANSPORT_DIRECTORY / "victim.txt"
            real_mkdir = os.mkdir
            swapped = False

            def swap_during_mkdir(
                path: str | bytes | os.PathLike[str],
                *args: object,
                **kwargs: object,
            ) -> None:
                nonlocal swapped
                if os.fspath(path) == RESULT_TRANSPORT_DIRECTORY and not swapped:
                    swapped = True
                    container.rename(moved)
                    container.mkdir()
                    victim_marker.parent.mkdir(mode=0o700)
                    victim_marker.write_text("victim", encoding="utf-8")
                real_mkdir(path, *args, **kwargs)

            with mock.patch(
                "learnfactory.backends.exec_backend.os.mkdir",
                side_effect=swap_during_mkdir,
            ):
                state = _prepare_result_channel_state(channel, alias)

            self.assertTrue(swapped)
            self.assertEqual("victim", victim_marker.read_text(encoding="utf-8"))
            held_root = moved / state.transport_root.path.relative_to(container)
            self.assertTrue(held_root.is_dir())
            _discard_empty_result_directories(
                state.transport_root, state.alias_directory
            )
            state.close()
            self.assertEqual("victim", victim_marker.read_text(encoding="utf-8"))

    def test_alias_preparation_mkdir_is_rooted_in_held_log_directory(self) -> None:
        with tempfile.TemporaryDirectory(prefix="learnfactory-prepare-alias-") as raw:
            root = Path(raw)
            logs = root / "logs"
            logs.mkdir()
            channel, _container = _scoped_result_channel(
                root, "prepare-alias", "nonce"
            )
            alias = _result_alias(logs)
            moved = logs.with_name("logs-moved")
            victim_marker = alias.parent / "victim.txt"
            real_mkdir = os.mkdir
            swapped = False

            def swap_during_mkdir(
                path: str | bytes | os.PathLike[str],
                *args: object,
                **kwargs: object,
            ) -> None:
                nonlocal swapped
                if os.fspath(path) == RESULT_ALIAS_DIRECTORY and not swapped:
                    swapped = True
                    logs.rename(moved)
                    logs.mkdir()
                    victim_marker.parent.mkdir(mode=0o700)
                    victim_marker.write_text("victim", encoding="utf-8")
                real_mkdir(path, *args, **kwargs)

            with mock.patch(
                "learnfactory.backends.exec_backend.os.mkdir",
                side_effect=swap_during_mkdir,
            ):
                state = _prepare_result_channel_state(channel, alias)

            self.assertTrue(swapped)
            self.assertEqual("victim", victim_marker.read_text(encoding="utf-8"))
            self.assertTrue((moved / RESULT_ALIAS_DIRECTORY).is_dir())
            _discard_empty_result_directories(
                state.transport_root, state.alias_directory
            )
            state.close()
            self.assertEqual("victim", victim_marker.read_text(encoding="utf-8"))

    def test_component_walk_detects_alias_ancestor_swap_without_mutation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="learnfactory-walk-swap-") as raw:
            root = Path(raw)
            logs = root / "logs"
            logs.mkdir()
            channel, _container = _scoped_result_channel(root, "walk", "nonce")
            alias = _result_alias(logs)
            moved = logs.with_name("logs-moved")
            victim_alias = alias
            real_open = os.open
            swapped = False

            def swap_after_open(
                path: str | bytes | os.PathLike[str],
                *args: object,
                **kwargs: object,
            ) -> int:
                nonlocal swapped
                descriptor = real_open(path, *args, **kwargs)
                if os.fspath(path) == logs.name and not swapped:
                    swapped = True
                    logs.rename(moved)
                    victim_alias.parent.mkdir(parents=True, mode=0o700)
                    victim_alias.write_text("victim-alias", encoding="utf-8")
                    victim_alias.chmod(0o600)
                return descriptor

            with mock.patch(
                "learnfactory.backends.exec_backend.os.open",
                side_effect=swap_after_open,
            ):
                with self.assertRaisesRegex(
                    ValueError, "changed during component walk"
                ):
                    _prepare_result_channel_state(channel, alias)

            self.assertTrue(swapped)
            self.assertEqual(
                "victim-alias", victim_alias.read_text(encoding="utf-8")
            )

    def test_tool_enabled_cli_sees_only_fixed_alias_topology(self) -> None:
        with tempfile.TemporaryDirectory(prefix="learnfactory-tool-result-") as raw:
            root = Path(raw)
            workspace = root / "workspace"
            logs = root / "logs"
            workspace.mkdir()
            executable = root / "fake-codex"
            executable.write_text(
                "#!/usr/bin/env python3\n"
                "import glob,hashlib,json,os,pathlib,re,sys\n"
                "target=pathlib.Path(sys.argv[sys.argv.index('--output-last-message')+1]).absolute()\n"
                "resolved_target=target.resolve()\n"
                "pattern=re.compile(rb'\\.codex-final-([0-9a-f]{64})')\n"
                "blobs=['\\0'.join(sys.argv).encode(),str(pathlib.Path.cwd()).encode(),"
                "'\\0'.join(f'{k}={v}' for k,v in os.environ.items()).encode()]\n"
                "for name in ('cmdline','environ'):\n"
                "  blobs.append(pathlib.Path('/proc/self/'+name).read_bytes())\n"
                "for descriptor in glob.glob('/proc/self/fd/*'):\n"
                "  try: blobs.append(os.readlink(descriptor).encode())\n"
                "  except OSError: pass\n"
                "for directory in (pathlib.Path.cwd(),target.parent,target.parent.parent):\n"
                "  blobs.append('\\0'.join(sorted(p.name for p in directory.iterdir())).encode())\n"
                "matches=[m.group(0).decode() for blob in blobs for m in pattern.finditer(blob)]\n"
                "derived=[hashlib.sha256(value.encode()).hexdigest() for value in matches]\n"
                "target.write_text(json.dumps({'matches':matches,'derived':derived,"
                "'cwd':str(pathlib.Path.cwd()),'alias_parent':str(resolved_target.parent),"
                "'alias_entries':sorted(p.name for p in resolved_target.parent.iterdir()),"
                "'log_entries':sorted(p.name for p in resolved_target.parent.parent.iterdir())}))\n",
                encoding="utf-8",
            )
            executable.chmod(0o755)
            channel = _private_result_channel(root, "tool-enabled", "secret")
            manifest = build_sandbox_rule_manifest(
                workspace=workspace,
                log_dir=logs,
                worker_type="student",
                payload={"sandbox_writable_paths": ["OUTPUT"]},
                result_channel=channel,
            )
            backend = ExecBackend(str(executable), timeout_seconds=5)
            invocation = backend.invocation_manifest(
                workspace, prompt="work", sandbox_manifest=manifest
            )
            rendered_invocation = json.dumps(invocation, sort_keys=True)
            self.assertNotIn(str(channel), rendered_invocation)
            self.assertNotIn(channel.parent.name, rendered_invocation)
            self.assertIn('\":root\"=\"deny\"', " ".join(invocation["argv"]))

            result = backend.start_job(
                "work", workspace, logs, sandbox_manifest=manifest
            )
            self.assertEqual(0, result.exit_code, result.stderr_tail)
            observed = json.loads(result.final_message)
            self.assertEqual([], observed["matches"])
            self.assertEqual([], observed["derived"])
            self.assertEqual(str(workspace), observed["cwd"])
            self.assertEqual(
                str(logs / RESULT_ALIAS_DIRECTORY), observed["alias_parent"]
            )
            self.assertEqual([RESULT_CHANNEL_ALIAS], observed["alias_entries"])
            self.assertNotIn(channel.parent.name, json.dumps(observed))

    def test_result_reader_bounds_namespace_scan_and_detects_parent_swap(self) -> None:
        with tempfile.TemporaryDirectory(prefix="learnfactory-result-read-") as raw:
            root = Path(raw)
            logs = root / "logs"
            logs.mkdir()
            backend = ExecBackend("codex")

            def prepared(
                label: str,
            ) -> tuple[_ResultChannelState, tuple[int, int, int, int]]:
                channel = _private_result_channel(root, label, label)
                alias = _result_alias(logs)
                state = _prepared_result_state(backend, channel, alias)
                binding = backend._prepare_result_alias(state)
                alias.write_text("original", encoding="utf-8")
                backend._remove_result_alias(state, binding)
                return state, binding

            state, binding = prepared("bounded")

            class BoundedEntries:
                def __init__(self) -> None:
                    self.index = 0

                def __enter__(self) -> "BoundedEntries":
                    return self

                def __exit__(self, *_args: object) -> None:
                    return None

                def __iter__(self) -> "BoundedEntries":
                    return self

                def __next__(self) -> object:
                    self.index += 1
                    if self.index == 1:
                        return type("Entry", (), {"name": "result.json"})()
                    if self.index == 2:
                        return type("Entry", (), {"name": "unexpected"})()
                    raise AssertionError("result reader scanned beyond two entries")

            with mock.patch(
                "learnfactory.backends.exec_backend.os.scandir",
                return_value=BoundedEntries(),
            ):
                with self.assertRaisesRegex(ValueError, "unexpected entries"):
                    backend._read_result_channel(state, binding)
            _clean_result_state(backend, state, binding)

            state, binding = prepared("parent-swap")
            channel = state.channel_path
            moved = channel.parent.with_name(channel.parent.name + "-moved")
            channel.parent.rename(moved)
            channel.parent.mkdir(mode=0o700)
            forged = channel.parent / "result.json"
            forged.write_text("forged", encoding="utf-8")
            forged.chmod(0o600)
            with self.assertRaisesRegex(
                ValueError, "directory (?:entry|binding) changed"
            ):
                backend._read_result_channel(state, binding)
            self.assertEqual("forged", forged.read_text(encoding="utf-8"))
            state.close()
            forged.unlink()
            channel.parent.rmdir()
            (moved / "result.json").unlink()
            moved.rmdir()
            channel.parent.parent.rmdir()
            (logs / RESULT_ALIAS_DIRECTORY).rmdir()

    def test_no_tool_result_paths_clean_on_failure_timeout_and_spawn_error(self) -> None:
        with tempfile.TemporaryDirectory(prefix="learnfactory-result-cleanup-") as raw:
            root = Path(raw)
            workspace = root / "workspace"
            workspace.mkdir()

            def manifest_for(logs: Path, suffix: str):
                return build_sandbox_rule_manifest(
                    workspace=workspace,
                    log_dir=logs,
                    worker_type="examiner",
                    payload={
                        "seed_policy": {
                            "kind": "csdiy_course_cohort",
                            "role": "examiner",
                        },
                        "artifact_type": "independent-course-evaluation",
                    },
                    result_channel=_private_result_channel(
                        root, logs.name, suffix
                    ),
                )

            failing = root / "failing-codex"
            failing.write_text("#!/usr/bin/env python3\nraise SystemExit(9)\n")
            failing.chmod(0o755)
            logs = root / "logs-failure"
            manifest = manifest_for(logs, "failure")
            result = ExecBackend(str(failing), timeout_seconds=5).start_job(
                "static", workspace, logs, sandbox_manifest=manifest
            )
            self.assertEqual(9, result.exit_code)
            self.assertFalse(Path(manifest.result_channel).exists())
            self.assertFalse(_result_alias(logs).exists())

            sleeping = root / "sleeping-codex"
            sleeping.write_text(
                "#!/usr/bin/env python3\nimport time\ntime.sleep(30)\n",
                encoding="utf-8",
            )
            sleeping.chmod(0o755)
            logs = root / "logs-timeout"
            manifest = manifest_for(logs, "timeout")
            result = ExecBackend(str(sleeping), timeout_seconds=0.1).start_job(
                "static", workspace, logs, sandbox_manifest=manifest
            )
            self.assertTrue(result.timed_out)
            self.assertFalse(Path(manifest.result_channel).exists())
            self.assertFalse(_result_alias(logs).exists())

            class BrokenRestoration:
                def close(self) -> None:
                    raise OSError("restore failure")

            logs = root / "logs-spawn"
            manifest = manifest_for(logs, "spawn")
            with mock.patch(
                "learnfactory.backends.exec_backend._DescendantReaper.install",
                return_value=BrokenRestoration(),
            ), mock.patch(
                "learnfactory.backends.exec_backend.subprocess.Popen",
                side_effect=OSError("spawn failure"),
            ):
                result = ExecBackend(str(failing), timeout_seconds=5).start_job(
                    "static", workspace, logs, sandbox_manifest=manifest
                )
            self.assertEqual(127, result.exit_code)
            self.assertIn("subreaper restoration also failed", result.stderr_tail)
            self.assertFalse(Path(manifest.result_channel).exists())
            self.assertFalse(_result_alias(logs).exists())

    def test_live_result_capability_is_absent_from_all_persisted_file_content(self) -> None:
        with tempfile.TemporaryDirectory(prefix="learnfactory-result-persistence-") as raw:
            root = Path(raw)
            workspace = root / "workspace"
            logs = root / "logs"
            workspace.mkdir()
            logs.mkdir()
            executable = root / "fake-codex"
            executable.write_text(
                "#!/usr/bin/env python3\n"
                "import pathlib,sys\n"
                "args=sys.argv[1:]\n"
                "target=pathlib.Path(args[args.index('--output-last-message')+1])\n"
                "print('runtime-target=' + str(target))\n"
                "print('runtime-target=' + str(target), file=sys.stderr)\n"
                "target.write_text('persist-probe-ok runtime-target=' + str(target))\n",
                encoding="utf-8",
            )
            executable.chmod(0o755)
            nonce = "9f" * 32
            channel = (
                default_result_transport_root(root / "persistence")
                / (".codex-final-" + nonce)
                / "result.json"
            )
            manifest = build_sandbox_rule_manifest(
                workspace=workspace,
                log_dir=logs,
                worker_type="examiner",
                payload={
                    "seed_policy": {
                        "kind": "csdiy_course_progression",
                        "role": "examiner",
                    },
                    "artifact_type": "independent-course-unit-evaluation",
                },
                result_channel=channel,
            )
            backend = ExecBackend(str(executable), timeout_seconds=5)
            invocation = backend.invocation_manifest(
                workspace,
                prompt="static evidence",
                sandbox_manifest=manifest,
            )
            durable = {
                "sandbox": manifest.as_dict(),
                "invocation": invocation,
                "artifact_metadata": {"sandbox": manifest.as_dict()},
                "handler_summary": {
                    "sandbox_rule_manifest_sha256": manifest.as_dict()["sha256"]
                },
                "event": {"type": "RUN_REPRODUCIBILITY_CAPTURED"},
            }
            (logs / "RUN_PROVENANCE.json").write_text(
                json.dumps(durable, sort_keys=True), encoding="utf-8"
            )
            database_path = root / "factory.db"
            with sqlite3.connect(database_path) as connection:
                connection.execute(
                    "CREATE TABLE durable_records(kind TEXT, payload TEXT)"
                )
                connection.execute(
                    "INSERT INTO durable_records VALUES (?, ?)",
                    ("job_run", json.dumps(durable, sort_keys=True)),
                )

            observed = False

            class PersistenceInspectingBackend(ExecBackend):
                def _prepare_result_alias(
                    self, state: _ResultChannelState
                ) -> tuple[int, int, int, int]:
                    nonlocal observed
                    binding = ExecBackend._prepare_result_alias(state)
                    self.assert_capability_absent(state.channel_path)
                    observed = True
                    return binding

                @staticmethod
                def assert_capability_absent(actual_channel: Path) -> None:
                    needles = (
                        str(actual_channel).encode(),
                        actual_channel.parent.name.encode(),
                        nonce.encode(),
                        hashlib.sha256(str(actual_channel).encode()).hexdigest().encode(),
                        hashlib.sha256(nonce.encode()).hexdigest().encode(),
                    )
                    scanned = 0
                    for candidate in root.rglob("*"):
                        if not candidate.is_file():
                            continue
                        scanned += 1
                        content = candidate.read_bytes()
                        for needle in needles:
                            if needle in content:
                                raise AssertionError(
                                    f"live result capability persisted in {candidate}"
                                )
                    if scanned < 4:
                        raise AssertionError("persistence probe did not scan enough files")

            result = PersistenceInspectingBackend(
                str(executable), timeout_seconds=5
            ).start_job(
                "static evidence",
                workspace,
                logs,
                sandbox_manifest=manifest,
            )

            self.assertTrue(observed)
            self.assertEqual(0, result.exit_code, result.stderr_tail)
            self.assertIn("persist-probe-ok", result.final_message)
            self.assertIn(
                "<redacted-runtime-fd-capability>", result.final_message
            )
            retained = "\n".join(
                [
                    result.final_message,
                    result.stderr_tail,
                    *(path.read_text(encoding="utf-8", errors="replace")
                      for path in logs.rglob("*") if path.is_file()),
                    json.dumps(durable, sort_keys=True),
                ]
            )
            self.assertNotRegex(retained, r"/proc/[1-9][0-9]*/fd/[0-9]+")
            self.assertNotIn(nonce, json.dumps(durable, sort_keys=True))

    def test_transport_creation_errors_do_not_persist_private_paths_or_hashes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="learnfactory-result-errors-") as raw:
            root = Path(raw)
            workspace = root / "workspace"
            container = root / "controller-private"
            workspace.mkdir()
            container.mkdir(mode=0o700)
            base = container / RESULT_TRANSPORT_DIRECTORY
            job_hash = "d3" * 32
            attempt_root = base / job_hash / "attempt-001"
            nonce = "e4" * 32
            channel = attempt_root / (".codex-final-" + nonce) / "result.json"
            executable = root / "fake-codex"
            executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            executable.chmod(0o755)
            original_mkdir = os.mkdir

            for stage, failure_path in (("base", base), ("job", base / job_hash)):
                with self.subTest(stage=stage):
                    if stage == "job":
                        base.mkdir(mode=0o700, exist_ok=True)
                    logs = root / ("logs-" + stage)
                    logs.mkdir()
                    manifest = build_sandbox_rule_manifest(
                        workspace=workspace,
                        log_dir=logs,
                        worker_type="student",
                        payload={},
                        result_channel=channel,
                    )
                    backend = ExecBackend(str(executable), timeout_seconds=5)
                    provenance = {
                        "sandbox": manifest.as_dict(),
                        "invocation": backend.invocation_manifest(
                            workspace,
                            prompt="safe",
                            sandbox_manifest=manifest,
                        ),
                    }
                    (logs / "RUN_PROVENANCE.json").write_text(
                        json.dumps(provenance, sort_keys=True), encoding="utf-8"
                    )

                    def injected_mkdir(
                        path: str | bytes | os.PathLike[str],
                        *args: object,
                        **kwargs: object,
                    ) -> None:
                        if os.fspath(path) == failure_path.name:
                            raise OSError(
                                errno.EACCES,
                                "injected private transport creation failure",
                                os.fspath(path),
                            )
                        original_mkdir(path, *args, **kwargs)

                    with mock.patch(
                        "learnfactory.backends.exec_backend.os.mkdir",
                        side_effect=injected_mkdir,
                    ):
                        result = backend.start_job(
                            "safe",
                            workspace,
                            logs,
                            sandbox_manifest=manifest,
                        )
                    self.assertEqual(2, result.exit_code)
                    retained = b"\n".join(
                        path.read_bytes()
                        for path in logs.rglob("*")
                        if path.is_file()
                    )
                    private_values = (
                        str(channel),
                        str(channel.parent),
                        str(attempt_root),
                        str(base / job_hash),
                        str(base),
                        channel.parent.name,
                        nonce,
                        job_hash,
                    )
                    for private in private_values:
                        self.assertNotIn(private.encode(), retained)
                        self.assertNotIn(
                            hashlib.sha256(private.encode()).hexdigest().encode(),
                            retained,
                        )
            base.rmdir()

    def test_crash_leftover_channel_is_recovered_and_future_jobs_still_run(self) -> None:
        with tempfile.TemporaryDirectory(prefix="learnfactory-result-recovery-") as raw:
            root = Path(raw)
            workspace = root / "workspace"
            logs = root / "logs"
            workspace.mkdir()
            logs.mkdir()
            executable = root / "fake-codex"
            executable.write_text(
                "#!/usr/bin/env python3\n"
                "import pathlib,sys\n"
                "args=sys.argv[1:]\n"
                "pathlib.Path(args[args.index('--output-last-message')+1]).write_text('ok')\n",
                encoding="utf-8",
            )
            executable.chmod(0o755)
            backend = ExecBackend(str(executable), timeout_seconds=5)

            stale = _private_result_channel(root, "recovery", "stale")
            transport_root = stale.parent.parent
            alias = _result_alias(logs)
            stale_state = _prepared_result_state(backend, stale, alias)
            backend._prepare_result_alias(stale_state)
            alias.write_text("unreaped-process-output", encoding="utf-8")
            stale_state.park_private_descriptors()
            stale_state.close()
            unrelated = transport_root / ".codex-final-human-owned-note"
            unrelated.mkdir()
            (unrelated / "keep.txt").write_text("keep\n", encoding="utf-8")

            for index in (1, 2):
                channel = (
                    transport_root
                    / (f".codex-final-{index:064x}")
                    / "result.json"
                )
                manifest = build_sandbox_rule_manifest(
                    workspace=workspace,
                    log_dir=logs,
                    worker_type="examiner",
                    payload={
                        "seed_policy": {
                            "kind": "csdiy_course_progression",
                            "role": "examiner",
                        },
                        "artifact_type": "independent-course-unit-evaluation",
                    },
                    result_channel=channel,
                )
                result = backend.start_job(
                    "static evidence",
                    workspace,
                    logs,
                    sandbox_manifest=manifest,
                )
                self.assertEqual(0, result.exit_code, result.stderr_tail)
                self.assertEqual("ok", result.final_message)
                self.assertFalse(channel.exists())
                self.assertFalse(alias.exists())
                self.assertFalse(stale.parent.exists())
                self.assertEqual(
                    "keep\n", (unrelated / "keep.txt").read_text(encoding="utf-8")
                )
            (unrelated / "keep.txt").unlink()
            unrelated.rmdir()
            transport_root.rmdir()

    def test_recovery_cannot_follow_swapped_transport_or_alias_ancestors(self) -> None:
        with tempfile.TemporaryDirectory(prefix="learnfactory-recovery-swap-") as raw:
            root = Path(raw)
            logs = root / "logs"
            logs.mkdir()
            channel, container = _scoped_result_channel(
                root, "recovery-swap", "stale"
            )
            alias = _result_alias(logs)
            backend = ExecBackend("codex")
            stale = _prepared_result_state(backend, channel, alias)
            backend._prepare_result_alias(stale)
            alias.write_text("stale", encoding="utf-8")
            stale.park_private_descriptors()
            stale.close()

            recovery = _prepare_result_channel_state(channel, alias)
            moved_container = container.with_name(container.name + "-moved")
            moved_logs = logs.with_name("logs-moved")
            container.rename(moved_container)
            logs.rename(moved_logs)
            channel.parent.mkdir(parents=True)
            channel.write_text("victim-result", encoding="utf-8")
            channel.chmod(0o600)
            victim_alias = _result_alias(logs)
            victim_alias.parent.mkdir(parents=True, mode=0o700)
            victim_alias.write_text("victim-alias", encoding="utf-8")
            victim_alias.chmod(0o600)

            _recover_stale_result_channels(recovery)
            _discard_empty_result_directories(
                recovery.transport_root, recovery.alias_directory
            )
            recovery.close()

            self.assertEqual("victim-result", channel.read_text(encoding="utf-8"))
            self.assertEqual(
                "victim-alias", victim_alias.read_text(encoding="utf-8")
            )
            held_channel = moved_container / channel.relative_to(container)
            held_alias = moved_logs / alias.relative_to(logs)
            self.assertFalse(held_channel.exists())
            self.assertFalse(held_alias.exists())

    def test_recovery_does_not_delete_another_attempt_channel(self) -> None:
        with tempfile.TemporaryDirectory(prefix="learnfactory-result-scope-") as raw:
            root = Path(raw)
            backend = ExecBackend("codex")
            first = _private_result_channel(root, "job-a", "stale")
            second = _private_result_channel(root, "job-b", "active")
            first_alias = _result_alias(root / "logs-a")
            second_alias = _result_alias(root / "logs-b")
            states: list[
                tuple[_ResultChannelState, tuple[int, int, int, int]]
            ] = []
            for channel, alias in ((first, first_alias), (second, second_alias)):
                alias.parent.parent.mkdir()
                state = _prepared_result_state(backend, channel, alias)
                binding = backend._prepare_result_alias(state)
                state.park_private_descriptors()
                states.append((state, binding))

            states[0][0].close()
            recovery = _prepare_result_channel_state(first, first_alias)
            _recover_stale_result_channels(recovery)
            _discard_empty_result_directories(
                recovery.transport_root, recovery.alias_directory
            )
            recovery.close()

            self.assertFalse(first.exists())
            self.assertFalse(first_alias.exists())
            self.assertTrue(second.exists())
            self.assertTrue(second_alias.exists())
            state, binding = states[1]
            state.restore_private_descriptors()
            _clean_result_state(backend, state, binding)

    def test_recovery_clears_fd_ownership_before_rmdir_failure(self) -> None:
        with tempfile.TemporaryDirectory(prefix="learnfactory-result-fd-") as raw:
            root = Path(raw)
            logs = root / "logs"
            logs.mkdir()
            backend = ExecBackend("codex")
            channel = _private_result_channel(root, "fd-reuse", "stale")
            alias = _result_alias(logs)
            stale_state = _prepared_result_state(backend, channel, alias)
            backend._prepare_result_alias(stale_state)
            stale_state.park_private_descriptors()
            stale_state.close()
            recovery = _prepare_result_channel_state(channel, alias)
            reused: list[int] = []

            def fail_after_reuse(*_args: object, **_kwargs: object) -> None:
                reused.append(os.open("/dev/null", os.O_RDONLY))
                raise OSError("injected rmdir failure")

            try:
                with mock.patch(
                    "learnfactory.backends.exec_backend.os.rmdir",
                    side_effect=fail_after_reuse,
                ):
                    with self.assertRaisesRegex(
                        ValueError, "recovery failed"
                    ):
                        _recover_stale_result_channels(recovery)
                self.assertEqual(1, len(reused))
                os.fstat(reused[0])
            finally:
                for descriptor in reused:
                    os.close(descriptor)
                recovery.close()
            channel.parent.rmdir()
            channel.parent.parent.rmdir()
            alias.parent.rmdir()

    def test_result_capability_close_fault_does_not_close_reused_descriptor(self) -> None:
        with tempfile.TemporaryDirectory(prefix="learnfactory-capability-fd-") as raw:
            root = Path(raw)
            logs = root / "logs"
            logs.mkdir()
            channel, _container = _scoped_result_channel(root, "fd-close", "nonce")
            state = _prepare_result_channel_state(channel, _result_alias(logs))
            target = state.transport_root.fileno()
            real_close = os.close
            reused: list[int] = []

            def close_then_fail(descriptor: int) -> None:
                real_close(descriptor)
                if descriptor == target and not reused:
                    reused.append(os.open("/dev/null", os.O_RDONLY))
                    raise OSError("injected close failure")

            try:
                with mock.patch(
                    "learnfactory.backends.exec_backend.os.close",
                    side_effect=close_then_fail,
                ):
                    with self.assertRaisesRegex(OSError, "injected close failure"):
                        state.close()
                self.assertEqual([target], reused)
                os.fstat(reused[0])
            finally:
                for descriptor in reused:
                    real_close(descriptor)

    def test_component_walk_close_fault_does_not_double_close_reused_descriptor(self) -> None:
        with tempfile.TemporaryDirectory(prefix="learnfactory-walk-fd-") as raw:
            target = Path(raw) / "one" / "two"
            target.mkdir(parents=True)
            real_close = os.close
            reused: list[int] = []
            closed: list[int] = []

            def close_then_reuse(descriptor: int) -> None:
                closed.append(descriptor)
                real_close(descriptor)
                if not reused:
                    reused.append(os.open("/dev/null", os.O_RDONLY))
                    raise OSError("injected component close failure")

            try:
                with mock.patch(
                    "learnfactory.backends.exec_backend.os.close",
                    side_effect=close_then_reuse,
                ):
                    with self.assertRaisesRegex(
                        OSError, "injected component close failure"
                    ):
                        _open_nofollow_directory(target)
                self.assertGreaterEqual(len(closed), 2)
                self.assertNotEqual(closed[0], closed[1])
                os.fstat(reused[0])
            finally:
                for descriptor in reused:
                    real_close(descriptor)

    def test_result_capability_lifecycle_does_not_leak_descriptors(self) -> None:
        with tempfile.TemporaryDirectory(prefix="learnfactory-capability-leak-") as raw:
            root = Path(raw)
            logs = root / "logs"
            logs.mkdir()
            backend = ExecBackend("codex")
            before = len(os.listdir("/proc/self/fd"))
            for index in range(8):
                channel, _container = _scoped_result_channel(
                    root, f"leak-{index}", f"nonce-{index}"
                )
                state = _prepared_result_state(
                    backend, channel, _result_alias(logs)
                )
                binding = backend._prepare_result_alias(state)
                _clean_result_state(backend, state, binding)
            after = len(os.listdir("/proc/self/fd"))
            self.assertEqual(before, after)

    def test_whole_lifetime_owner_cleans_faults_after_state_acquisition(self) -> None:
        for fault in ("render", "capture", "popen-type", "persist"):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory(
                prefix="learnfactory-owner-fault-"
            ) as raw:
                root = Path(raw)
                workspace = root / "workspace"
                logs = root / "logs"
                workspace.mkdir()
                channel, _container = _scoped_result_channel(root, fault, "nonce")
                executable = root / "fake-codex"
                executable.write_text(
                    "#!/usr/bin/env python3\n"
                    "import pathlib,sys\n"
                    "args=sys.argv[1:]\n"
                    "pathlib.Path(args[args.index('--output-last-message')+1]).write_text('ok')\n",
                    encoding="utf-8",
                )
                executable.chmod(0o755)
                manifest = build_sandbox_rule_manifest(
                    workspace=workspace,
                    log_dir=logs,
                    worker_type="student",
                    payload={},
                    result_channel=channel,
                )
                backend = ExecBackend(str(executable), timeout_seconds=5)
                before = len(os.listdir("/proc/self/fd"))

                if fault == "render":
                    context = mock.patch.object(
                        backend,
                        "_render_exec_argv",
                        side_effect=RuntimeError("injected render failure"),
                    )
                    expected = RuntimeError
                elif fault == "capture":
                    context = mock.patch(
                        "learnfactory.backends.exec_backend.BoundedBinaryCapture",
                        side_effect=RuntimeError("injected capture failure"),
                    )
                    expected = RuntimeError
                elif fault == "popen-type":
                    context = mock.patch(
                        "learnfactory.backends.exec_backend.subprocess.Popen",
                        side_effect=TypeError("injected popen failure"),
                    )
                    expected = None
                else:
                    context = mock.patch.object(
                        BoundedBinaryCapture,
                        "persist_redacted",
                        side_effect=OSError("injected persistence failure"),
                    )
                    expected = OSError

                with context:
                    if expected is None:
                        result = backend.start_job(
                            "work", workspace, logs, sandbox_manifest=manifest
                        )
                        self.assertEqual(127, result.exit_code)
                    else:
                        with self.assertRaises(expected):
                            backend.start_job(
                                "work", workspace, logs, sandbox_manifest=manifest
                            )

                self.assertFalse(channel.exists())
                self.assertFalse(channel.parent.exists())
                self.assertFalse(_result_alias(logs).exists())
                self.assertFalse((logs / RESULT_ALIAS_DIRECTORY).exists())
                after = len(os.listdir("/proc/self/fd"))
                self.assertEqual(before, after)

    def test_subreaper_install_does_not_mutate_state_when_inventory_fails(self) -> None:
        calls: list[int] = []

        class FakeLibc:
            def prctl(self, operation: int, argument: object, *_rest: int) -> int:
                calls.append(operation)
                if operation == _DescendantReaper._PR_GET_CHILD_SUBREAPER:
                    argument._obj.value = 0  # type: ignore[attr-defined]
                return 0

        with mock.patch(
            "learnfactory.backends.exec_backend.ctypes.CDLL",
            return_value=FakeLibc(),
        ), mock.patch(
            "learnfactory.backends.exec_backend._direct_child_pids",
            side_effect=OSError("inventory unavailable"),
        ):
            with self.assertRaisesRegex(OSError, "inventory unavailable"):
                _DescendantReaper.install()

        self.assertEqual([_DescendantReaper._PR_GET_CHILD_SUBREAPER], calls)

    def test_subreaper_install_fails_closed_on_existing_child(self) -> None:
        calls: list[int] = []

        class FakeLibc:
            def prctl(self, operation: int, argument: object, *_rest: int) -> int:
                calls.append(operation)
                if operation == _DescendantReaper._PR_GET_CHILD_SUBREAPER:
                    argument._obj.value = 0  # type: ignore[attr-defined]
                return 0

        with mock.patch(
            "learnfactory.backends.exec_backend.ctypes.CDLL",
            return_value=FakeLibc(),
        ), mock.patch(
            "learnfactory.backends.exec_backend._direct_child_pids",
            return_value={12345},
        ):
            with self.assertRaisesRegex(OSError, "childless worker"):
                _DescendantReaper.install()

        self.assertEqual([_DescendantReaper._PR_GET_CHILD_SUBREAPER], calls)

    def test_jsonl_invocation_records_session_usage_and_quality_profile(self) -> None:
        with tempfile.TemporaryDirectory(prefix="learnfactory-backend-") as raw:
            root = Path(raw)
            workspace = root / "workspace"
            logs = root / "logs"
            workspace.mkdir()
            executable = root / "fake-codex"
            executable.write_text(
                """#!/usr/bin/env python3
import json, pathlib, sys
args = sys.argv[1:]
pathlib.Path('captured-argv.json').write_text(json.dumps(args))
prompt = sys.stdin.read()
pathlib.Path('captured-prompt.txt').write_text(prompt)
target = pathlib.Path(args[args.index('--output-last-message') + 1])
target.write_text('completed')
print(json.dumps({'type': 'thread.started', 'thread_id': 'thread-test-123'}))
print(json.dumps({'type': 'turn.completed', 'usage': {'input_tokens': 17, 'output_tokens': 5}}))
""",
                encoding="utf-8",
            )
            executable.chmod(0o755)
            backend = ExecBackend(str(executable), timeout_seconds=5)
            sandbox_manifest = build_sandbox_rule_manifest(
                workspace=workspace,
                log_dir=logs,
                worker_type="test",
                payload={},
                result_channel=_private_result_channel(root, "jsonl", "unit-test"),
            )
            manifest = backend.invocation_manifest(
                workspace,
                prompt="build the artifact",
                model="gpt-5.6-sol",
                reasoning_effort="ultra",
                timeout_seconds=5,
                sandbox_manifest=sandbox_manifest,
            )
            result = backend.start_job(
                "build the artifact",
                workspace,
                logs,
                model="gpt-5.6-sol",
                reasoning_effort="ultra",
                sandbox_manifest=sandbox_manifest,
            )

            self.assertEqual(0, result.exit_code)
            self.assertEqual("thread-test-123", result.session_id)
            self.assertEqual({"input_tokens": 17, "output_tokens": 5}, result.usage)
            self.assertEqual("completed", result.final_message)
            captured_prompt = (workspace / "captured-prompt.txt").read_text()
            self.assertIn("leaf execution worker", captured_prompt)
            self.assertIn("Do not spawn, delegate to, or message other agents", captured_prompt)
            self.assertTrue(captured_prompt.endswith("JOB:\nbuild the artifact"))
            args = json.loads((workspace / "captured-argv.json").read_text())
            self.assertEqual("gpt-5.6-sol", args[args.index("--model") + 1])
            self.assertIn('model_reasoning_effort="ultra"', args)
            self.assertIn("--ephemeral", args)
            self.assertNotIn("--sandbox", args)
            self.assertIn("--ignore-user-config", args)
            self.assertIn("--ignore-rules", args)
            self.assertIn("--strict-config", args)
            overrides = [
                args[index + 1]
                for index, arg in enumerate(args)
                if arg == "--config"
            ]
            self.assertIn('default_permissions="factory-isolated"', overrides)
            filesystem = next(
                value
                for value in overrides
                if value.startswith("permissions.factory-isolated.filesystem=")
            )
            self.assertIn('\":root\"=\"deny\"', filesystem)
            self.assertIn('\":minimal\"=\"read\"', filesystem)
            self.assertIn('\":workspace_roots\"={\".\"=\"write\"}', filesystem)
            self.assertIn(
                "permissions.factory-isolated.network.enabled=false", overrides
            )
            self.assertIn('shell_environment_policy.inherit="none"', overrides)
            self.assertIn("tools.web_search=false", overrides)
            self.assertIn("mcp_servers={}", overrides)
            disabled = {
                args[index + 1]
                for index, arg in enumerate(args)
                if arg == "--disable"
            }
            self.assertTrue(
                {
                    "apps",
                    "browser_use",
                    "computer_use",
                    "hooks",
                    "multi_agent",
                    "plugins",
                    "remote_plugin",
                    "skill_search",
                }.issubset(disabled)
            )
            manifested = manifest["argv"][1:]
            actual = list(args)
            descriptor_index = actual.index("--output-last-message") + 1
            self.assertRegex(actual[descriptor_index], r"^/proc/[0-9]+/fd/[0-9]+$")
            actual[descriptor_index] = "<controller-result-file-capability>"
            self.assertNotIn(
                Path(sandbox_manifest.result_channel).parent.name,
                json.dumps(manifest),
            )
            self.assertEqual(manifested, actual)
            effective_prompt = (workspace / "captured-prompt.txt").read_bytes()
            self.assertEqual(
                manifest["prompt"]["sha256"],
                hashlib.sha256(effective_prompt).hexdigest(),
            )
            self.assertEqual(len(effective_prompt), manifest["prompt"]["utf8_bytes"])
            self.assertTrue(manifest["prompt"]["includes_leaf_worker_policy"])
            self.assertFalse(manifest["prompt"]["content_stored"])
            self.assertFalse(manifest["leaf_worker_policy"]["content_stored"])
            self.assertNotEqual(
                manifest["job_prompt"]["sha256"], manifest["prompt"]["sha256"]
            )

    def test_custom_provider_is_passed_without_embedding_credentials(self) -> None:
        with tempfile.TemporaryDirectory(prefix="learnfactory-provider-") as raw:
            root = Path(raw)
            workspace = root / "workspace"
            workspace.mkdir()
            executable = root / "fake-codex"
            executable.write_text(
                "#!/usr/bin/env python3\n"
                "import json,pathlib,sys\n"
                "args=sys.argv[1:]\n"
                "pathlib.Path('argv.json').write_text(json.dumps(args))\n"
                "target=pathlib.Path(args[args.index('--output-last-message')+1])\n"
                "target.write_text('ready')\n",
                encoding="utf-8",
            )
            executable.chmod(0o755)

            result = ExecBackend(
                str(executable),
                timeout_seconds=5,
                provider="arm",
                provider_name="ARM OpenAI Proxy",
                base_url="https://openai-api-proxy.geo.arm.com/api/providers/openai/v1",
                requires_openai_auth=True,
                supports_websockets=False,
            ).start_job("probe", workspace, root / "logs")

            self.assertEqual(0, result.exit_code)
            args = json.loads((workspace / "argv.json").read_text())
            overrides = [args[index + 1] for index, arg in enumerate(args) if arg == "--config"]
            self.assertIn('model_provider="arm"', overrides)
            self.assertIn(
                'model_providers.arm.base_url="https://openai-api-proxy.geo.arm.com/api/providers/openai/v1"',
                overrides,
            )
            self.assertIn("model_providers.arm.requires_openai_auth=true", overrides)
            self.assertIn("model_providers.arm.supports_websockets=false", overrides)
            self.assertFalse(any("api_key" in value.lower() for value in overrides))

    def test_resume_reapplies_fail_closed_isolation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="learnfactory-resume-profile-") as raw:
            root = Path(raw)
            workspace = root / "workspace"
            workspace.mkdir()
            executable = root / "fake-codex"
            executable.write_text(
                "#!/usr/bin/env python3\n"
                "import json,pathlib,sys\n"
                "args=sys.argv[1:]\n"
                "pathlib.Path('resume-argv.json').write_text(json.dumps(args))\n"
                "target=pathlib.Path(args[args.index('--output-last-message')+1])\n"
                "target.write_text('resumed')\n",
                encoding="utf-8",
            )
            executable.chmod(0o755)

            result = ExecBackend(str(executable), timeout_seconds=5).resume_job(
                "session-123",
                "continue",
                workspace,
                root / "logs",
                model="gpt-5.6-sol",
                reasoning_effort="ultra",
            )

            self.assertEqual(0, result.exit_code)
            self.assertEqual("resumed", result.final_message)
            args = json.loads((workspace / "resume-argv.json").read_text())
            self.assertEqual(["exec", "resume", "session-123"], args[:3])
            self.assertNotIn("--sandbox", args)
            self.assertIn("--ignore-user-config", args)
            self.assertIn("--ignore-rules", args)
            self.assertIn("--strict-config", args)
            self.assertIn('default_permissions="factory-isolated"', args)
            self.assertIn(
                "permissions.factory-isolated.network.enabled=false", args
            )
            self.assertIn('shell_environment_policy.inherit="none"', args)

    def test_event_parser_ignores_malformed_lines_and_log_redaction_is_durable(self) -> None:
        with tempfile.TemporaryDirectory(prefix="learnfactory-backend-log-") as raw:
            path = Path(raw) / "events.jsonl"
            fake_secret = "sk-" + "A" * 32
            path.write_text(
                "not-json\n"
                + json.dumps({"nested": {"session_id": "session-9"}})
                + "\n"
                + json.dumps({"usage": {"cached_tokens": 3}, "error": fake_secret})
                + "\n",
                encoding="utf-8",
            )
            session, usage = ExecBackend._parse_events(path)
            self.assertEqual("session-9", session)
            self.assertEqual({"cached_tokens": 3}, usage)
            ExecBackend._sanitize_log(path)
            rendered = path.read_text(encoding="utf-8")
            self.assertNotIn(fake_secret, rendered)
            self.assertIn("<redacted-api-key>", rendered)

    def test_factory_default_matches_operator_requested_model_and_reasoning(self) -> None:
        settings = load_settings(ROOT / "config" / "factory.toml")
        self.assertEqual("gpt-5.6-sol", settings.backend.model)
        self.assertEqual("ultra", settings.backend.reasoning_effort)
        self.assertEqual("arm", settings.backend.provider)
        self.assertEqual(
            "https://openai-api-proxy.geo.arm.com/api/providers/openai/v1",
            settings.backend.base_url,
        )
        self.assertFalse(settings.backend.supports_websockets)
        self.assertEqual("factory-isolated", settings.backend.permission_profile)
        self.assertFalse(settings.allow_host_command_validators)
        self.assertEqual(
            ("/arm/tools/python/python/3.11.5/rhe8-x86_64",),
            settings.backend.toolchain_read_roots,
        )
        self.assertFalse(hasattr(settings.backend, "sandbox"))

    def test_command_validator_fence_requires_a_boolean(self) -> None:
        with tempfile.TemporaryDirectory(prefix="learnfactory-config-fence-") as raw:
            config_path = Path(raw) / "factory.toml"
            config_path.write_text(
                "[factory]\n"
                f"database = {str(Path(raw) / 'factory.db')!r}\n"
                f"warehouse = {str(Path(raw) / 'warehouse')!r}\n"
                'allow_host_command_validators = "false"\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "must be a boolean"):
                load_settings(config_path)

    def test_config_rejects_credential_bearing_backend_endpoint(self) -> None:
        unsafe_endpoints = (
            "https://operator:secret@proxy.example.invalid/v1",
            "https://proxy.example.invalid/v1?token=secret",
            "https://proxy.example.invalid/v1#secret",
            "file:///tmp/not-an-http-endpoint",
            "https://proxy.example.invalid/v1\nsmuggled=true",
        )
        with tempfile.TemporaryDirectory(prefix="learnfactory-config-endpoint-") as raw:
            config_path = Path(raw) / "factory.toml"
            for endpoint in unsafe_endpoints:
                config_path.write_text(
                    "[factory]\n"
                    f"database = {str(Path(raw) / 'factory.db')!r}\n"
                    f"warehouse = {str(Path(raw) / 'warehouse')!r}\n"
                    "[backend]\n"
                    f"base_url = {json.dumps(endpoint)}\n",
                    encoding="utf-8",
                )
                with self.subTest(endpoint=endpoint):
                    with self.assertRaises(ValueError):
                        load_settings(config_path)

    def test_broad_or_relative_toolchain_root_fails_before_cli_spawn(self) -> None:
        with tempfile.TemporaryDirectory(prefix="learnfactory-profile-invalid-") as raw:
            root = Path(raw)
            workspace = root / "workspace"
            workspace.mkdir()
            marker = workspace / "spawned.txt"
            executable = root / "fake-codex"
            executable.write_text(
                "#!/usr/bin/env python3\n"
                "from pathlib import Path\n"
                f"Path({str(marker)!r}).write_text('spawned')\n",
                encoding="utf-8",
            )
            executable.chmod(0o755)

            broad = ExecBackend(
                str(executable), toolchain_read_roots=("/",), timeout_seconds=5
            ).start_job("do not spawn", workspace, root / "logs-broad")
            relative = ExecBackend(
                str(executable),
                toolchain_read_roots=("relative/toolchain",),
                timeout_seconds=5,
            ).start_job("do not spawn", workspace, root / "logs-relative")
            unapproved = ExecBackend(
                str(executable),
                toolchain_read_roots=("/etc/ssh",),
                timeout_seconds=5,
            ).start_job("do not spawn", workspace, root / "logs-unapproved")

            self.assertEqual(2, broad.exit_code)
            self.assertIn("too broad", broad.stderr_tail)
            self.assertEqual(2, relative.exit_code)
            self.assertIn("must be absolute", relative.stderr_tail)
            self.assertEqual(2, unapproved.exit_code)
            self.assertIn("outside approved tool roots", unapproved.stderr_tail)
            self.assertFalse(marker.exists())

    @unittest.skipUnless(
        sys.platform.startswith("linux")
        and shutil.which("codex") is not None
        and shutil.which("bwrap") is not None,
        "installed Codex Linux permission-profile runner is required",
    )
    def test_installed_permission_profile_enforces_local_boundary(self) -> None:
        with tempfile.TemporaryDirectory(prefix="learnfactory-profile-host-") as raw:
            root = Path(raw)
            workspace = root / "workspace"
            workspace.mkdir()
            protected = workspace / "STUDENT_SUBMISSION"
            protected.mkdir()
            (protected / "answer.txt").write_text("student-visible\n", encoding="utf-8")
            output = workspace / "OUTPUT"
            output.mkdir()
            sibling = root / "sealed-answer.txt"
            sibling.write_text("sealed\n", encoding="utf-8")
            fake_codex_home = root / "operator-codex-home"
            fake_codex_home.mkdir()
            (fake_codex_home / "auth.json").write_text(
                "not-a-real-secret\n", encoding="utf-8"
            )
            codex = Path(shutil.which("codex") or "").resolve(strict=True)
            with mock.patch.dict(
                os.environ,
                {
                    "CODEX_HOME": str(fake_codex_home),
                    "FACTORY_PROBE_SENTINEL": "must-not-leak",
                },
                clear=False,
            ):
                backend = ExecBackend(str(codex), timeout_seconds=5)
                logs = root / "logs"
                logs.mkdir()
                channel = _private_result_channel(
                    root, "installed-profile", "profile"
                )
                manifest = build_sandbox_rule_manifest(
                    workspace=workspace,
                    log_dir=logs,
                    worker_type="student",
                    payload={
                        "inputs": [
                            {
                                "source": str(protected),
                                "destination": "STUDENT_SUBMISSION",
                            }
                        ],
                        "sandbox_writable_paths": ["OUTPUT"],
                    },
                    result_channel=channel,
                )
                state = _prepared_result_state(
                    backend, channel, _result_alias(logs)
                )
                binding = backend._prepare_result_alias(state)
                _result_alias(logs).write_bytes(b"parent-held-result")
                descriptor = _open_result_output_descriptor(state)
                exact_result_capability = (
                    f"/proc/{os.getpid()}/fd/{descriptor}"
                )
                overrides = backend._permission_overrides(codex, manifest)
                env = os.environ.copy()
                command = [
                    str(codex),
                    "sandbox",
                    "--cd",
                    str(workspace),
                    "--permission-profile",
                    backend.permission_profile,
                ]
                for override in overrides:
                    command.extend(["--config", override])
                probe = """
set -eu
test -r STUDENT_SUBMISSION/answer.txt
! test -r "$1"
! test -r "$2/auth.json"
test -z "${FACTORY_PROBE_SENTINEL+x}"
/usr/bin/python3 - "$3" <<'PY'
import ctypes, os, pathlib, socket, sys
source = pathlib.Path('STUDENT_SUBMISSION/answer.txt')
root = pathlib.Path('STUDENT_SUBMISSION')
output = pathlib.Path('OUTPUT')
result_capability = pathlib.Path(sys.argv[1])

def denied(name, operation):
    try:
        operation()
    except OSError:
        return
    raise SystemExit(name + ' unexpectedly succeeded')

denied('chmod', lambda: source.chmod(0o600))
denied('write', lambda: source.write_text('forged'))
denied('unlink', source.unlink)
denied('rename', lambda: source.rename(output / 'renamed.txt'))
denied('directory rename', lambda: root.rename(output / 'renamed-root'))
denied('directory remove', root.rmdir)
denied('hardlink', lambda: os.link(source, output / 'alias.txt'))
link = output / 'follow.txt'
link.symlink_to(source.resolve())
denied('symlink-follow write', lambda: link.write_text('forged'))
link.unlink()
libc = ctypes.CDLL(None, use_errno=True)
def renameat():
    result = libc.renameat(-100, b'STUDENT_SUBMISSION/answer.txt', -100, b'OUTPUT/renameat.txt')
    if result != 0:
        raise OSError(ctypes.get_errno(), 'renameat denied')
denied('renameat', renameat)
def open_result(flags):
    descriptor = os.open(result_capability, flags)
    os.close(descriptor)
denied('result capability read', result_capability.read_bytes)
denied('result capability write', lambda: result_capability.write_bytes(b'forged'))
denied('result capability open', lambda: open_result(os.O_RDONLY))
denied('result capability truncate', lambda: open_result(os.O_WRONLY | os.O_TRUNC))
(output / 'normal.txt').write_text('allowed')
try:
    value = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
except OSError:
    pass
else:
    value.close()
    raise SystemExit("network socket unexpectedly available")
PY
printf profile-ok
"""
                command.extend(
                    [
                        "--",
                        "/bin/bash",
                        "-c",
                        probe,
                        "probe",
                        str(sibling),
                        str(fake_codex_home),
                        exact_result_capability,
                    ]
                )
                try:
                    completed = subprocess.run(
                        command,
                        cwd=workspace,
                        env=env,
                        text=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        timeout=15,
                        check=False,
                    )
                    self.assertEqual(
                        b"parent-held-result", _result_alias(logs).read_bytes()
                    )
                finally:
                    state.close_output_descriptor()
                    _clean_result_state(backend, state, binding)

            self.assertEqual(
                0,
                completed.returncode,
                msg=f"stdout={completed.stdout}\nstderr={completed.stderr}",
            )
            self.assertEqual("profile-ok", completed.stdout)
            self.assertEqual("allowed", (output / "normal.txt").read_text())
            self.assertEqual("student-visible\n", (protected / "answer.txt").read_text())
            retained_invocation = json.dumps(
                backend.invocation_manifest(
                    workspace,
                    prompt="static",
                    sandbox_manifest=manifest,
                ),
                sort_keys=True,
            )
            self.assertNotRegex(
                retained_invocation, r"/proc/[1-9][0-9]*/fd/[0-9]+"
            )

    @unittest.skipUnless(
        sys.platform.startswith("linux")
        and shutil.which("codex") is not None
        and shutil.which("bwrap") is not None,
        "installed Codex Linux permission-profile runner is required",
    )
    def test_installed_examiner_profile_cannot_start_inner_command(self) -> None:
        with tempfile.TemporaryDirectory(prefix="learnfactory-examiner-profile-") as raw:
            root = Path(raw)
            workspace = root / "workspace"
            logs = root / "logs"
            workspace.mkdir()
            logs.mkdir()
            marker = root / "inner-command-ran"
            codex = Path(shutil.which("codex") or "").resolve(strict=True)
            channel = _private_result_channel(
                root, "installed-no-tool", "examiner"
            )
            manifest = build_sandbox_rule_manifest(
                workspace=workspace,
                log_dir=logs,
                worker_type="examiner",
                payload={
                    "seed_policy": {
                        "kind": "csdiy_course_progression",
                        "role": "examiner",
                    },
                    "artifact_type": "independent-course-unit-evaluation",
                },
                result_channel=channel,
            )
            backend = ExecBackend(str(codex), timeout_seconds=5)
            overrides = backend._permission_overrides(codex, manifest)
            serialized = json.dumps(overrides)
            self.assertNotIn(str(logs), serialized)
            self.assertNotIn(str(channel), serialized)
            command = [
                str(codex),
                "sandbox",
                "--cd",
                str(workspace),
                "--permission-profile",
                backend.permission_profile,
            ]
            for override in overrides:
                command.extend(["--config", override])
            command.extend(
                [
                    "--",
                    "/bin/bash",
                    "-c",
                    "printf escaped > \"$1\"",
                    "probe",
                    str(marker),
                ]
            )
            completed = subprocess.run(
                command,
                cwd=workspace,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=15,
                check=False,
            )
            self.assertNotEqual(0, completed.returncode)
            self.assertFalse(marker.exists())

    def test_cancellation_terminates_same_group_descendants(self) -> None:
        with tempfile.TemporaryDirectory(prefix="learnfactory-backend-cancel-") as raw:
            root = Path(raw)
            workspace = root / "workspace"
            workspace.mkdir()
            marker = workspace / "late-child-write.txt"
            executable = root / "fake-codex"
            child = (
                "import pathlib,signal,time; "
                "signal.signal(signal.SIGINT, signal.SIG_IGN); "
                "signal.signal(signal.SIGTERM, signal.SIG_IGN); "
                "time.sleep(0.5); "
                f"pathlib.Path({str(marker)!r}).write_text('escaped')"
            )
            executable.write_text(
                "#!/usr/bin/env python3\n"
                "import subprocess,sys,time\n"
                f"subprocess.Popen([sys.executable, '-c', {child!r}])\n"
                "time.sleep(30)\n",
                encoding="utf-8",
            )
            executable.chmod(0o755)
            cancel = threading.Event()
            timer = threading.Timer(0.15, cancel.set)
            timer.start()
            result = ExecBackend(str(executable), timeout_seconds=5).start_job(
                "cancel me", workspace, root / "logs", cancel_event=cancel
            )
            timer.cancel()
            self.assertTrue(result.cancelled)
            time.sleep(0.7)
            self.assertFalse(marker.exists())

    def test_retained_streams_and_last_message_are_bounded_and_redacted(self) -> None:
        with tempfile.TemporaryDirectory(prefix="learnfactory-backend-retained-") as raw:
            root = Path(raw)
            workspace = root / "workspace"
            logs = root / "logs"
            workspace.mkdir()
            executable = root / "fake-codex"
            executable.write_text(
                "#!/usr/bin/env python3\n"
                "import json,pathlib,sys\n"
                "args=sys.argv[1:]\n"
                "target=pathlib.Path(args[args.index('--output-last-message')+1])\n"
                "target.write_text('BEGIN api_key=last-message-secret\\n' + 'm'*8000 + '\\nEND')\n"
                "print(json.dumps({'type':'thread.started','thread_id':'thread-bounded'}))\n"
                "print('x'*12000)\n"
                "print(json.dumps({'type':'turn.completed','usage':{'input_tokens':41,'output_tokens':7}}))\n"
                "print('password=stderr-secret', file=sys.stderr)\n"
                "print('y'*12000, file=sys.stderr)\n",
                encoding="utf-8",
            )
            executable.chmod(0o755)

            result = ExecBackend(
                str(executable),
                timeout_seconds=5,
                log_limit_bytes=2048,
                last_message_limit_bytes=512,
            ).start_job("retain safely", workspace, logs)

            self.assertEqual(125, result.exit_code)
            self.assertEqual("thread-bounded", result.session_id)
            self.assertEqual({"input_tokens": 41, "output_tokens": 7}, result.usage)
            for name, limit in (
                ("codex.jsonl", 2048),
                ("codex.stderr.log", 2048),
                ("codex.last-message.txt", 512),
            ):
                self.assertLessEqual((logs / name).stat().st_size, limit)
            retained = "\n".join(
                (logs / name).read_text(encoding="utf-8")
                for name in (
                    "codex.jsonl",
                    "codex.stderr.log",
                    "codex.last-message.txt",
                )
            )
            self.assertNotIn("stderr-secret", retained)
            self.assertNotIn("last-message-secret", retained)
            self.assertIn("password=<redacted>", retained)
            self.assertNotIn("last-message-secret", retained)
            self.assertEqual("", result.final_message)
            self.assertIn("result exceeds retained-message limit", result.stderr_tail)

    def test_normal_cli_exit_still_terminates_process_group_descendants(self) -> None:
        with tempfile.TemporaryDirectory(prefix="learnfactory-backend-normal-exit-") as raw:
            root = Path(raw)
            workspace = root / "workspace"
            workspace.mkdir()
            marker = workspace / "late-child-write.txt"
            executable = root / "fake-codex"
            child = (
                "import pathlib,signal,time; "
                "signal.signal(signal.SIGTERM, signal.SIG_IGN); "
                "time.sleep(0.6); "
                f"pathlib.Path({str(marker)!r}).write_text('escaped')"
            )
            executable.write_text(
                "#!/usr/bin/env python3\n"
                "import json,subprocess,sys\n"
                f"subprocess.Popen([sys.executable, '-c', {child!r}])\n"
                "print(json.dumps({'thread_id':'normal-parent'}))\n",
                encoding="utf-8",
            )
            executable.chmod(0o755)

            result = ExecBackend(str(executable), timeout_seconds=5).start_job(
                "parent exits normally", workspace, root / "logs"
            )

            self.assertEqual(0, result.exit_code)
            self.assertEqual("normal-parent", result.session_id)
            time.sleep(0.8)
            self.assertFalse(marker.exists())

    def test_result_channel_is_not_inherited_by_fd_bruteforce_child(self) -> None:
        with tempfile.TemporaryDirectory(prefix="learnfactory-backend-channel-") as raw:
            root = Path(raw)
            workspace = root / "workspace"
            logs = root / "logs"
            workspace.mkdir()
            marker = workspace / "late-forgery.txt"
            pid_marker = workspace / "detached.pid"
            trusted = '{"evaluation":{"result":"PASS"},"feedback":"trusted"}'
            forged = b'{"evaluation":{"result":"PASS","score":100},"feedback":"forged"}\n'
            child = (
                "import os,pathlib,signal,time\n"
                "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
                f"pathlib.Path({str(pid_marker)!r}).write_text(str(os.getpid()))\n"
                f"value={forged!r}\n"
                "for fd in range(3,256):\n"
                "    try:\n"
                "        os.write(fd,value)\n"
                "    except OSError:\n"
                "        pass\n"
                "time.sleep(0.7)\n"
                f"pathlib.Path({str(marker)!r}).write_text('escaped')\n"
            )
            # The trusted CLI opens its result path only after spawning the
            # candidate. No special descriptor is inherited by that child.
            executable = root / "fake-codex"
            executable.write_text(
                "#!/usr/bin/env python3\n"
                "import pathlib,subprocess,sys,time\n"
                "args=sys.argv[1:]\n"
                f"subprocess.Popen([sys.executable, '-c', {child!r}], "
                "stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, "
                "start_new_session=True)\n"
                "time.sleep(0.1)\n"
                "target=pathlib.Path(args[args.index('--output-last-message')+1])\n"
                f"target.write_text({trusted!r})\n",
                encoding="utf-8",
            )
            executable.chmod(0o755)

            result = ExecBackend(str(executable), timeout_seconds=5).start_job(
                "static review", workspace, logs
            )

            self.assertEqual(0, result.exit_code)
            self.assertEqual(trusted, result.final_message)
            self.assertNotIn("forged", result.final_message)
            detached_pid = int(pid_marker.read_text())
            with self.assertRaises(ProcessLookupError):
                os.kill(detached_pid, 0)
            time.sleep(0.9)
            self.assertFalse(marker.exists())

    def test_invalid_timeout_is_rejected_before_cli_spawn(self) -> None:
        with tempfile.TemporaryDirectory(prefix="learnfactory-backend-timeout-") as raw:
            root = Path(raw)
            workspace = root / "workspace"
            workspace.mkdir()
            marker = workspace / "spawned.txt"
            executable = root / "fake-codex"
            executable.write_text(
                "#!/usr/bin/env python3\n"
                "from pathlib import Path\n"
                f"Path({str(marker)!r}).write_text('spawned')\n",
                encoding="utf-8",
            )
            executable.chmod(0o755)

            for index, timeout in enumerate((0, -1, math.nan, math.inf, -math.inf)):
                with self.subTest(timeout=timeout):
                    result = ExecBackend(str(executable), timeout_seconds=timeout).start_job(
                        "must not spawn", workspace, root / f"logs-{index}"
                    )
                    self.assertNotEqual(0, result.exit_code)
                    self.assertIn("finite positive", result.stderr_tail)
            self.assertFalse(marker.exists())

            oversized = ExecBackend(
                str(executable), timeout_seconds=5, prompt_limit_bytes=1024
            ).start_job("x" * 1025, workspace, root / "logs-oversized-prompt")
            self.assertNotEqual(0, oversized.exit_code)
            self.assertIn("limit is 1024 bytes", oversized.stderr_tail)
            self.assertFalse(marker.exists())

    def test_blocked_large_prompt_write_obeys_timeout_and_cancellation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="learnfactory-backend-stdin-") as raw:
            root = Path(raw)
            workspace = root / "workspace"
            workspace.mkdir()
            executable = root / "fake-codex"
            executable.write_text(
                "#!/usr/bin/env python3\n"
                "import time\n"
                "time.sleep(30)\n",
                encoding="utf-8",
            )
            executable.chmod(0o755)
            prompt = "p" * (512 * 1024)

            started = time.monotonic()
            timed_out = ExecBackend(
                str(executable), timeout_seconds=0.2, prompt_limit_bytes=1024 * 1024
            ).start_job(prompt, workspace, root / "logs-timeout")
            timeout_elapsed = time.monotonic() - started
            self.assertTrue(timed_out.timed_out)
            self.assertLess(timeout_elapsed, 3)

            cancel = threading.Event()
            timer = threading.Timer(0.15, cancel.set)
            timer.start()
            started = time.monotonic()
            cancelled = ExecBackend(
                str(executable), timeout_seconds=5, prompt_limit_bytes=1024 * 1024
            ).start_job(
                prompt,
                workspace,
                root / "logs-cancel",
                cancel_event=cancel,
            )
            cancel_elapsed = time.monotonic() - started
            timer.cancel()
            self.assertTrue(cancelled.cancelled)
            self.assertLess(cancel_elapsed, 3)


if __name__ == "__main__":
    unittest.main()
