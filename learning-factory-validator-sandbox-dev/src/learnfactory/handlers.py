from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import tempfile
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from .backends import BackendResult, ExecBackend, FakeBackend
from .config import FactorySettings
from .db import Database
from .jobs import ClaimedJob
from .util import (
    canonical_json,
    file_sha256,
    redact,
    tree_sha256,
    tree_sha256_for_algorithm,
)
from .workspace import WorkspaceError, WorkspaceManager, contained, safe_relative


_OUTPUT_ONLY_ARCHIVES: dict[str, tuple[str, ...]] = {
    "byox-independent-review": (
        "EVALUATION.json",
        "REVIEW.md",
        "VALIDATION.md",
    ),
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


@dataclass
class HandlerResult:
    evidence: dict[str, Any]
    validators: list[dict[str, Any]]
    artifact_type: str
    semantic_path: str
    metadata: dict[str, Any] = field(default_factory=dict)
    backend_result: BackendResult | None = None
    backend_name: str = "local"
    on_publish: Callable[[sqlite3.Connection], None] | None = None
    on_commit: Callable[[], None] | None = None
    archive_paths: tuple[str, ...] | None = None


class HandlerFailure(RuntimeError):
    def __init__(self, message: str, *, kind: str, retryable: bool):
        super().__init__(message)
        self.kind = kind
        self.retryable = retryable


def _staged_input_record(path: Path, relative: str) -> dict[str, Any]:
    if path.is_symlink():
        raise WorkspaceError(f"staged input may not be a symlink: {relative}")
    if path.is_file():
        return {
            "path": relative,
            "kind": "file",
            "checksum_algorithm": "file-sha256",
            "checksum": file_sha256(path),
        }
    if path.is_dir():
        return {
            "path": relative,
            "kind": "directory",
            "checksum_algorithm": "tree-sha256-v2",
            "checksum": tree_sha256(path),
        }
    raise WorkspaceError(f"staged input is not a regular file or directory: {relative}")


def _copy_dependency_tree(source: Path, destination: Path) -> Path:
    """Single seam for taking the full dependency snapshot used for staging."""

    return shutil.copytree(source, destination, symlinks=True)


def _archive_paths_exclude_staged_inputs(
    archive_paths: tuple[str, ...], staged_inputs: list[dict[str, Any]]
) -> None:
    """Fail closed if an output-only archive would retain a staged input.

    The projection flag is a security/provenance claim, not just a filesystem
    optimization.  A malformed or future payload must not be able to stage an
    input beneath one of the selected output roots and still advertise that all
    staged material was excluded.
    """

    outputs = [safe_relative(value) for value in archive_paths]
    for record in staged_inputs:
        staged = safe_relative(str(record["path"]))
        for output in outputs:
            if (
                output == staged
                or output in staged.parents
                or staged in output.parents
            ):
                raise HandlerFailure(
                    "output-only archive path overlaps staged input: "
                    f"output={output.as_posix()} input={staged.as_posix()}",
                    kind="unsafe_archive_projection",
                    retryable=False,
                )


def _enforce_byox_remediation_backend(
    job: ClaimedJob, settings: FactorySettings
) -> None:
    """Fail before launch if a remediation job lost its hardened execution fence."""

    policy = job.payload.get("seed_policy")
    if not isinstance(policy, dict):
        return
    kind = policy.get("kind")
    generation = job.payload.get("remediation_generation")
    is_repair = kind == "byox_reference_repair"
    is_repair_review = bool(
        kind == "byox_reference_review"
        and isinstance(generation, int)
        and not isinstance(generation, bool)
        and generation >= 1
    )
    if not is_repair and not is_repair_review:
        return
    from .byox_remediation import BYOX_REPAIR_ARTIFACT_TYPE

    expected_artifact_type = (
        BYOX_REPAIR_ARTIFACT_TYPE if is_repair else "byox-independent-review"
    )
    expected_worker_type = "reference_builder" if is_repair else "examiner"
    required = job.payload.get("required_backend")
    if (
        required
        != {"name": "exec", "permission_profile": "factory-isolated"}
        or job.payload.get("execution_policy")
        != {
            "backend": "exec",
            "permission_profile": "factory-isolated",
            "model": "gpt-5.6-sol",
            "reasoning_effort": "ultra",
        }
        or policy.get("role") != ("builder" if is_repair else "reviewer")
        or job.payload.get("artifact_type") != expected_artifact_type
        or job.worker_type != expected_worker_type
        or settings.backend.name != "exec"
        or settings.backend.permission_profile != "factory-isolated"
        or job.model != "gpt-5.6-sol"
        or job.reasoning_effort != "ultra"
    ):
        raise HandlerFailure(
            "BYOX remediation requires exec/factory-isolated with gpt-5.6-sol ultra",
            kind="blocked_backend_configuration",
            retryable=False,
        )


def _enforce_kickoff_revision_backend(
    job: ClaimedJob, settings: FactorySettings
) -> None:
    """Keep learner revisions on the factory's hardened Codex execution path."""

    policy = job.payload.get("seed_policy")
    if not isinstance(policy, dict) or policy.get("kind") != (
        "csdiy_course_kickoff_revision"
    ):
        return
    if (
        job.payload.get("required_backend")
        != {"name": "exec", "permission_profile": "factory-isolated"}
        or settings.backend.name != "exec"
        or settings.backend.permission_profile != "factory-isolated"
        or job.model != "gpt-5.6-sol"
        or job.reasoning_effort != "ultra"
    ):
        raise HandlerFailure(
            "CSDIY kickoff revision requires exec/factory-isolated with gpt-5.6-sol ultra",
            kind="blocked_backend_configuration",
            retryable=False,
        )


def _with_byox_runtime_safety_validators(
    job: ClaimedJob, validators: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Apply the canonical BYOX runtime floor without rewriting job payloads.

    Older queued jobs intentionally retain their immutable validator payloads.
    Reserved validator names are nevertheless authoritative: an exact existing
    specification is accepted, a missing specification is appended for this run,
    and collisions fail closed instead of suppressing or shadowing the floor.
    """

    if job.payload.get("artifact_type") not in {
        "byox-challenge-pack",
        "byox-remediated-challenge-pack",
    }:
        return validators

    from .byox_jobs import byox_runtime_safety_validators

    result = list(validators)
    for authoritative in byox_runtime_safety_validators():
        name = str(authoritative["name"])
        matching = [
            item
            for item in result
            if isinstance(item, dict) and str(item.get("name")) == name
        ]
        if not matching:
            result.append(authoritative)
            continue
        if len(matching) != 1 or matching[0] != authoritative:
            raise HandlerFailure(
                f"BYOX runtime validator contract collision: {name}",
                kind="unsafe_validator_contract",
                retryable=False,
            )
    return result


def _byox_repair_archive_selection(
    job: ClaimedJob,
    workspace: Path,
    staged_inputs: list[dict[str, Any]],
) -> tuple[tuple[str, ...] | None, dict[str, Any] | None]:
    """Declare repair outputs as verified prior roots plus canonical required roots."""

    policy = job.payload.get("seed_policy")
    is_repair_policy = bool(
        isinstance(policy, dict)
        and policy.get("kind") == "byox_reference_repair"
    )
    from .byox_remediation import (
        BYOX_ARTIFACT_PROFILES,
        BYOX_CANONICAL_DIRECTORY_ROOTS,
        BYOX_REPAIR_ARTIFACT_TYPE,
        BYOX_REPAIR_CONTROL_ROOTS,
        BYOX_REPAIR_STAGED_ROOTS,
    )

    is_repair_type = job.payload.get("artifact_type") == BYOX_REPAIR_ARTIFACT_TYPE
    if not is_repair_policy and not is_repair_type:
        return None, None
    if not is_repair_policy or not is_repair_type:
        raise HandlerFailure(
            "BYOX repair policy and artifact type must be declared together",
            kind="unsafe_archive_projection",
            retryable=False,
        )
    if job.payload.get("protected_input_roots") != list(BYOX_REPAIR_STAGED_ROOTS):
        raise HandlerFailure(
            "BYOX repair staged roots do not match the protected-root contract",
            kind="unsafe_archive_projection",
            retryable=False,
        )
    prior_records = [
        item
        for item in staged_inputs
        if item.get("origin") == "dependency-artifact"
        and item.get("path") == "PRIOR_BUILD"
        and item.get("artifact_subpath") == "."
    ]
    if len(prior_records) != 1:
        raise HandlerFailure(
            "BYOX repair requires exactly one full prior-builder artifact input",
            kind="unsafe_archive_projection",
            retryable=False,
        )
    prior = prior_records[0]
    inventory = prior.get("artifact_inventory")
    profile_name = job.payload.get("artifact_profile")
    if (
        prior.get("kind") != "directory"
        or prior.get("checksum_algorithm") != "tree-sha256-v2"
        or prior.get("artifact_checksum_algorithm") != "tree-sha256-v2"
        or not isinstance(prior.get("checksum"), str)
        or not isinstance(prior.get("artifact_checksum"), str)
        or not isinstance(inventory, dict)
        or not isinstance(profile_name, str)
        or inventory.get("profile") != profile_name
        or profile_name not in BYOX_ARTIFACT_PROFILES
    ):
        raise HandlerFailure(
            "BYOX repair full-root input is not the exact verified artifact tree",
            kind="unsafe_archive_projection",
            retryable=False,
        )
    root = workspace / "PRIOR_BUILD"
    if root.is_symlink() or not root.is_dir() or not contained(workspace, root):
        raise HandlerFailure(
            "BYOX repair prior-builder root is missing or unsafe",
            kind="unsafe_archive_projection",
            retryable=False,
        )
    try:
        entries = list(root.iterdir())
    except OSError as error:
        raise HandlerFailure(
            f"cannot enumerate BYOX prior-builder artifact: {error}",
            kind="unsafe_archive_projection",
            retryable=False,
        ) from error
    if not entries:
        raise HandlerFailure(
            "BYOX prior-builder artifact has no output roots",
            kind="unsafe_archive_projection",
            retryable=False,
        )
    control_names = {name.casefold() for name in BYOX_REPAIR_CONTROL_ROOTS}
    staged_root_names = {
        safe_relative(str(item["path"])).parts[0].casefold()
        for item in staged_inputs
    }
    source_paths: list[str] = []
    source_root_kinds: dict[str, str] = {}
    folded: set[str] = set()
    for entry in entries:
        relative = safe_relative(entry.name)
        name = relative.as_posix()
        normalized = name.casefold()
        if len(relative.parts) != 1:
            raise HandlerFailure(
                f"BYOX prior-builder output root is not a single safe name: {name}",
                kind="unsafe_archive_projection",
                retryable=False,
            )
        if (
            normalized in control_names
            or normalized in staged_root_names
            or name.startswith(".archive-projection-")
        ):
            raise HandlerFailure(
                f"BYOX prior-builder artifact contains a control root: {name}",
                kind="unsafe_archive_projection",
                retryable=False,
            )
        if normalized in folded:
            raise HandlerFailure(
                f"BYOX prior-builder artifact has case-colliding roots: {name}",
                kind="unsafe_archive_projection",
                retryable=False,
            )
        folded.add(normalized)
        if entry.is_symlink() or (not entry.is_file() and not entry.is_dir()):
            raise HandlerFailure(
                f"BYOX prior-builder output root is not regular: {name}",
                kind="unsafe_archive_projection",
                retryable=False,
            )
        source_paths.append(name)
        source_root_kinds[name] = "file" if entry.is_file() else "directory"
    source_paths_tuple = tuple(sorted(source_paths))
    inventory_root_kinds = inventory.get("root_kinds")
    selected_inventory_root_kinds = (
        {
            path: inventory_root_kinds.get(path)
            for path in inventory.get("selected_paths", [])
        }
        if isinstance(inventory_root_kinds, dict)
        and isinstance(inventory.get("selected_paths"), list)
        else None
    )
    if (
        inventory.get("selected_paths") != list(source_paths_tuple)
        or selected_inventory_root_kinds
        != dict(sorted(source_root_kinds.items()))
    ):
        raise HandlerFailure(
            "BYOX repair staged inventory differs from its verified root selection",
            kind="unsafe_archive_projection",
            retryable=False,
        )
    required_roots = set(BYOX_ARTIFACT_PROFILES[profile_name]["required_roots"])
    missing = sorted(required_roots - set(source_paths_tuple))
    if missing:
        raise HandlerFailure(
            "BYOX prior-builder artifact lacks canonical roots: " + ", ".join(missing),
            kind="unsafe_archive_projection",
            retryable=False,
        )
    output_required_roots = set(
        BYOX_ARTIFACT_PROFILES[profile_name]["output_required_roots"]
    )
    projected_paths = tuple(sorted(set(source_paths_tuple) | output_required_roots))
    if len({path.casefold() for path in projected_paths}) != len(projected_paths):
        raise HandlerFailure(
            "BYOX repair projected roots collide by case",
            kind="unsafe_archive_projection",
            retryable=False,
        )
    projected_root_kinds = dict(source_root_kinds)
    for path in sorted(output_required_roots):
        expected_kind = (
            "directory" if path in BYOX_CANONICAL_DIRECTORY_ROOTS else "file"
        )
        existing_kind = projected_root_kinds.get(path)
        if existing_kind is not None and existing_kind != expected_kind:
            raise HandlerFailure(
                f"BYOX canonical root has the wrong type: {path}",
                kind="unsafe_archive_projection",
                retryable=False,
            )
        projected_root_kinds[path] = expected_kind
    added_required_paths = sorted(output_required_roots - set(source_paths_tuple))
    added_required_root_kinds = {
        path: projected_root_kinds[path] for path in added_required_paths
    }
    required_added_inventory = {
        "schema_version": 1,
        "paths": added_required_paths,
        "root_kinds": added_required_root_kinds,
        "paths_sha256": hashlib.sha256(
            canonical_json(added_required_paths).encode("utf-8")
        ).hexdigest(),
        "root_kinds_sha256": hashlib.sha256(
            canonical_json(added_required_root_kinds).encode("utf-8")
        ).hexdigest(),
    }
    projected_inventory = {
        "schema_version": 1,
        "profile": profile_name,
        "source_artifact_type": BYOX_REPAIR_ARTIFACT_TYPE,
        "original_paths": list(projected_paths),
        "selected_paths": list(projected_paths),
        "excluded_paths": [],
        "root_kinds": dict(sorted(projected_root_kinds.items())),
        "original_paths_sha256": hashlib.sha256(
            canonical_json(list(projected_paths)).encode("utf-8")
        ).hexdigest(),
        "selected_paths_sha256": hashlib.sha256(
            canonical_json(list(projected_paths)).encode("utf-8")
        ).hexdigest(),
        "excluded_paths_sha256": hashlib.sha256(
            canonical_json([]).encode("utf-8")
        ).hexdigest(),
        "root_kinds_sha256": hashlib.sha256(
            canonical_json(dict(sorted(projected_root_kinds.items()))).encode("utf-8")
        ).hexdigest(),
    }
    _archive_paths_exclude_staged_inputs(projected_paths, staged_inputs)
    selection = {
        "schema_version": 1,
        "source": {
            key: prior[key]
            for key in (
                "job_id",
                "artifact_id",
                "artifact_type",
                "artifact_checksum",
                "artifact_checksum_algorithm",
                "artifact_attempt",
            )
        },
        # Staging removes write bits after verifying the immutable artifact
        # snapshot, so its mode-sensitive tree hash is expected to differ from
        # the published artifact hash. Retain both identities explicitly.
        "protected_staged_tree": {
            "checksum_algorithm": prior["checksum_algorithm"],
            "checksum": prior["checksum"],
        },
        "source_artifact_inventory": inventory,
        "required_added_inventory": required_added_inventory,
        "artifact_inventory": projected_inventory,
        "paths": list(projected_paths),
        "paths_sha256": hashlib.sha256(
            canonical_json(list(projected_paths)).encode("utf-8")
        ).hexdigest(),
    }
    return projected_paths, selection


def _validate_byox_repair_outputs(
    workspace: Path,
    archive_paths: tuple[str, ...],
    selection: dict[str, Any],
    staged_inputs: list[dict[str, Any]],
) -> None:
    """Reject undeclared or type-shifted repair roots after the worker exits."""

    inventory = selection.get("artifact_inventory")
    root_kinds = inventory.get("root_kinds") if isinstance(inventory, dict) else None
    if (
        not isinstance(root_kinds, dict)
        or inventory.get("selected_paths") != list(archive_paths)
        or set(root_kinds) != set(archive_paths)
    ):
        raise HandlerFailure(
            "BYOX repair projected inventory is malformed",
            kind="unsafe_archive_projection",
            retryable=False,
        )
    _archive_paths_exclude_staged_inputs(archive_paths, staged_inputs)
    staged_roots = {
        safe_relative(str(item["path"])).parts[0] for item in staged_inputs
    }
    expected_roots = set(archive_paths)
    if expected_roots & staged_roots:
        raise HandlerFailure(
            "BYOX repair projected output overlaps a staged root",
            kind="unsafe_archive_projection",
            retryable=False,
        )
    try:
        entries = list(workspace.iterdir())
    except OSError as error:
        raise HandlerFailure(
            f"cannot enumerate BYOX repair outputs: {error}",
            kind="unsafe_archive_projection",
            retryable=False,
        ) from error
    actual_roots: set[str] = set()
    folded: set[str] = set()
    for entry in entries:
        relative = safe_relative(entry.name)
        name = relative.as_posix()
        normalized = name.casefold()
        if len(relative.parts) != 1 or normalized in folded:
            raise HandlerFailure(
                "BYOX repair produced an unsafe or case-colliding root",
                kind="unsafe_archive_projection",
                retryable=False,
            )
        folded.add(normalized)
        actual_roots.add(name)
    unexpected = sorted(actual_roots - expected_roots - staged_roots)
    if unexpected:
        raise HandlerFailure(
            "BYOX repair produced undeclared top-level roots: "
            + ", ".join(unexpected),
            kind="unsafe_archive_projection",
            retryable=False,
        )
    missing = sorted(expected_roots - actual_roots)
    if missing:
        raise HandlerFailure(
            "BYOX repair omitted declared output roots: " + ", ".join(missing),
            kind="unsafe_archive_projection",
            retryable=False,
        )
    for name in archive_paths:
        path = workspace / safe_relative(name)
        if path.is_symlink() or not contained(workspace, path):
            raise HandlerFailure(
                f"BYOX repair projected root is unsafe: {name}",
                kind="unsafe_archive_projection",
                retryable=False,
            )
        expected_kind = root_kinds.get(name)
        if expected_kind == "file":
            valid_kind = path.is_file()
            descendants: list[Path] = []
        elif expected_kind == "directory":
            valid_kind = path.is_dir()
            descendants = list(path.rglob("*")) if valid_kind else []
        else:
            valid_kind = False
            descendants = []
        if not valid_kind:
            raise HandlerFailure(
                f"BYOX repair projected root has the wrong type: {name}",
                kind="unsafe_archive_projection",
                retryable=False,
            )
        if any(item.is_symlink() for item in descendants) or any(
            not item.is_file() and not item.is_dir() for item in descendants
        ):
            raise HandlerFailure(
                f"BYOX repair projected root is not a regular tree: {name}",
                kind="unsafe_archive_projection",
                retryable=False,
            )


def _enforce_dependency_artifact_binding(
    item: dict[str, Any], artifact: sqlite3.Row, dependency: str
) -> None:
    """Apply optional immutable artifact pins without coercing malformed values."""

    fields: tuple[tuple[str, str, type], ...] = (
        ("artifact_id", "artifact_id", str),
        ("artifact_checksum", "checksum", str),
        ("artifact_attempt", "attempt_number", int),
        ("checksum_algorithm", "checksum_algorithm", str),
    )
    for payload_name, column_name, expected_type in fields:
        if payload_name not in item:
            continue
        value = item[payload_name]
        malformed = (
            isinstance(value, bool)
            or not isinstance(value, expected_type)
            or (expected_type is str and (not value or len(value) > 1_000 or "\0" in value))
            or (expected_type is int and value < 1)
        )
        if malformed:
            raise HandlerFailure(
                f"dependency artifact binding {payload_name} is malformed: {dependency}",
                kind="artifact_integrity_failure",
                retryable=False,
            )
        if value != artifact[column_name]:
            raise HandlerFailure(
                f"dependency artifact binding {payload_name} mismatch: {dependency}",
                kind="artifact_integrity_failure",
                retryable=False,
            )


def _byox_artifact_root_source(
    item: dict[str, Any],
    artifact: sqlite3.Row,
    snapshot: Path,
    temporary: Path,
) -> tuple[Path, dict[str, Any]]:
    """Build a symlink-free filtered root from one explicit BYOX artifact profile."""

    from .byox_remediation import (
        BYOX_ARTIFACT_PROFILES,
        BYOX_REPAIR_ARTIFACT_TYPE,
        BYOX_REPAIR_CONTROL_ROOTS,
        ByoxRemediationError,
        byox_artifact_profile,
    )

    try:
        parent_payload = json.loads(str(artifact["parent_payload_json"]))
    except (TypeError, json.JSONDecodeError) as error:
        raise HandlerFailure(
            "full-root dependency parent payload is invalid",
            kind="artifact_integrity_failure",
            retryable=False,
        ) from error
    if not isinstance(parent_payload, dict):
        raise HandlerFailure(
            "full-root dependency parent payload is not an object",
            kind="artifact_integrity_failure",
            retryable=False,
        )
    declared_profile = item.get("artifact_profile")
    if not isinstance(declared_profile, str):
        raise HandlerFailure(
            "full-root BYOX dependency lacks an artifact profile",
            kind="artifact_integrity_failure",
            retryable=False,
        )
    try:
        resolved_profile = byox_artifact_profile(
            str(artifact["type"]), parent_payload
        )
    except ByoxRemediationError as error:
        raise HandlerFailure(
            str(error), kind="artifact_integrity_failure", retryable=False
        ) from error
    if declared_profile != resolved_profile:
        raise HandlerFailure(
            "full-root BYOX artifact profile does not match its dependency",
            kind="artifact_integrity_failure",
            retryable=False,
        )
    profile = BYOX_ARTIFACT_PROFILES[resolved_profile]
    required_roots = set(
        profile[
            "output_required_roots"
            if artifact["type"] == BYOX_REPAIR_ARTIFACT_TYPE
            else "required_roots"
        ]
    )
    allowed_exclusions = set(profile["allowed_control_exclusions"])
    descendants = list(snapshot.rglob("*"))
    if any(path.is_symlink() for path in descendants):
        raise HandlerFailure(
            "full-root BYOX artifact contains a symlink",
            kind="artifact_integrity_failure",
            retryable=False,
        )
    if any(not path.is_file() and not path.is_dir() for path in descendants):
        raise HandlerFailure(
            "full-root BYOX artifact contains a special file",
            kind="artifact_integrity_failure",
            retryable=False,
        )
    entries = list(snapshot.iterdir())
    original: list[str] = []
    selected: list[str] = []
    excluded: list[str] = []
    root_kinds: dict[str, str] = {}
    folded: set[str] = set()
    controls = {name.casefold() for name in BYOX_REPAIR_CONTROL_ROOTS}
    for entry in entries:
        try:
            relative = safe_relative(entry.name)
        except WorkspaceError as error:
            raise HandlerFailure(
                "full-root BYOX artifact contains an unsafe top-level name",
                kind="artifact_integrity_failure",
                retryable=False,
            ) from error
        name = relative.as_posix()
        normalized = name.casefold()
        if len(relative.parts) != 1 or normalized in folded:
            raise HandlerFailure(
                "full-root BYOX artifact contains duplicate or overlapping roots",
                kind="artifact_integrity_failure",
                retryable=False,
            )
        folded.add(normalized)
        original.append(name)
        root_kinds[name] = "file" if entry.is_file() else "directory"
        if normalized in controls or name.startswith(".archive-projection-"):
            if name not in allowed_exclusions:
                raise HandlerFailure(
                    f"full-root BYOX artifact contains a forbidden control root: {name}",
                    kind="artifact_integrity_failure",
                    retryable=False,
                )
            excluded.append(name)
            continue
        selected.append(name)
    if not selected:
        raise HandlerFailure(
            "full-root BYOX artifact has an empty safe projection",
            kind="artifact_integrity_failure",
            retryable=False,
        )
    missing = sorted(required_roots - set(selected))
    if missing:
        raise HandlerFailure(
            "full-root BYOX artifact lacks profile roots: " + ", ".join(missing),
            kind="artifact_integrity_failure",
            retryable=False,
        )
    destination_key = str(item.get("destination", ""))
    filtered = temporary / (
        "filtered-artifact-root-"
        + hashlib.sha256(destination_key.encode("utf-8")).hexdigest()[:12]
    )
    filtered.mkdir()
    for name in sorted(selected):
        source = snapshot / name
        destination = filtered / name
        if source.is_dir():
            shutil.copytree(source, destination, symlinks=True)
        else:
            shutil.copy2(source, destination, follow_symlinks=False)
    original = sorted(original)
    selected = sorted(selected)
    excluded = sorted(excluded)
    inventory = {
        "schema_version": 1,
        "profile": resolved_profile,
        "source_artifact_type": artifact["type"],
        "original_paths": original,
        "selected_paths": selected,
        "excluded_paths": excluded,
        "root_kinds": dict(sorted(root_kinds.items())),
        "original_paths_sha256": hashlib.sha256(
            canonical_json(original).encode("utf-8")
        ).hexdigest(),
        "selected_paths_sha256": hashlib.sha256(
            canonical_json(selected).encode("utf-8")
        ).hexdigest(),
        "excluded_paths_sha256": hashlib.sha256(
            canonical_json(excluded).encode("utf-8")
        ).hexdigest(),
        "root_kinds_sha256": hashlib.sha256(
            canonical_json(dict(sorted(root_kinds.items()))).encode("utf-8")
        ).hexdigest(),
    }
    declared_inventory = item.get("artifact_inventory")
    if declared_inventory is not None and declared_inventory != inventory:
        raise HandlerFailure(
            "full-root BYOX declared inventory does not match the verified artifact",
            kind="artifact_integrity_failure",
            retryable=False,
        )
    return filtered, inventory


def _revision_student_dependency_is_safe(
    job: ClaimedJob,
    *,
    dependency_job_id: str,
    parent_worker_type: object,
    parent_payload_raw: object,
    artifact: sqlite3.Row,
    subpath: Path,
) -> bool:
    """Allow only provenance-bound prior work/feedback into a CSDIY revision.

    Ordinary student jobs remain restricted to ``student_safe/``.  A versioned
    revision additionally needs its own immediately prior attempt and the
    learner-facing output of its prior examiner.  The immutable revision
    snapshot binds both exact artifact identities, so a payload cannot substitute
    another student's work or an examiner-only material tree.
    """

    policy = job.payload.get("seed_policy")
    revision = job.payload.get("revision_snapshot")
    attempt_number = policy.get("attempt_number") if isinstance(policy, dict) else None
    if (
        not isinstance(policy, dict)
        or policy
        != {
            "kind": "csdiy_course_progression",
            "version": 1,
            "attempt_number": attempt_number,
            "role": "student_revision",
        }
        or isinstance(attempt_number, bool)
        or not isinstance(attempt_number, int)
        or attempt_number < 2
        or not isinstance(revision, dict)
        or revision.get("attempt_number") != attempt_number
    ):
        return False
    try:
        parent_payload = json.loads(str(parent_payload_raw))
    except (TypeError, json.JSONDecodeError):
        return False
    if not isinstance(parent_payload, dict) or any(
        parent_payload.get(name) != job.payload.get(name)
        for name in ("student_id", "course_id", "batch_id")
    ):
        return False

    def binding_matches(raw: object, expected_artifact_type: str) -> bool:
        return bool(
            isinstance(raw, dict)
            and raw.get("job_id") == dependency_job_id
            and raw.get("artifact_id") == artifact["artifact_id"]
            and raw.get("artifact_type") == expected_artifact_type
            and raw.get("artifact_type") == artifact["type"]
            and raw.get("artifact_checksum") == artifact["checksum"]
            and raw.get("artifact_attempt") == artifact["attempt_number"]
        )

    if (
        parent_worker_type == "student"
        and subpath.parts
        in {
            ("student_work", "notes.md"),
            ("student_work", "submission.md"),
            ("student_work", "debugging-log.md"),
            ("student_work", "self-check.md"),
        }
    ):
        return binding_matches(
            revision.get("prior_student"), "student-course-unit-attempt"
        )
    if (
        parent_worker_type == "examiner"
        and subpath.parts in {("evaluation.json",), ("feedback.md",)}
    ):
        return binding_matches(
            revision.get("prior_examiner"),
            "independent-course-unit-evaluation",
        )
    return False


def _kickoff_revision_student_dependency_is_safe(
    job: ClaimedJob,
    *,
    dependency_job_id: str,
    parent_worker_type: object,
    parent_payload_raw: object,
    artifact: sqlite3.Row,
    subpath: Path,
) -> bool:
    """Admit only the prior kickoff work and learner-facing feedback it binds."""

    policy = job.payload.get("seed_policy")
    revision = job.payload.get("revision_snapshot")
    attempt_number = policy.get("attempt_number") if isinstance(policy, dict) else None
    if (
        not isinstance(policy, dict)
        or policy
        != {
            "kind": "csdiy_course_kickoff_revision",
            "version": 1,
            "attempt_number": attempt_number,
            "role": "student_revision",
        }
        or isinstance(attempt_number, bool)
        or not isinstance(attempt_number, int)
        or attempt_number < 2
        or not isinstance(revision, dict)
        or revision.get("attempt_number") != attempt_number
        or revision.get("student_id") != job.payload.get("student_id")
    ):
        return False
    checksum = revision.get("revision_snapshot_sha256")
    without_checksum = dict(revision)
    without_checksum.pop("revision_snapshot_sha256", None)
    if (
        not isinstance(checksum, str)
        or len(checksum) != 64
        or hashlib.sha256(
            canonical_json(without_checksum).encode("utf-8")
        ).hexdigest()
        != checksum
    ):
        return False
    identity_input = dict(without_checksum)
    revision_id = identity_input.pop("revision_id", None)
    expected_digest = hashlib.sha256(
        canonical_json(identity_input).encode("utf-8")
    ).hexdigest()
    if revision_id != f"csdiy-kickoff-revision-v1-{expected_digest[:24]}":
        return False
    course = revision.get("course")
    if (
        not isinstance(course, dict)
        or course.get("course_id") != job.payload.get("course_id")
        or job.payload.get("student_id") != "student-target"
    ):
        return False
    try:
        parent_payload = json.loads(str(parent_payload_raw))
    except (TypeError, json.JSONDecodeError):
        return False
    if not isinstance(parent_payload, dict) or any(
        parent_payload.get(name) != job.payload.get(name)
        for name in ("student_id", "course_id")
    ):
        return False

    def binding_matches(raw: object, expected_artifact_type: str) -> bool:
        return bool(
            isinstance(raw, dict)
            and raw.get("job_id") == dependency_job_id
            and raw.get("artifact_id") == artifact["artifact_id"]
            and raw.get("artifact_type") == expected_artifact_type
            and raw.get("artifact_type") == artifact["type"]
            and raw.get("artifact_checksum") == artifact["checksum"]
            and raw.get("artifact_checksum_algorithm")
            == artifact["checksum_algorithm"]
            and raw.get("artifact_attempt") == artifact["attempt_number"]
        )

    if (
        parent_worker_type == "student"
        and subpath.parts
        in {("notes.md",), ("submission.md",), ("debugging-log.md",)}
    ):
        return binding_matches(revision.get("prior_student"), "student-course-attempt")
    if parent_worker_type == "examiner" and subpath.parts == ("feedback.md",):
        return binding_matches(
            revision.get("prior_examiner"), "independent-course-evaluation"
        )
    return False


class JobHandlers:
    def __init__(self, settings: FactorySettings, db: Database, workspaces: WorkspaceManager):
        self.settings = settings
        self.db = db
        self.workspaces = workspaces

    def execute(
        self,
        job: ClaimedJob,
        workspace: Path,
        log_dir: Path,
        cancel_event: threading.Event,
    ) -> HandlerResult:
        if job.type == "fake":
            return self._fake(job, workspace, log_dir, cancel_event)
        if job.type == "codex_task":
            return self._codex(job, workspace, log_dir, cancel_event)
        if job.type == "source_ingest":
            return self._ingest(job, workspace)
        if job.type == "catalog_synthesis":
            from .catalog_synthesis import (
                CatalogSynthesisError,
                generate_catalog_synthesis,
            )

            try:
                generated = generate_catalog_synthesis(workspace, job.payload, self.db)
            except CatalogSynthesisError as error:
                raise HandlerFailure(
                    str(error), kind="permanent", retryable=False
                ) from error
            return HandlerResult(
                generated.evidence,
                generated.validators,
                generated.artifact_type,
                generated.semantic_path,
                generated.metadata,
            )
        if job.type == "course_vertical_slice":
            from .vertical_slices import generate_course_slice

            generated = generate_course_slice(workspace, job.payload, self.db)
            return HandlerResult(
                generated.evidence,
                generated.validators,
                generated.artifact_type,
                generated.semantic_path,
                generated.metadata,
            )
        if job.type == "project_vertical_slice":
            from .vertical_slices import generate_project_slice

            generated = generate_project_slice(workspace, job.payload, self.db)
            return HandlerResult(
                generated.evidence,
                generated.validators,
                generated.artifact_type,
                generated.semantic_path,
                generated.metadata,
            )
        if job.type == "http_service_vertical_slice":
            from .http_service_slice import generate_http_service_slice

            generated = generate_http_service_slice(workspace, job.payload, self.db)
            return HandlerResult(
                generated.evidence,
                generated.validators,
                generated.artifact_type,
                generated.semantic_path,
                generated.metadata,
            )
        if job.type == "allocator_vertical_slice":
            from .allocator_slice import generate_allocator_slice

            generated = generate_allocator_slice(workspace, job.payload, self.db)
            return HandlerResult(
                generated.evidence,
                generated.validators,
                generated.artifact_type,
                generated.semantic_path,
                generated.metadata,
            )
        if job.type == "bytecode_vertical_slice":
            from .bytecode_slice import generate_bytecode_slice

            generated = generate_bytecode_slice(workspace, job.payload, self.db)
            return HandlerResult(
                generated.evidence,
                generated.validators,
                generated.artifact_type,
                generated.semantic_path,
                generated.metadata,
            )
        if job.type == "event_service_vertical_slice":
            from .event_service_slice import generate_event_service_slice

            generated = generate_event_service_slice(workspace, job.payload, self.db)
            return HandlerResult(
                generated.evidence,
                generated.validators,
                generated.artifact_type,
                generated.semantic_path,
                generated.metadata,
            )
        raise HandlerFailure(f"unknown job type: {job.type}", kind="permanent", retryable=False)

    def _fake(
        self,
        job: ClaimedJob,
        workspace: Path,
        log_dir: Path,
        cancel_event: threading.Event,
    ) -> HandlerResult:
        files = job.payload.get("files", {"result.txt": "ok\n"})
        if not isinstance(files, dict):
            raise HandlerFailure("fake files must be an object", kind="permanent", retryable=False)
        safe_files: dict[str, str] = {}
        for raw, content in files.items():
            try:
                relative = safe_relative(str(raw))
            except WorkspaceError as error:
                raise HandlerFailure(str(error), kind="permanent", retryable=False) from error
            target = workspace / relative
            if not contained(workspace, target):
                raise HandlerFailure("fake output escapes workspace", kind="permanent", retryable=False)
            safe_files[str(relative)] = str(content)
        backend = FakeBackend(
            delay=float(job.payload.get("delay", 0)),
            exit_code=int(job.payload.get("exit_code", 0)),
            files=safe_files,
        )
        result = backend.start_job("fake", workspace, log_dir, cancel_event=cancel_event)
        if result.cancelled:
            raise HandlerFailure("fake worker cancelled", kind="cancelled", retryable=False)
        if result.exit_code:
            raise HandlerFailure(f"fake backend exited {result.exit_code}", kind="agent_failure", retryable=True)
        validators = list(job.payload.get("validators", []))
        if not validators:
            validators = [{"type": "required_paths", "name": "fake-output", "paths": list(safe_files)}]
        return HandlerResult(
            {"files": list(safe_files)},
            validators,
            str(job.payload.get("artifact_type", "test-output")),
            str(job.payload.get("artifact_path", "smoke/fake")),
            dict(job.payload.get("provenance", {"generated": True})),
            result,
            backend.name,
        )

    def _codex(
        self,
        job: ClaimedJob,
        workspace: Path,
        log_dir: Path,
        cancel_event: threading.Event,
    ) -> HandlerResult:
        _enforce_byox_remediation_backend(job, self.settings)
        _enforce_kickoff_revision_backend(job, self.settings)
        input_integrity, staged_input_provenance = self._stage_declared_inputs(
            job, workspace
        )
        repair_archive_paths, repair_projection = _byox_repair_archive_selection(
            job, workspace, staged_input_provenance
        )
        prompt = str(job.payload.get("prompt", "")).strip()
        if not prompt:
            raise HandlerFailure("Codex task has no prompt", kind="permanent", retryable=False)
        (workspace / "JOB.md").write_text(prompt + "\n", encoding="utf-8")
        schema = None
        if job.payload.get("output_schema"):
            schema = log_dir / "response-schema.json"
            schema.parent.mkdir(parents=True, exist_ok=True)
            schema.write_text(canonical_json(job.payload["output_schema"]) + "\n", encoding="utf-8")
        backend = ExecBackend(
            self.settings.backend.command,
            timeout_seconds=self.settings.backend.timeout_seconds,
            permission_profile=self.settings.backend.permission_profile,
            toolchain_read_roots=self.settings.backend.toolchain_read_roots,
            provider=self.settings.backend.provider,
            base_url=self.settings.backend.base_url,
            provider_name=self.settings.backend.provider_name,
            requires_openai_auth=self.settings.backend.requires_openai_auth,
            supports_websockets=self.settings.backend.supports_websockets,
        )
        result = backend.start_job(
            prompt,
            workspace,
            log_dir,
            output_schema=schema,
            model=job.model or self.settings.backend.model,
            reasoning_effort=job.reasoning_effort or self.settings.backend.reasoning_effort,
            timeout_seconds=float(job.payload.get("timeout_seconds", self.settings.backend.timeout_seconds)),
            cancel_event=cancel_event,
        )
        if result.cancelled:
            raise HandlerFailure("Codex process cancelled", kind="cancelled", retryable=False)
        if result.timed_out:
            raise HandlerFailure("Codex process timed out", kind="timeout", retryable=True)
        if result.exit_code != 0:
            lower = result.stderr_tail.lower()
            if "model provider" in lower and "not found" in lower:
                raise HandlerFailure(
                    f"Codex backend configuration unavailable: {result.stderr_tail}",
                    kind="blocked_backend_configuration",
                    retryable=False,
                )
            if any(term in lower for term in ("401 unauthorized", "incorrect api key", "not logged in")):
                raise HandlerFailure(
                    "Codex authentication is unavailable or invalid; operator login is required",
                    kind="blocked_authentication",
                    retryable=False,
                )
            transient = any(term in lower for term in ("rate limit", "temporarily unavailable", "connection", "timeout", "try again"))
            raise HandlerFailure(
                f"Codex exited {result.exit_code}: {result.stderr_tail}",
                kind="transient_infrastructure" if transient else "agent_failure",
                retryable=True,
            )
        removed_metadata = [
            name
            for name in (".git", ".agents", ".codex", "JOB.md", ".factory-workspace")
            if self.workspaces.discard_root_metadata(workspace, name)
        ]
        if repair_archive_paths is not None and repair_projection is not None:
            _validate_byox_repair_outputs(
                workspace,
                repair_archive_paths,
                repair_projection,
                staged_input_provenance,
            )
        validators = list(job.payload.get("validators", []))
        if not validators:
            raise HandlerFailure(
                "Codex task lacks an external validator", kind="permanent", retryable=False
            )
        validators = _with_byox_runtime_safety_validators(job, validators)
        if input_integrity:
            validators.append(
                {
                    "type": "input_integrity",
                    "name": "declared-inputs-remained-immutable",
                    "inputs": input_integrity,
                }
            )
        publication = None
        if "learner_evidence" in job.payload:
            from .learners import prepare_examiner_learner_publication

            try:
                publication = prepare_examiner_learner_publication(
                    self.db,
                    self.settings.warehouse,
                    examiner_job_id=job.job_id,
                    examiner_attempt=job.attempt_count,
                    worker_type=job.worker_type,
                    payload=job.payload,
                    workspace=workspace,
                )
            except ValueError as error:
                raise HandlerFailure(
                    f"examiner learner evidence is invalid: {error}",
                    kind="validation_failure",
                    retryable=bool(job.payload.get("retry_validation", False)),
                ) from error
        artifact_type = str(job.payload.get("artifact_type", "codex-output"))
        archive_paths = repair_archive_paths or _OUTPUT_ONLY_ARCHIVES.get(artifact_type)
        if archive_paths is not None:
            _archive_paths_exclude_staged_inputs(
                archive_paths, staged_input_provenance
            )
        return HandlerResult(
            {
                "session_id": result.session_id,
                "usage": result.usage,
                "removed_root_metadata": removed_metadata,
            },
            validators,
            artifact_type,
            str(job.payload.get("artifact_path", f"codex/{job.job_id}")),
            {
                **dict(job.payload.get("provenance", {"agent_generated": True})),
                "staged_inputs": staged_input_provenance,
                "removed_root_metadata": removed_metadata,
                **(
                    {"repair_archive_selection": repair_projection}
                    if repair_projection is not None
                    else {}
                ),
            },
            result,
            backend.name,
            on_publish=publication.on_publish if publication is not None else None,
            on_commit=publication.on_commit if publication is not None else None,
            archive_paths=archive_paths,
        )

    def _stage_declared_inputs(
        self, job: ClaimedJob, workspace: Path
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        payload = job.payload
        raw_protected_values = payload.get("protected_input_roots", [])
        if not isinstance(raw_protected_values, list) or not all(
            isinstance(value, str) for value in raw_protected_values
        ):
            raise WorkspaceError("protected input roots must be a list of paths")
        protected_values = list(raw_protected_values)
        declared_protected = {
            safe_relative(value).as_posix() for value in protected_values
        }
        public_source_roots = [
            (self.settings.root.parent / "cs-self-learning").resolve(),
            (self.settings.root.parent / "build-your-own-x").resolve(),
        ]
        allowed_roots = list(public_source_roots)
        # Student jobs may only receive warehouse material through a declared,
        # successful dependency and an explicit learner-safe subpath.
        if job.worker_type != "student":
            allowed_roots.append(self.settings.warehouse.resolve())

        destinations: list[Path] = []
        integrity: list[dict[str, Any]] = []
        provenance: list[dict[str, Any]] = []

        def stage(
            source: Path, destination_value: object, origin: dict[str, Any]
        ) -> None:
            destination = safe_relative(str(destination_value))
            if any(
                destination == existing
                or destination in existing.parents
                or existing in destination.parents
                for existing in destinations
            ):
                raise WorkspaceError(
                    f"overlapping staged destination: {destination.as_posix()}"
                )
            destinations.append(destination)
            if source.is_file() and not source.is_symlink():
                target = self.workspaces.stage_file(
                    source, workspace, destination.as_posix()
                )
            elif source.is_dir() and not source.is_symlink():
                target = self.workspaces.stage_tree(
                    source, workspace, destination.as_posix()
                )
            else:
                raise WorkspaceError(
                    f"staged input is neither a regular file nor directory: {source}"
                )
            record = _staged_input_record(target, destination.as_posix())
            integrity.append(record)
            provenance.append({**record, **origin})

        for item in payload.get("inputs", []):
            if not isinstance(item, dict):
                raise WorkspaceError("declared input must be an object")
            declared_source = Path(str(item["source"]))
            if declared_source.is_symlink():
                raise WorkspaceError(
                    f"declared input may not be a symlink: {declared_source}"
                )
            source = declared_source.resolve()
            if not any(contained(root, source) for root in allowed_roots):
                raise WorkspaceError(f"input is outside allowed roots: {source}")
            stage(source, item["destination"], {"origin": "declared-source"})

        dependency_inputs: dict[str, list[dict[str, Any]]] = {}
        for item in payload.get("inputs_from_dependencies", []):
            if not isinstance(item, dict):
                raise WorkspaceError("dependency input must be an object")
            dependency_inputs.setdefault(str(item["job_id"]), []).append(item)

        # Take exactly one immutable, checksum-verified snapshot per dependency,
        # then select every declared input from that same snapshot.
        for dependency, items in dependency_inputs.items():
            with self.db.connect() as connection:
                artifact = connection.execute(
                    """
                    SELECT a.artifact_id,a.type,a.path,a.checksum,a.checksum_algorithm,
                           a.integrity_status,a.attempt_number,
                           parent.worker_type AS parent_worker_type,
                           parent.payload_json AS parent_payload_json
                    FROM job_dependencies d
                    JOIN jobs parent ON parent.job_id=d.depends_on_job_id
                    JOIN artifacts a ON a.job_id=parent.job_id
                                   AND a.attempt_number=parent.attempt_count
                    WHERE d.job_id=? AND d.depends_on_job_id=?
                      AND parent.state='SUCCEEDED'
                    ORDER BY a.created_at DESC LIMIT 1
                    """,
                    (job.job_id, dependency),
                ).fetchone()
            if artifact is None:
                raise HandlerFailure(
                    f"declared dependency {dependency} has no current succeeded artifact",
                    kind="blocked_dependency",
                    retryable=False,
                )
            root = Path(artifact["path"])
            if (
                artifact["checksum_algorithm"] != "tree-sha256-v2"
                or artifact["integrity_status"] != "VERIFIED_V2"
            ):
                raise HandlerFailure(
                    f"dependency artifact uses non-stageable legacy integrity evidence: {dependency}",
                    kind="artifact_integrity_failure",
                    retryable=False,
                )
            if not contained(self.workspaces.artifacts, root):
                raise HandlerFailure(
                    f"dependency artifact is outside the managed store: {dependency}",
                    kind="artifact_integrity_failure",
                    retryable=False,
                )
            if root.is_symlink() or not root.is_dir():
                raise HandlerFailure(
                    f"dependency artifact is missing: {dependency}",
                    kind="artifact_integrity_failure",
                    retryable=False,
                )
            try:
                with tempfile.TemporaryDirectory(
                    prefix=f".dependency-{job.job_id}-", dir=workspace.parent
                ) as temporary:
                    snapshot = Path(temporary) / "artifact"
                    _copy_dependency_tree(root, snapshot)
                    if tree_sha256_for_algorithm(
                        snapshot, artifact["checksum_algorithm"]
                    ) != artifact["checksum"]:
                        raise HandlerFailure(
                            f"dependency artifact checksum mismatch: {dependency}",
                            kind="artifact_integrity_failure",
                            retryable=False,
                        )
                    for item in items:
                        _enforce_dependency_artifact_binding(
                            item, artifact, dependency
                        )
                        expected_type = item.get("artifact_type")
                        if expected_type is not None and (
                            not isinstance(expected_type, str)
                            or not expected_type
                            or expected_type != artifact["type"]
                        ):
                            raise HandlerFailure(
                                f"dependency artifact type mismatch: {dependency}",
                                kind="artifact_integrity_failure",
                                retryable=False,
                            )
                        raw_artifact_root = item.get("artifact_root", False)
                        if not isinstance(raw_artifact_root, bool):
                            raise HandlerFailure(
                                f"dependency artifact_root is malformed: {dependency}",
                                kind="artifact_integrity_failure",
                                retryable=False,
                            )
                        destination = safe_relative(str(item.get("destination", "")))
                        artifact_inventory: dict[str, Any] | None = None
                        if raw_artifact_root:
                            raw_subpath = item.get("subpath")
                            if raw_subpath not in (None, "", "."):
                                raise HandlerFailure(
                                    "full-root dependency input cannot declare a nontrivial subpath",
                                    kind="artifact_integrity_failure",
                                    retryable=False,
                                )
                            if destination.as_posix() not in declared_protected:
                                raise HandlerFailure(
                                    "full-root dependency destination must be a protected input root",
                                    kind="artifact_integrity_failure",
                                    retryable=False,
                                )
                            if job.worker_type == "student":
                                raise WorkspaceError(
                                    "student dependency input must be under student_safe/"
                                )
                            subpath = None
                            selected, artifact_inventory = _byox_artifact_root_source(
                                item, artifact, snapshot, Path(temporary)
                            )
                        else:
                            if "subpath" not in item:
                                raise HandlerFailure(
                                    f"dependency input has no subpath: {dependency}",
                                    kind="artifact_integrity_failure",
                                    retryable=False,
                                )
                            subpath = safe_relative(str(item["subpath"]))
                        if (
                            subpath is not None
                            and job.worker_type == "student"
                            and (not subpath.parts or subpath.parts[0] != "student_safe")
                            and not _revision_student_dependency_is_safe(
                                job,
                                dependency_job_id=dependency,
                                parent_worker_type=artifact["parent_worker_type"],
                                parent_payload_raw=artifact["parent_payload_json"],
                                artifact=artifact,
                                subpath=subpath,
                            )
                            and not _kickoff_revision_student_dependency_is_safe(
                                job,
                                dependency_job_id=dependency,
                                parent_worker_type=artifact["parent_worker_type"],
                                parent_payload_raw=artifact["parent_payload_json"],
                                artifact=artifact,
                                subpath=subpath,
                            )
                        ):
                            raise WorkspaceError(
                                "student dependency input must be under student_safe/"
                            )
                        if subpath is not None:
                            selected = snapshot / subpath
                        source = selected.resolve()
                        selection_root = snapshot if subpath is not None else Path(temporary)
                        if selected.is_symlink() or not contained(selection_root, source):
                            raise WorkspaceError("dependency subpath escapes artifact")
                        stage(
                            source,
                            item["destination"],
                            {
                                "origin": "dependency-artifact",
                                "job_id": dependency,
                                "artifact_id": artifact["artifact_id"],
                                "artifact_type": artifact["type"],
                                "artifact_checksum": artifact["checksum"],
                                "artifact_checksum_algorithm": artifact[
                                    "checksum_algorithm"
                                ],
                                "artifact_attempt": artifact["attempt_number"],
                                "artifact_subpath": (
                                    "." if subpath is None else subpath.as_posix()
                                ),
                                **(
                                    {"artifact_inventory": artifact_inventory}
                                    if artifact_inventory is not None
                                    else {}
                                ),
                            },
                        )
            except HandlerFailure:
                raise
            except OSError as error:
                raise HandlerFailure(
                    f"cannot snapshot dependency artifact {dependency}: {error}",
                    kind="artifact_integrity_failure",
                    retryable=False,
                ) from error

        top_level_parts = {
            destination.parts[0]
            for destination in destinations
            if len(destination.parts) > 1
        }
        if (
            destinations
            and len(top_level_parts) == 1
            and all(len(destination.parts) > 1 for destination in destinations)
        ):
            inferred = next(iter(top_level_parts))
            if inferred not in {str(value) for value in protected_values}:
                protected_values.append(inferred)

        protected: list[Path] = []
        for raw in protected_values:
            relative = safe_relative(str(raw))
            target = workspace / relative
            if (
                not contained(workspace, target)
                or target.is_symlink()
                or not target.is_dir()
            ):
                raise WorkspaceError(
                    f"protected input root is missing or unsafe: {relative.as_posix()}"
                )
            if not any(
                destination == relative or relative in destination.parents
                for destination in destinations
            ):
                raise WorkspaceError(
                    f"protected input root has no staged inputs: {relative.as_posix()}"
                )
            target.chmod(target.stat().st_mode & ~0o222)
            protected.append(relative)

        if protected:
            integrity = [
                record
                for record in integrity
                if not any(
                    Path(record["path"]) == root
                    or root in Path(record["path"]).parents
                    for root in protected
                )
            ]
            integrity.extend(
                _staged_input_record(workspace / root, root.as_posix())
                for root in protected
            )
        return integrity, provenance

    def _ingest(self, job: ClaimedJob, workspace: Path) -> HandlerResult:
        from .sources import detect_source

        source_path = Path(str(job.payload["source_path"])).resolve()
        allowed = {self.settings.root.parent.resolve()}
        if source_path.parent.resolve() not in allowed:
            raise HandlerFailure("source path is outside configured source parent", kind="permanent", retryable=False)
        adapter = detect_source(source_path)
        if adapter is None:
            raise HandlerFailure(
                f"no source adapter recognizes {source_path}",
                kind="permanent",
                retryable=False,
            )
        prepared = adapter.prepare(source_path)
        expected_commit = str(job.payload.get("expected_commit", "")).strip()
        if (
            expected_commit
            and prepared.descriptor.commit_hash != expected_commit
        ):
            raise HandlerFailure(
                "source HEAD changed before preparation: "
                f"expected {expected_commit}, got {prepared.descriptor.commit_hash}",
                kind="source_snapshot_changed",
                retryable=False,
            )
        summary = prepared.result().as_dict()
        (workspace / "prepared-source.json").write_text(
            json.dumps(
                prepared.as_dict(), indent=2, sort_keys=True, ensure_ascii=False
            )
            + "\n",
            encoding="utf-8",
        )
        (workspace / "ingestion-summary.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        count = int(summary.get("records", summary.get("courses", 0) + summary.get("projects", 0)))
        return HandlerResult(
            summary,
            [
                {
                    "type": "handler_evidence",
                    "name": "catalog-records-prepared",
                    "passed": count > 0,
                    "evidence": {"record_count": count},
                },
                {"type": "json_fields", "name": "ingestion-summary", "path": "ingestion-summary.json", "required": ["source_id"]},
                {
                    "type": "json_fields",
                    "name": "prepared-source",
                    "path": "prepared-source.json",
                    "required": ["schema_version", "descriptor", "normalized", "summary"],
                },
            ],
            "source-ingestion",
            f"sources/{source_path.name}",
            {
                "source_path": str(source_path),
                "source_commit": prepared.descriptor.commit_hash,
                "normalization": "deterministic-from-pinned-git-objects",
                "byte_reproducible": False,
                "publication": "fenced-with-job-success",
            },
            on_publish=lambda connection: adapter.activate_prepared(
                self.db, connection, prepared
            ),
        )
