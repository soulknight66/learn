from __future__ import annotations

import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from learnfactory.config import load_settings
from learnfactory.db import Database
from learnfactory.jobs import JobRepository
from learnfactory.reporting import status_snapshot, write_catalog
from learnfactory.review_contract import MAX_REVIEW_EVALUATION_BYTES
from learnfactory.scheduler import run_scheduler
from learnfactory.seeding import BYOX_REVIEW_CONTRACT_VERSION
from learnfactory.validation import Validator
from learnfactory.workspace import WorkspaceManager


ROOT = Path(__file__).resolve().parents[1]


class ByoxReviewSemanticsTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="learnfactory-byox-review-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.config_path = self.root / "factory.toml"
        database_path = self.root / "factory.db"
        warehouse_path = self.root / "warehouse"
        self.config_path.write_text(
            "\n".join(
                [
                    "[factory]",
                    f'database = "{database_path}"',
                    f'warehouse = "{warehouse_path}"',
                    "lease_seconds = 5",
                    "heartbeat_seconds = 0.05",
                    "poll_seconds = 0.01",
                    "max_concurrency = 6",
                    "allow_host_command_validators = true",
                    "shutdown_grace_seconds = 1",
                    "[backend]",
                    'name = "exec"',
                    'command = "codex"',
                    'sandbox = "workspace-write"',
                    'model = "gpt-5.6-sol"',
                    'reasoning_effort = "ultra"',
                    "timeout_seconds = 5",
                    "[limits]",
                    "test = 6",
                    "[retry]",
                    "base_seconds = 0.01",
                    "max_seconds = 0.02",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        self.settings = load_settings(self.config_path)
        self.database = Database(self.settings.database, self.settings.migrations)
        self.database.migrate()
        WorkspaceManager(self.settings.warehouse, self.database).initialize()
        self.jobs = JobRepository(self.database, retry_base=0.01, retry_max=0.02)

    def _validator_job(
        self, suffix: str, payload: dict[str, object] | None = None
    ) -> str:
        return self.jobs.create(
            "test", "test", payload or {}, job_id=f"job_verdict_{suffix}"
        )

    def test_verdict_validator_preserves_negative_outcomes_without_review_claim(self) -> None:
        outcomes = {}
        for verdict in ("PASS", "REVISE", "FAIL"):
            job_id = self._validator_job(verdict.lower())
            workspace = self.root / f"validator-{verdict.lower()}"
            workspace.mkdir()
            (workspace / "EVALUATION.json").write_text(
                json.dumps(
                    {
                        "project_id": f"project-{verdict.lower()}",
                        "builder_job_id": f"builder-{verdict.lower()}",
                        "verdict": verdict,
                        "evidence": ["observed result"],
                        "checks_run": ["bounded deterministic check"],
                        "limitations": [],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            [result] = Validator(self.database).run(
                job_id,
                workspace,
                [
                    {
                        "type": "review_verdict",
                        "name": "byox-independent-review-verdict",
                        "path": "EVALUATION.json",
                        "contract_version": BYOX_REVIEW_CONTRACT_VERSION,
                    }
                ],
                self.root / "logs" / job_id,
            )
            outcomes[verdict] = result

        self.assertEqual(
            ["PASS", "PASS", "PASS"],
            [outcomes[value].status for value in ("PASS", "REVISE", "FAIL")],
        )
        self.assertEqual((), outcomes["PASS"].claims)
        self.assertEqual((), outcomes["REVISE"].claims)
        self.assertEqual((), outcomes["FAIL"].claims)
        for verdict, result in outcomes.items():
            self.assertEqual(
                f"project-{verdict.lower()}", result.evidence["project_id"]
            )
            self.assertEqual(
                f"builder-{verdict.lower()}", result.evidence["builder_job_id"]
            )
            self.assertEqual(verdict, result.evidence["verdict"])
            self.assertEqual(
                verdict == "PASS",
                result.evidence["reviewer_recommends_acceptance"],
            )
            self.assertFalse(result.evidence["workflow_accepted"])
            self.assertEqual(
                BYOX_REVIEW_CONTRACT_VERSION,
                result.evidence["contract_version"],
            )
            self.assertEqual(
                {"evidence": 1, "checks_run": 1, "limitations": 0},
                result.evidence["entry_counts"],
            )
            self.assertEqual(64, len(result.evidence["evaluation_sha256"]))

        for suffix, invalid_verdict in (
            ("unknown", "ACCEPT"),
            ("nonstr", ["PASS"]),
        ):
            invalid_job = self._validator_job(suffix)
            invalid_workspace = self.root / f"validator-{suffix}"
            invalid_workspace.mkdir()
            (invalid_workspace / "EVALUATION.json").write_text(
                json.dumps(
                    {
                        "project_id": f"project-{suffix}",
                        "builder_job_id": f"builder-{suffix}",
                        "verdict": invalid_verdict,
                        "evidence": ["observed result"],
                        "checks_run": ["check"],
                        "limitations": [],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            [invalid] = Validator(self.database).run(
                invalid_job,
                invalid_workspace,
                [
                    {
                        "type": "review_verdict",
                        "path": "EVALUATION.json",
                        "contract_version": BYOX_REVIEW_CONTRACT_VERSION,
                    }
                ],
                self.root / "logs" / invalid_job,
            )
            self.assertEqual("FAIL", invalid.status)
            self.assertEqual((), invalid.claims)

    def test_verdict_contract_rejects_unversioned_empty_or_untrimmed_evidence(self) -> None:
        valid = {
            "project_id": "project-contract",
            "builder_job_id": "builder-contract",
            "verdict": "REVISE",
            "evidence": ["concrete evidence"],
            "checks_run": ["python -m unittest"],
            "limitations": [],
        }
        cases = {
            "missing-version": (valid, None, "ERROR"),
            "wrong-version": (valid, 1, "ERROR"),
            "empty-evidence": (
                {**valid, "evidence": []},
                BYOX_REVIEW_CONTRACT_VERSION,
                "FAIL",
            ),
            "empty-checks": (
                {**valid, "checks_run": []},
                BYOX_REVIEW_CONTRACT_VERSION,
                "FAIL",
            ),
            "whitespace-evidence": (
                {**valid, "evidence": ["  "]},
                BYOX_REVIEW_CONTRACT_VERSION,
                "FAIL",
            ),
            "leading-space": (
                {**valid, "checks_run": [" check"]},
                BYOX_REVIEW_CONTRACT_VERSION,
                "FAIL",
            ),
            "trailing-space": (
                {**valid, "limitations": ["limit "]},
                BYOX_REVIEW_CONTRACT_VERSION,
                "FAIL",
            ),
            "non-string-limit": (
                {**valid, "limitations": [1]},
                BYOX_REVIEW_CONTRACT_VERSION,
                "FAIL",
            ),
            "missing-limitations": (
                {key: value for key, value in valid.items() if key != "limitations"},
                BYOX_REVIEW_CONTRACT_VERSION,
                "FAIL",
            ),
        }
        for suffix, (evaluation, contract_version, expected) in cases.items():
            with self.subTest(suffix=suffix):
                job_id = self._validator_job(f"contract-{suffix}")
                workspace = self.root / f"contract-{suffix}"
                workspace.mkdir()
                (workspace / "EVALUATION.json").write_text(
                    json.dumps(evaluation) + "\n", encoding="utf-8"
                )
                specification: dict[str, object] = {
                    "type": "review_verdict",
                    "path": "EVALUATION.json",
                }
                if contract_version is not None:
                    specification["contract_version"] = contract_version
                [result] = Validator(self.database).run(
                    job_id,
                    workspace,
                    [specification],
                    self.root / "logs" / job_id,
                )
                self.assertEqual(expected, result.status)
                self.assertEqual((), result.claims)

    def test_schema_validator_persists_the_canonical_pass_evidence_shape(self) -> None:
        job_id = self._validator_job("schema-evidence")
        workspace = self.root / "schema-evidence"
        workspace.mkdir()
        evaluation = {
            "project_id": "project-schema-evidence",
            "builder_job_id": "builder-schema-evidence",
            "verdict": "PASS",
            "evidence": ["observed"],
            "checks_run": ["checked"],
            "limitations": [],
        }
        (workspace / "EVALUATION.json").write_text(
            json.dumps(evaluation) + "\n", encoding="utf-8"
        )
        [result] = Validator(self.database).run(
            job_id,
            workspace,
            [
                {
                    "type": "json_schema",
                    "name": "byox-independent-review-schema",
                    "path": "EVALUATION.json",
                    "schema": {
                        "type": "object",
                        "properties": {
                            key: {"type": "string"}
                            for key in ("project_id", "builder_job_id", "verdict")
                        },
                        "required": ["project_id", "builder_job_id", "verdict"],
                    },
                }
            ],
            self.root / "logs" / job_id,
        )
        self.assertEqual("PASS", result.status)
        self.assertEqual({"errors": [], "error_count": 0}, result.evidence)

    def test_required_review_paths_persist_exact_canonical_evidence(self) -> None:
        job_id = self._validator_job("required-review-paths")
        workspace = self.root / "required-review-paths"
        workspace.mkdir()
        for name in ("EVALUATION.json", "REVIEW.md", "VALIDATION.md"):
            (workspace / name).write_text("present\n", encoding="utf-8")
        [result] = Validator(self.database).run(
            job_id,
            workspace,
            [
                {
                    "type": "required_paths",
                    "name": "byox-independent-review-files",
                    "paths": ["EVALUATION.json", "REVIEW.md", "VALIDATION.md"],
                }
            ],
            self.root / "logs" / job_id,
        )
        self.assertEqual("PASS", result.status)
        self.assertEqual(
            {
                "missing": [],
                "checked": ["EVALUATION.json", "REVIEW.md", "VALIDATION.md"],
            },
            result.evidence,
        )

    def test_review_json_limits_fail_before_file_content_is_read(self) -> None:
        specifications = (
            (
                "schema",
                {
                    "type": "json_schema",
                    "name": "byox-independent-review-schema",
                    "path": "EVALUATION.json",
                    "max_bytes": MAX_REVIEW_EVALUATION_BYTES,
                    "schema": {"type": "object"},
                },
            ),
            (
                "verdict",
                {
                    "type": "review_verdict",
                    "name": "byox-independent-review-verdict",
                    "path": "EVALUATION.json",
                    "contract_version": BYOX_REVIEW_CONTRACT_VERSION,
                },
            ),
        )
        for suffix, specification in specifications:
            with self.subTest(suffix=suffix):
                job_id = self._validator_job(f"oversized-review-json-{suffix}")
                workspace = self.root / f"oversized-review-json-{suffix}"
                workspace.mkdir()
                (workspace / "EVALUATION.json").write_bytes(
                    b" " * (MAX_REVIEW_EVALUATION_BYTES + 1)
                )
                with patch(
                    "learnfactory.validation.os.read",
                    side_effect=AssertionError(
                        "oversized review JSON must not be read"
                    ),
                ) as read_mock:
                    [result] = Validator(self.database).run(
                        job_id,
                        workspace,
                        [specification],
                        self.root / "logs" / job_id,
                    )
                self.assertEqual("FAIL", result.status)
                read_mock.assert_not_called()

    def test_verdict_contract_version_is_type_strict_after_duplicate_key_decode(self) -> None:
        evaluation = {
            "project_id": "project-version-type",
            "builder_job_id": "builder-version-type",
            "verdict": "PASS",
            "evidence": ["observed"],
            "checks_run": ["checked"],
            "limitations": [],
        }
        specifications = (
            {
                "type": "review_verdict",
                "path": "EVALUATION.json",
                "contract_version": 2.0,
            },
            json.loads(
                '{"type":"review_verdict","path":"EVALUATION.json",'
                '"contract_version":2,"contract_version":2.0}'
            ),
        )
        for index, specification in enumerate(specifications):
            with self.subTest(index=index):
                job_id = self._validator_job(f"version-type-{index}")
                workspace = self.root / f"version-type-{index}"
                workspace.mkdir()
                (workspace / "EVALUATION.json").write_text(
                    json.dumps(evaluation) + "\n", encoding="utf-8"
                )
                [result] = Validator(self.database).run(
                    job_id,
                    workspace,
                    [specification],
                    self.root / "logs" / job_id,
                )
                self.assertEqual("ERROR", result.status)

    def test_verdict_contract_rejects_duplicate_evaluation_keys(self) -> None:
        job_id = self._validator_job("duplicate-evaluation-key")
        workspace = self.root / "duplicate-evaluation-key"
        workspace.mkdir()
        (workspace / "EVALUATION.json").write_text(
            '{"project_id":"project-duplicate",'
            '"builder_job_id":"builder-duplicate",'
            '"verdict":"FAIL","verdict":"PASS",'
            '"evidence":["observed"],"checks_run":["checked"],'
            '"limitations":[]}\n',
            encoding="utf-8",
        )
        [result] = Validator(self.database).run(
            job_id,
            workspace,
            [
                {
                    "type": "review_verdict",
                    "path": "EVALUATION.json",
                    "contract_version": BYOX_REVIEW_CONTRACT_VERSION,
                }
            ],
            self.root / "logs" / job_id,
        )
        self.assertEqual("FAIL", result.status)

    def test_verdict_contract_normalizes_pathological_json_failures(self) -> None:
        pathological_documents = {
            "deep-nesting": "[" * 1_100 + "0" + "]" * 1_100,
            "integer-digit-limit": "9" * 5_000,
            "non-utf8-encoding": '{"verdict":"FAIL"}'.encode("utf-16"),
        }
        for suffix, raw_value in pathological_documents.items():
            with self.subTest(suffix=suffix):
                job_id = self._validator_job(f"pathological-{suffix}")
                workspace = self.root / f"pathological-{suffix}"
                workspace.mkdir()
                evaluation_path = workspace / "EVALUATION.json"
                if isinstance(raw_value, bytes):
                    evaluation_path.write_bytes(raw_value)
                else:
                    evaluation_path.write_text(raw_value, encoding="utf-8")
                [result] = Validator(self.database).run(
                    job_id,
                    workspace,
                    [
                        {
                            "type": "review_verdict",
                            "path": "EVALUATION.json",
                            "contract_version": BYOX_REVIEW_CONTRACT_VERSION,
                        }
                    ],
                    self.root / "logs" / job_id,
                )
                self.assertEqual("FAIL", result.status)
                self.assertNotIn("RecursionError", result.evidence.get("error", ""))

    def test_review_acceptance_requires_a_separate_captured_command(self) -> None:
        def run_case(
            suffix: str,
            verdict: str,
            specification: dict[str, object],
            *,
            byox_review: bool = False,
        ):
            payload = (
                {
                    "seed_policy": {"kind": "byox_reference_review"},
                    "artifact_type": "byox-independent-review",
                }
                if byox_review
                else {}
            )
            job_id = self._validator_job(suffix, payload)
            workspace = self.root / suffix
            workspace.mkdir()
            (workspace / "EVALUATION.json").write_text(
                json.dumps({"verdict": verdict}) + "\n", encoding="utf-8"
            )
            [result] = Validator(self.database).run(
                job_id,
                workspace,
                [specification],
                self.root / "logs" / job_id,
            )
            return result

        closed = run_case(
            "acceptance-closed",
            "PASS",
            {
                "type": "review_acceptance",
                "name": "byox-independent-review-acceptance",
                "mode": "closed",
            },
        )
        self.assertEqual("PASS", closed.status)
        self.assertEqual((), closed.claims)
        self.assertFalse(closed.evidence["workflow_accepted"])

        accepted = run_case(
            "acceptance-command-pass",
            "PASS",
            {
                "type": "review_acceptance",
                "name": "byox-independent-review-acceptance",
                "mode": "command",
                "argv": ["python3", "-c", "raise SystemExit(0)"],
                "timeout_seconds": 10,
                "claims": ["REVIEWED"],
            },
        )
        self.assertEqual("PASS", accepted.status)
        self.assertEqual(("REVIEWED",), accepted.claims)
        self.assertEqual(0, accepted.exit_code)
        self.assertTrue(accepted.evidence["workflow_accepted"])

        rejected = run_case(
            "acceptance-command-reject",
            "PASS",
            {
                "type": "review_acceptance",
                "name": "byox-independent-review-acceptance",
                "mode": "command",
                "argv": ["python3", "-c", "raise SystemExit(7)"],
                "timeout_seconds": 10,
                "claims": ["REVIEWED"],
            },
        )
        self.assertEqual("PASS", rejected.status)
        self.assertEqual((), rejected.claims)
        self.assertEqual(7, rejected.exit_code)
        self.assertEqual("FAIL", rejected.evidence["acceptance_check_status"])
        self.assertFalse(rejected.evidence["workflow_accepted"])

        negative = run_case(
            "acceptance-negative-verdict",
            "REVISE",
            {
                "type": "review_acceptance",
                "name": "byox-independent-review-acceptance",
                "mode": "command",
                "argv": ["python3", "-c", "raise SystemExit(0)"],
                "timeout_seconds": 10,
                "claims": ["REVIEWED"],
            },
        )
        self.assertEqual("PASS", negative.status)
        self.assertEqual((), negative.claims)
        self.assertIsNone(negative.command)
        self.assertFalse(negative.evidence["command_executed"])

        smuggled = run_case(
            "acceptance-smuggled-command",
            "PASS",
            {
                "type": "command",
                "name": "not-an-acceptance-gate",
                "argv": ["python3", "-c", "raise SystemExit(0)"],
                "timeout_seconds": 10,
                "claims": ["REVIEWED"],
            },
            byox_review=True,
        )
        self.assertEqual("PASS", smuggled.status)
        self.assertEqual((), smuggled.claims)

    def _catalog_project(self, project_id: str) -> None:
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO sources(
                    source_id,type,name,path,commit_hash,ingested_at,metadata_json,is_active
                ) VALUES ('source_byox','project_catalog','Build Your Own X',
                          '/public/byox','commit-byox',1,
                          '{"adapter":"build_your_own_x"}',1)
                """
            )
            connection.execute(
                """
                INSERT INTO build_projects(
                    project_id,source_id,slug,title,category,upstream_reference
                ) VALUES (?,?,?,?,?,?)
                """,
                (
                    project_id,
                    "source_byox",
                    project_id,
                    f"Project {project_id}",
                    "Systems",
                    f"https://example.invalid/{project_id}",
                ),
            )

    def _review_job(
        self,
        project_id: str,
        builder_id: str,
        verdict: str,
        *,
        policy_version: int = 1,
        verdict_contract: bool = True,
        acceptance_command: bool = False,
    ) -> str:
        suffix = "" if policy_version == 1 else f"_v{policy_version}"
        reviewer_id = f"job_reviewer{suffix}_{project_id}"
        self.jobs.create(
            "fake",
            "test",
            {
                "seed_policy": {
                    "kind": "byox_reference_review",
                    "version": policy_version,
                    "role": "reviewer",
                },
                "project_id": project_id,
                "builder_job_id": builder_id,
                "files": {
                    "EVALUATION.json": json.dumps(
                        {
                            "project_id": project_id,
                            "builder_job_id": builder_id,
                            "verdict": verdict,
                            "evidence": ["observed result"],
                            "checks_run": ["bounded check"],
                            "limitations": [],
                        }
                    )
                    + "\n",
                    "REVIEW.md": f"# {verdict} review\n",
                    "VALIDATION.md": "# Checks\n",
                },
                "validators": (
                    [
                        {
                            "type": "review_verdict",
                            "name": "byox-independent-review-verdict",
                            "path": "EVALUATION.json",
                            "contract_version": BYOX_REVIEW_CONTRACT_VERSION,
                        },
                        *(
                            [
                                {
                                    "type": "review_acceptance",
                                    "name": "byox-independent-review-acceptance",
                                    "mode": "command",
                                    "argv": [
                                        "python3",
                                        "-c",
                                        "raise SystemExit(0)",
                                    ],
                                    "timeout_seconds": 10,
                                    "claims": ["REVIEWED"],
                                }
                            ]
                            if acceptance_command
                            else []
                        ),
                    ]
                    if verdict_contract
                    else [
                        {
                            "type": "required_paths",
                            "name": "legacy-review-output",
                            "paths": ["EVALUATION.json", "REVIEW.md", "VALIDATION.md"],
                        }
                    ]
                ),
                "artifact_type": "byox-independent-review",
                "artifact_path": f"tests/reviews/{project_id}/v{policy_version}",
            },
            dependencies=[builder_id],
            max_attempts=1,
            job_id=reviewer_id,
        )
        return reviewer_id

    def _review_pair(
        self,
        project_id: str,
        verdict: str,
        *,
        verdict_contract: bool = True,
        acceptance_command: bool = False,
    ) -> tuple[str, str]:
        self._catalog_project(project_id)
        builder_id = f"job_builder_{project_id}"
        self.jobs.create(
            "fake",
            "test",
            {
                "seed_policy": {
                    "kind": "byox_reference_build",
                    "version": 1,
                    "role": "builder",
                },
                "project_id": project_id,
                "files": {"README.md": f"candidate {project_id}\n"},
                "validators": [
                    {
                        "type": "required_paths",
                        "name": "candidate-exists",
                        "paths": ["README.md"],
                    }
                ],
                "artifact_type": "byox-challenge-pack",
                "artifact_path": f"tests/builders/{project_id}",
            },
            max_attempts=1,
            job_id=builder_id,
        )
        reviewer_id = self._review_job(
            project_id,
            builder_id,
            verdict,
            verdict_contract=verdict_contract,
            acceptance_command=acceptance_command,
        )
        return builder_id, reviewer_id

    def _bind_review_artifacts_to_current_builders(self) -> None:
        """Model the provenance written by real dependency staging."""

        with self.database.transaction(immediate=True) as connection:
            rows = connection.execute(
                """
                SELECT r.artifact_id,r.metadata_json,j.payload_json,
                       b.artifact_id AS builder_artifact_id,
                       b.checksum AS builder_checksum,b.type AS builder_type
                FROM artifacts r JOIN jobs j ON j.job_id=r.job_id
                JOIN jobs parent
                  ON parent.job_id=json_extract(j.payload_json,'$.builder_job_id')
                JOIN artifacts b
                  ON b.job_id=parent.job_id
                 AND b.attempt_number=parent.attempt_count
                WHERE r.type='byox-independent-review'
                """
            ).fetchall()
            for row in rows:
                payload = json.loads(row["payload_json"])
                metadata = json.loads(row["metadata_json"])
                metadata["staged_inputs"] = [
                    {
                        "origin": "dependency-artifact",
                        "job_id": payload["builder_job_id"],
                        "artifact_id": row["builder_artifact_id"],
                        "artifact_checksum": row["builder_checksum"],
                        "artifact_type": row["builder_type"],
                    }
                ]
                connection.execute(
                    "UPDATE artifacts SET metadata_json=? WHERE artifact_id=?",
                    (
                        json.dumps(metadata, sort_keys=True, separators=(",", ":")),
                        row["artifact_id"],
                    ),
                )

    def test_negative_review_artifacts_survive_but_only_pass_pair_is_accepted(self) -> None:
        review_jobs = {
            verdict: self._review_pair(
                f"project-{verdict.lower()}",
                verdict,
                acceptance_command=verdict == "PASS",
            )[1]
            for verdict in ("PASS", "REVISE", "FAIL")
        }
        superseded_builder, superseded_v1 = self._review_pair(
            "project-superseded", "FAIL", verdict_contract=False
        )
        superseded_v2 = self._review_job(
            "project-superseded",
            superseded_builder,
            "PASS",
            policy_version=2,
            acceptance_command=True,
        )
        self.jobs.promote_eligible()
        dispatched = asyncio.run(
            run_scheduler(
                self.settings,
                self.database,
                until_idle=True,
                max_jobs=9,
            )
        )
        self.assertEqual(9, dispatched)
        self.assertTrue(
            all(
                self.jobs.get(job_id)["state"] == "SUCCEEDED"
                for job_id in review_jobs.values()
            )
        )
        self.assertEqual("SUCCEEDED", self.jobs.get(superseded_v1)["state"])
        self.assertEqual("SUCCEEDED", self.jobs.get(superseded_v2)["state"])

        self._bind_review_artifacts_to_current_builders()

        snapshot = status_snapshot(self.database)
        byox = snapshot["metrics"]["scaleout_coverage"]["byox"]
        self.assertEqual(4, byox["complete_pairs"])
        self.assertEqual(4, byox["review_job_succeeded_pairs"])
        self.assertEqual(2, byox["succeeded_pairs"])
        self.assertEqual(
            {
                "PASS": 2,
                "REVISE": 1,
                "FAIL": 1,
                "UNKNOWN": 0,
                "AMBIGUOUS": 0,
            },
            byox["review_outcomes"],
        )

        with self.database.connect() as connection:
            review_artifacts = connection.execute(
                """
                SELECT job_id,artifact_id FROM artifacts
                WHERE type='byox-independent-review'
                """
            ).fetchall()
            labels = {
                str(row["job_id"]): {
                    str(label["label"])
                    for label in connection.execute(
                        "SELECT label FROM artifact_validation_labels WHERE artifact_id=?",
                        (row["artifact_id"],),
                    )
                }
                for row in review_artifacts
            }
        self.assertEqual(5, len(review_artifacts))
        self.assertEqual({"GENERATED", "REVIEWED"}, labels[review_jobs["PASS"]])
        self.assertEqual({"GENERATED"}, labels[review_jobs["REVISE"]])
        self.assertEqual({"GENERATED"}, labels[review_jobs["FAIL"]])
        self.assertEqual({"GENERATED"}, labels[superseded_v1])
        self.assertEqual({"GENERATED", "REVIEWED"}, labels[superseded_v2])

        _, catalog_path = write_catalog(
            self.database, self.settings.warehouse / "catalog"
        )
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        archived_review_jobs = {
            artifact["job_id"]
            for artifact in catalog["artifacts"]
            if artifact["type"] == "byox-independent-review"
        }
        self.assertEqual(
            {*review_jobs.values(), superseded_v1, superseded_v2},
            archived_review_jobs,
        )

        # Quarantining the reviewed builder invalidates acceptance immediately,
        # even though both job rows remain SUCCEEDED.
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                """
                UPDATE artifacts SET integrity_status='LEGACY_UNVERIFIED'
                WHERE job_id=?
                """,
                (superseded_builder,),
            )
        quarantined = status_snapshot(self.database)["metrics"]["scaleout_coverage"]["byox"]
        self.assertEqual(1, quarantined["succeeded_pairs"])

    def test_pending_higher_review_version_supersedes_older_pass(self) -> None:
        builder_id, v1 = self._review_pair(
            "project-pending-v2", "PASS", acceptance_command=True
        )
        self.jobs.promote_eligible()
        asyncio.run(
            run_scheduler(self.settings, self.database, until_idle=True, max_jobs=2)
        )
        self._bind_review_artifacts_to_current_builders()
        before = status_snapshot(self.database)["metrics"]["scaleout_coverage"]["byox"]
        self.assertEqual(1, before["succeeded_pairs"])

        v2 = self._review_job(
            "project-pending-v2", builder_id, "PASS", policy_version=2
        )
        self.assertEqual("DISCOVERED", self.jobs.get(v2)["state"])
        self.assertEqual("SUCCEEDED", self.jobs.get(v1)["state"])
        after = status_snapshot(self.database)["metrics"]["scaleout_coverage"]["byox"]
        self.assertEqual(0, after["succeeded_pairs"])
        self.assertEqual(1, after["review_outcomes"]["UNKNOWN"])

    def test_reviewer_pass_without_acceptance_gate_fails_closed(self) -> None:
        _, reviewer_id = self._review_pair("project-ungated-pass", "PASS")
        self.jobs.promote_eligible()
        dispatched = asyncio.run(
            run_scheduler(
                self.settings,
                self.database,
                until_idle=True,
                max_jobs=2,
            )
        )
        self.assertEqual(2, dispatched)
        self._bind_review_artifacts_to_current_builders()

        byox = status_snapshot(self.database)["metrics"]["scaleout_coverage"]["byox"]
        self.assertEqual(0, byox["succeeded_pairs"])
        self.assertEqual(1, byox["review_outcomes"]["UNKNOWN"])
        with self.database.connect() as connection:
            artifact = connection.execute(
                "SELECT artifact_id FROM artifacts WHERE job_id=?",
                (reviewer_id,),
            ).fetchone()
            assert artifact is not None
            labels = {
                row["label"]
                for row in connection.execute(
                    "SELECT label FROM artifact_validation_labels WHERE artifact_id=?",
                    (artifact["artifact_id"],),
                )
            }
        self.assertEqual({"GENERATED"}, labels)


if __name__ == "__main__":
    unittest.main()
