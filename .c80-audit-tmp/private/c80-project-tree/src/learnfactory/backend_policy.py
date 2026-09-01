from __future__ import annotations

import hashlib
import re
from typing import Any, Mapping

from .config import FactorySettings
from .jobs import ClaimedJob


MASS_SEED_BACKEND_REQUIREMENT = {
    "name": "exec",
    "permission_profile": "factory-isolated",
}
MASS_SEED_EXECUTION_POLICY = {
    "backend": "exec",
    "permission_profile": "factory-isolated",
    "model": "gpt-5.6-sol",
    "reasoning_effort": "ultra",
}
MASS_SEED_ROUTE_REQUIREMENT = {
    "provider": "arm",
    "base_url": "https://openai-api-proxy.geo.arm.com/api/providers/openai/v1",
    "requires_openai_auth": True,
    "supports_websockets": False,
}
_LEGACY_BYOX_EXECUTION_POLICY = {
    "model": "gpt-5.6-sol",
    "reasoning_effort": "ultra",
}

_MASS_SEED_POLICY_KINDS = frozenset(
    {
        "codex_backend_gate",
        "csdiy_course_cohort",
        "csdiy_course_kickoff_revision",
        "csdiy_course_progression",
        "byox_reference_build",
        "byox_reference_repair",
        "byox_reference_review",
    }
)
_MASS_SEED_ARTIFACT_TYPES = frozenset(
    {
        "backend-capability-gate",
        "course-preparation",
        "student-course-attempt",
        "independent-course-evaluation",
        "course-unit-materialization",
        "student-course-unit-attempt",
        "independent-course-unit-evaluation",
        "byox-challenge-pack",
        "byox-remediated-challenge-pack",
        "byox-independent-review",
    }
)
_BYOX_BUILD_JOB_ID = re.compile(
    r"^job_byox_build_v[1-9][0-9]*_[0-9a-f]{32}$"
)
_BYOX_REPAIR_JOB_ID = re.compile(
    r"^job_byox_repair_v[1-9][0-9]*_g[1-9][0-9]*_[0-9a-f]{32}$"
)
_BYOX_REPAIR_REVIEW_JOB_ID = re.compile(
    r"^job_byox_repair_review_v[1-9][0-9]*_g[1-9][0-9]*_[0-9a-f]{32}$"
)
_KICKOFF_REVISION_JOB_ID = re.compile(
    r"^job_csdiy_kickoff_rev_v1_([0-9a-f]{24})_(student_target|examiner)$"
)
_MASS_SEED_JOB_IDS = (
    re.compile(r"^job_codex_backend_gate_v[1-9][0-9]*$"),
    _BYOX_BUILD_JOB_ID,
    re.compile(r"^job_byox_review_v[1-9][0-9]*_[0-9a-f]{32}$"),
    _BYOX_REPAIR_JOB_ID,
    _BYOX_REPAIR_REVIEW_JOB_ID,
    re.compile(
        r"^job_csdiy_.+_(?:prepare|student_target|examiner)_v[1-9][0-9]*$"
    ),
    re.compile(
        r"^job_csdiy_progress_v[1-9][0-9]*_[0-9a-f]{24}"
        r"(?:_contract_v[1-9][0-9]*)?_(?:materialize|student_target|examiner)$"
    ),
    re.compile(
        r"^job_csdiy_revision_v[1-9][0-9]*_[0-9a-f]{24}"
        r"_(?:student_target|examiner)$"
    ),
    _KICKOFF_REVISION_JOB_ID,
)


class MassSeedBackendPolicyError(ValueError):
    """A mass-seeded Codex job or its effective runtime violates the floor."""


def with_mass_seed_backend_policy(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return a new payload carrying the exact current backend requirement.

    Seeders use this only when creating a new job. Existing queued payloads are
    deliberately left byte-for-byte unchanged and receive the same protection
    from :func:`mass_seed_backend_policy_violation` at execution time.
    """

    required = payload.get("required_backend")
    if required is not None and required != MASS_SEED_BACKEND_REQUIREMENT:
        raise MassSeedBackendPolicyError("conflicting required_backend declaration")
    execution = payload.get("execution_policy")
    if execution is not None:
        if not isinstance(execution, dict):
            raise MassSeedBackendPolicyError("execution_policy must be an object")
        for key, expected in MASS_SEED_EXECUTION_POLICY.items():
            if key in execution and execution[key] != expected:
                raise MassSeedBackendPolicyError(
                    f"conflicting execution_policy field: {key}"
                )
    result = dict(payload)
    result["required_backend"] = dict(MASS_SEED_BACKEND_REQUIREMENT)
    result["execution_policy"] = dict(MASS_SEED_EXECUTION_POLICY)
    return result


def mass_seed_payloads_equivalent(
    first: Mapping[str, Any], second: Mapping[str, Any]
) -> bool:
    """Compare seed contracts while tolerating only the legacy policy omission.

    This is intentionally symmetric so a fresh explicitly fenced progression
    job remains idempotent against its policy-neutral deterministic spec, while
    an older queued payload can remain unchanged. Partial, conflicting, or
    malformed declarations are never normalized away.
    """

    def normalized(value: Mapping[str, Any]) -> dict[str, Any] | None:
        result = dict(value)
        has_required = "required_backend" in result
        has_execution = "execution_policy" in result
        if not has_required and not has_execution:
            return result
        if (
            result.get("required_backend") != MASS_SEED_BACKEND_REQUIREMENT
            or result.get("execution_policy") != MASS_SEED_EXECUTION_POLICY
        ):
            return None
        result.pop("required_backend")
        result.pop("execution_policy")
        return result

    normalized_first = normalized(first)
    normalized_second = normalized(second)
    return bool(
        normalized_first is not None
        and normalized_second is not None
        and normalized_first == normalized_second
    )


def is_exact_legacy_byox_partial_policy(
    *,
    job_id: object,
    job_type: object,
    worker_type: object,
    payload: Mapping[str, Any],
) -> bool:
    """Recognize the one immutable pre-required_backend BYOX builder shape."""

    project_id = payload.get("project_id")
    if not isinstance(project_id, str) or not project_id:
        return False
    expected_digest = hashlib.sha256(f"1\0{project_id}".encode("utf-8")).hexdigest()[
        :32
    ]
    return bool(
        job_type == "codex_task"
        and worker_type == "reference_builder"
        and job_id == f"job_byox_build_v1_{expected_digest}"
        and _BYOX_BUILD_JOB_ID.fullmatch(str(job_id))
        and payload.get("seed_policy")
        == {"kind": "byox_reference_build", "version": 1, "role": "builder"}
        and payload.get("artifact_type") == "byox-challenge-pack"
        and "required_backend" not in payload
        and payload.get("execution_policy") == _LEGACY_BYOX_EXECUTION_POLICY
    )


def _is_exact_legacy_kickoff_partial_policy(job: ClaimedJob) -> bool:
    """Recognize the exact kickoff-revision shape deployed before full policy."""

    match = _KICKOFF_REVISION_JOB_ID.fullmatch(job.job_id)
    if match is None:
        return False
    digest, suffix = match.groups()
    revision_id = job.payload.get("revision_id")
    if revision_id != f"csdiy-kickoff-revision-v1-{digest}":
        return False
    policy = job.payload.get("seed_policy")
    if not isinstance(policy, dict) or set(policy) != {
        "kind",
        "version",
        "attempt_number",
        "role",
    }:
        return False
    attempt_number = policy.get("attempt_number")
    if (
        isinstance(attempt_number, bool)
        or not isinstance(attempt_number, int)
        or attempt_number < 2
    ):
        return False
    role = policy.get("role")
    expected_role = "student_revision" if suffix == "student_target" else "examiner_revision"
    expected_worker = "student" if suffix == "student_target" else "examiner"
    expected_artifact = (
        "student-course-attempt"
        if suffix == "student_target"
        else "independent-course-evaluation"
    )
    return bool(
        policy.get("kind") == "csdiy_course_kickoff_revision"
        and policy.get("version") == 1
        and role == expected_role
        and job.worker_type == expected_worker
        and job.payload.get("artifact_type") == expected_artifact
        and job.payload.get("required_backend")
        == MASS_SEED_BACKEND_REQUIREMENT
        and "execution_policy" not in job.payload
    )


def is_mass_seeded_codex_job(job: ClaimedJob) -> bool:
    """Recognize the protected graph through independent durable markers.

    Job ID and artifact type intentionally backstop ``seed_policy.kind`` so
    deleting or changing just that mutable JSON field cannot bypass the floor.
    """

    if job.type != "codex_task":
        return False
    policy = job.payload.get("seed_policy")
    kind = policy.get("kind") if isinstance(policy, dict) else None
    artifact_type = job.payload.get("artifact_type")
    return bool(
        (isinstance(kind, str) and kind in _MASS_SEED_POLICY_KINDS)
        or (
            isinstance(artifact_type, str)
            and artifact_type in _MASS_SEED_ARTIFACT_TYPES
        )
        or any(pattern.fullmatch(job.job_id) for pattern in _MASS_SEED_JOB_IDS)
    )


def mass_seed_backend_policy_violation(
    job: ClaimedJob, settings: FactorySettings
) -> str | None:
    """Return a generic violation reason, or ``None`` for an exact runtime.

    Legacy payloads may omit the two policy objects. If present, declarations
    must not conflict with the authoritative floor. The transport route is
    checked against effective controller settings, while model and reasoning
    are checked on the durable job columns. Those exact values are passed to
    ``codex exec`` and must never fall back to ambient configuration.
    """

    if not is_mass_seeded_codex_job(job):
        return None
    if settings.backend.name != MASS_SEED_BACKEND_REQUIREMENT["name"]:
        return "backend"
    if (
        settings.backend.permission_profile
        != MASS_SEED_BACKEND_REQUIREMENT["permission_profile"]
    ):
        return "permission_profile"
    if settings.backend.provider != MASS_SEED_ROUTE_REQUIREMENT["provider"]:
        return "provider"
    if settings.backend.base_url != MASS_SEED_ROUTE_REQUIREMENT["base_url"]:
        return "base_url"
    if settings.backend.requires_openai_auth is not True:
        return "requires_openai_auth"
    if settings.backend.supports_websockets is not False:
        return "supports_websockets"
    if job.model != MASS_SEED_EXECUTION_POLICY["model"]:
        return "model"
    if job.reasoning_effort != MASS_SEED_EXECUTION_POLICY["reasoning_effort"]:
        return "reasoning_effort"

    has_required = "required_backend" in job.payload
    has_execution = "execution_policy" in job.payload
    required = job.payload.get("required_backend")
    execution = job.payload.get("execution_policy")
    if not has_required and not has_execution:
        return None
    if (
        required == MASS_SEED_BACKEND_REQUIREMENT
        and execution == MASS_SEED_EXECUTION_POLICY
    ):
        return None
    # Historical generic BYOX builders declared only quality settings before
    # required_backend existed. The exact two-field shape is immutable legacy,
    # not a generally accepted partial policy.
    if (
        is_exact_legacy_byox_partial_policy(
            job_id=job.job_id,
            job_type=job.type,
            worker_type=job.worker_type,
            payload=job.payload,
        )
    ):
        return None
    # Kickoff revisions were already independently fenced before the unified
    # policy gained execution_policy. Preserve only that exact historical form.
    if (
        _is_exact_legacy_kickoff_partial_policy(job)
    ):
        return None
    if required != MASS_SEED_BACKEND_REQUIREMENT:
        return "required_backend"
    if execution != MASS_SEED_EXECUTION_POLICY:
        return "execution_policy"
    return None
