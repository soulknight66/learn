from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Mapping

from .strict_json import StrictJsonError, strict_json_loads


DETERMINISTIC_REVIEW_VERDICT_CONTRACT_VERSION = 2
MAX_REVIEW_EVALUATION_BYTES = 1024 * 1024
MAX_REVIEW_DOCUMENT_BYTES = 4 * 1024 * 1024
REVIEW_ARTIFACT_REQUIRED_PATHS = (
    "EVALUATION.json",
    "REVIEW.md",
    "VALIDATION.md",
)
REVIEW_VERDICT_REQUIRED_NONEMPTY_ARRAYS = ("evidence", "checks_run")
REVIEW_VERDICT_TRIMMED_STRING_ARRAYS = (
    "evidence",
    "checks_run",
    "limitations",
)
REVIEW_EVALUATION_FIELDS = frozenset(
    {
        "project_id",
        "builder_job_id",
        "verdict",
        *REVIEW_VERDICT_TRIMMED_STRING_ARRAYS,
    }
)
REVIEW_VERDICTS = frozenset({"PASS", "REVISE", "FAIL"})
REVIEW_VERDICT_CONSTRAINT_FIELDS = frozenset(
    {"allowed_verdicts", "required_evidence_entries"}
)


class ReviewContractError(ValueError):
    """A review document is ambiguous or violates the versioned contract."""


@dataclass(frozen=True)
class ReviewVerdictConstraints:
    allowed_verdicts: tuple[str, ...] | None
    required_evidence_entries: tuple[str, ...]


@dataclass(frozen=True)
class DeterministicReviewEvaluation:
    project_id: str
    builder_job_id: str
    verdict: str
    evidence_entries: tuple[str, ...]
    entry_counts: dict[str, int]
    evaluation_sha256: str

    def validation_evidence(self, *, path: str = "EVALUATION.json") -> dict[str, Any]:
        return {
            "path": path,
            "contract_version": DETERMINISTIC_REVIEW_VERDICT_CONTRACT_VERSION,
            "project_id": self.project_id,
            "builder_job_id": self.builder_job_id,
            "verdict": self.verdict,
            "entry_counts": dict(self.entry_counts),
            "evaluation_sha256": self.evaluation_sha256,
            "reviewer_recommends_acceptance": self.verdict == "PASS",
            "workflow_accepted": False,
        }


def parse_deterministic_review_evaluation(
    raw_evaluation: bytes,
) -> DeterministicReviewEvaluation:
    """Parse exact bytes with no duplicate keys and enforce contract v2."""

    if len(raw_evaluation) > MAX_REVIEW_EVALUATION_BYTES:
        raise ReviewContractError("review evaluation exceeds the contract byte limit")
    try:
        value = strict_json_loads(
            raw_evaluation,
            max_bytes=MAX_REVIEW_EVALUATION_BYTES,
        )
    except StrictJsonError as error:
        raise ReviewContractError(str(error)) from error
    if not isinstance(value, dict):
        raise ReviewContractError("review evaluation root must be an object")
    if set(value) != REVIEW_EVALUATION_FIELDS:
        raise ReviewContractError("review evaluation fields do not match contract v2")

    project_id = value.get("project_id")
    builder_job_id = value.get("builder_job_id")
    if not isinstance(project_id, str) or not project_id:
        raise ReviewContractError("project_id must be a nonempty string")
    if not isinstance(builder_job_id, str) or not builder_job_id:
        raise ReviewContractError("builder_job_id must be a nonempty string")
    verdict = value.get("verdict")
    if not isinstance(verdict, str) or verdict not in REVIEW_VERDICTS:
        raise ReviewContractError("review verdict must be exactly PASS, REVISE, or FAIL")

    entry_counts: dict[str, int] = {}
    errors: list[str] = []
    for field in REVIEW_VERDICT_TRIMMED_STRING_ARRAYS:
        entries = value.get(field)
        if not isinstance(entries, list):
            errors.append(f"{field} must be an array")
            continue
        entry_counts[field] = len(entries)
        if field in REVIEW_VERDICT_REQUIRED_NONEMPTY_ARRAYS and not entries:
            errors.append(f"{field} must be nonempty")
        for index, entry in enumerate(entries):
            if not isinstance(entry, str) or not entry or entry.strip() != entry:
                errors.append(
                    f"{field}[{index}] must be a nonempty exactly-trimmed string"
                )
    if errors:
        raise ReviewContractError("; ".join(errors))
    return DeterministicReviewEvaluation(
        project_id=project_id,
        builder_job_id=builder_job_id,
        verdict=verdict,
        evidence_entries=tuple(value["evidence"]),
        entry_counts=entry_counts,
        evaluation_sha256=hashlib.sha256(raw_evaluation).hexdigest(),
    )


def review_verdict_constraints(
    specification: Mapping[str, Any],
) -> ReviewVerdictConstraints:
    """Parse optional controller-owned review constraints with strict types.

    These constraints narrow a structurally valid contract-v2 review.  They do
    not alter the review document or its canonical validation-evidence shape.
    """

    if not isinstance(specification, Mapping):
        raise ReviewContractError("review verdict specification must be an object")

    missing = object()
    raw_allowed = specification.get("allowed_verdicts", missing)
    allowed: tuple[str, ...] | None
    if raw_allowed is missing:
        allowed = None
    else:
        if (
            not isinstance(raw_allowed, list)
            or not raw_allowed
            or any(
                not isinstance(value, str) or value not in REVIEW_VERDICTS
                for value in raw_allowed
            )
            or len(set(raw_allowed)) != len(raw_allowed)
        ):
            raise ReviewContractError(
                "allowed_verdicts must be a nonempty duplicate-free array of "
                "PASS, REVISE, or FAIL"
            )
        allowed = tuple(raw_allowed)

    raw_required = specification.get("required_evidence_entries", missing)
    if raw_required is missing:
        required: tuple[str, ...] = ()
    else:
        if (
            not isinstance(raw_required, list)
            or not raw_required
            or any(
                not isinstance(value, str)
                or not value
                or value.strip() != value
                for value in raw_required
            )
            or len(set(raw_required)) != len(raw_required)
        ):
            raise ReviewContractError(
                "required_evidence_entries must be a nonempty duplicate-free "
                "array of exactly-trimmed strings"
            )
        required = tuple(raw_required)

    return ReviewVerdictConstraints(
        allowed_verdicts=allowed,
        required_evidence_entries=required,
    )
