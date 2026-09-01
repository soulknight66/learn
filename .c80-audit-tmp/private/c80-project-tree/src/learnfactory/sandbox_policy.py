from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .result_channel import (
    RESULT_CHANNEL_DIRECTORY,
    RESULT_CHANNEL_FILENAME,
    RESULT_TRANSPORT_DIRECTORY,
    lexical_absolute,
    result_alias_directory,
    result_channel_contract,
)
from .workspace import WorkspaceError, safe_relative


_OUTPUT_PATHS: dict[str, tuple[str, ...]] = {
    "byox-independent-review": ("EVALUATION.json", "REVIEW.md", "VALIDATION.md"),
    "independent-course-evaluation": ("evaluation.json", "feedback.md"),
    "independent-course-unit-evaluation": ("evaluation.json", "feedback.md"),
    "student-course-attempt": ("notes.md", "submission.md", "debugging-log.md"),
    "student-course-unit-attempt": ("student_work",),
    "course-unit-materialization": (
        "BATCH_MANIFEST.json",
        "student_safe",
        "examiner_only",
    ),
}

_CSDIY_EXAMINER_ROLES = frozenset(
    {
        ("csdiy_course_cohort", "examiner"),
        ("csdiy_course_kickoff_revision", "examiner_revision"),
        ("csdiy_course_progression", "examiner"),
        ("csdiy_course_progression", "examiner_revision"),
    }
)

def is_csdiy_examiner(worker_type: str, payload: dict[str, Any]) -> bool:
    policy = payload.get("seed_policy")
    return bool(
        worker_type == "examiner"
        and isinstance(policy, dict)
        and (policy.get("kind"), policy.get("role")) in _CSDIY_EXAMINER_ROLES
    )


def csdiy_examiner_channel_schema(evaluation_schema: object) -> dict[str, Any]:
    if not isinstance(evaluation_schema, dict):
        raise WorkspaceError("CSDIY examiner output schema must be an object")
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "evaluation": evaluation_schema,
            "feedback": {"type": "string", "minLength": 1, "maxLength": 262_144},
        },
        "required": ["evaluation", "feedback"],
    }


def is_examiner_prompt_context_input(
    worker_type: str, payload: dict[str, Any], item: dict[str, Any]
) -> bool:
    """Return whether a verified dependency is model context, never a mount.

    The destination fallback protects already-queued CSDIY jobs whose immutable
    payload predates the explicit ``prompt_context`` bit.
    """

    prompt_context = item.get("prompt_context", False)
    if not isinstance(prompt_context, bool):
        raise WorkspaceError("dependency prompt_context must be boolean")
    if prompt_context and not is_csdiy_examiner(worker_type, payload):
        raise WorkspaceError("prompt_context is restricted to CSDIY examiner jobs")
    if not is_csdiy_examiner(worker_type, payload):
        return False
    # A CSDIY examiner is a no-tool model context.  No candidate, rubric,
    # manifest, prior evaluation, or other dependency is mounted in its
    # workspace.  Every verified dependency is converted to a bounded textual
    # projection by the controller before the Codex process starts.  The
    # destination check below still validates legacy payloads rather than
    # silently accepting an empty/escaping label.
    destination = safe_relative(str(item.get("destination", "")))
    return bool(destination.parts)


@dataclass(frozen=True)
class SandboxPathRule:
    path: str
    access: str
    kind: str

    def as_dict(self) -> dict[str, str]:
        return {"path": self.path, "access": self.access, "kind": self.kind}


@dataclass(frozen=True)
class SandboxRuleManifest:
    """Canonical filesystem policy consumed by provenance and execution."""

    schema_version: int
    workspace: str
    workspace_access: str
    staged_inputs: tuple[str, ...]
    declared_outputs: tuple[str, ...]
    rules: tuple[SandboxPathRule, ...]
    result_channel: str
    result_alias_directory: str
    tools_enabled: bool

    def as_dict(self) -> dict[str, Any]:
        # The concrete randomized channel is an ephemeral controller capability,
        # not provenance. Persisting it (or a hash derived from it) would leak a
        # live capability and make otherwise identical invocation records vary.
        body = {
            "schema_version": self.schema_version,
            "workspace": self.workspace,
            "workspace_access": self.workspace_access,
            "staged_inputs": list(self.staged_inputs),
            "declared_outputs": list(self.declared_outputs),
            "rules": [rule.as_dict() for rule in self.rules],
            "result_channel": result_channel_contract(),
            "tools_enabled": self.tools_enabled,
        }
        return {
            **body,
            "sha256": hashlib.sha256(
                json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest(),
        }

    @property
    def writable_rules(self) -> tuple[SandboxPathRule, ...]:
        return tuple(rule for rule in self.rules if rule.access == "write")


def build_sandbox_rule_manifest(
    *,
    workspace: Path,
    log_dir: Path,
    worker_type: str,
    payload: dict[str, Any],
    result_channel: Path,
) -> SandboxRuleManifest:
    """Derive one deterministic, absolute, fail-closed job filesystem policy."""

    workspace = lexical_absolute(workspace)
    log_dir = lexical_absolute(log_dir)
    result_channel = lexical_absolute(result_channel)
    transport_root = result_channel.parent.parent
    alias_directory = result_alias_directory(log_dir)
    if (
        not RESULT_CHANNEL_DIRECTORY.fullmatch(result_channel.parent.name)
        or result_channel.name != RESULT_CHANNEL_FILENAME
    ):
        raise WorkspaceError("result channel does not match the private channel contract")
    if transport_root.parts.count(RESULT_TRANSPORT_DIRECTORY) != 1:
        raise WorkspaceError("result channel is outside the controller transport namespace")
    if transport_root.name == RESULT_TRANSPORT_DIRECTORY:
        raise WorkspaceError("result channel has no attempt-scoped transport root")
    if _overlaps(transport_root, log_dir):
        raise WorkspaceError("result transport root must be separate from the job log directory")
    if _overlaps(transport_root, workspace):
        raise WorkspaceError("result transport root overlaps the worker workspace")
    if _overlaps(transport_root, alias_directory):
        raise WorkspaceError("result transport root overlaps the fixed launch namespace")

    csdiy_examiner = is_csdiy_examiner(worker_type, payload)
    staged: list[Path] = []
    for raw in payload.get("inputs", []):
        if not isinstance(raw, dict):
            raise WorkspaceError("declared input must be an object")
        destination = safe_relative(str(raw.get("destination", "")))
        if not csdiy_examiner:
            staged.append(destination)
    for raw in payload.get("inputs_from_dependencies", []):
        if not isinstance(raw, dict):
            raise WorkspaceError("dependency input must be an object")
        if is_examiner_prompt_context_input(worker_type, payload, raw):
            continue
        staged.append(safe_relative(str(raw.get("destination", ""))))
    _reject_overlaps(staged, "staged input")

    writable = [] if csdiy_examiner else _declared_writable_paths(payload, staged)
    _reject_overlaps(writable, "writable output")
    for output in writable:
        if any(_overlaps(output, item) for item in staged):
            raise WorkspaceError(
                "writable output overlaps staged input: "
                f"{output.as_posix()}"
            )

    # Examiner results never exist during model execution and CSDIY examiners
    # receive no mounts at all. Other roles retain a writable fresh workspace,
    # while each staged input is over-mounted read-only by a more-specific rule.
    workspace_access = "deny" if csdiy_examiner else "write"
    rules: list[SandboxPathRule] = []
    seen: set[tuple[str, str]] = set()

    def add(relative: Path, access: str, kind: str) -> None:
        absolute = str(workspace / relative) if relative.parts else str(workspace)
        key = (absolute, access)
        if key not in seen:
            rules.append(SandboxPathRule(absolute, access, kind))
            seen.add(key)

    # Explicitly enumerate every ancestor. This is deliberately redundant with
    # workspace_access so audit/provenance can prove the exact destination set.
    for item in sorted(staged, key=lambda value: value.as_posix()):
        add(Path(), "read", "staged-input-ancestor")
        current = Path()
        for part in item.parts:
            current /= part
            add(
                current,
                "read",
                "staged-input" if current == item else "staged-input-ancestor",
            )
    return SandboxRuleManifest(
        schema_version=1,
        workspace=str(workspace),
        workspace_access=workspace_access,
        staged_inputs=tuple(item.as_posix() for item in sorted(staged, key=str)),
        declared_outputs=tuple(
            item.as_posix() for item in sorted(writable, key=str)
        ),
        rules=tuple(rules),
        result_channel=str(result_channel),
        result_alias_directory=str(alias_directory),
        tools_enabled=not csdiy_examiner,
    )


def _declared_writable_paths(
    payload: dict[str, Any], staged: list[Path]
) -> list[Path]:
    explicit = payload.get("sandbox_writable_paths")
    if explicit is not None:
        if not isinstance(explicit, list) or not all(
            isinstance(value, str) for value in explicit
        ):
            raise WorkspaceError("sandbox_writable_paths must be a list of paths")
        return [safe_relative(value) for value in explicit]

    artifact_type = str(payload.get("artifact_type", ""))
    values = list(_OUTPUT_PATHS.get(artifact_type, ()))
    if (
        artifact_type == "student-course-attempt"
        and payload.get("student_submission_format") == "student-work-tree-v1"
    ):
        values = ["student_work"]
    if values:
        return [safe_relative(value) for value in values]

    # Compatibility for bounded jobs with staged inputs that already declare
    # their outputs through deterministic validators.
    input_roots = {item.parts[0] for item in staged if item.parts}
    candidates: list[Path] = []
    for validator in payload.get("validators", []):
        if not isinstance(validator, dict) or validator.get("type") in {
            "forbidden_paths",
            "forbidden_tree_names",
            "input_integrity",
            "handler_evidence",
        }:
            continue
        raw_paths: Iterable[object]
        if isinstance(validator.get("paths"), list):
            raw_paths = validator["paths"]
        elif "path" in validator:
            raw_paths = (validator["path"],)
        else:
            continue
        for raw in raw_paths:
            candidate = safe_relative(str(raw))
            if candidate.parts and candidate.parts[0] not in input_roots:
                candidates.append(candidate)
    unique: list[Path] = []
    for candidate in candidates:
        if candidate not in unique:
            unique.append(candidate)
    return unique


def _overlaps(left: Path, right: Path) -> bool:
    return left == right or left in right.parents or right in left.parents


def _reject_overlaps(paths: list[Path], label: str) -> None:
    for index, left in enumerate(paths):
        for right in paths[index + 1 :]:
            if _overlaps(left, right):
                raise WorkspaceError(
                    f"overlapping {label} paths: {left.as_posix()} and {right.as_posix()}"
                )
