from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

from learnfactory.db import Database
from learnfactory.jobs import JobState
from learnfactory.reporting import status_snapshot, write_checkpoint


ROOT = Path(__file__).resolve().parents[1]


class ScaleoutReportingTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="learnfactory-reporting-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.database = Database(self.root / "factory.db", ROOT / "migrations")
        self.database.migrate()

    def _source(
        self,
        source_id: str,
        *,
        source_type: str,
        name: str,
        adapter: str,
        active: bool = True,
    ) -> None:
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                """
                INSERT INTO sources(
                    source_id,type,name,path,commit_hash,ingested_at,metadata_json,is_active
                ) VALUES (?,?,?,?,?,?,?,?)
                """,
                (
                    source_id,
                    source_type,
                    name,
                    f"/public/{source_id}",
                    f"commit-{source_id}",
                    1.0,
                    json.dumps({"adapter": adapter}),
                    int(active),
                ),
            )

    def _project(self, project_id: str, source_id: str) -> None:
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                """
                INSERT INTO build_projects(
                    project_id,source_id,slug,title,category,upstream_reference
                ) VALUES (?,?,?,?,?,?)
                """,
                (
                    project_id,
                    source_id,
                    project_id,
                    f"Project {project_id}",
                    "Systems",
                    f"https://example.invalid/{project_id}",
                ),
            )

    def _course(self, course_id: str, source_id: str) -> None:
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                "INSERT INTO courses(course_id,source_id,slug,title) VALUES (?,?,?,?)",
                (course_id, source_id, course_id, f"Course {course_id}"),
            )

    def _job(
        self,
        suffix: str,
        payload: dict[str, Any] | list[Any] | str,
        *,
        state: JobState,
        worker_type: str = "test",
    ) -> None:
        encoded = payload if isinstance(payload, str) else json.dumps(payload)
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                """
                INSERT INTO jobs(job_id,type,worker_type,state,payload_json,created_at)
                VALUES (?,?,?,?,?,?)
                """,
                (
                    f"job_{suffix}",
                    "codex_task",
                    worker_type,
                    state.value,
                    encoded,
                    1.0,
                ),
            )

    def _catalog_fixture(self, *, entries: int = 3) -> None:
        self._source(
            "source_byox",
            source_type="project_catalog",
            name="Build Your Own X",
            adapter="build_your_own_x",
        )
        self._source(
            "source_csdiy",
            source_type="course_catalog",
            name="CSDIY",
            adapter="csdiy",
        )
        for number in range(1, entries + 1):
            self._project(f"project-{number}", "source_byox")
            self._course(f"course-{number}", "source_csdiy")

    def _succeeded_course_cohort(
        self, course_id: str, *, examiner_result: str | None
    ) -> None:
        """Insert archived kickoff outputs with optional attempt-bound evidence."""

        suffix = course_id.replace("-", "_")
        task_id = f"{course_id}-kickoff-v1"
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO students(
                    student_id,persona,profile_json,created_at,current_state_json
                ) VALUES ('student-target','target','{}',1,'{}')
                """
            )
        for role in ("preparation", "student"):
            self._job(
                f"{suffix}_{role}",
                {
                    "seed_policy": {
                        "kind": "csdiy_course_cohort",
                        "version": 1,
                        "role": role,
                    },
                    "course_id": course_id,
                },
                state=JobState.SUCCEEDED,
            )
        examiner_suffix = f"{suffix}_examiner"
        examiner_job_id = f"job_{examiner_suffix}"
        self._job(
            examiner_suffix,
            {
                "seed_policy": {
                    "kind": "csdiy_course_cohort",
                    "version": 1,
                    "role": "examiner",
                },
                "course_id": course_id,
                "learner_evidence": {
                    "student_id": "student-target",
                    "task_id": task_id,
                    "task_type": "course-kickoff",
                    "attempt_number": 1,
                },
            },
            state=JobState.SUCCEEDED,
        )
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                """
                INSERT INTO artifacts(
                    artifact_id,job_id,type,path,checksum,metadata_json,created_at,
                    validation_status,attempt_number,checksum_algorithm,integrity_status
                ) VALUES (?,?,?,?,?,'{}',1,'GENERATED',0,'tree-sha256-v2','VERIFIED_V2')
                """,
                (
                    f"artifact_{examiner_suffix}",
                    examiner_job_id,
                    "independent-course-evaluation",
                    str(self.root / examiner_suffix),
                    f"checksum-{examiner_suffix}",
                ),
            )
            if examiner_result is not None:
                attempt_id = f"attempt_{examiner_suffix}"
                connection.execute(
                    """
                    INSERT INTO attempts(
                        attempt_id,student_id,task_id,task_type,attempt_number,
                        start_time,end_time,result
                    ) VALUES (?,'student-target',?,'course-kickoff',1,1,2,?)
                    """,
                    (attempt_id, task_id, examiner_result),
                )
                connection.execute(
                    """
                    INSERT INTO evaluations(
                        evaluation_id,attempt_id,evaluator,rubric_json,result,
                        evidence_json,created_at
                    ) VALUES (?,?,'independent-test','{}',?,?,2)
                    """,
                    (
                        f"evaluation_{examiner_suffix}",
                        attempt_id,
                        examiner_result,
                        json.dumps(
                            {
                                "examiner_job_id": examiner_job_id,
                                "examiner_attempt": 0,
                            }
                        ),
                    ),
                )

    def test_coverage_is_zero_safe_before_mass_jobs_exist(self) -> None:
        empty = status_snapshot(self.database)["metrics"]["scaleout_coverage"]
        self.assertEqual(0, empty["byox"]["catalog_entries"])
        self.assertEqual(0.0, empty["byox"]["coverage_percent"])
        self.assertEqual(0, empty["csdiy"]["catalog_entries"])
        self.assertEqual(0.0, empty["csdiy"]["coverage_percent"])

        self._catalog_fixture(entries=2)
        self._source(
            "source_other",
            source_type="project_catalog",
            name="Other Catalog",
            adapter="other",
        )
        self._project("project-other", "source_other")
        self._course("course-other", "source_other")
        self._source(
            "source_byox_old",
            source_type="build-your-own-x",
            name="Build Your Own X old",
            adapter="build_your_own_x",
            active=False,
        )
        self._project("project-old", "source_byox_old")

        coverage = status_snapshot(self.database)["metrics"]["scaleout_coverage"]
        expected_states = {state.value: 0 for state in JobState}
        self.assertEqual(
            {
                "catalog_entries": 2,
                "planned_entries": 0,
                "unplanned_entries": 2,
                "coverage_percent": 0.0,
                "builder_entries": 0,
                "specialized_builder_entries": 0,
                "reviewer_entries": 0,
                "complete_pairs": 0,
                "complete_pair_percent": 0.0,
                "review_job_succeeded_pairs": 0,
                "succeeded_pairs": 0,
                "review_outcomes": {
                    "PASS": 0,
                    "REVISE": 0,
                    "FAIL": 0,
                    "UNKNOWN": 0,
                    "AMBIGUOUS": 0,
                },
                "builder_states": expected_states,
                "reviewer_states": expected_states,
                "orphaned_entries": 0,
                "unattributed_jobs": 0,
            },
            coverage["byox"],
        )
        self.assertEqual(2, coverage["csdiy"]["catalog_entries"])
        self.assertEqual(0, coverage["csdiy"]["planned_entries"])
        self.assertEqual(expected_states, coverage["csdiy"]["manager_states"])
        self.assertEqual(expected_states, coverage["csdiy"]["student_states"])
        self.assertEqual(expected_states, coverage["csdiy"]["examiner_states"])

    def test_seed_policy_coverage_counts_distinct_ids_roles_and_states(self) -> None:
        self._catalog_fixture()
        self._job(
            "byox_legacy_builder",
            {
                "seed_policy": {"kind": "byox_reference_build", "version": 1},
                "provenance": {"project": {"project_id": "project-1"}},
            },
            state=JobState.READY,
        )
        self._job(
            "byox_duplicate_builder",
            {
                "seed_policy": {
                    "kind": "byox_reference_build",
                    "version": 1,
                    "role": "builder",
                },
                "project_id": "project-1",
            },
            state=JobState.READY,
        )
        self._job(
            "byox_reviewer_one",
            {
                "seed_policy": {
                    "kind": "byox_reference_review",
                    "version": 1,
                    "role": "reviewer",
                },
                "project_id": "project-1",
            },
            state=JobState.DISCOVERED,
        )
        self._job(
            "byox_builder_two",
            {
                "seed_policy": {
                    "kind": "byox_reference_build",
                    "version": 1,
                    "role": "builder",
                },
                "project_id": "project-2",
            },
            state=JobState.SUCCEEDED,
        )
        self._job(
            "byox_specialized_builder_three",
            {"project_id": "project-3"},
            state=JobState.SUCCEEDED,
            worker_type="reference_builder",
        )
        self._job(
            "byox_reviewer_three",
            {
                "seed_policy": {
                    "kind": "byox_reference_review",
                    "version": 1,
                    "role": "reviewer",
                },
                "project_id": "project-3",
                "builder_job_id": "job_byox_specialized_builder_three",
            },
            state=JobState.FAILED,
        )
        self._job(
            "byox_orphan",
            {
                "seed_policy": {
                    "kind": "byox_reference_build",
                    "version": 1,
                    "role": "builder",
                },
                "project_id": "project-stale",
            },
            state=JobState.READY,
        )
        self._job(
            "byox_unattributed",
            {
                "seed_policy": {
                    "kind": "byox_reference_review",
                    "version": 1,
                    "role": "reviewer",
                }
            },
            state=JobState.DISCOVERED,
        )

        for suffix, role, course_id, state in (
            ("manager_one", "preparation", "course-1", JobState.READY),
            ("manager_one_duplicate", "preparation", "course-1", JobState.READY),
            ("student_one", "student", "course-1", JobState.SUCCEEDED),
            ("examiner_one", "examiner", "course-1", JobState.BLOCKED),
            ("student_two", "student", "course-2", JobState.FAILED),
            ("student_stale", "student", "course-stale", JobState.READY),
        ):
            self._job(
                suffix,
                {
                    "seed_policy": {
                        "kind": "csdiy_course_cohort",
                        "version": 1,
                        "role": role,
                    },
                    "course_id": course_id,
                },
                state=state,
            )
        self._job(
            "ignored_no_policy",
            {"project_id": "project-3", "course_id": "course-3"},
            state=JobState.SUCCEEDED,
        )
        self._job("ignored_malformed", "not-json", state=JobState.READY)

        coverage = status_snapshot(self.database)["metrics"]["scaleout_coverage"]
        byox = coverage["byox"]
        self.assertEqual(3, byox["catalog_entries"])
        self.assertEqual(3, byox["planned_entries"])
        self.assertEqual(3, byox["builder_entries"])
        self.assertEqual(1, byox["specialized_builder_entries"])
        self.assertEqual(2, byox["reviewer_entries"])
        self.assertEqual(2, byox["complete_pairs"])
        self.assertEqual(1, byox["orphaned_entries"])
        self.assertEqual(1, byox["unattributed_jobs"])
        self.assertEqual(1, byox["builder_states"]["READY"])
        self.assertEqual(2, byox["builder_states"]["SUCCEEDED"])
        self.assertEqual(1, byox["reviewer_states"]["DISCOVERED"])
        self.assertEqual(1, byox["reviewer_states"]["FAILED"])

        csdiy = coverage["csdiy"]
        self.assertEqual(3, csdiy["catalog_entries"])
        self.assertEqual(2, csdiy["planned_entries"])
        self.assertEqual(1, csdiy["unplanned_entries"])
        self.assertEqual(66.7, csdiy["coverage_percent"])
        self.assertEqual(1, csdiy["manager_entries"])
        self.assertEqual(2, csdiy["student_entries"])
        self.assertEqual(1, csdiy["examiner_entries"])
        self.assertEqual(1, csdiy["complete_cohorts"])
        self.assertEqual(0, csdiy["succeeded_cohorts"])
        self.assertEqual(1, csdiy["manager_states"]["READY"])
        self.assertEqual(1, csdiy["student_states"]["SUCCEEDED"])
        self.assertEqual(1, csdiy["student_states"]["FAILED"])
        self.assertEqual(1, csdiy["examiner_states"]["BLOCKED"])
        self.assertEqual(1, csdiy["orphaned_entries"])

    def test_checkpoint_markdown_summarizes_catalog_graph_coverage(self) -> None:
        self._catalog_fixture(entries=1)
        self._job(
            "builder",
            {
                "seed_policy": {
                    "kind": "byox_reference_build",
                    "version": 1,
                    "role": "builder",
                },
                "project_id": "project-1",
            },
            state=JobState.READY,
        )
        self._job(
            "reviewer",
            {
                "seed_policy": {
                    "kind": "byox_reference_review",
                    "version": 1,
                    "role": "reviewer",
                },
                "project_id": "project-1",
            },
            state=JobState.DISCOVERED,
        )
        for suffix, role in (
            ("manager", "preparation"),
            ("student", "student"),
            ("examiner", "examiner"),
        ):
            self._job(
                suffix,
                {
                    "seed_policy": {
                        "kind": "csdiy_course_cohort",
                        "version": 1,
                        "role": role,
                    },
                    "course_id": "course-1",
                },
                state=JobState.DISCOVERED,
            )

        markdown_path, json_path = write_checkpoint(
            self.database,
            self.root / "reports",
            self.root / "warehouse",
        )
        markdown = markdown_path.read_text(encoding="utf-8")
        machine = json.loads(json_path.read_text(encoding="utf-8"))
        self.assertIn("## Scale-out coverage", markdown)
        self.assertIn(
            "BYOX: 1/1 entries planned; builders 1, reviewers 1, graph-complete pairs 1, "
            "review outputs succeeded 0, verdict-accepted pairs 0, "
            "review outcomes `",
            markdown,
        )
        self.assertIn("specialized builders 0", markdown)
        self.assertIn(
            "CSDIY: 1/1 courses planned; managers 1, students 1, examiners 1, "
            "graph-complete cohorts 1, workflow-succeeded cohorts 0",
            markdown,
        )
        self.assertIn('builder={"READY": 1}', markdown)
        self.assertEqual(
            1,
            machine["metrics"]["scaleout_coverage"]["csdiy"]["complete_cohorts"],
        )

    def test_course_success_requires_attempt_bound_examiner_pass(self) -> None:
        self._catalog_fixture(entries=4)
        self._succeeded_course_cohort("course-1", examiner_result="PASS")
        self._succeeded_course_cohort("course-2", examiner_result="REVISE")
        self._succeeded_course_cohort("course-3", examiner_result="FAIL")
        self._succeeded_course_cohort("course-4", examiner_result=None)

        csdiy = status_snapshot(self.database)["metrics"]["scaleout_coverage"]["csdiy"]
        self.assertEqual(4, csdiy["archived_output_cohorts"])
        self.assertEqual(1, csdiy["succeeded_cohorts"])
        self.assertEqual(
            {"PASS": 1, "REVISE": 1, "FAIL": 1, "UNKNOWN": 1, "AMBIGUOUS": 0},
            csdiy["examiner_outcomes"],
        )


if __name__ == "__main__":
    unittest.main()
