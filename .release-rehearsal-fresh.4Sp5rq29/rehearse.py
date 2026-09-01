from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path
from unittest.mock import patch

from learnfactory.backend_policy import (
    MASS_SEED_BACKEND_REQUIREMENT,
    MASS_SEED_EXECUTION_POLICY,
)
from learnfactory.byox_baselines import load_verified_binding
from learnfactory.db import Database
from learnfactory.jobs import JobRepository
from learnfactory.learners import seed_students
from learnfactory.seeding import (
    BYOX_BUILD_S2_POLICY_KIND,
    BYOX_REVIEW_S2_POLICY_KIND,
    CODEX_BACKEND_GATE_JOB_ID,
    seed_all_byox_reference_jobs,
    seed_all_catalog_jobs,
)


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def physical_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def insert_catalog_fixture(database: Database) -> None:
    with database.transaction(immediate=True) as connection:
        connection.execute(
            """
            INSERT INTO sources(
                source_id,type,name,path,upstream_url,commit_hash,license,
                ingested_at,metadata_json,is_active
            ) VALUES (?,?,?,?,?,?,?,?,?,1)
            """,
            (
                "source_csdiy_active",
                "course_catalog",
                "CSDIY",
                "/public/catalogs/csdiy",
                "https://github.com/PKUFlyingPig/cs-self-learning",
                "csdiy-commit-1",
                "CC-BY-SA-4.0",
                1000.0,
                canonical_json(
                    {"adapter": "cs_self_learning", "extractor_version": "1.0"}
                ),
            ),
        )
        connection.execute(
            """
            INSERT INTO sources(
                source_id,type,name,path,upstream_url,commit_hash,license,
                ingested_at,metadata_json,is_active
            ) VALUES (?,?,?,?,?,?,?,?,?,1)
            """,
            (
                "source_byox_active",
                "project_catalog",
                "Build Your Own X",
                "/public/catalogs/build-your-own-x",
                "https://github.com/codecrafters-io/build-your-own-x",
                "byox-commit-1",
                "CC0-1.0",
                1001.0,
                canonical_json(
                    {
                        "adapter": "build_your_own_x",
                        "extractor_version": "1.1",
                        "snapshot_reader": "git-object-database",
                        "tree_hash": "byox-tree-1",
                    }
                ),
            ),
        )
        connection.executemany(
            """
            INSERT INTO courses(
                course_id,source_id,slug,institution,title,topic,description,
                prerequisites_json,estimated_human_hours,difficulty,
                source_metadata_json,status
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            [
                (
                    f"course_{index:032x}",
                    "source_csdiy_active",
                    f"systems-course-{index}",
                    f"Institution {index % 7}",
                    f"Systems Engineering Course {index}",
                    "systems",
                    "A source-derived catalog description.",
                    "[]",
                    float(20 + index),
                    float(1 + index % 10),
                    canonical_json(
                        {
                            "catalog_index": index,
                            "links": [f"https://example.invalid/{index}"],
                        }
                    ),
                    "DISCOVERED",
                )
                for index in range(82)
            ],
        )
        connection.executemany(
            """
            INSERT INTO course_units(
                unit_id,course_id,type,unit_order,title,dependencies_json,
                source_reference,metadata_json
            ) VALUES (?,?,?,?,?,?,?,?)
            """,
            [
                (
                    f"unit_{index:032x}",
                    f"course_{index % 82:032x}",
                    "reading",
                    index // 82,
                    f"Catalog resource {index}",
                    "[]",
                    f"https://example.invalid/resource/{index}",
                    canonical_json({"normalized_resource_link": True}),
                )
                for index in range(394)
            ],
        )
        connection.executemany(
            """
            INSERT INTO build_projects(
                project_id,source_id,slug,title,category,implementation_language,
                upstream_reference,concepts_json,difficulty,production_relevance,
                source_format,priority_tier,metadata_json
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            [
                (
                    f"project_{index:032x}",
                    "source_byox_active",
                    f"build-system-{index}",
                    f"Build System {index}",
                    "Database" if index % 2 == 0 else "Networking",
                    "Rust" if index % 3 == 0 else "C++",
                    f"https://example.invalid/byox/{index}",
                    canonical_json(
                        ["testing", "systems", f"concept-{index % 11}"]
                    ),
                    float(3 + index % 8),
                    float(4 + index % 7),
                    "repository",
                    1 + index % 3,
                    canonical_json(
                        {
                            "catalog_index": index,
                            "linked_resource_license": "NOASSERTION",
                        }
                    ),
                )
                for index in range(359)
            ],
        )


def payload_rows(connection: sqlite3.Connection) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    for row in connection.execute(
        "SELECT job_id,model,reasoning_effort,payload_json FROM jobs ORDER BY job_id"
    ):
        payload = json.loads(str(row["payload_json"]))
        assert isinstance(payload, dict)
        result.append(
            {
                "job_id": str(row["job_id"]),
                "model": row["model"],
                "reasoning_effort": row["reasoning_effort"],
                "payload": payload,
            }
        )
    return result


def dependencies(connection: sqlite3.Connection, job_id: str) -> set[str]:
    return {
        str(row["depends_on_job_id"])
        for row in connection.execute(
            "SELECT depends_on_job_id FROM job_dependencies WHERE job_id=?",
            (job_id,),
        )
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()

    repo = arguments.repo.resolve()
    output = arguments.output.resolve()
    output.mkdir(mode=0o700, parents=True, exist_ok=True)
    database_path = output / "factory.db"
    warehouse = (output / "warehouse").resolve()
    database = Database(database_path, repo / "migrations")

    applied_migrations = database.migrate()
    jobs = JobRepository(database)
    student_ids = seed_students(database, warehouse)
    insert_catalog_fixture(database)
    first = seed_all_catalog_jobs(database, jobs, warehouse=warehouse)

    assert first["courses"]["active_catalog_entries"] == 82
    assert first["courses"]["covered_entries"] == 82
    assert first["courses"]["seeded_cohorts"] == 82
    assert first["build_projects"]["active_catalog_entries"] == 359
    assert first["build_projects"]["covered_entries"] == 359
    assert first["build_projects"]["generic_builders"] == 359
    assert first["build_projects"]["reviewers"] == 359
    assert first["build_projects"]["recognized_specialized"] == 0
    assert first["build_projects"]["deferred_active_legacy"] == 0
    assert first["created_jobs"] == 965
    assert first["execution_started"] is False

    with database.connect() as connection:
        rows = payload_rows(connection)
        course_roles: dict[str, set[str]] = {}
        builders: list[dict[str, object]] = []
        reviewers: list[dict[str, object]] = []
        for record in rows:
            payload = record["payload"]
            assert isinstance(payload, dict)
            policy = payload.get("seed_policy")
            kind = policy.get("kind") if isinstance(policy, dict) else None
            role = policy.get("role") if isinstance(policy, dict) else None
            if kind == "csdiy_course_cohort":
                course_id = payload.get("course_id")
                assert isinstance(course_id, str)
                assert isinstance(role, str)
                course_roles.setdefault(course_id, set()).add(role)
            elif kind == BYOX_BUILD_S2_POLICY_KIND:
                builders.append(record)
            elif kind == BYOX_REVIEW_S2_POLICY_KIND:
                reviewers.append(record)

        assert len(rows) == 965
        assert len(course_roles) == 82
        assert all(
            roles == {"preparation", "student", "examiner"}
            for roles in course_roles.values()
        )
        assert len(builders) == 359
        assert len(reviewers) == 359
        assert all(record["model"] == "gpt-5.6-sol" for record in rows)
        assert all(record["reasoning_effort"] == "ultra" for record in rows)
        assert all(
            record["payload"].get("required_backend")
            == MASS_SEED_BACKEND_REQUIREMENT
            for record in rows
        )
        assert all(
            record["payload"].get("execution_policy")
            == MASS_SEED_EXECUTION_POLICY
            for record in rows
        )

        graphs = first["build_projects"]["projects"]
        assert len(graphs) == 359
        graph_baselines: set[str] = set()
        for project_id, graph in graphs.items():
            assert graph["mode"] == "seeded_generic_s2"
            builder_id = graph["builder"]
            reviewer_id = graph["reviewer"]
            assert isinstance(builder_id, str) and isinstance(reviewer_id, str)
            assert dependencies(connection, builder_id) == {
                CODEX_BACKEND_GATE_JOB_ID
            }
            assert dependencies(connection, reviewer_id) == {
                CODEX_BACKEND_GATE_JOB_ID,
                builder_id,
            }
            graph_baselines.add(graph["baseline_sha256"])
            assert project_id.startswith("project_")
        assert len(graph_baselines) == 359

        baseline_count = int(
            connection.execute(
                "SELECT COUNT(*) AS n FROM byox_baseline_snapshots"
            ).fetchone()["n"]
        )
        binding_ids = [
            str(row["job_id"])
            for row in connection.execute(
                "SELECT job_id FROM byox_baseline_job_bindings ORDER BY job_id"
            )
        ]
        verified = [load_verified_binding(connection, job_id) for job_id in binding_ids]
        assert baseline_count == 359
        assert len(binding_ids) == 718
        assert all(value is not None for value in verified)
        binding_roles = {
            str(row["role"]): int(row["n"])
            for row in connection.execute(
                "SELECT role,COUNT(*) AS n FROM byox_baseline_job_bindings GROUP BY role"
            )
        }
        assert binding_roles == {"builder": 359, "reviewer": 359}
        foreign_key_check = [tuple(row) for row in connection.execute("PRAGMA foreign_key_check")]
        quick_check = [str(row[0]) for row in connection.execute("PRAGMA quick_check")]
        assert foreign_key_check == []
        assert quick_check == ["ok"]
        event_count_before = int(
            connection.execute("SELECT COUNT(*) AS n FROM events").fetchone()["n"]
        )

    sha_before = physical_sha256(database_path)
    traced_control_statements: list[str] = []
    original_connect = database.connect

    def traced_connect() -> sqlite3.Connection:
        connection = original_connect()

        def trace(statement: str) -> None:
            normalized = " ".join(statement.strip().split())
            command = normalized.partition(" ")[0].upper()
            if command in {
                "BEGIN",
                "COMMIT",
                "ROLLBACK",
                "INSERT",
                "UPDATE",
                "DELETE",
                "REPLACE",
            }:
                traced_control_statements.append(normalized)

        connection.set_trace_callback(trace)
        return connection

    with patch.object(database, "connect", side_effect=traced_connect), patch.object(
        database,
        "transaction",
        side_effect=AssertionError("repeat attempted a managed writer transaction"),
    ) as writer_api:
        repeated = seed_all_byox_reference_jobs(
            database,
            jobs,
            warehouse=warehouse,
        )
        managed_writer_api_calls = writer_api.call_count

    sha_after = physical_sha256(database_path)
    with database.connect() as connection:
        event_count_after = int(
            connection.execute("SELECT COUNT(*) AS n FROM events").fetchone()["n"]
        )
        foreign_key_check_after = [
            tuple(row) for row in connection.execute("PRAGMA foreign_key_check")
        ]
        quick_check_after = [str(row[0]) for row in connection.execute("PRAGMA quick_check")]

    write_statements = [
        statement
        for statement in traced_control_statements
        if statement.partition(" ")[0].upper()
        in {"INSERT", "UPDATE", "DELETE", "REPLACE"}
        or statement.upper().startswith("BEGIN IMMEDIATE")
        or statement.upper().startswith("BEGIN EXCLUSIVE")
    ]
    assert repeated["created_jobs"] == 0
    assert repeated["created_builder_jobs"] == 0
    assert repeated["created_reviewer_jobs"] == 0
    assert repeated["projects"] == first["build_projects"]["projects"]
    assert managed_writer_api_calls == 0
    # SQLite reports the explicit deferred read transaction and its clean
    # context-manager close as BEGIN/COMMIT.  Neither statement takes the
    # single-writer lock; BEGIN IMMEDIATE/EXCLUSIVE and DML remain forbidden.
    assert traced_control_statements == ["BEGIN", "COMMIT"]
    assert write_statements == []
    assert sha_after == sha_before
    assert event_count_after == event_count_before
    assert foreign_key_check_after == []
    assert quick_check_after == ["ok"]

    result = {
        "status": "PASS",
        "database": str(database_path),
        "warehouse": str(warehouse),
        "migrations_applied": len(applied_migrations),
        "last_migration": applied_migrations[-1],
        "students": sorted(student_ids),
        "course_catalog_entries": 82,
        "course_units": 394,
        "course_cohorts": 82,
        "course_jobs": 246,
        "byox_catalog_entries": 359,
        "s2_builders": 359,
        "s2_reviewers": 359,
        "s2_graphs": 359,
        "baselines": baseline_count,
        "bindings": len(binding_ids),
        "verified_bindings": sum(value is not None for value in verified),
        "binding_roles": binding_roles,
        "total_jobs": len(rows),
        "created_jobs": first["created_jobs"],
        "model": "gpt-5.6-sol",
        "reasoning_effort": "ultra",
        "model_policy_jobs_verified": len(rows),
        "event_count_before_repeat": event_count_before,
        "event_count_after_repeat": event_count_after,
        "db_sha256_before_repeat": sha_before,
        "db_sha256_after_repeat": sha_after,
        "repeat_created_jobs": repeated["created_jobs"],
        "repeat_managed_writer_api_calls": managed_writer_api_calls,
        "repeat_control_statements": traced_control_statements,
        "repeat_write_statements": write_statements,
        "foreign_key_check": foreign_key_check_after,
        "quick_check": quick_check_after,
        "execution_started": first["execution_started"],
    }
    report_path = output / "result.json"
    report_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
