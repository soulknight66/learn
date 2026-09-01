from __future__ import annotations

import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

from learnfactory.backends.exec_backend import ExecBackend
from learnfactory.config import load_settings


ROOT = Path(__file__).resolve().parents[1]


class ExecBackendTests(unittest.TestCase):
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
            manifest = backend.invocation_manifest(
                workspace,
                prompt="build the artifact",
                model="gpt-5.6-sol",
                reasoning_effort="ultra",
                timeout_seconds=5,
            )
            result = backend.start_job(
                "build the artifact",
                workspace,
                logs,
                model="gpt-5.6-sol",
                reasoning_effort="ultra",
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
            actual[descriptor_index] = "<INHERITED_OUTPUT_FD>"
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
        self.assertEqual(
            ("/arm/tools/python/python/3.11.5/rhe8-x86_64",),
            settings.backend.toolchain_read_roots,
        )
        self.assertFalse(hasattr(settings.backend, "sandbox"))

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
            (workspace / "JOB.md").write_text("student-visible\n", encoding="utf-8")
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
                overrides = backend._permission_overrides(codex)
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
test -r JOB.md
! test -r "$1"
! test -r "$2/auth.json"
test -z "${FACTORY_PROBE_SENTINEL+x}"
/usr/bin/python3 - <<'PY'
import socket
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
                    ["--", "/bin/bash", "-c", probe, "probe", str(sibling), str(fake_codex_home)]
                )
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
                0,
                completed.returncode,
                msg=f"stdout={completed.stdout}\nstderr={completed.stderr}",
            )
            self.assertEqual("profile-ok", completed.stdout)

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

            self.assertEqual(0, result.exit_code)
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
            self.assertIn("api_key=<redacted>", retained)
            self.assertNotIn("last-message-secret", result.final_message)
            self.assertLessEqual(len(result.final_message.encode("utf-8")), 512)

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
