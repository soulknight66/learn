#!/usr/bin/env python3
"""Measure the exact scheduler selection and course-scan production helpers.

Fixtures live in unique ``tempfile`` directories and are always removed. Reported
VM steps come from SQLite's progress hook at an interval of one opcode. Logical
payload bytes describe rows returned to Python; they are not disk-throughput claims.
"""

from __future__ import annotations

import argparse
import json
import platform
import sqlite3
import tempfile
import time
from pathlib import Path
from typing import Any, Callable

from learnfactory.course_kickoff_revisions import _revision_groups_by_course
from learnfactory.course_progression import _progression_groups
from learnfactory.db import Database
from learnfactory.jobs import JobRepository


ROOT = Path(__file__).resolve().parents[1]


class _MeasuredDatabase(Database):
    def __init__(self, path: Path):
        super().__init__(path, ROOT / "migrations")
        self.vm_steps = 0

    def connect(
        self,
        *,
        busy_timeout_seconds: float | None = None,
    ) -> sqlite3.Connection:
        connection = super().connect(
            busy_timeout_seconds=busy_timeout_seconds
        )
        connection.set_progress_handler(self._progress, 1)
        return connection

    def _progress(self) -> int:
        self.vm_steps += 1
        return 0

    def reset_steps(self) -> None:
        self.vm_steps = 0


def _timed(operation: Callable[[], Any]) -> tuple[Any, float]:
    started = time.perf_counter()
    result = operation()
    return result, time.perf_counter() - started


def _fixture_job_id(index: int, job_count: int, scoped_jobs: int) -> str:
    if index < job_count - scoped_jobs:
        return f"job_unrelated_{index:06d}"
    kinds = (
        "csdiy_progress_v1",
        "csdiy_progress_v2",
        "csdiy_revision_v1",
        "csdiy_revision_v2",
        "csdiy_kickoff_rev_v1",
        "csdiy_kickoff_rev_v2",
    )
    return f"job_{kinds[index % len(kinds)]}_fixture_{index:06d}"


def _build_fixture(
    root: Path,
    *,
    job_count: int,
    payload_bytes: int,
    fenced_jobs: int,
    equal_priority: bool = False,
    unsatisfied_dependencies: bool = False,
) -> tuple[Path, int]:
    path = root / "factory.db"
    database = Database(path, ROOT / "migrations")
    database.migrate()
    scoped_jobs = max(6, job_count // 20)
    padding = "x" * payload_bytes
    open_payload = json.dumps({"padding": padding}, separators=(",", ":"))
    fenced_payload = json.dumps(
        {
            "padding": padding,
            "validators": [{"type": "command", "argv": ["true"]}],
        },
        separators=(",", ":"),
    )
    records = [
        (
            _fixture_job_id(index, job_count, scoped_jobs),
            "synthetic",
            "test",
            "DISCOVERED" if unsatisfied_dependencies else "READY",
            0.0 if equal_priority else float(job_count - index),
            fenced_payload if index < fenced_jobs else open_payload,
            float(index),
        )
        for index in range(job_count)
    ]
    with database.transaction(immediate=True) as connection:
        connection.executemany(
            """
            INSERT INTO jobs(
                job_id,type,worker_type,state,priority,payload_json,created_at
            ) VALUES (?,?,?,?,?,?,?)
            """,
            records,
        )
        if unsatisfied_dependencies:
            connection.execute(
                """
                INSERT INTO jobs(
                    job_id,type,worker_type,state,payload_json,created_at
                ) VALUES (
                    'job_benchmark_cancelled_dependency','synthetic','test',
                    'CANCELLED','{}',-1
                )
                """
            )
            connection.executemany(
                """
                INSERT INTO job_dependencies(job_id,depends_on_job_id)
                VALUES (?,'job_benchmark_cancelled_dependency')
                """,
                [(record[0],) for record in records],
            )
            connection.execute(
                """
                UPDATE jobs SET state='READY'
                WHERE job_id <> 'job_benchmark_cancelled_dependency'
                """
            )
    return path, scoped_jobs


def _measure_claim_selection(
    database: _MeasuredDatabase,
) -> dict[str, object]:
    jobs = JobRepository(database)

    def select() -> object:
        database.reset_steps()
        return jobs._select_claimable_candidate(
            max_total=12,
            type_limits={"test": 12},
            blocked_validator_types=frozenset({"command"}),
        )

    selected, elapsed = _timed(select)
    return {
        "selected_job_id": selected.job_id if selected else None,
        "vm_steps": database.vm_steps,
        "elapsed_ms_with_per_opcode_hook": round(elapsed * 1000, 3),
    }


def _measure_all_fenced(
    job_count: int,
    payload_bytes: int,
    *,
    equal_priority: bool = False,
) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="learnfactory-io-fenced-") as raw:
        path, _ = _build_fixture(
            Path(raw),
            job_count=job_count,
            payload_bytes=payload_bytes,
            fenced_jobs=job_count,
            equal_priority=equal_priority,
        )
        result = _measure_claim_selection(_MeasuredDatabase(path))
    if result["selected_job_id"] is not None:
        raise RuntimeError("all-fenced fixture unexpectedly selected a job")
    return result


def _measure_all_unsatisfied_dependencies(
    job_count: int,
    payload_bytes: int,
) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="learnfactory-io-dependencies-") as raw:
        path, _ = _build_fixture(
            Path(raw),
            job_count=job_count,
            payload_bytes=payload_bytes,
            fenced_jobs=0,
            unsatisfied_dependencies=True,
        )
        result = _measure_claim_selection(_MeasuredDatabase(path))
    if result["selected_job_id"] is not None:
        raise RuntimeError("unsatisfied-dependency fixture selected a job")
    return result


def _measure_primary(
    job_count: int, payload_bytes: int, eligible_offset: int
) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="learnfactory-io-primary-") as raw:
        path, scoped_jobs = _build_fixture(
            Path(raw),
            job_count=job_count,
            payload_bytes=payload_bytes,
            fenced_jobs=eligible_offset,
        )
        database = _MeasuredDatabase(path)
        claim = _measure_claim_selection(database)

        def progression() -> object:
            database.reset_steps()
            return _progression_groups(database)

        _, progression_elapsed = _timed(progression)
        progression_steps = database.vm_steps

        def kickoff() -> object:
            database.reset_steps()
            return _revision_groups_by_course(
                database,
                {"course-fixture": ("source-fixture", "f" * 40)},
            )

        _, kickoff_elapsed = _timed(kickoff)
        kickoff_steps = database.vm_steps

        with database.connect() as connection:
            legacy_started = time.perf_counter()
            legacy_rows = connection.execute(
                """
                SELECT * FROM jobs
                WHERE state='READY' AND cancel_requested=0
                  AND attempt_count < max_attempts
                ORDER BY priority DESC,created_at,job_id
                """
            ).fetchall()
            legacy_elapsed = time.perf_counter() - legacy_started
            database_bytes = path.stat().st_size
        legacy_payload_bytes = sum(
            len(str(row["payload_json"]).encode("utf-8"))
            for row in legacy_rows
        )
    return {
        "fixture": {
            "database_bytes": database_bytes,
            "jobs": job_count,
            "payload_padding_bytes_per_job": payload_bytes,
            "first_eligible_candidate_offset": eligible_offset,
            "scoped_course_job_ids": scoped_jobs,
        },
        "production_claim_selection": claim,
        "legacy_whole_ready_materialization": {
            "rows": len(legacy_rows),
            "payload_bytes": legacy_payload_bytes,
            "elapsed_ms": round(legacy_elapsed * 1000, 3),
        },
        "production_course_helpers": {
            "progression_groups": {
                "vm_steps": progression_steps,
                "elapsed_ms_with_per_opcode_hook": round(
                    progression_elapsed * 1000, 3
                ),
            },
            "kickoff_revision_groups": {
                "vm_steps": kickoff_steps,
                "elapsed_ms_with_per_opcode_hook": round(
                    kickoff_elapsed * 1000, 3
                ),
            },
        },
    }


def measure(job_count: int, payload_bytes: int, eligible_offset: int) -> dict[str, object]:
    if job_count < 12 or payload_bytes < 1:
        raise ValueError("job_count must be >= 12 and payload_bytes must be positive")
    eligible_offset = min(max(0, eligible_offset), job_count - 1)
    half_count = max(12, job_count // 2)
    half = _measure_all_fenced(half_count, payload_bytes)
    full = _measure_all_fenced(job_count, payload_bytes)
    equal_half = _measure_all_fenced(
        half_count,
        payload_bytes,
        equal_priority=True,
    )
    equal_full = _measure_all_fenced(
        job_count,
        payload_bytes,
        equal_priority=True,
    )
    dependency_half = _measure_all_unsatisfied_dependencies(
        half_count,
        payload_bytes,
    )
    dependency_full = _measure_all_unsatisfied_dependencies(
        job_count,
        payload_bytes,
    )
    half_steps = int(half["vm_steps"])
    full_steps = int(full["vm_steps"])
    equal_half_steps = int(equal_half["vm_steps"])
    equal_full_steps = int(equal_full["vm_steps"])
    dependency_half_steps = int(dependency_half["vm_steps"])
    dependency_full_steps = int(dependency_full["vm_steps"])
    return {
        "environment": {
            "python": platform.python_version(),
            "sqlite": sqlite3.sqlite_version,
            "platform": platform.platform(),
            "temp_root": "unique tempfile.TemporaryDirectory (removed)",
        },
        "primary": _measure_primary(job_count, payload_bytes, eligible_offset),
        "all_fenced_production_scan_scaling": {
            "half": {"jobs": half_count, **half},
            "full": {"jobs": job_count, **full},
            "vm_step_ratio_full_over_half": round(full_steps / half_steps, 3),
            "vm_steps_per_job_full": round(full_steps / job_count, 3),
        },
        "all_fenced_equal_priority_scan_scaling": {
            "half": {"jobs": half_count, **equal_half},
            "full": {"jobs": job_count, **equal_full},
            "vm_step_ratio_full_over_half": round(
                equal_full_steps / equal_half_steps, 3
            ),
            "vm_steps_per_job_full": round(
                equal_full_steps / job_count, 3
            ),
        },
        "all_unsatisfied_dependency_scan_scaling": {
            "half": {"jobs": half_count, **dependency_half},
            "full": {"jobs": job_count, **dependency_full},
            "vm_step_ratio_full_over_half": round(
                dependency_full_steps / dependency_half_steps,
                3,
            ),
            "vm_steps_per_job_full": round(
                dependency_full_steps / job_count,
                3,
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--jobs", type=int, default=2_000)
    parser.add_argument("--payload-bytes", type=int, default=4_096)
    parser.add_argument("--eligible-offset", type=int, default=129)
    args = parser.parse_args()
    print(
        json.dumps(
            measure(args.jobs, args.payload_bytes, args.eligible_offset),
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
