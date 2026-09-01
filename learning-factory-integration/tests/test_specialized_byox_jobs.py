from __future__ import annotations

import hashlib
import unittest
from dataclasses import replace

from learnfactory.byox_jobs import ByoxProjectSnapshot
from learnfactory.specialized_byox_jobs import (
    ALLOCATOR_JOB_ID,
    ALLOCATOR_PROJECT_ID,
    BYTECODE_JOB_ID,
    BYTECODE_PROJECT_ID,
    CATALOG_SYNTHESIS_JOB_ID,
    HTTP_SERVICE_JOB_ID,
    KVSTORE_JOB_ID,
    KVSTORE_REVISION_JOB_ID,
    specialized_byox_job_specs_by_id,
    specialized_reviewer_payload,
)
from learnfactory.util import canonical_json


class SpecializedByoxJobSpecTests(unittest.TestCase):
    def _snapshot(
        self,
        project_id: str,
        *,
        title: str,
        category: str,
        language: str | None,
        upstream: str,
        priority_tier: int = 1,
        production_relevance: float | None = 8.5,
    ) -> ByoxProjectSnapshot:
        return ByoxProjectSnapshot(
            project_id=project_id,
            source_id="source_eac489a34bed5db9a1f2a580b457bcef",
            slug=f"slug-{project_id}",
            title=title,
            category=category,
            implementation_language=language,
            upstream_reference=upstream,
            concepts=(),
            difficulty=8.0,
            production_relevance=production_relevance,
            source_format="article",
            priority_tier=priority_tier,
            project_metadata_json="{}",
            source_type="project_catalog",
            source_name="Build Your Own X",
            source_path="/public/build-your-own-x",
            source_upstream_url=(
                "git@github.com:codecrafters-io/build-your-own-x.git"
            ),
            source_commit_hash="aa17439b62f384511a5561ce308e9598b94d8989",
            source_license="CC0-1.0",
            source_ingested_at=1.0,
            source_metadata_json="{}",
        )

    def _released_snapshots(self) -> tuple[ByoxProjectSnapshot, ...]:
        return (
            self._snapshot(
                "project_5187715307b13e38b82d4dacf47b4946",
                title="DBDB: Dog Bed Database",
                category="Database",
                language="Python",
                upstream=(
                    "http://aosabook.org/en/500L/dbdb-dog-bed-database.html"
                ),
            ),
            self._snapshot(
                "project_c72c12c5b510bb2fbeffe9a2175fea74",
                title="A Simple Web Server",
                category="Web Server",
                language="Python",
                upstream="http://aosabook.org/en/500L/a-simple-web-server.html",
            ),
            self._snapshot(
                ALLOCATOR_PROJECT_ID,
                title="Malloc is not magic -- Implementing your own memory allocator",
                category="Memory Allocator",
                language="C",
                upstream="https://medium.com/p/e0354e914402",
            ),
            self._snapshot(
                BYTECODE_PROJECT_ID,
                title="Home-grown bytecode interpreters",
                category="Emulator / Virtual Machine",
                language="C",
                upstream=(
                    "https://medium.com/bumble-tech/"
                    "home-grown-bytecode-interpreters-51e12d59b25c"
                ),
            ),
        )

    def test_released_specs_match_audited_live_contract_fingerprints(self) -> None:
        specs = specialized_byox_job_specs_by_id(self._released_snapshots())
        expected = {
            KVSTORE_JOB_ID: (
                "fe75d7ce988295355bba687f58dc1a1f63f9a6612e445d1254b147510e8c62d4",
                "58331985b71d554afe640eb90cc2c34a55260f4610b59113d899e9153bda7d00",
                "project_vertical_slice",
                "project_challenge_pack",
                90.3,
                3,
                (),
            ),
            KVSTORE_REVISION_JOB_ID: (
                "7af016db951144628f0810ec072a4f5e7e62ccab265e6826ee6293cf8ab22c6b",
                "58331985b71d554afe640eb90cc2c34a55260f4610b59113d899e9153bda7d00",
                "project_vertical_slice",
                "project_challenge_pack",
                91.3,
                3,
                (KVSTORE_JOB_ID,),
            ),
            HTTP_SERVICE_JOB_ID: (
                "2315b0b3e5bd64dd5ebc6c632bfdb89186b62287bf0748ff9c46f5929117f21c",
                "5300abead4ebc03433098c4949e8716da798875de1411c8626f4cb55523bce4e",
                "http_service_vertical_slice",
                "http_service_challenge_pack",
                93.0,
                2,
                (CATALOG_SYNTHESIS_JOB_ID,),
            ),
            ALLOCATOR_JOB_ID: (
                "9d94229e86643d7ed9f41be45d8607f6171bb299beaad3f68e4df0a0433d7a2f",
                "2df4d0579dfb297036f6cdf73c0e8a64a5698de8f5052ecfd855a9305a288d78",
                "allocator_vertical_slice",
                "allocator_challenge_pack",
                94.8,
                2,
                (CATALOG_SYNTHESIS_JOB_ID,),
            ),
            BYTECODE_JOB_ID: (
                "d18ca7cf5b869fee04d46d156f52bd3e8f9ee3745ee386a6d40396171f1ea050",
                "db642b116dfead0c44e245cd0882eb645960a4441d7bea421c5f740ae2ccc9d1",
                "bytecode_vertical_slice",
                "bytecode_vm_challenge_pack",
                93.2,
                2,
                (CATALOG_SYNTHESIS_JOB_ID,),
            ),
        }
        self.assertEqual(set(expected), set(specs))
        for job_id, contract in expected.items():
            with self.subTest(job_id=job_id):
                spec = specs[job_id]
                payload_hash = hashlib.sha256(
                    canonical_json(spec.payload).encode("utf-8")
                ).hexdigest()
                score_hash = hashlib.sha256(
                    canonical_json(spec.score_components).encode("utf-8")
                ).hexdigest()
                self.assertEqual(contract[0], payload_hash)
                self.assertEqual(contract[1], score_hash)
                self.assertEqual(contract[2], spec.job_type)
                self.assertEqual(contract[3], spec.artifact_type)
                self.assertEqual(contract[4], spec.priority)
                self.assertEqual(contract[5], spec.max_attempts)
                self.assertEqual(contract[6], spec.dependencies)
                self.assertEqual("reference_builder", spec.worker_type)
                self.assertIsNone(spec.model)
                self.assertIsNone(spec.reasoning_effort)

    def test_selectors_match_released_sql_ordering(self) -> None:
        base = self._snapshot(
            "project-base",
            title="Database tutorial",
            category="Database",
            language="Rust",
            upstream="https://example.invalid/base",
            priority_tier=1,
            production_relevance=10,
        )
        python_substring = replace(
            base,
            project_id="project-python-substring",
            implementation_language="CPython 3",
            priority_tier=9,
            production_relevance=None,
        )
        dbdb = replace(
            base,
            project_id="project-dbdb",
            upstream_reference="https://example.invalid/DBDB",
            priority_tier=99,
            production_relevance=None,
        )
        specs = specialized_byox_job_specs_by_id((base, python_substring))
        self.assertEqual(
            python_substring.project_id,
            specs[KVSTORE_JOB_ID].project_id,
        )
        specs = specialized_byox_job_specs_by_id((base, python_substring, dbdb))
        self.assertEqual(dbdb.project_id, specs[KVSTORE_JOB_ID].project_id)

        relevant = replace(base, project_id="project-relevant", priority_tier=4)
        null_relevance = replace(
            relevant,
            project_id="project-null",
            production_relevance=None,
        )
        specs = specialized_byox_job_specs_by_id((null_relevance, relevant))
        self.assertEqual(relevant.project_id, specs[KVSTORE_JOB_ID].project_id)
        tie_later = replace(relevant, project_id="project-z")
        tie_earlier = replace(relevant, project_id="project-a")
        specs = specialized_byox_job_specs_by_id((tie_later, tie_earlier))
        self.assertEqual(tie_earlier.project_id, specs[KVSTORE_JOB_ID].project_id)

        web_python3 = replace(
            base,
            project_id="project-web-python3",
            title="Other server",
            category="Web Server",
            implementation_language="Python 3",
            priority_tier=1,
        )
        web_python = replace(
            web_python3,
            project_id="project-web-python",
            implementation_language="PYTHON",
            priority_tier=9,
        )
        specs = specialized_byox_job_specs_by_id((web_python3, web_python))
        self.assertEqual(web_python.project_id, specs[HTTP_SERVICE_JOB_ID].project_id)

        non_ascii_category = replace(
            base,
            project_id="project-non-ascii",
            category="DatabasÉ",
            upstream_reference="https://example.invalid/dbdb",
        )
        specs = specialized_byox_job_specs_by_id((base, non_ascii_category))
        self.assertEqual(base.project_id, specs[KVSTORE_JOB_ID].project_id)

    def test_specs_and_transient_reviewer_payloads_are_fresh(self) -> None:
        first = specialized_byox_job_specs_by_id(self._released_snapshots())
        first[KVSTORE_JOB_ID].payload["provenance"]["commit"] = "mutated"
        first[KVSTORE_JOB_ID].score_components["systems_depth"] = -1

        second = specialized_byox_job_specs_by_id(self._released_snapshots())
        self.assertEqual(
            "aa17439b62f384511a5561ce308e9598b94d8989",
            second[KVSTORE_JOB_ID].payload["provenance"]["commit"],
        )

        self.assertEqual(8, second[KVSTORE_JOB_ID].score_components["systems_depth"])
        self.assertEqual(
            "aa17439b62f384511a5561ce308e9598b94d8989",
            second[KVSTORE_REVISION_JOB_ID].payload["provenance"]["commit"],
        )

        reviewer_payload = specialized_reviewer_payload(second[KVSTORE_JOB_ID])
        self.assertEqual("project_challenge_pack", reviewer_payload["artifact_type"])
        self.assertNotIn("artifact_type", second[KVSTORE_JOB_ID].payload)
        reviewer_payload["provenance"]["commit"] = "mutated-review"
        self.assertEqual(
            "aa17439b62f384511a5561ce308e9598b94d8989",
            second[KVSTORE_JOB_ID].payload["provenance"]["commit"],
        )

    def test_constructor_rejects_non_snapshots_and_duplicate_identities(self) -> None:
        snapshot = self._released_snapshots()[0]
        with self.assertRaisesRegex(TypeError, "normalized project snapshots"):
            specialized_byox_job_specs_by_id((snapshot, object()))
        with self.assertRaisesRegex(ValueError, "duplicate project IDs"):
            specialized_byox_job_specs_by_id((snapshot, snapshot))


if __name__ == "__main__":
    unittest.main()
