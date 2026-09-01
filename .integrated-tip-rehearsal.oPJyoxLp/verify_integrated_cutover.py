from __future__ import annotations

import collections
import hashlib
import json
import sqlite3
from pathlib import Path

from learnfactory.byox_baselines import load_verified_binding


ROOT = Path(
    "/projects/se/pj34000401_refsys/users/yuali01/learn/"
    ".integrated-tip-rehearsal.oPJyoxLp"
)
PRE = ROOT / "copied-live-pristine.db"
POST = ROOT / "warehouse" / "cutover-final.db"


def connection(path: Path) -> sqlite3.Connection:
    db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    return db


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def jobs_by_policy(db: sqlite3.Connection, kind: str) -> dict[str, sqlite3.Row]:
    return {
        str(row["job_id"]): row
        for row in db.execute(
            """
            SELECT * FROM jobs
            WHERE json_extract(payload_json,'$.seed_policy.kind')=?
            ORDER BY job_id
            """,
            (kind,),
        )
    }


with connection(PRE) as before, connection(POST) as after:
    legacy_filter = """
        job_id LIKE 'job_byox_%'
        AND json_extract(payload_json,'$.seed_policy.kind')
            IN ('byox_reference_build','byox_reference_review')
    """
    before_legacy = {
        str(row["job_id"]): row
        for row in before.execute(
            f"SELECT * FROM jobs WHERE {legacy_filter} ORDER BY job_id"
        )
    }
    after_legacy = {
        str(row["job_id"]): row
        for row in after.execute(
            f"SELECT * FROM jobs WHERE {legacy_filter} ORDER BY job_id"
        )
    }
    assert before_legacy.keys() == after_legacy.keys()
    assert len(before_legacy) == 723

    terminal = {"SUCCEEDED", "FAILED", "CANCELLED"}
    retired_ids = {
        identifier
        for identifier, row in before_legacy.items()
        if str(row["state"]) not in terminal
    }
    preserved_terminal_ids = before_legacy.keys() - retired_ids
    assert len(retired_ids) == 655
    assert len(preserved_terminal_ids) == 68
    for identifier in retired_ids:
        row = after_legacy[identifier]
        assert row["state"] == "CANCELLED"
        assert row["cancel_requested"] == 1
        assert row["failure_kind"] == "superseded_byox_snapshot_scheme"
        assert str(row["error"]).startswith(
            "superseded by immutable BYOX S2 job "
        )
    for identifier in preserved_terminal_ids:
        assert after_legacy[identifier]["state"] == before_legacy[identifier]["state"]

    immutable_columns = (
        "job_id",
        "type",
        "worker_type",
        "priority",
        "score_components_json",
        "payload_json",
        "max_attempts",
        "model",
        "reasoning_effort",
    )
    for identifier, old in before_legacy.items():
        new = after_legacy[identifier]
        assert all(old[column] == new[column] for column in immutable_columns)

    retirement_events = after.execute(
        """
        SELECT job_id FROM events
        WHERE type='JOB_CANCELLED'
          AND json_extract(payload_json,'$.kind')='superseded_byox_snapshot_scheme'
        """
    ).fetchall()
    retirement_event_ids = [str(row["job_id"]) for row in retirement_events]
    assert len(retirement_event_ids) == 655
    assert set(retirement_event_ids) == retired_ids
    assert len(retirement_event_ids) == len(set(retirement_event_ids))

    active_projects = after.execute(
        """
        SELECT count(*) FROM build_projects project
        JOIN sources source ON source.source_id=project.source_id
        WHERE source.is_active=1 AND source.type='project_catalog'
        """
    ).fetchone()[0]
    assert active_projects == 359
    baselines = after.execute(
        "SELECT project_id,baseline_sha256 FROM byox_baseline_snapshots"
    ).fetchall()
    assert len(baselines) == 359
    assert len({str(row["project_id"]) for row in baselines}) == 359

    bindings = after.execute(
        "SELECT job_id,role,builder_job_id FROM byox_baseline_job_bindings ORDER BY job_id"
    ).fetchall()
    assert len(bindings) == 718
    role_counts = collections.Counter(str(row["role"]) for row in bindings)
    assert role_counts == {"builder": 359, "reviewer": 359}
    verified = 0
    for row in bindings:
        binding = load_verified_binding(after, str(row["job_id"]))
        assert binding is not None
        assert binding.role == row["role"]
        if row["role"] == "builder":
            assert row["builder_job_id"] is None
        else:
            assert isinstance(row["builder_job_id"], str)
        verified += 1

    bound_job_profile = after.execute(
        """
        SELECT job.worker_type,job.model,job.reasoning_effort,count(*) AS count
        FROM jobs job
        JOIN byox_baseline_job_bindings binding ON binding.job_id=job.job_id
        GROUP BY job.worker_type,job.model,job.reasoning_effort
        ORDER BY job.worker_type
        """
    ).fetchall()
    assert [tuple(row) for row in bound_job_profile] == [
        ("examiner", "gpt-5.6-sol", "ultra", 359),
        ("reference_builder", "gpt-5.6-sol", "ultra", 359),
    ]

    active_courses = after.execute(
        """
        SELECT count(*) FROM courses course
        JOIN sources source ON source.source_id=course.source_id
        WHERE source.is_active=1 AND source.type='course_catalog'
        """
    ).fetchone()[0]
    assert active_courses == 82

    before_cohorts = jobs_by_policy(before, "csdiy_course_cohort")
    after_cohorts = jobs_by_policy(after, "csdiy_course_cohort")
    assert len(before_cohorts) == 246
    assert before_cohorts.keys() <= after_cohorts.keys()
    for identifier, old in before_cohorts.items():
        new = after_cohorts[identifier]
        assert all(old[column] == new[column] for column in immutable_columns)

    current_rows = after.execute(
        """
        SELECT job_id,
               json_extract(payload_json,'$.course_id') AS course_id,
               json_extract(payload_json,'$.seed_policy.role') AS role,
               json_extract(payload_json,'$.seed_policy.version') AS version,
               json_extract(payload_json,'$.student_id') AS student_id,
               model,reasoning_effort
        FROM jobs
        WHERE json_extract(payload_json,'$.seed_policy.kind')='csdiy_course_cohort'
          AND (
            json_extract(payload_json,'$.seed_policy.role')='preparation'
            OR json_extract(payload_json,'$.seed_policy.version')=2
          )
        ORDER BY job_id
        """
    ).fetchall()
    assert len(current_rows) == 246
    course_roles: dict[str, set[str]] = collections.defaultdict(set)
    target_courses: set[str] = set()
    for row in current_rows:
        course_id = str(row["course_id"])
        role = str(row["role"])
        course_roles[course_id].add(role)
        assert row["model"] == "gpt-5.6-sol"
        assert row["reasoning_effort"] == "ultra"
        if role in {"student", "examiner"}:
            assert row["student_id"] == "student-target"
            target_courses.add(course_id)
    assert len(course_roles) == 82
    assert len(target_courses) == 82
    assert all(
        roles == {"preparation", "student", "examiner"}
        for roles in course_roles.values()
    )

    students = after.execute(
        "SELECT student_id,persona FROM students ORDER BY student_id"
    ).fetchall()
    assert [tuple(row) for row in students] == [
        ("student-balanced", "balanced"),
        ("student-novice", "novice"),
        ("student-target", "target"),
    ]

    quick_check = [str(row[0]) for row in after.execute("PRAGMA quick_check")]
    foreign_key_violations = after.execute("PRAGMA foreign_key_check").fetchall()
    active_jobs = after.execute(
        "SELECT count(*) FROM jobs WHERE state IN ('CLAIMED','RUNNING')"
    ).fetchone()[0]
    active_workers = after.execute(
        "SELECT count(*) FROM workers WHERE state IN ('STARTING','RUNNING')"
    ).fetchone()[0]
    paused = json.loads(
        after.execute(
            "SELECT value_json FROM system_state WHERE key='paused'"
        ).fetchone()[0]
    )
    assert quick_check == ["ok"]
    assert not foreign_key_violations
    assert active_jobs == 0
    assert active_workers == 0
    assert paused is True

    report = {
        "active_courses": active_courses,
        "preexisting_csdiy_cohort_rows_preserved": len(before_cohorts),
        "current_csdiy_cohort_graph_jobs": len(current_rows),
        "current_csdiy_course_role_coverage": len(course_roles),
        "student_target_course_coverage": len(target_courses),
        "durable_students": len(students),
        "active_byox_projects": active_projects,
        "baselines": len(baselines),
        "bindings": len(bindings),
        "verified_bindings": verified,
        "binding_roles": dict(sorted(role_counts.items())),
        "bound_job_profiles": [dict(row) for row in bound_job_profile],
        "legacy_total": len(before_legacy),
        "legacy_before_states": dict(
            sorted(
                collections.Counter(
                    str(row["state"]) for row in before_legacy.values()
                ).items()
            )
        ),
        "legacy_retired": len(retired_ids),
        "legacy_terminal_preserved": len(preserved_terminal_ids),
        "legacy_retirement_events": len(retirement_event_ids),
        "legacy_after_states": dict(
            sorted(
                collections.Counter(
                    str(row["state"]) for row in after_legacy.values()
                ).items()
            )
        ),
        "events": after.execute("SELECT count(*) FROM events").fetchone()[0],
        "jobs": after.execute("SELECT count(*) FROM jobs").fetchone()[0],
        "quick_check": quick_check,
        "foreign_key_violations": len(foreign_key_violations),
        "active_jobs": active_jobs,
        "active_workers": active_workers,
        "paused": paused,
        "db_sha256": sha256(POST),
    }
    print(json.dumps(report, indent=2, sort_keys=True))
