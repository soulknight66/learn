from __future__ import annotations

import copy
from dataclasses import dataclass
from types import MappingProxyType
from typing import Iterable, Mapping

from .byox_jobs import ByoxProjectSnapshot
from .scoring import priority_score


CATALOG_SYNTHESIS_JOB_ID = "job_catalog_synthesis_v1"
KVSTORE_JOB_ID = "job_project_kvstore_vertical"
KVSTORE_REVISION_JOB_ID = "job_project_kvstore_vertical_v2"
HTTP_SERVICE_JOB_ID = "job_project_http_service_vertical_v1"
ALLOCATOR_JOB_ID = "job_project_allocator_vertical_v1"
BYTECODE_JOB_ID = "job_project_bytecode_vertical_v1"
ALLOCATOR_PROJECT_ID = "project_62500cd7d143a95230c724df71a56c4a"
BYTECODE_PROJECT_ID = "project_4b7f4b85b17b06eeba75d235767a898f"

SPECIALIZED_BYOX_JOB_IDS = (
    KVSTORE_JOB_ID,
    KVSTORE_REVISION_JOB_ID,
    HTTP_SERVICE_JOB_ID,
    ALLOCATOR_JOB_ID,
    BYTECODE_JOB_ID,
)
SPECIALIZED_ARTIFACT_TYPE_BY_JOB_TYPE: Mapping[str, str] = MappingProxyType(
    {
        "project_vertical_slice": "project_challenge_pack",
        "bytecode_vertical_slice": "bytecode_vm_challenge_pack",
        "allocator_vertical_slice": "allocator_challenge_pack",
        "http_service_vertical_slice": "http_service_challenge_pack",
    }
)


@dataclass(frozen=True)
class SpecializedByoxJobSpec:
    """Complete controller definition of one released slice builder."""

    job_id: str
    job_type: str
    worker_type: str
    artifact_type: str
    semantic_path: str
    project_id: str
    payload: dict[str, object]
    priority: float
    score_components: dict[str, float]
    max_attempts: int
    model: str | None
    reasoning_effort: str | None
    dependencies: tuple[str, ...]


_KVSTORE_FEATURES = MappingProxyType(
    {
        "expected_future_learning_value": 10,
        "future_regeneration_cost": 9,
        "production_relevance": 9,
        "systems_depth": 8,
        "curriculum_importance": 9,
        "source_availability": 9,
        "prerequisite_value": 9,
        "artifact_uniqueness": 8,
        "agent_compute_cost": 5,
    }
)
_HTTP_SERVICE_FEATURES = MappingProxyType(
    {
        "expected_future_learning_value": 10,
        "future_regeneration_cost": 10,
        "production_relevance": 10,
        "systems_depth": 8,
        "curriculum_importance": 8,
        "source_availability": 9,
        "prerequisite_value": 9,
        "artifact_uniqueness": 9,
        "agent_compute_cost": 5,
    }
)
_ALLOCATOR_FEATURES = MappingProxyType(
    {
        "expected_future_learning_value": 10,
        "future_regeneration_cost": 10,
        "production_relevance": 9,
        "systems_depth": 10,
        "curriculum_importance": 9,
        "source_availability": 8,
        "prerequisite_value": 9,
        "artifact_uniqueness": 9,
        "agent_compute_cost": 5,
    }
)
_BYTECODE_FEATURES = MappingProxyType(
    {
        "expected_future_learning_value": 10,
        "future_regeneration_cost": 10,
        "production_relevance": 8,
        "systems_depth": 9,
        "curriculum_importance": 9,
        "source_availability": 9,
        "prerequisite_value": 9,
        "artifact_uniqueness": 9,
        "agent_compute_cost": 4,
    }
)
_SQLITE_ASCII_LOWER = str.maketrans(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
    "abcdefghijklmnopqrstuvwxyz",
)


def build_specialized_byox_job_specs(
    projects: Iterable[ByoxProjectSnapshot],
) -> tuple[SpecializedByoxJobSpec, ...]:
    """Derive every released specialized builder from normalized active snapshots.

    The returned objects are fresh values. Callers may therefore pass their payloads
    to persistence code without making a historical database row the template for a
    later job revision. Inputs must be values emitted by the strict catalog loader;
    duplicate identities are rejected rather than resolved by iteration order.
    """

    normalized = tuple(projects)
    if any(type(project) is not ByoxProjectSnapshot for project in normalized):
        raise TypeError("specialized BYOX specs require normalized project snapshots")
    by_id = {project.project_id: project for project in normalized}
    if len(by_id) != len(normalized):
        raise ValueError("specialized BYOX snapshots contain duplicate project IDs")
    specs: list[SpecializedByoxJobSpec] = []

    database = _select_database_project(by_id.values())
    if database is not None:
        features = dict(_KVSTORE_FEATURES)
        payload: dict[str, object] = {
            "project_id": database.project_id,
            "title": "Durable Key-Value Store",
            "category": database.category,
            "upstream_reference": database.upstream_reference,
            "source_title": database.title,
            "provenance": {
                "source": database.source_name,
                "source_id": database.source_id,
                "commit": database.source_commit_hash,
                "catalog_entry": database.upstream_reference,
                "catalog_license": database.source_license,
                "linked_tutorial_license": "NOASSERTION",
                "classification": (
                    "independently agent-generated; not copied from linked tutorial"
                ),
            },
            "validation_status": "TESTED",
        }
        specs.append(
            SpecializedByoxJobSpec(
                job_id=KVSTORE_JOB_ID,
                job_type="project_vertical_slice",
                worker_type="reference_builder",
                artifact_type="project_challenge_pack",
                semantic_path="projects/database/durable-bytes-kv",
                project_id=database.project_id,
                payload=payload,
                priority=priority_score(features),
                score_components=features,
                max_attempts=3,
                model=None,
                reasoning_effort=None,
                dependencies=(),
            )
        )
        revision_payload = copy.deepcopy(payload)
        revision_payload["revision"] = {
            "version": 2,
            "basis": "meta-evaluation-001",
            "changes": [
                "short-write handling",
                "exception-safe compaction",
                "negative-path validation",
                "calibrated PARTIAL label",
            ],
        }
        specs.append(
            SpecializedByoxJobSpec(
                job_id=KVSTORE_REVISION_JOB_ID,
                job_type="project_vertical_slice",
                worker_type="reference_builder",
                artifact_type="project_challenge_pack",
                semantic_path="projects/database/durable-bytes-kv",
                project_id=database.project_id,
                payload=revision_payload,
                priority=priority_score(features) + 1,
                score_components=dict(features),
                max_attempts=3,
                model=None,
                reasoning_effort=None,
                dependencies=(KVSTORE_JOB_ID,),
            )
        )

    web_server = _select_web_server_project(by_id.values())
    if web_server is not None:
        features = dict(_HTTP_SERVICE_FEATURES)
        specs.append(
            SpecializedByoxJobSpec(
                job_id=HTTP_SERVICE_JOB_ID,
                job_type="http_service_vertical_slice",
                worker_type="reference_builder",
                artifact_type="http_service_challenge_pack",
                semantic_path="projects/networking/bounded-http-counter-service",
                project_id=web_server.project_id,
                payload={
                    "job_id": HTTP_SERVICE_JOB_ID,
                    "project_id": web_server.project_id,
                    "source_id": web_server.source_id,
                    "title": "Bounded HTTP/1.1 Counter Service",
                    "category": web_server.category,
                    "upstream_reference": web_server.upstream_reference,
                    "source_title": web_server.title,
                    "provenance": {
                        "source": web_server.source_name,
                        "source_id": web_server.source_id,
                        "commit": web_server.source_commit_hash,
                        "upstream": web_server.source_upstream_url,
                        "catalog_entry": web_server.upstream_reference,
                        "catalog_license": web_server.source_license,
                        "linked_tutorial_license": "NOASSERTION",
                        "classification": (
                            "independently agent-generated challenge pack; "
                            "linked tutorial is provenance only"
                        ),
                    },
                    "validation_status": "GENERATED_CANDIDATE",
                },
                priority=priority_score(features),
                score_components=features,
                max_attempts=2,
                model=None,
                reasoning_effort=None,
                dependencies=(CATALOG_SYNTHESIS_JOB_ID,),
            )
        )

    allocator = by_id.get(ALLOCATOR_PROJECT_ID)
    if allocator is not None:
        specs.append(
            _fixed_project_spec(
                project=allocator,
                job_id=ALLOCATOR_JOB_ID,
                job_type="allocator_vertical_slice",
                artifact_type="allocator_challenge_pack",
                score_components=dict(_ALLOCATOR_FEATURES),
            )
        )
    bytecode = by_id.get(BYTECODE_PROJECT_ID)
    if bytecode is not None:
        specs.append(
            _fixed_project_spec(
                project=bytecode,
                job_id=BYTECODE_JOB_ID,
                job_type="bytecode_vertical_slice",
                artifact_type="bytecode_vm_challenge_pack",
                score_components=dict(_BYTECODE_FEATURES),
            )
        )
    return tuple(specs)


def specialized_byox_job_specs_by_id(
    projects: Iterable[ByoxProjectSnapshot],
) -> dict[str, SpecializedByoxJobSpec]:
    """Return canonical specialized specs indexed by their stable job IDs."""

    return {spec.job_id: spec for spec in build_specialized_byox_job_specs(projects)}


def specialized_reviewer_payload(spec: SpecializedByoxJobSpec) -> dict[str, object]:
    """Return the transient artifact-typed payload released to review jobs.

    Specialized builder rows predate top-level ``artifact_type`` declarations.
    Review seeding added the independently verified artifact type without changing
    the historical builder row. Keep those two exact representations distinct.
    """

    payload = copy.deepcopy(spec.payload)
    payload["artifact_type"] = spec.artifact_type
    return payload


def _fixed_project_spec(
    *,
    project: ByoxProjectSnapshot,
    job_id: str,
    job_type: str,
    artifact_type: str,
    score_components: dict[str, float],
) -> SpecializedByoxJobSpec:
    return SpecializedByoxJobSpec(
        job_id=job_id,
        job_type=job_type,
        worker_type="reference_builder",
        artifact_type=artifact_type,
        semantic_path=(
            "projects/systems/caller-owned-arena-c-allocator"
            if job_id == ALLOCATOR_JOB_ID
            else "projects/languages/sprig-bytecode-vm"
        ),
        project_id=project.project_id,
        payload={
            "job_id": job_id,
            "project_id": project.project_id,
            "source_id": project.source_id,
            "provenance": _project_provenance(project),
            "validation_status": "GENERATED_CANDIDATE",
        },
        priority=priority_score(score_components),
        score_components=score_components,
        max_attempts=2,
        model=None,
        reasoning_effort=None,
        dependencies=(CATALOG_SYNTHESIS_JOB_ID,),
    )


def _project_provenance(project: ByoxProjectSnapshot) -> dict[str, object]:
    return {
        "source": project.source_name,
        "source_id": project.source_id,
        "commit": project.source_commit_hash,
        "upstream": project.source_upstream_url,
        "catalog_entry": project.upstream_reference,
        "catalog_license": project.source_license,
        "linked_tutorial_license": "NOASSERTION",
        "classification": (
            "independently agent-generated; catalog entry is provenance only"
        ),
    }


def _select_database_project(
    projects: Iterable[ByoxProjectSnapshot],
) -> ByoxProjectSnapshot | None:
    candidates = [
        project
        for project in projects
        if _sqlite_ascii_lower(project.category) == "database"
    ]
    if not candidates:
        return None
    return min(
        candidates,
        key=lambda project: (
            0
            if "dbdb" in _sqlite_ascii_lower(project.upstream_reference)
            else 1
            if "python"
            in _sqlite_ascii_lower(project.implementation_language or "")
            else 2,
            project.priority_tier,
            -(
                project.production_relevance
                if project.production_relevance is not None
                else float("-inf")
            ),
            project.project_id,
        ),
    )


def _select_web_server_project(
    projects: Iterable[ByoxProjectSnapshot],
) -> ByoxProjectSnapshot | None:
    candidates = [
        project
        for project in projects
        if _sqlite_ascii_lower(project.category) == "web server"
    ]
    if not candidates:
        return None
    return min(
        candidates,
        key=lambda project: (
            0
            if _sqlite_ascii_lower(project.title) == "a simple web server"
            else 1,
            0
            if _sqlite_ascii_lower(project.implementation_language or "")
            == "python"
            else 1,
            project.priority_tier,
            -(
                project.production_relevance
                if project.production_relevance is not None
                else float("-inf")
            ),
            project.project_id,
        ),
    )


def _sqlite_ascii_lower(value: str) -> str:
    """Match SQLite's built-in ``lower`` used by the released seed selectors."""

    return value.translate(_SQLITE_ASCII_LOWER)
