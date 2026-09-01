from __future__ import annotations

import collections
import hashlib
import json
import sqlite3
from pathlib import Path

from learnfactory.byox_baselines import load_verified_binding


ROOT = Path("/projects/se/pj34000401_refsys/users/yuali01/learn/.byox-release-rehearsal.Gs1PpV")
PRE = ROOT / "copied-live.db"
POST = ROOT / "cutover-working.db"


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
    preserved_ids = before_legacy.keys() - retired_ids
    assert len(retired_ids) == 655
    assert len(preserved_ids) == 68
    for identifier in retired_ids:
        row = after_legacy[identifier]
        assert row["state"] == "CANCELLED"
        assert row["cancel_requested"] == 1
        assert row["failure_kind"] == "superseded_byox_snapshot_scheme"
        assert str(row["error"]).startswith("superseded by immutable BYOX S2 job ")
    for identifier in preserved_ids:
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

    baselines = after.execute(
        "SELECT project_id,baseline_sha256 FROM byox_baseline_snapshots"
    ).fetchall()
    assert len(baselines) == 359
    assert len({str(row["project_id"]) for row in baselines}) == 359
    active_projects = after.execute(
        """
        SELECT count(*) FROM build_projects project
        JOIN sources source ON source.source_id=project.source_id
        WHERE source.is_active=1 AND source.type='project_catalog'
        """
    ).fetchone()[0]
    assert active_projects == 359

    bindings = after.execute(
        "SELECT job_id,role FROM byox_baseline_job_bindings ORDER BY job_id"
    ).fetchall()
    assert len(bindings) == 718
    role_counts = collections.Counter(str(row["role"]) for row in bindings)
    assert role_counts == {"builder": 359, "reviewer": 359}
    for row in bindings:
        verified = load_verified_binding(after, str(row["job_id"]))
        assert verified is not None
        assert verified.role == row["role"]

    bound_job_profile = after.execute(
        """
        SELECT model,reasoning_effort,count(*) AS count
        FROM jobs job
        JOIN byox_baseline_job_bindings binding ON binding.job_id=job.job_id
        GROUP BY model,reasoning_effort
        """
    ).fetchall()
    assert [tuple(row) for row in bound_job_profile] == [
        ("gpt-5.6-sol", "ultra", 718)
    ]

    active_courses = after.execute(
        """
        SELECT count(*) FROM courses course
        JOIN sources source ON source.source_id=course.source_id
        WHERE source.is_active=1 AND source.type='course_catalog'
        """
    ).fetchone()[0]
    assert active_courses == 82
    cohort_rows = after.execute(
        """
        SELECT json_extract(payload_json,'$.course_id') AS course_id,
               json_extract(payload_json,'$.seed_policy.role') AS role,
               json_extract(payload_json,'$.student_id') AS student_id
        FROM jobs
        WHERE json_extract(payload_json,'$.seed_policy.kind')='csdiy_course_cohort'
        """
    ).fetchall()
    assert len(cohort_rows) == 246
    course_roles: dict[str, set[str]] = collections.defaultdict(set)
    for row in cohort_rows:
        course_id = str(row["course_id"])
        role = str(row["role"])
        course_roles[course_id].add(role)
        if role in {"student", "examiner"}:
            assert row["student_id"] == "student-target"
    assert len(course_roles) == 82
    assert all(roles == {"preparation", "student", "examiner"} for roles in course_roles.values())

    quick_check = [str(row[0]) for row in after.execute("PRAGMA quick_check")]
    foreign_key_violations = after.execute("PRAGMA foreign_key_check").fetchall()
    assert quick_check == ["ok"]
    assert not foreign_key_violations

    report = {
        "active_courses": active_courses,
        "course_cohort_jobs": len(cohort_rows),
        "student_target_course_coverage": len(course_roles),
        "active_byox_projects": active_projects,
        "baselines": len(baselines),
        "bindings": len(bindings),
        "verified_bindings": len(bindings),
        "binding_roles": dict(sorted(role_counts.items())),
        "bound_job_profile": [dict(row) for row in bound_job_profile],
        "legacy_total": len(before_legacy),
        "legacy_before_states": dict(
            sorted(collections.Counter(str(row["state"]) for row in before_legacy.values()).items())
        ),
        "legacy_retired": len(retired_ids),
        "legacy_terminal_preserved": len(preserved_ids),
        "legacy_retirement_events": len(retirement_event_ids),
        "legacy_after_states": dict(
            sorted(collections.Counter(str(row["state"]) for row in after_legacy.values()).items())
        ),
        "events": after.execute("SELECT count(*) FROM events").fetchone()[0],
        "jobs": after.execute("SELECT count(*) FROM jobs").fetchone()[0],
        "quick_check": quick_check,
        "foreign_key_violations": len(foreign_key_violations),
        "db_sha256": sha256(POST),
    }
    print(json.dumps(report, indent=2, sort_keys=True))
