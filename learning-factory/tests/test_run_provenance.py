from __future__ import annotations

import hashlib
import json
import os
import stat
import subprocess
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest import mock

from learnfactory.config import BackendSettings, FactorySettings
from learnfactory.run_provenance import (
    _frame,
    _git,
    capture_run_provenance,
    unavailable_run_provenance,
    write_run_provenance,
)
from learnfactory.result_channel import (
    placeholder_result_channel,
    result_channel_contract,
)
from learnfactory.util import canonical_json


class RunProvenanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="learnfactory-run-provenance-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / "src").mkdir()
        (self.root / "migrations").mkdir()
        (self.root / "bin").mkdir()
        (self.root / "toolchain").mkdir()
        (self.root / "src" / "engine.py").write_text("VERSION = 1\n", encoding="utf-8")
        (self.root / "migrations" / "001.sql").write_text("SELECT 1;\n", encoding="utf-8")
        executable = self.root / "bin" / "codex"
        executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        executable.chmod(0o755)
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        subprocess.run(
            ["git", "-C", str(self.root), "config", "user.name", "Test"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(self.root), "config", "user.email", "test@example.invalid"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(self.root), "add", "src", "migrations"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(self.root), "commit", "-qm", "fixture"],
            check=True,
        )
        (self.root / "src" / "engine.py").write_text("VERSION = 2\n", encoding="utf-8")
        (self.root / "src" / "new_worker.py").write_text("ENABLED = True\n", encoding="utf-8")
        self.config_path = self.root / "factory.toml"
        self.config_path.write_text("# raw config is never copied\n", encoding="utf-8")
        self.workspace = self.root / "workspace" / "attempt-001"
        self.log_dir = self.root / "warehouse" / "logs" / "job-1" / "attempt-001"
        self.workspace.mkdir(parents=True)
        self.settings = FactorySettings(
            root=self.root,
            database=self.root / "warehouse" / "factory.db",
            warehouse=self.root / "warehouse",
            config_path=self.config_path,
            max_concurrency=12,
            limits={"student": 2, "reference_builder": 5},
            backend=BackendSettings(
                command=str(executable),
                permission_profile="factory-isolated",
                toolchain_read_roots=(),
                model="gpt-5.6-sol",
                reasoning_effort="ultra",
                provider="arm",
                provider_name="token=CONFIG_SECRET_SENTINEL",
                base_url=(
                    "https://user:CONFIG_SECRET_SENTINEL@proxy.example.invalid/v1"
                    "?api_key=CONFIG_SECRET_SENTINEL"
                ),
                requires_openai_auth=True,
                supports_websockets=False,
            ),
        )
        self.payload = {
            "seed_policy": {"kind": "test", "version": 1, "role": "student"},
            "prompt": "api_key=PAYLOAD_SECRET_SENTINEL produce output",
            "output_schema": {
                "type": "object",
                "properties": {"answer": {"type": "string"}},
            },
            "validators": [{"type": "required_paths", "paths": ["answer.txt"]}],
            "artifact_type": "test-output",
            "artifact_path": "tests/output",
            "timeout_seconds": 37,
        }

    def _capture(
        self,
        *,
        settings: FactorySettings | None = None,
        payload: dict[str, object] | None = None,
    ):
        return capture_run_provenance(
            settings or self.settings,
            job_id="job-1",
            job_type="codex_task",
            worker_type="student",
            payload=self.payload if payload is None else payload,
            dependency_job_ids=["dependency-b", "dependency-a"],
            workspace=self.workspace,
            log_dir=self.log_dir,
            effective_model="gpt-5.6-sol",
            effective_reasoning="ultra",
        )

    def test_record_is_deterministic_complete_and_secret_safe(self) -> None:
        with mock.patch.dict(
            os.environ,
            {
                "OPERATOR_SECRET": "ENV_SECRET_SENTINEL",
                "CODEX_HOME": "/opaque/CODEX_HOME_SECRET_SENTINEL",
            },
            clear=False,
        ):
            first = self._capture()
            second = self._capture()

        self.assertEqual(first.digest, second.digest)
        self.assertEqual(first.metadata, second.metadata)
        self.assertEqual("learnfactory-run-provenance-v3", first.metadata["schema"])
        self.assertEqual("RECORDED", first.metadata["status"])
        self.assertEqual("safe-execution-envelope", first.metadata["binding"]["scope"])
        self.assertRegex(first.digest, r"^[0-9a-f]{64}$")
        self.assertEqual(
            hashlib.sha256(
                canonical_json(
                    {
                        "schema": first.metadata["schema"],
                        "status": first.metadata["status"],
                        "components": first.metadata["components"],
                    }
                ).encode("utf-8")
            ).hexdigest(),
            first.digest,
        )
        repository = first.metadata["repository"]
        self.assertEqual("RECORDED", repository["status"])
        self.assertFalse(repository["tracked_worktree_clean"])
        self.assertEqual(["src/engine.py"], repository["dirty_tracked_paths"])
        self.assertEqual(["src/new_worker.py"], repository["untracked_paths"])
        self.assertEqual("COMPLETE", repository["tracked"]["status"])
        self.assertEqual("COMPLETE", repository["untracked"]["status"])
        self.assertEqual(
            ["dependency-a", "dependency-b"],
            first.metadata["policy"]["dependency_job_ids"],
        )
        invocation = first.metadata["invocation"]
        self.assertEqual("RECORDED", invocation["status"])
        self.assertEqual("gpt-5.6-sol", invocation["model"])
        self.assertEqual("ultra", invocation["reasoning_effort"])
        self.assertEqual(37.0, invocation["timeout_seconds"])
        self.assertIn(
            "<controller-result-file-capability>",
            invocation["argv"],
        )
        self.assertEqual(
            "parent-held-fixed-alias-file-descriptor",
            invocation["dynamic_placeholders"][
                "<controller-result-file-capability>"
            ]["kind"],
        )
        self.assertEqual(
            result_channel_contract(),
            invocation["result_channel"],
        )
        self.assertIn("<cli-executable>", invocation["argv"])
        self.assertEqual("RECORDED", invocation["cli_binary"]["status"])
        self.assertRegex(invocation["cli_binary"]["sha256"], r"^[0-9a-f]{64}$")
        self.assertTrue(invocation["prompt"]["includes_leaf_worker_policy"])
        self.assertFalse(invocation["prompt"]["content_stored"])
        self.assertRegex(
            invocation["leaf_worker_policy"]["sha256"], r"^[0-9a-f]{64}$"
        )
        safe_prompt = b"api_key=<redacted> produce output"
        self.assertEqual(
            hashlib.sha256(safe_prompt).hexdigest(),
            invocation["job_prompt"]["sha256"],
        )
        self.assertEqual(
            "safe-redacted-envelope", invocation["job_prompt"]["binding_scope"]
        )
        self.assertEqual(
            "safe-redacted-envelope",
            first.metadata["policy"]["payload_binding_scope"],
        )
        self.assertNotEqual(
            invocation["job_prompt"]["sha256"], invocation["prompt"]["sha256"]
        )
        rendered = json.dumps(first.metadata, sort_keys=True)
        for forbidden in (
            "CONFIG_SECRET_SENTINEL",
            "PAYLOAD_SECRET_SENTINEL",
            "ENV_SECRET_SENTINEL",
            "CODEX_HOME_SECRET_SENTINEL",
        ):
            self.assertNotIn(forbidden, rendered)
        internal_channel = placeholder_result_channel(self.log_dir)
        self.assertNotIn(".codex-final-", rendered)
        self.assertNotIn(
            hashlib.sha256(str(internal_channel).encode()).hexdigest(), rendered
        )
        self.assertNotIn(
            hashlib.sha256(internal_channel.parent.name.encode()).hexdigest(), rendered
        )
        self.assertIn("<external-provider-name-omitted>", rendered)

    def test_frame_hashes_one_length_prefix_and_one_value(self) -> None:
        actual = hashlib.sha256()
        _frame(actual, b"ab")
        _frame(actual, b"c")

        expected = hashlib.sha256()
        expected.update((2).to_bytes(8, "big"))
        expected.update(b"ab")
        expected.update((1).to_bytes(8, "big"))
        expected.update(b"c")
        self.assertEqual(expected.hexdigest(), actual.hexdigest())

    def test_read_only_git_queries_disable_optional_index_locks(self) -> None:
        completed = subprocess.CompletedProcess(
            ["git"], 0, stdout=b"", stderr=b""
        )
        with mock.patch.dict(
            os.environ, {"GIT_OPTIONAL_LOCKS": "1"}, clear=False
        ), mock.patch(
            "learnfactory.run_provenance.subprocess.run",
            return_value=completed,
        ) as run:
            self.assertIs(completed, _git(self.root, "rev-parse", "HEAD"))
            self.assertEqual("1", os.environ["GIT_OPTIONAL_LOCKS"])

        self.assertEqual("0", run.call_args.kwargs["env"]["GIT_OPTIONAL_LOCKS"])
        self.assertEqual(
            [
                "git",
                "-c",
                "diff.autoRefreshIndex=false",
                "-C",
                str(self.root),
                "rev-parse",
                "HEAD",
            ],
            run.call_args.args[0],
        )
        self.assertEqual(10, run.call_args.kwargs["timeout"])

    def test_untracked_content_changes_code_and_combined_digest(self) -> None:
        first = self._capture()
        (self.root / "src" / "new_worker.py").write_text(
            "ENABLED = False\n", encoding="utf-8"
        )
        second = self._capture()

        self.assertNotEqual(
            first.metadata["components"]["code_sha256"],
            second.metadata["components"]["code_sha256"],
        )
        self.assertNotEqual(first.digest, second.digest)
        self.assertEqual(
            first.metadata["components"]["safe_configuration_sha256"],
            second.metadata["components"]["safe_configuration_sha256"],
        )
        self.assertEqual(
            first.metadata["components"]["safe_policy_sha256"],
            second.metadata["components"]["safe_policy_sha256"],
        )

    def test_repository_revision_is_bound_even_when_worktree_bytes_do_not_change(self) -> None:
        first = self._capture()
        subprocess.run(
            [
                "git",
                "-C",
                str(self.root),
                "commit",
                "--allow-empty",
                "-qm",
                "new provenance identity",
            ],
            check=True,
        )
        second = self._capture()

        self.assertNotEqual(
            first.metadata["repository"]["commit"],
            second.metadata["repository"]["commit"],
        )
        self.assertNotEqual(
            first.metadata["components"]["code_sha256"],
            second.metadata["components"]["code_sha256"],
        )
        self.assertNotEqual(first.digest, second.digest)

    def test_secret_substitutions_are_excluded_before_hashing(self) -> None:
        first_backend = replace(
            self.settings.backend,
            provider_name="OPAQUE_PROVIDER_VALUE_ALPHA",
            base_url=(
                "https://OPAQUE_USER_ALPHA:OPAQUE_PASSWORD_ALPHA@proxy.example.invalid/v1"
                "?session=OPAQUE_QUERY_ALPHA#OPAQUE_FRAGMENT_ALPHA"
            ),
        )
        second_backend = replace(
            first_backend,
            provider_name="OPAQUE_PROVIDER_VALUE_BRAVO",
            base_url=(
                "https://OPAQUE_USER_BRAVO:OPAQUE_PASSWORD_BRAVO@proxy.example.invalid/v1"
                "?session=OPAQUE_QUERY_BRAVO#OPAQUE_FRAGMENT_BRAVO"
            ),
        )
        first_settings = replace(self.settings, backend=first_backend)
        second_settings = replace(self.settings, backend=second_backend)
        first_payload = {
            **self.payload,
            "prompt": "password=LOW_ENTROPY_ALPHA produce stable output",
            "api_key": "OPAQUE_PAYLOAD_ALPHA",
        }
        second_payload = {
            **first_payload,
            "prompt": "password=LOW_ENTROPY_BRAVO produce stable output",
            "api_key": "OPAQUE_PAYLOAD_BRAVO",
        }

        first = self._capture(settings=first_settings, payload=first_payload)
        second = self._capture(settings=second_settings, payload=second_payload)

        self.assertEqual(first.digest, second.digest)
        self.assertEqual(
            first.metadata["components"]["safe_configuration_sha256"],
            second.metadata["components"]["safe_configuration_sha256"],
        )
        self.assertEqual(
            first.metadata["components"]["safe_policy_sha256"],
            second.metadata["components"]["safe_policy_sha256"],
        )
        self.assertEqual(
            first.metadata["components"]["safe_invocation_sha256"],
            second.metadata["components"]["safe_invocation_sha256"],
        )
        self.assertEqual(
            "safe-redacted-envelope",
            first.metadata["policy"]["payload_binding_scope"],
        )
        self.assertEqual(
            "safe-redacted-envelope",
            first.metadata["invocation"]["job_prompt"]["binding_scope"],
        )
        base_url = first.metadata["configuration"]["backend"]["base_url"]
        self.assertEqual("https://proxy.example.invalid/v1", base_url["safe_endpoint"])
        self.assertTrue(base_url["userinfo_omitted"])
        self.assertTrue(base_url["query_omitted"])
        self.assertTrue(base_url["fragment_omitted"])
        self.assertEqual(
            "<external-provider-name-omitted>",
            first.metadata["configuration"]["backend"]["provider_name"]["value"],
        )

        rendered = canonical_json(first.metadata)
        raw_hashes = (
            hashlib.sha256(first_payload["prompt"].encode("utf-8")).hexdigest(),
            hashlib.sha256(canonical_json(first_payload).encode("utf-8")).hexdigest(),
            hashlib.sha256(b"LOW_ENTROPY_ALPHA").hexdigest(),
            hashlib.sha256(b"OPAQUE_PAYLOAD_ALPHA").hexdigest(),
        )
        for forbidden in (
            "OPAQUE_PROVIDER_VALUE_ALPHA",
            "OPAQUE_USER_ALPHA",
            "OPAQUE_PASSWORD_ALPHA",
            "OPAQUE_QUERY_ALPHA",
            "OPAQUE_FRAGMENT_ALPHA",
            "LOW_ENTROPY_ALPHA",
            "OPAQUE_PAYLOAD_ALPHA",
            *raw_hashes,
        ):
            self.assertNotIn(forbidden, rendered)

    def test_non_secret_prompt_bytes_remain_exactly_bound(self) -> None:
        first_payload = {**self.payload, "prompt": "produce alpha output"}
        second_payload = {**first_payload, "prompt": "produce bravo output"}

        first = self._capture(payload=first_payload)
        second = self._capture(payload=second_payload)

        self.assertEqual("exact", first.metadata["policy"]["payload_binding_scope"])
        self.assertEqual(
            "exact", first.metadata["invocation"]["job_prompt"]["binding_scope"]
        )
        self.assertEqual(
            hashlib.sha256(b"produce alpha output").hexdigest(),
            first.metadata["invocation"]["job_prompt"]["sha256"],
        )
        self.assertNotEqual(
            first.metadata["components"]["safe_policy_sha256"],
            second.metadata["components"]["safe_policy_sha256"],
        )
        self.assertNotEqual(
            first.metadata["components"]["safe_invocation_sha256"],
            second.metadata["components"]["safe_invocation_sha256"],
        )
        self.assertNotEqual(first.digest, second.digest)

    def test_cli_binary_bytes_are_bound_without_storing_its_path(self) -> None:
        first = self._capture()
        executable = Path(self.settings.backend.command)
        executable.write_text("#!/bin/sh\n# revision two\nexit 0\n", encoding="utf-8")
        executable.chmod(0o755)
        second = self._capture()

        self.assertEqual(
            first.metadata["components"]["code_sha256"],
            second.metadata["components"]["code_sha256"],
        )
        self.assertNotEqual(
            first.metadata["invocation"]["cli_binary"]["sha256"],
            second.metadata["invocation"]["cli_binary"]["sha256"],
        )
        self.assertNotEqual(
            first.metadata["components"]["safe_invocation_sha256"],
            second.metadata["components"]["safe_invocation_sha256"],
        )
        self.assertNotIn(str(executable), canonical_json(first.metadata))
        self.assertNotEqual(first.digest, second.digest)

    def test_empty_output_schema_is_recorded_as_absent_like_execution(self) -> None:
        record = self._capture(payload={**self.payload, "output_schema": {}})

        self.assertFalse(record.metadata["invocation"]["output_schema"]["present"])
        self.assertIsNone(record.metadata["invocation"]["output_schema"]["sha256"])
        self.assertNotIn("--output-schema", record.metadata["invocation"]["argv"])

    def test_capture_failure_does_not_store_or_hash_exception_message(self) -> None:
        first = unavailable_run_provenance(
            RuntimeError("opaque failure OPAQUE_EXCEPTION_SECRET_ALPHA")
        )
        second = unavailable_run_provenance(
            RuntimeError("opaque failure OPAQUE_EXCEPTION_SECRET_BRAVO")
        )

        self.assertEqual(first.digest, second.digest)
        self.assertEqual("CAPTURE_FAILED", first.metadata["status"])
        self.assertEqual("RuntimeError", first.metadata["error"]["type"])
        rendered = canonical_json(first.metadata)
        self.assertNotIn("OPAQUE_EXCEPTION_SECRET_ALPHA", rendered)
        self.assertNotIn(
            hashlib.sha256(b"opaque failure OPAQUE_EXCEPTION_SECRET_ALPHA").hexdigest(),
            rendered,
        )

    def test_human_record_is_private_and_matches_database_metadata(self) -> None:
        record = self._capture()
        stale = self.log_dir / f".RUN_PROVENANCE.{os.getpid()}.tmp"
        stale.parent.mkdir(parents=True, exist_ok=True)
        stale.write_text("stale writer state", encoding="utf-8")
        path = write_run_provenance(self.log_dir, record)
        path.chmod(0o644)
        path = write_run_provenance(self.log_dir, record)

        self.assertEqual("RUN_PROVENANCE.json", path.name)
        self.assertEqual(record.metadata, json.loads(path.read_text(encoding="utf-8")))
        self.assertEqual(0o600, stat.S_IMODE(path.stat().st_mode))
        self.assertTrue(stale.exists())
        self.assertEqual({stale}, set(self.log_dir.glob(".RUN_PROVENANCE.*.tmp")))


if __name__ == "__main__":
    unittest.main()
