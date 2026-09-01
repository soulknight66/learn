from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import hashlib
import json
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any

from .byox_remediation import (
    DEFAULT_MAX_REPAIR_GENERATIONS,
    seed_byox_remediation_jobs,
)
from .config import load_settings
from .course_progression import (
    DEFAULT_MAX_COURSES,
    seed_next_csdiy_course_batches,
)
from .db import Database, MigrationError
from .jobs import JobError, JobRepository
from .learners import seed_students
from .planner import curriculum_plan, plan_markdown
from .reporting import status_snapshot, write_checkpoint
from .scheduler import run_scheduler
from .seeding import seed_all_catalog_jobs, seed_catalog_synthesis_job, seed_initial_jobs
from .sources import describe as describe_source
from .util import json_value, slugify
from .workspace import WorkspaceManager, contained


_SAFE_COMPONENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,155}$")


def _context(
    config: Path | None = None, *, migrate: bool = True
) -> tuple[Any, Database, JobRepository, WorkspaceManager]:
    settings = load_settings(config)
    db = Database(settings.database, settings.migrations)
    if migrate:
        db.migrate()
    jobs = JobRepository(db, retry_base=settings.retry_base_seconds, retry_max=settings.retry_max_seconds)
    workspaces = WorkspaceManager(settings.warehouse, db)
    return settings, db, jobs, workspaces


def cmd_init(args: argparse.Namespace) -> int:
    settings, db, _, workspaces = _context(args.config, migrate=False)
    applied = db.migrate()
    workspaces.initialize()
    students = seed_students(db, settings.warehouse)
    print(json.dumps({"database": str(settings.database), "migrations_applied": applied, "students": students}, indent=2))
    return 0


def cmd_ingest(args: argparse.Namespace) -> int:
    settings, db, jobs, workspaces = _context(args.config)
    db.migrate()
    workspaces.initialize()
    created: list[str] = []
    for raw in args.paths:
        path = Path(raw).resolve()
        if not path.is_dir():
            raise RuntimeError(f"source path is not a directory: {path}")
        descriptor = describe_source(path)
        base_identifier = f"job_ingest_{path.name.replace('-', '_')}"
        extractor_version = str(descriptor.metadata.get("extractor_version", "unknown"))
        fingerprint = hashlib.sha256(str(path).encode("utf-8")).hexdigest()[:10]
        revision = re.sub(r"[^A-Za-z0-9_.-]", "-", extractor_version).strip("-.") or "unknown"
        identifier = base_identifier
        base_job = jobs.get(base_identifier)
        base_payload = base_job["payload"] if base_job is not None else {}
        base_matches_snapshot = (
            base_payload.get("source_path") == str(path)
            and base_payload.get("expected_commit") == descriptor.commit_hash
            and base_payload.get("extractor_version") == extractor_version
        )
        if base_job is not None and not base_matches_snapshot:
            identifier = (
                f"job_ingest_{slugify(path.name)}_{fingerprint}_"
                f"{descriptor.commit_hash[:12]}_v{revision}"
            )
        existing = jobs.get(identifier)
        if existing is None:
            jobs.create(
                "source_ingest",
                "ingestion",
                {
                    "source_path": str(path),
                    "expected_commit": descriptor.commit_hash,
                    "adapter": str(descriptor.metadata.get("adapter", "unknown")),
                    "extractor_version": extractor_version,
                    "artifact_path": f"sources/{path.name}",
                },
                priority=101 if identifier != base_identifier else 100,
                max_attempts=2,
                job_id=identifier,
            )
            created.append(identifier)
    synthesis_job: str | None = None
    if created:
        with db.connect() as connection:
            available = connection.execute(
                """
                SELECT
                  (SELECT COUNT(*) FROM courses c JOIN sources s ON s.source_id=c.source_id
                   WHERE s.is_active=1) AS courses,
                  (SELECT COUNT(*) FROM build_projects p JOIN sources s ON s.source_id=p.source_id
                   WHERE s.is_active=1) AS projects
                """
            ).fetchone()
        if available["courses"] and available["projects"]:
            refresh_key = hashlib.sha256(
                "\0".join(sorted(created)).encode("utf-8")
            ).hexdigest()[:16]
            synthesis_job = seed_catalog_synthesis_job(
                db,
                jobs,
                job_id=f"job_catalog_synthesis_refresh_{refresh_key}",
                dependencies=created,
            )
    jobs.promote_eligible()
    print(
        json.dumps(
            {
                "created": created,
                "existing": len(args.paths) - len(created),
                "synthesis_job": synthesis_job,
            },
            indent=2,
        )
    )
    return 0


def cmd_seed(args: argparse.Namespace) -> int:
    settings, db, jobs, workspaces = _context(args.config)
    db.migrate()
    workspaces.initialize()
    students = seed_students(db, settings.warehouse)
    identifiers = seed_initial_jobs(db, jobs)
    print(json.dumps({"students": students, "jobs": identifiers}, indent=2))
    return 0


def cmd_seed_all(args: argparse.Namespace) -> int:
    """Durably seed the full catalog graph; deliberately do not run it."""

    settings, db, jobs, workspaces = _context(args.config)
    db.migrate()
    workspaces.initialize()
    students = seed_students(db, settings.warehouse)
    result = seed_all_catalog_jobs(db, jobs)
    print(json.dumps({"students": students, **result}, indent=2, sort_keys=True))
    return 0


def cmd_seed_course_next(args: argparse.Namespace) -> int:
    """Refill one bounded post-kickoff unit batch for eligible courses."""

    settings, db, jobs, workspaces = _context(args.config)
    db.migrate()
    workspaces.initialize()
    students = seed_students(db, settings.warehouse)
    result = seed_next_csdiy_course_batches(
        db,
        jobs,
        max_courses=args.max_courses,
        max_revisions=(
            settings.course_revision_limit
            if args.max_revisions is None
            else args.max_revisions
        ),
        course_ids=args.course_id,
    )
    promoted = jobs.promote_eligible()
    print(
        json.dumps(
            {"students": students, **result, "promoted_ready": promoted},
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def cmd_seed_byox_repairs(args: argparse.Namespace) -> int:
    """Advance one deterministic phase for each bounded BYOX repair graph."""

    settings, db, jobs, workspaces = _context(args.config)
    db.migrate()
    workspaces.initialize()
    result = seed_byox_remediation_jobs(
        db,
        jobs,
        max_repair_generations=args.max_generations,
        project_ids=args.project_id,
        max_projects=args.max_projects,
    )
    promoted = jobs.promote_eligible()
    print(
        json.dumps(
            {**result, "promoted_ready": promoted},
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    settings, db, _, workspaces = _context(args.config)
    db.migrate()
    workspaces.initialize()
    dispatched = asyncio.run(
        run_scheduler(settings, db, until_idle=args.until_idle, max_jobs=args.max_jobs)
    )
    write_checkpoint(db, settings.root / "reports", settings.warehouse)
    print(json.dumps({"dispatched": dispatched}))
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    settings, db, _, _ = _context(args.config)
    snapshot = status_snapshot(db)
    if args.json:
        print(json.dumps(snapshot, indent=2, sort_keys=True))
        return 0
    print(f"paused: {snapshot['paused']}")
    print("jobs: " + ", ".join(f"{key}={value}" for key, value in sorted(snapshot["jobs"].items())))
    print("corpus: " + ", ".join(f"{key}={value}" for key, value in snapshot["counts"].items()))
    print(f"active workers: {len(snapshot['active_workers'])}")
    for worker in snapshot["active_workers"]:
        print(f"  {worker['worker_id']} {worker['type']} job={worker['current_job']} pid={worker['process_id']}")
    if snapshot["recent_failures"]:
        print("recent failures:")
        for failure in snapshot["recent_failures"]:
            print(f"  {failure['job_id']} {failure['failure_kind']}: {failure['error']}")
    return 0


def cmd_jobs(args: argparse.Namespace) -> int:
    _, db, _, _ = _context(args.config)
    query = "SELECT job_id,type,worker_type,state,priority,attempt_count,max_attempts,owner,lease_expires_at,error FROM jobs"
    values: tuple[Any, ...] = ()
    if args.state:
        query += " WHERE state=?"
        values = (args.state,)
    query += " ORDER BY created_at,job_id"
    with db.connect() as connection:
        rows = [dict(row) for row in connection.execute(query, values)]
    if args.json:
        print(json.dumps(rows, indent=2, sort_keys=True))
    else:
        for row in rows:
            print(
                f"{row['job_id']} {row['state']:<10} {row['worker_type']:<18} "
                f"attempts={row['attempt_count']}/{row['max_attempts']} priority={row['priority']:.1f}"
            )
    return 0


def cmd_workers(args: argparse.Namespace) -> int:
    _, db, _, _ = _context(args.config)
    with db.connect() as connection:
        rows = [dict(row) for row in connection.execute("SELECT * FROM workers ORDER BY started_at DESC")]
    print(json.dumps(rows, indent=2, sort_keys=True))
    return 0


def cmd_failures(args: argparse.Namespace) -> int:
    args.state = "FAILED"
    return cmd_jobs(args)


def cmd_artifacts(args: argparse.Namespace) -> int:
    _, db, _, _ = _context(args.config)
    with db.connect() as connection:
        rows = [dict(row) for row in connection.execute(
            """
            SELECT artifact_id,job_id,type,path,checksum,checksum_algorithm,integrity_status,
                   validation_status,created_at
            FROM artifacts ORDER BY created_at DESC
            """
        )]
    print(json.dumps(rows, indent=2, sort_keys=True))
    return 0


def cmd_inspect(args: argparse.Namespace) -> int:
    _, db, jobs, _ = _context(args.config)
    job = jobs.get(args.job_id)
    if job is None:
        raise JobError(f"unknown job {args.job_id}")
    with db.connect() as connection:
        dependencies = [row[0] for row in connection.execute(
            "SELECT depends_on_job_id FROM job_dependencies WHERE job_id=?", (args.job_id,)
        )]
        events = [dict(row) for row in connection.execute(
            "SELECT event_id,timestamp,actor,type,payload_json FROM events WHERE job_id=? ORDER BY event_id", (args.job_id,)
        )]
        validations = [dict(row) for row in connection.execute(
            "SELECT validator,status,exit_code,evidence_json,started_at,finished_at FROM validations WHERE job_id=?", (args.job_id,)
        )]
        artifacts = [dict(row) for row in connection.execute(
            """
            SELECT artifact_id,type,path,checksum,checksum_algorithm,integrity_status,validation_status
            FROM artifacts WHERE job_id=?
            """,
            (args.job_id,),
        )]
        runs = []
        for row in connection.execute(
            """
            SELECT run_id,attempt_number,backend,model,reasoning_effort,provider,
                   base_url,wire_api,supports_websockets,session_id,process_id,
                   started_at,finished_at,exit_code,reproducibility_digest,
                   reproducibility_path,reproducibility_json
            FROM job_runs WHERE job_id=? ORDER BY attempt_number,started_at,run_id
            """,
            (args.job_id,),
        ):
            rendered = dict(row)
            rendered["reproducibility"] = json_value(
                rendered.pop("reproducibility_json"), {}
            )
            runs.append(rendered)
    print(json.dumps({"job": job, "dependencies": dependencies, "events": events, "validations": validations, "artifacts": artifacts, "runs": runs}, indent=2, sort_keys=True))
    return 0


def cmd_retry(args: argparse.Namespace) -> int:
    _, _, jobs, _ = _context(args.config)
    jobs.retry(args.job_id)
    print(args.job_id)
    return 0


def cmd_cancel(args: argparse.Namespace) -> int:
    _, _, jobs, _ = _context(args.config)
    jobs.cancel(args.job_id)
    print(args.job_id)
    return 0


def cmd_pause(args: argparse.Namespace) -> int:
    _, db, _, _ = _context(args.config)
    db.set_system_value("paused", True)
    db.emit_event("operator", "FACTORY_PAUSED")
    print("paused")
    return 0


def cmd_resume(args: argparse.Namespace) -> int:
    _, db, _, _ = _context(args.config)
    db.set_system_value("paused", False)
    db.emit_event("operator", "FACTORY_RESUMED")
    print("resumed")
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    settings, db, _, _ = _context(args.config)
    markdown, machine = write_checkpoint(db, settings.root / "reports", settings.warehouse)
    print(json.dumps({"markdown": str(markdown), "json": str(machine)}, indent=2))
    return 0


def cmd_exercise_start(args: argparse.Namespace) -> int:
    settings, db, _, manager = _context(args.config)
    if _SAFE_COMPONENT.fullmatch(args.student) is None:
        raise ValueError("student must be one safe path component")
    if _SAFE_COMPONENT.fullmatch(args.exercise_id) is None:
        raise ValueError("exercise id must be one safe path component")
    with db.connect() as connection:
        if connection.execute(
            "SELECT 1 FROM students WHERE student_id=?", (args.student,)
        ).fetchone() is None:
            raise ValueError(f"unknown student: {args.student}")
    challenge = Path(args.challenge).resolve()
    if not contained(settings.warehouse / "artifacts", challenge):
        raise ValueError("challenge must be a published warehouse artifact")
    destination = settings.warehouse / "learners" / args.student / "exercises" / args.exercise_id
    if not contained(settings.warehouse / "learners", destination):
        raise ValueError("exercise destination escapes the learner store")
    manager.create_student_view(challenge, destination)
    print(destination)
    return 0


def cmd_plan(args: argparse.Namespace) -> int:
    settings, db, _, _ = _context(args.config)
    plan = curriculum_plan(
        db,
        topic=args.topic,
        weeks=args.weeks,
        hours_per_week=args.hours_per_week,
        language=args.language,
        persona=args.student.removeprefix("student-"),
    )
    if args.json:
        print(json.dumps(plan, indent=2, sort_keys=True, ensure_ascii=False))
    else:
        print(plan_markdown(plan), end="")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="learnfactory", description="Operate the autonomous CS learning factory")
    parser.add_argument("--config", type=Path, help="factory TOML path")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init", help="apply migrations and initialize warehouse").set_defaults(func=cmd_init)
    ingest = commands.add_parser("ingest", help="enqueue explicit local source repositories")
    ingest.add_argument("paths", nargs="+")
    ingest.set_defaults(func=cmd_ingest)
    commands.add_parser("seed", help="seed initial vertical slices and learners").set_defaults(func=cmd_seed)
    commands.add_parser(
        "seed-all",
        help="seed the backend-gated all-catalog graph without running it",
    ).set_defaults(func=cmd_seed_all)
    course_next = commands.add_parser(
        "seed-course-next",
        help="seed one bounded post-kickoff unit batch for each eligible CSDIY course",
    )
    course_next.add_argument("--course-id", action="append")
    course_next.add_argument("--max-courses", type=int, default=DEFAULT_MAX_COURSES)
    course_next.add_argument(
        "--max-revisions",
        type=int,
        help="revision attempts after the initial unit attempt (default: configured limit)",
    )
    course_next.set_defaults(func=cmd_seed_course_next)
    byox_repairs = commands.add_parser(
        "seed-byox-repairs",
        help="advance bounded independently triggered BYOX repair graphs",
    )
    byox_repairs.add_argument("--project-id", action="append")
    byox_repairs.add_argument(
        "--max-generations",
        type=int,
        default=DEFAULT_MAX_REPAIR_GENERATIONS,
        help="maximum repair generations per project (default: 2)",
    )
    byox_repairs.add_argument(
        "--max-projects",
        type=int,
        help="optional deterministic bound on examined active projects",
    )
    byox_repairs.set_defaults(func=cmd_seed_byox_repairs)
    run = commands.add_parser("run", help="run bounded scheduler")
    run.add_argument("--until-idle", action="store_true")
    run.add_argument("--max-jobs", type=int)
    run.set_defaults(func=cmd_run)
    status = commands.add_parser("status", help="show health and progress")
    status.add_argument("--json", action="store_true")
    status.set_defaults(func=cmd_status)
    jobs = commands.add_parser("jobs", help="list jobs")
    jobs.add_argument("--state")
    jobs.add_argument("--json", action="store_true")
    jobs.set_defaults(func=cmd_jobs)
    workers = commands.add_parser("workers", help="list worker history")
    workers.set_defaults(func=cmd_workers)
    failures = commands.add_parser("failures", help="list failed jobs")
    failures.add_argument("--json", action="store_true")
    failures.set_defaults(func=cmd_failures)
    artifacts = commands.add_parser("artifacts", help="list durable artifacts")
    artifacts.set_defaults(func=cmd_artifacts)
    inspect = commands.add_parser("inspect", help="inspect a job and its evidence")
    inspect.add_argument("job_id")
    inspect.set_defaults(func=cmd_inspect)
    retry = commands.add_parser("retry", help="retry a failed or blocked job")
    retry.add_argument("job_id")
    retry.set_defaults(func=cmd_retry)
    cancel = commands.add_parser("cancel", help="cancel or request cancellation")
    cancel.add_argument("job_id")
    cancel.set_defaults(func=cmd_cancel)
    commands.add_parser("pause", help="pause new claims").set_defaults(func=cmd_pause)
    commands.add_parser("resume", help="resume new claims").set_defaults(func=cmd_resume)
    commands.add_parser("report", help="write checkpoint and catalog").set_defaults(func=cmd_report)
    exercise = commands.add_parser("exercise-start", help="create a student-safe challenge view")
    exercise.add_argument("exercise_id")
    exercise.add_argument("challenge")
    exercise.add_argument("--student", default="student-target")
    exercise.set_defaults(func=cmd_exercise_start)
    plan = commands.add_parser("plan", help="build a curriculum from normalized catalog metadata")
    plan.add_argument("--topic", required=True)
    plan.add_argument("--weeks", type=int, default=12)
    plan.add_argument("--hours-per-week", type=float, default=10)
    plan.add_argument("--language")
    plan.add_argument("--student", default="student-target")
    plan.add_argument("--json", action="store_true")
    plan.set_defaults(func=cmd_plan)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except (RuntimeError, JobError, MigrationError, OSError, ValueError, sqlite3.Error) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
