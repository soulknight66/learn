from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import shutil
import sqlite3
import stat
import tempfile
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from .backends import BackendResult, ExecBackend, FakeBackend
from .backend_policy import mass_seed_backend_policy_violation
from .config import FactorySettings
from .db import Database
from .jobs import ClaimedJob
from .publication import PublicationConnection, PublicationScope
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
    on_publish: Callable[[PublicationConnection], None] | None = None
    publication_scope: PublicationScope | None = None
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


def _enforce_mass_seed_backend(
    job: ClaimedJob, settings: FactorySettings
) -> None:
    """Fence legacy and current mass-seeded Codex graphs before any launch."""

    violation = mass_seed_backend_policy_violation(job, settings)
    if violation is not None:
        raise HandlerFailure(
            "mass-seeded Codex jobs require exec/factory-isolated with "
            "gpt-5.6-sol ultra on the approved ARM HTTPS route",
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
) -> dict[str, Any]:
    """Replace worker scratch with the sole authoritative validation snapshot.

    The Codex subprocess has exited before this function runs.  All selected
    outputs and protected inputs are copied once, through held no-follow
    descriptors, into fresh inodes in a factory-owned sibling directory.
    Excluded roots are hashed as capture-time evidence but are not copied.  The
    fresh directory is then renamed onto the allocated attempt path.  Every
    later validator and archive operation therefore consumes the cutover bytes,
    never the mutable worker scratch tree.
    """

    from .byox_remediation import (
        BYOX_REPAIR_CUTOVER_MAX_DEPTH,
        BYOX_REPAIR_CUTOVER_MAX_ENTRIES,
        BYOX_REPAIR_CUTOVER_MAX_FILE_BYTES,
        BYOX_REPAIR_CUTOVER_MAX_TOTAL_BYTES,
        BYOX_REPAIR_CUTOVER_POLICY,
        BYOX_REPAIR_QUARANTINE_MAX_ROOTS,
    )

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
    staged_root_kinds: dict[str, str] = {}
    staged_bindings: list[dict[str, str]] = []
    staged_binding_paths: set[str] = set()
    for item in staged_inputs:
        relative = safe_relative(str(item.get("path", "")))
        kind = item.get("kind")
        algorithm = item.get("checksum_algorithm")
        checksum = item.get("checksum")
        root = relative.parts[0]
        root_kind = str(kind) if len(relative.parts) == 1 else "directory"
        prior_root_kind = staged_root_kinds.get(root)
        if (
            relative.as_posix() in staged_binding_paths
            or kind not in {"file", "directory"}
            or algorithm not in {"file-sha256", "tree-sha256-v2"}
            or (kind == "file" and algorithm != "file-sha256")
            or (kind == "directory" and algorithm != "tree-sha256-v2")
            or not isinstance(checksum, str)
            or re.fullmatch(r"[0-9a-f]{64}", checksum) is None
            or (
                prior_root_kind is not None
                and prior_root_kind != root_kind
            )
        ):
            raise HandlerFailure(
                "BYOX repair staged-input binding is malformed",
                kind="unsafe_archive_projection",
                retryable=False,
            )
        staged_root_kinds[root] = root_kind
        staged_binding_paths.add(relative.as_posix())
        staged_bindings.append(
            {
                "path": relative.as_posix(),
                "kind": str(kind),
                "checksum_algorithm": str(algorithm),
                "checksum": checksum,
            }
        )
    staged_bindings.sort(key=lambda item: item["path"])
    staged_roots = set(staged_root_kinds)
    expected_roots = set(archive_paths)
    if expected_roots & staged_roots:
        raise HandlerFailure(
            "BYOX repair projected output overlaps a staged root",
            kind="unsafe_archive_projection",
            retryable=False,
        )
    if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY"):
        raise HandlerFailure(
            "BYOX repair validation requires no-follow descriptor support",
            kind="unsafe_archive_projection",
            retryable=False,
        )
    directory_flags = (
        os.O_RDONLY
        | os.O_DIRECTORY
        | os.O_NOFOLLOW
        | getattr(os, "O_CLOEXEC", 0)
    )
    try:
        workspace_name = safe_relative(workspace.name).as_posix()
        if "/" in workspace_name:
            raise WorkspaceError("workspace name is not one component")
        parent_descriptor = os.open(workspace.parent, directory_flags)
    except (OSError, WorkspaceError) as error:
        raise HandlerFailure(
            "BYOX repair workspace parent cannot be safely opened",
            kind="unsafe_archive_projection",
            retryable=False,
        ) from error
    workspace_descriptor = -1
    snapshot_descriptor = -1
    snapshot_name: str | None = None
    retired_name: str | None = None
    cutover_complete = False
    try:
        try:
            workspace_descriptor = os.open(
                workspace_name,
                directory_flags,
                dir_fd=parent_descriptor,
            )
        except OSError as error:
            raise HandlerFailure(
                "BYOX repair workspace cannot be safely opened",
                kind="unsafe_archive_projection",
                retryable=False,
            ) from error
        maximum_workspace_roots = (
            len(expected_roots)
            + len(staged_roots)
            + BYOX_REPAIR_QUARANTINE_MAX_ROOTS
        )
        actual_roots = _enumerate_byox_repair_roots(
            workspace_descriptor,
            directory_flags,
            maximum_roots=maximum_workspace_roots,
        )
        quarantined_paths = sorted(
            actual_roots - expected_roots - staged_roots
        )
        missing = sorted(expected_roots - actual_roots)
        if missing:
            raise HandlerFailure(
                "BYOX repair omitted declared output roots: "
                + ", ".join(missing),
                kind="unsafe_archive_projection",
                retryable=False,
            )
        # factory-isolated binds the allocated workspace directory object, not
        # its host parent.  A descendant retaining that mount or an open fd can
        # continue touching only the object renamed to ``retired_name`` below;
        # it cannot resolve this sibling or the fresh object installed at the
        # old host path.  The retained-source-fd regression exercises the same
        # inode boundary without relying on permission bits as isolation.
        snapshot_name = _create_byox_repair_private_directory(
            parent_descriptor, ".repair-cutover-"
        )
        snapshot_descriptor = os.open(
            snapshot_name,
            directory_flags,
            dir_fd=parent_descriptor,
        )
        cutover_limits = {
            "max_entries": BYOX_REPAIR_CUTOVER_MAX_ENTRIES,
            "max_total_bytes": BYOX_REPAIR_CUTOVER_MAX_TOTAL_BYTES,
            "max_file_bytes": BYOX_REPAIR_CUTOVER_MAX_FILE_BYTES,
            "max_depth": BYOX_REPAIR_CUTOVER_MAX_DEPTH,
        }
        source_root_identity = os.fstat(workspace_descriptor)
        destination_root_identity = os.fstat(snapshot_descriptor)
        source_scan = _ByoxRepairCutoverSourceScan(
            source_device=source_root_identity.st_dev,
            source_identities={
                (source_root_identity.st_dev, source_root_identity.st_ino)
            },
            destination_identities={
                (
                    destination_root_identity.st_dev,
                    destination_root_identity.st_ino,
                )
            },
        )
        for name in sorted(expected_roots):
            _copy_byox_repair_authoritative_entry(
                workspace_descriptor,
                snapshot_descriptor,
                name,
                name,
                depth=1,
                expected_kind=root_kinds.get(name),
                state=source_scan,
                limits=cutover_limits,
            )
        for name in sorted(staged_roots):
            _copy_byox_repair_authoritative_entry(
                workspace_descriptor,
                snapshot_descriptor,
                name,
                name,
                depth=1,
                expected_kind=staged_root_kinds[name],
                state=source_scan,
                limits=cutover_limits,
            )
        record = _capture_byox_repair_quarantine(
            workspace_descriptor,
            quarantined_paths,
            source_scan=source_scan,
            cutover_limits=cutover_limits,
        )
        copied_roots = _enumerate_byox_repair_roots(
            snapshot_descriptor,
            directory_flags,
            maximum_roots=len(expected_roots) + len(staged_roots),
        )
        if copied_roots != expected_roots | staged_roots:
            raise HandlerFailure(
                "BYOX repair authoritative snapshot has inconsistent roots",
                kind="unsafe_archive_projection",
                retryable=False,
            )
        snapshot_path = workspace.parent / snapshot_name
        _verify_byox_repair_staged_bindings(snapshot_path, staged_bindings)
        _verify_byox_repair_staged_root_manifests(
            snapshot_path,
            staged_bindings,
            BYOX_REPAIR_CUTOVER_MAX_ENTRIES,
        )
        selected_checksum = _byox_repair_selected_tree_sha256(
            snapshot_path, archive_paths, BYOX_REPAIR_CUTOVER_MAX_ENTRIES
        )
        validation_checksum = tree_sha256(snapshot_path)
        cutover_body = {
            "schema_version": 1,
            "policy": BYOX_REPAIR_CUTOVER_POLICY,
            "classification": "factory-authoritative-validation-snapshot",
            "source_disposition": "retired-and-discarded",
            "quarantine_evidence_scope": "capture-time-retired-source-only",
            "quarantine_manifest_sha256": record["manifest_sha256"],
            "archive_paths": list(archive_paths),
            "archive_paths_sha256": selection.get("paths_sha256"),
            "snapshot_roots": sorted(expected_roots | staged_roots),
            "staged_inputs": staged_bindings,
            "limits": cutover_limits,
            "validation_snapshot_checksum_algorithm": "tree-sha256-v2",
            "validation_snapshot_checksum": validation_checksum,
            "selected_output_checksum_algorithm": "tree-sha256-v2",
            "selected_output_checksum": selected_checksum,
        }
        cutover_record = {
            **cutover_body,
            "manifest_sha256": hashlib.sha256(
                canonical_json(cutover_body).encode("utf-8")
            ).hexdigest(),
        }
        os.fsync(snapshot_descriptor)
        retired_name = _unused_byox_repair_private_name(
            parent_descriptor, ".repair-retired-"
        )
        try:
            os.rename(
                workspace_name,
                retired_name,
                src_dir_fd=parent_descriptor,
                dst_dir_fd=parent_descriptor,
            )
            try:
                os.rename(
                    snapshot_name,
                    workspace_name,
                    src_dir_fd=parent_descriptor,
                    dst_dir_fd=parent_descriptor,
                )
            except OSError as cutover_error:
                try:
                    os.rename(
                        retired_name,
                        workspace_name,
                        src_dir_fd=parent_descriptor,
                        dst_dir_fd=parent_descriptor,
                    )
                except OSError as rollback_error:
                    cutover_error.add_note(
                        f"workspace cutover rollback also failed: {rollback_error}"
                    )
                raise
            snapshot_name = None
            os.fsync(parent_descriptor)
        except OSError as error:
            raise HandlerFailure(
                "BYOX repair authoritative workspace cutover failed",
                kind="unsafe_archive_projection",
                retryable=False,
            ) from error
        try:
            replacement = os.stat(
                workspace_name, dir_fd=parent_descriptor, follow_symlinks=False
            )
            snapshot_identity = os.fstat(snapshot_descriptor)
            if (
                not stat.S_ISDIR(replacement.st_mode)
                or (replacement.st_dev, replacement.st_ino)
                != (snapshot_identity.st_dev, snapshot_identity.st_ino)
                or tree_sha256(workspace) != validation_checksum
                or _byox_repair_selected_tree_sha256(
                    workspace, archive_paths, BYOX_REPAIR_CUTOVER_MAX_ENTRIES
                )
                != selected_checksum
            ):
                raise HandlerFailure(
                    "BYOX repair authoritative cutover identity is inconsistent",
                    kind="unsafe_archive_projection",
                    retryable=False,
                )
        except BaseException as error:
            failed_snapshot_name = _unused_byox_repair_private_name(
                parent_descriptor, ".repair-failed-cutover-"
            )
            try:
                os.rename(
                    workspace_name,
                    failed_snapshot_name,
                    src_dir_fd=parent_descriptor,
                    dst_dir_fd=parent_descriptor,
                )
                os.rename(
                    retired_name,
                    workspace_name,
                    src_dir_fd=parent_descriptor,
                    dst_dir_fd=parent_descriptor,
                )
                os.fsync(parent_descriptor)
                snapshot_name = failed_snapshot_name
                retired_name = None
            except OSError as rollback_error:
                error.add_note(
                    f"post-cutover verification rollback also failed: {rollback_error}"
                )
            raise
        cutover_complete = True
        selection["quarantined_outputs"] = record
        selection["authoritative_cutover"] = cutover_record
    except HandlerFailure:
        raise
    except (OSError, WorkspaceError, ValueError) as error:
        raise HandlerFailure(
            "BYOX repair authoritative snapshot operation failed",
            kind="unsafe_archive_projection",
            retryable=False,
        ) from error
    finally:
        if snapshot_descriptor >= 0:
            os.close(snapshot_descriptor)
        if workspace_descriptor >= 0:
            os.close(workspace_descriptor)
        if cutover_complete and retired_name is not None:
            _discard_byox_repair_private_tree(parent_descriptor, retired_name)
            retired_name = None
        if snapshot_name is not None:
            _discard_byox_repair_private_tree(parent_descriptor, snapshot_name)
        os.close(parent_descriptor)
    return record


def _cutover_byox_validation_workspace(workspace: Path) -> dict[str, Any]:
    """Install a fresh-inode BYOX tree as the validation/archive authority.

    A Codex process can retain a descriptor or bind mount for its original
    workspace after its direct child exits.  Hashing that live object before
    validation cannot bind later archive reads.  Copy the complete candidate
    through held no-follow descriptors, atomically replace the host pathname,
    and discard the retired object.  Retained worker handles then address only
    the unlinked source while validators and the archiver share this replacement
    tree and its recorded checksum.

    The copy need not represent one instantaneous view of a concurrently
    changing source.  It *becomes* the authoritative candidate at cutover; its
    fresh inodes and checksum are the stable boundary used by the controller.
    """

    from .byox_remediation import (
        BYOX_REPAIR_CUTOVER_MAX_ENTRIES,
        BYOX_REPAIR_CUTOVER_MAX_FILE_BYTES,
        BYOX_REPAIR_CUTOVER_MAX_TOTAL_BYTES,
        BYOX_REPAIR_CUTOVER_POLICY,
    )
    from .validation import BYOX_TREE_MAX_DEPTH

    if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY"):
        raise HandlerFailure(
            "BYOX validation cutover requires no-follow descriptor support",
            kind="unsafe_archive_projection",
            retryable=False,
        )
    directory_flags = (
        os.O_RDONLY
        | os.O_DIRECTORY
        | os.O_NOFOLLOW
        | getattr(os, "O_CLOEXEC", 0)
    )
    try:
        workspace_name = safe_relative(workspace.name).as_posix()
        if "/" in workspace_name:
            raise WorkspaceError("workspace name is not one component")
        parent_descriptor = _open_byox_absolute_directory(workspace.parent)
    except (OSError, WorkspaceError) as error:
        raise HandlerFailure(
            "BYOX workspace parent cannot be safely opened",
            kind="unsafe_archive_projection",
            retryable=False,
        ) from error

    workspace_descriptor = -1
    snapshot_descriptor = -1
    snapshot_name: str | None = None
    retired_name: str | None = None
    cutover_complete = False
    try:
        try:
            workspace_descriptor = os.open(
                workspace_name,
                directory_flags,
                dir_fd=parent_descriptor,
            )
        except OSError as error:
            raise HandlerFailure(
                "BYOX workspace cannot be safely opened",
                kind="unsafe_archive_projection",
                retryable=False,
            ) from error
        roots = _enumerate_byox_repair_roots(
            workspace_descriptor,
            directory_flags,
            maximum_roots=BYOX_REPAIR_CUTOVER_MAX_ENTRIES,
        )
        snapshot_name = _create_byox_repair_private_directory(
            parent_descriptor, ".byox-cutover-"
        )
        snapshot_descriptor = os.open(
            snapshot_name,
            directory_flags,
            dir_fd=parent_descriptor,
        )
        # Whole-workspace depth includes the top-level root itself.  The public
        # structural policies measure descendants below that root.
        limits = {
            "max_entries": BYOX_REPAIR_CUTOVER_MAX_ENTRIES,
            "max_total_bytes": BYOX_REPAIR_CUTOVER_MAX_TOTAL_BYTES,
            "max_file_bytes": BYOX_REPAIR_CUTOVER_MAX_FILE_BYTES,
            "max_depth": BYOX_TREE_MAX_DEPTH + 1,
            "max_file_depth": BYOX_TREE_MAX_DEPTH + 2,
            "policy_root_max_directory_depth": BYOX_TREE_MAX_DEPTH,
        }
        source_root_identity = os.fstat(workspace_descriptor)
        destination_root_identity = os.fstat(snapshot_descriptor)
        source_scan = _ByoxRepairCutoverSourceScan(
            source_device=source_root_identity.st_dev,
            source_identities={
                (source_root_identity.st_dev, source_root_identity.st_ino)
            },
            destination_identities={
                (
                    destination_root_identity.st_dev,
                    destination_root_identity.st_ino,
                )
            },
        )
        for name in sorted(roots):
            _copy_byox_repair_authoritative_entry(
                workspace_descriptor,
                snapshot_descriptor,
                name,
                name,
                depth=1,
                expected_kind=None,
                state=source_scan,
                limits=limits,
            )
        copied_roots = _enumerate_byox_repair_roots(
            snapshot_descriptor,
            directory_flags,
            maximum_roots=len(roots) + 1,
        )
        if copied_roots != roots:
            raise HandlerFailure(
                "BYOX validation snapshot has inconsistent roots",
                kind="unsafe_archive_projection",
                retryable=False,
            )
        snapshot_path = workspace.parent / snapshot_name
        validation_checksum = tree_sha256(snapshot_path)
        body = {
            "schema_version": 1,
            "policy": BYOX_REPAIR_CUTOVER_POLICY,
            "classification": "factory-authoritative-validation-snapshot",
            "source_disposition": "retired-and-discarded",
            "archive_paths": None,
            "snapshot_roots": sorted(roots),
            "limits": limits,
            "summary": {
                "entries": source_scan.entry_count,
                "files": source_scan.file_count,
                "directories": source_scan.directory_count,
                "total_bytes": source_scan.total_bytes,
                "max_depth": source_scan.max_depth,
            },
            "validation_snapshot_checksum_algorithm": "tree-sha256-v2",
            "validation_snapshot_checksum": validation_checksum,
            "selected_output_checksum_algorithm": "tree-sha256-v2",
            "selected_output_checksum": validation_checksum,
        }
        record = {
            **body,
            "manifest_sha256": hashlib.sha256(
                canonical_json(body).encode("utf-8")
            ).hexdigest(),
        }
        os.fsync(snapshot_descriptor)
        retired_name = _unused_byox_repair_private_name(
            parent_descriptor, ".byox-retired-"
        )
        try:
            os.rename(
                workspace_name,
                retired_name,
                src_dir_fd=parent_descriptor,
                dst_dir_fd=parent_descriptor,
            )
            try:
                os.rename(
                    snapshot_name,
                    workspace_name,
                    src_dir_fd=parent_descriptor,
                    dst_dir_fd=parent_descriptor,
                )
            except OSError as cutover_error:
                try:
                    os.rename(
                        retired_name,
                        workspace_name,
                        src_dir_fd=parent_descriptor,
                        dst_dir_fd=parent_descriptor,
                    )
                except OSError as rollback_error:
                    cutover_error.add_note(
                        f"workspace cutover rollback also failed: {rollback_error}"
                    )
                raise
            snapshot_name = None
            os.fsync(parent_descriptor)
        except OSError as error:
            raise HandlerFailure(
                "BYOX authoritative workspace cutover failed",
                kind="unsafe_archive_projection",
                retryable=False,
            ) from error
        try:
            replacement = os.stat(
                workspace_name,
                dir_fd=parent_descriptor,
                follow_symlinks=False,
            )
            snapshot_identity = os.fstat(snapshot_descriptor)
            if (
                not stat.S_ISDIR(replacement.st_mode)
                or (replacement.st_dev, replacement.st_ino)
                != (snapshot_identity.st_dev, snapshot_identity.st_ino)
                or tree_sha256(workspace) != validation_checksum
            ):
                raise HandlerFailure(
                    "BYOX authoritative cutover identity is inconsistent",
                    kind="unsafe_archive_projection",
                    retryable=False,
                )
        except BaseException as error:
            failed_snapshot_name = _unused_byox_repair_private_name(
                parent_descriptor, ".byox-failed-cutover-"
            )
            try:
                os.rename(
                    workspace_name,
                    failed_snapshot_name,
                    src_dir_fd=parent_descriptor,
                    dst_dir_fd=parent_descriptor,
                )
                os.rename(
                    retired_name,
                    workspace_name,
                    src_dir_fd=parent_descriptor,
                    dst_dir_fd=parent_descriptor,
                )
                os.fsync(parent_descriptor)
                snapshot_name = failed_snapshot_name
                retired_name = None
            except OSError as rollback_error:
                error.add_note(
                    f"post-cutover verification rollback also failed: {rollback_error}"
                )
            raise
        cutover_complete = True
    except HandlerFailure:
        raise
    except (OSError, WorkspaceError, ValueError) as error:
        raise HandlerFailure(
            "BYOX authoritative snapshot operation failed",
            kind="unsafe_archive_projection",
            retryable=False,
        ) from error
    finally:
        if snapshot_descriptor >= 0:
            os.close(snapshot_descriptor)
        if workspace_descriptor >= 0:
            os.close(workspace_descriptor)
        if cutover_complete and retired_name is not None:
            _discard_byox_repair_private_tree(parent_descriptor, retired_name)
            retired_name = None
        if snapshot_name is not None:
            _discard_byox_repair_private_tree(parent_descriptor, snapshot_name)
        os.close(parent_descriptor)
    return record


def _open_byox_absolute_directory(path: Path) -> int:
    """Open a canonical absolute directory without following any component."""

    absolute = Path(os.path.abspath(path))
    if path != absolute or not absolute.is_absolute():
        raise WorkspaceError("BYOX directory path is not canonical and absolute")
    flags = (
        os.O_RDONLY
        | os.O_DIRECTORY
        | os.O_NOFOLLOW
        | getattr(os, "O_CLOEXEC", 0)
    )
    try:
        current = os.open(Path(absolute.anchor), flags)
    except OSError as error:
        raise WorkspaceError("BYOX directory root is unreadable") from error
    try:
        for part in absolute.parts[1:]:
            expected = os.stat(part, dir_fd=current, follow_symlinks=False)
            if stat.S_ISLNK(expected.st_mode) or not stat.S_ISDIR(expected.st_mode):
                raise WorkspaceError("BYOX directory has an unsafe path component")
            child = os.open(part, flags, dir_fd=current)
            try:
                actual = os.fstat(child)
            except BaseException:
                os.close(child)
                raise
            if _byox_repair_stat_fingerprint(expected) != (
                _byox_repair_stat_fingerprint(actual)
            ):
                os.close(child)
                raise WorkspaceError("BYOX directory component changed while opening")
            os.close(current)
            current = child
        return current
    except BaseException:
        os.close(current)
        raise


def _enumerate_byox_repair_roots(
    workspace_descriptor: int,
    directory_flags: int,
    *,
    maximum_roots: int,
) -> set[str]:
    """Enumerate one held workspace through a fresh descriptor offset."""

    try:
        scan_descriptor = os.open(
            ".", directory_flags, dir_fd=workspace_descriptor
        )
    except OSError as error:
        raise HandlerFailure(
            "cannot open BYOX repair workspace for root enumeration",
            kind="unsafe_archive_projection",
            retryable=False,
        ) from error
    try:
        actual_roots: set[str] = set()
        normalized_roots: set[str] = set()
        with os.scandir(scan_descriptor) as iterator:
            for entry in iterator:
                relative = safe_relative(entry.name)
                name = relative.as_posix()
                normalized = _byox_repair_security_name_key(name)
                if len(relative.parts) != 1 or normalized in normalized_roots:
                    raise HandlerFailure(
                        "BYOX repair produced an unsafe or case-colliding root",
                        kind="unsafe_archive_projection",
                        retryable=False,
                    )
                if len(actual_roots) >= maximum_roots:
                    raise HandlerFailure(
                        "BYOX repair workspace exceeds its bounded root count",
                        kind="unsafe_archive_projection",
                        retryable=False,
                    )
                normalized_roots.add(normalized)
                actual_roots.add(name)
        return actual_roots
    except HandlerFailure:
        raise
    except OSError as error:
        raise HandlerFailure(
            f"cannot enumerate BYOX repair outputs: {error}",
            kind="unsafe_archive_projection",
            retryable=False,
        ) from error
    finally:
        os.close(scan_descriptor)


@dataclass
class _ByoxRepairCutoverSourceScan:
    entry_count: int = 0
    file_count: int = 0
    directory_count: int = 0
    total_bytes: int = 0
    max_depth: int = 0
    source_device: int | None = None
    source_identities: set[tuple[int, int]] = field(default_factory=set)
    destination_identities: set[tuple[int, int]] = field(default_factory=set)


def _copy_byox_repair_authoritative_entry(
    source_parent_descriptor: int,
    destination_parent_descriptor: int,
    name: str,
    relative: str,
    *,
    depth: int,
    expected_kind: object | None,
    state: _ByoxRepairCutoverSourceScan,
    limits: dict[str, int],
) -> None:
    """Copy one source entry to a fresh inode through held descriptors."""

    _validate_byox_repair_copy_name(name)
    # A regular file beneath the deepest accepted directory is one path
    # component deeper.  Generic BYOX cutover declares that separate bound;
    # legacy repair callers retain their prior single-bound behavior.
    maximum_entry_depth = limits.get("max_file_depth", limits["max_depth"])
    if depth > maximum_entry_depth:
        raise HandlerFailure(
            "BYOX repair authoritative snapshot exceeds maximum depth",
            kind="unsafe_archive_projection",
            retryable=False,
        )
    source_flags = (
        os.O_RDONLY
        | os.O_NOFOLLOW
        | getattr(os, "O_NONBLOCK", 0)
        | getattr(os, "O_CLOEXEC", 0)
    )
    try:
        source_descriptor = os.open(
            name, source_flags, dir_fd=source_parent_descriptor
        )
    except OSError as error:
        raise HandlerFailure(
            "BYOX repair source entry is unsafe or unreadable",
            kind="unsafe_archive_projection",
            retryable=False,
        ) from error
    try:
        before = os.fstat(source_descriptor)
        if stat.S_ISDIR(before.st_mode) and depth > limits["max_depth"]:
            raise HandlerFailure(
                "BYOX repair authoritative snapshot exceeds maximum depth",
                kind="unsafe_archive_projection",
                retryable=False,
            )
        _register_byox_repair_source_entry(
            before, depth=depth, state=state, limits=limits
        )
        source_fingerprint = _byox_repair_stat_fingerprint(before)
        if stat.S_ISREG(before.st_mode):
            if expected_kind not in (None, "file"):
                raise HandlerFailure(
                    "BYOX repair source root has the wrong kind",
                    kind="unsafe_archive_projection",
                    retryable=False,
                )
            _copy_byox_repair_authoritative_file(
                source_descriptor,
                destination_parent_descriptor,
                name,
                before,
                state=state,
                limits=limits,
            )
            return
        if not stat.S_ISDIR(before.st_mode) or expected_kind not in (
            None,
            "directory",
        ):
            raise HandlerFailure(
                "BYOX repair source contains a special or type-invalid entry",
                kind="unsafe_archive_projection",
                retryable=False,
            )
        try:
            os.mkdir(name, mode=0o700, dir_fd=destination_parent_descriptor)
            destination_descriptor = os.open(
                name,
                os.O_RDONLY
                | os.O_DIRECTORY
                | os.O_NOFOLLOW
                | getattr(os, "O_CLOEXEC", 0),
                dir_fd=destination_parent_descriptor,
            )
        except OSError as error:
            raise HandlerFailure(
                "BYOX repair cannot create its private directory snapshot",
                kind="unsafe_archive_projection",
                retryable=False,
            ) from error
        try:
            _register_byox_repair_destination_entry(
                os.fstat(destination_descriptor), state
            )
            children: list[str] = []
            try:
                with os.scandir(source_descriptor) as iterator:
                    for item in iterator:
                        _validate_byox_repair_copy_name(item.name)
                        children.append(item.name)
                        if (
                            state.entry_count + len(children)
                            > limits["max_entries"]
                        ):
                            raise HandlerFailure(
                                "BYOX repair authoritative snapshot exceeds "
                                "maximum entries",
                                kind="unsafe_archive_projection",
                                retryable=False,
                            )
            except HandlerFailure:
                raise
            except OSError as error:
                raise HandlerFailure(
                    "BYOX repair source directory is unreadable",
                    kind="unsafe_archive_projection",
                    retryable=False,
                ) from error
            for child in sorted(children):
                _copy_byox_repair_authoritative_entry(
                    source_descriptor,
                    destination_descriptor,
                    child,
                    f"{relative}/{child}",
                    depth=depth + 1,
                    expected_kind=None,
                    state=state,
                    limits=limits,
                )
            if source_fingerprint != _byox_repair_stat_fingerprint(
                os.fstat(source_descriptor)
            ):
                raise HandlerFailure(
                    "BYOX repair source directory changed during cutover",
                    kind="unsafe_archive_projection",
                    retryable=False,
                )
            os.fchmod(destination_descriptor, stat.S_IMODE(before.st_mode))
            os.fsync(destination_descriptor)
            copied = os.fstat(destination_descriptor)
            if (
                not stat.S_ISDIR(copied.st_mode)
                or stat.S_IMODE(copied.st_mode) != stat.S_IMODE(before.st_mode)
            ):
                raise HandlerFailure(
                    "BYOX repair directory snapshot is inconsistent",
                    kind="unsafe_archive_projection",
                    retryable=False,
                )
        finally:
            os.close(destination_descriptor)
    finally:
        os.close(source_descriptor)


def _copy_byox_repair_authoritative_file(
    source_descriptor: int,
    destination_parent_descriptor: int,
    name: str,
    before: os.stat_result,
    *,
    state: _ByoxRepairCutoverSourceScan,
    limits: dict[str, int],
) -> None:
    try:
        destination_descriptor = os.open(
            name,
            os.O_RDWR
            | os.O_CREAT
            | os.O_EXCL
            | os.O_NOFOLLOW
            | getattr(os, "O_CLOEXEC", 0),
            0o600,
            dir_fd=destination_parent_descriptor,
        )
    except OSError as error:
        raise HandlerFailure(
            "BYOX repair cannot create its private file snapshot",
            kind="unsafe_archive_projection",
            retryable=False,
        ) from error
    try:
        _register_byox_repair_destination_entry(
            os.fstat(destination_descriptor), state
        )
        source_digest = hashlib.sha256()
        observed_size = 0
        while True:
            remaining = limits["max_file_bytes"] + 1 - observed_size
            chunk = os.read(source_descriptor, min(1024 * 1024, remaining))
            if not chunk:
                break
            observed_size += len(chunk)
            if observed_size > limits["max_file_bytes"]:
                raise HandlerFailure(
                    "BYOX repair source file exceeds the cutover bound",
                    kind="unsafe_archive_projection",
                    retryable=False,
                )
            source_digest.update(chunk)
            view = memoryview(chunk)
            while view:
                written = os.write(destination_descriptor, view)
                if written <= 0:
                    raise OSError("short write while creating repair snapshot")
                view = view[written:]
        after = os.fstat(source_descriptor)
        if (
            observed_size != before.st_size
            or _byox_repair_stat_fingerprint(before)
            != _byox_repair_stat_fingerprint(after)
        ):
            raise HandlerFailure(
                "BYOX repair source file changed during cutover",
                kind="unsafe_archive_projection",
                retryable=False,
            )
        os.fchmod(destination_descriptor, stat.S_IMODE(before.st_mode))
        os.fsync(destination_descriptor)
        copied = os.fstat(destination_descriptor)
        if (
            not stat.S_ISREG(copied.st_mode)
            or copied.st_nlink != 1
            or copied.st_size != observed_size
            or stat.S_IMODE(copied.st_mode) != stat.S_IMODE(before.st_mode)
        ):
            raise HandlerFailure(
                "BYOX repair file snapshot is inconsistent",
                kind="unsafe_archive_projection",
                retryable=False,
            )
        os.lseek(destination_descriptor, 0, os.SEEK_SET)
        copied_digest = hashlib.sha256()
        while True:
            chunk = os.read(destination_descriptor, 1024 * 1024)
            if not chunk:
                break
            copied_digest.update(chunk)
        if copied_digest.digest() != source_digest.digest():
            raise HandlerFailure(
                "BYOX repair file snapshot bytes are inconsistent",
                kind="unsafe_archive_projection",
                retryable=False,
            )
    finally:
        os.close(destination_descriptor)


def _register_byox_repair_source_entry(
    value: os.stat_result,
    *,
    depth: int,
    state: _ByoxRepairCutoverSourceScan,
    limits: dict[str, int],
) -> None:
    if state.entry_count >= limits["max_entries"]:
        raise HandlerFailure(
            "BYOX repair authoritative snapshot exceeds maximum entries",
            kind="unsafe_archive_projection",
            retryable=False,
        )
    identity = (value.st_dev, value.st_ino)
    if value.st_dev != state.source_device or identity in state.source_identities:
        raise HandlerFailure(
            "BYOX repair source crosses a filesystem or repeats an inode across "
            "trust boundaries",
            kind="unsafe_archive_projection",
            retryable=False,
        )
    if stat.S_ISREG(value.st_mode):
        if value.st_nlink != 1:
            raise HandlerFailure(
                "BYOX repair source contains a multi-linked file",
                kind="unsafe_archive_projection",
                retryable=False,
            )
        if value.st_size > limits["max_file_bytes"]:
            raise HandlerFailure(
                "BYOX repair source file exceeds the cutover bound",
                kind="unsafe_archive_projection",
                retryable=False,
            )
        if state.total_bytes + value.st_size > limits["max_total_bytes"]:
            raise HandlerFailure(
                "BYOX repair source exceeds the cutover byte bound",
                kind="unsafe_archive_projection",
                retryable=False,
            )
        state.file_count += 1
        state.total_bytes += value.st_size
    elif stat.S_ISDIR(value.st_mode):
        state.directory_count += 1
    state.source_identities.add(identity)
    state.entry_count += 1
    state.max_depth = max(state.max_depth, depth)


def _register_byox_repair_destination_entry(
    value: os.stat_result, state: _ByoxRepairCutoverSourceScan
) -> None:
    identity = (value.st_dev, value.st_ino)
    if identity in state.destination_identities:
        raise HandlerFailure(
            "BYOX repair snapshot repeats a destination inode",
            kind="unsafe_archive_projection",
            retryable=False,
        )
    state.destination_identities.add(identity)


def _validate_byox_repair_copy_name(name: object) -> None:
    if not isinstance(name, str) or not name or name in {".", ".."} or "/" in name:
        raise HandlerFailure(
            "BYOX repair source contains an unsafe name",
            kind="unsafe_archive_projection",
            retryable=False,
        )
    try:
        name.encode("utf-8")
    except UnicodeEncodeError as error:
        raise HandlerFailure(
            "BYOX repair source contains a non-UTF-8 name",
            kind="unsafe_archive_projection",
            retryable=False,
        ) from error


def _verify_byox_repair_staged_bindings(
    snapshot: Path, bindings: list[dict[str, str]]
) -> None:
    for binding in bindings:
        path = snapshot / safe_relative(binding["path"])
        try:
            if binding["kind"] == "file":
                valid_kind = path.is_file() and not path.is_symlink()
                actual = file_sha256(path) if valid_kind else None
            else:
                valid_kind = path.is_dir() and not path.is_symlink()
                actual = tree_sha256(path) if valid_kind else None
        except OSError as error:
            raise HandlerFailure(
                "BYOX repair staged snapshot cannot be verified",
                kind="unsafe_archive_projection",
                retryable=False,
            ) from error
        if not valid_kind or actual != binding["checksum"]:
            raise HandlerFailure(
                "BYOX repair staged snapshot checksum is inconsistent",
                kind="unsafe_archive_projection",
                retryable=False,
            )


def _verify_byox_repair_staged_root_manifests(
    snapshot: Path,
    bindings: list[dict[str, str]],
    maximum_entries: int,
) -> None:
    """Reject worker-added material beneath partially staged root directories."""

    grouped: dict[str, list[dict[str, str]]] = {}
    for binding in bindings:
        relative = safe_relative(binding["path"])
        grouped.setdefault(relative.parts[0], []).append(binding)
    observed_entries = 0
    for root_name, records in grouped.items():
        if any(record["path"] == root_name for record in records):
            # A direct file checksum or complete tree checksum already binds all
            # content reachable through this root.
            continue
        root = snapshot / root_name
        exact_paths = {root_name}
        covered_directories: set[str] = set()
        for record in records:
            relative = safe_relative(record["path"])
            for length in range(1, len(relative.parts) + 1):
                exact_paths.add(Path(*relative.parts[:length]).as_posix())
            if record["kind"] == "directory":
                covered_directories.add(relative.as_posix())
        candidates: list[Path] = [root]
        if root.is_dir() and not root.is_symlink():
            for child in root.rglob("*"):
                candidates.append(child)
                observed_entries += 1
                if observed_entries > maximum_entries:
                    raise HandlerFailure(
                        "BYOX repair staged manifest exceeds maximum entries",
                        kind="unsafe_archive_projection",
                        retryable=False,
                    )
        for candidate in candidates:
            rendered = candidate.relative_to(snapshot).as_posix()
            if rendered in exact_paths or any(
                rendered.startswith(directory + "/")
                for directory in covered_directories
            ):
                continue
            raise HandlerFailure(
                "BYOX repair staged root contains an unbound entry",
                kind="unsafe_archive_projection",
                retryable=False,
            )


def _byox_repair_selected_tree_sha256(
    snapshot: Path, archive_paths: tuple[str, ...], maximum_entries: int
) -> str:
    """Hash selected roots exactly as a projected tree, without copying again."""

    entries: list[Path] = []
    for raw in archive_paths:
        root = snapshot / safe_relative(raw)
        entries.append(root)
        if len(entries) > maximum_entries:
            raise HandlerFailure(
                "BYOX repair selected snapshot exceeds maximum entries",
                kind="unsafe_archive_projection",
                retryable=False,
            )
        if root.is_dir() and not root.is_symlink():
            for child in root.rglob("*"):
                entries.append(child)
                if len(entries) > maximum_entries:
                    raise HandlerFailure(
                        "BYOX repair selected snapshot exceeds maximum entries",
                        kind="unsafe_archive_projection",
                        retryable=False,
                    )
    digest = hashlib.sha256()
    digest.update(b"learnfactory-tree-sha256-v2\0")
    for path in sorted(entries, key=lambda item: item.relative_to(snapshot).as_posix()):
        relative = path.relative_to(snapshot).as_posix().encode("utf-8")
        if path.is_symlink():
            raise HandlerFailure(
                "BYOX repair selected snapshot contains a symlink",
                kind="unsafe_archive_projection",
                retryable=False,
            )
        if path.is_file():
            value = path.stat()
            if value.st_nlink != 1:
                raise HandlerFailure(
                    "BYOX repair selected snapshot contains a multi-linked file",
                    kind="unsafe_archive_projection",
                    retryable=False,
                )
            digest.update(b"F")
            _byox_repair_hash_field(digest, relative)
            _byox_repair_hash_field(
                digest, (value.st_mode & 0o777).to_bytes(4, "big")
            )
            _byox_repair_hash_field(
                digest, bytes.fromhex(file_sha256(path))
            )
        elif path.is_dir():
            digest.update(b"D")
            _byox_repair_hash_field(digest, relative)
        else:
            raise HandlerFailure(
                "BYOX repair selected snapshot contains a special file",
                kind="unsafe_archive_projection",
                retryable=False,
            )
    return digest.hexdigest()


def _byox_repair_hash_field(digest: Any, value: bytes) -> None:
    digest.update(len(value).to_bytes(8, "big"))
    digest.update(value)


def _create_byox_repair_private_directory(
    parent_descriptor: int, prefix: str
) -> str:
    for _ in range(32):
        name = prefix + secrets.token_hex(16)
        try:
            os.mkdir(name, mode=0o700, dir_fd=parent_descriptor)
            return name
        except FileExistsError:
            continue
        except OSError as error:
            raise HandlerFailure(
                "cannot create BYOX repair private cutover directory",
                kind="unsafe_archive_projection",
                retryable=False,
            ) from error
    raise HandlerFailure(
        "cannot allocate a unique BYOX repair cutover directory",
        kind="unsafe_archive_projection",
        retryable=False,
    )


def _unused_byox_repair_private_name(
    parent_descriptor: int, prefix: str
) -> str:
    for _ in range(32):
        name = prefix + secrets.token_hex(16)
        try:
            os.stat(name, dir_fd=parent_descriptor, follow_symlinks=False)
        except FileNotFoundError:
            return name
        except OSError as error:
            raise HandlerFailure(
                "cannot reserve BYOX repair private cutover name",
                kind="unsafe_archive_projection",
                retryable=False,
            ) from error
    raise HandlerFailure(
        "cannot reserve a unique BYOX repair cutover name",
        kind="unsafe_archive_projection",
        retryable=False,
    )


def _discard_byox_repair_private_tree(
    parent_descriptor: int, name: str
) -> None:
    try:
        value = os.stat(name, dir_fd=parent_descriptor, follow_symlinks=False)
        if not stat.S_ISDIR(value.st_mode) or not shutil.rmtree.avoids_symlink_attacks:
            raise OSError("private cutover target is not an fd-safe directory")
        directory_flags = (
            os.O_RDONLY
            | os.O_DIRECTORY
            | os.O_NOFOLLOW
            | getattr(os, "O_CLOEXEC", 0)
        )
        descriptor = os.open(name, directory_flags, dir_fd=parent_descriptor)
        try:
            _make_byox_repair_tree_discardable(
                descriptor, directory_flags, remaining=[200_000]
            )
        finally:
            os.close(descriptor)
        shutil.rmtree(name, dir_fd=parent_descriptor)
    except FileNotFoundError:
        return
    except OSError as error:
        raise HandlerFailure(
            "cannot safely discard BYOX repair private source tree",
            kind="unsafe_archive_projection",
            retryable=False,
        ) from error


def _make_byox_repair_tree_discardable(
    descriptor: int, directory_flags: int, *, remaining: list[int]
) -> None:
    """Restore owner directory access before fd-safe removal of staged trees."""

    children: list[str] = []
    with os.scandir(descriptor) as iterator:
        for item in iterator:
            remaining[0] -= 1
            if remaining[0] < 0:
                raise OSError("private cutover cleanup exceeds its entry bound")
            children.append(item.name)
    for name in children:
        value = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
        if not stat.S_ISDIR(value.st_mode):
            continue
        child_descriptor = os.open(name, directory_flags, dir_fd=descriptor)
        try:
            _make_byox_repair_tree_discardable(
                child_descriptor, directory_flags, remaining=remaining
            )
            os.fchmod(child_descriptor, stat.S_IMODE(value.st_mode) | 0o700)
        finally:
            os.close(child_descriptor)
    current = os.fstat(descriptor)
    os.fchmod(descriptor, stat.S_IMODE(current.st_mode) | 0o700)


@dataclass
class _ByoxRepairQuarantineScan:
    entries: list[dict[str, Any]] = field(default_factory=list)
    entry_count: int = 0
    file_count: int = 0
    directory_count: int = 0
    total_bytes: int = 0
    max_depth: int = 0


def _capture_byox_repair_quarantine(
    workspace_descriptor: int,
    quarantined_paths: list[str],
    *,
    source_scan: _ByoxRepairCutoverSourceScan,
    cutover_limits: dict[str, int],
) -> dict[str, Any]:
    """Capture excluded roots through no-follow descriptors under hard bounds."""

    from .byox_remediation import (
        BYOX_REPAIR_CONTROL_ROOTS,
        BYOX_REPAIR_QUARANTINE_FORBIDDEN_NAMES,
        BYOX_REPAIR_QUARANTINE_MAX_DEPTH,
        BYOX_REPAIR_QUARANTINE_MAX_ENTRIES,
        BYOX_REPAIR_QUARANTINE_MAX_FILE_BYTES,
        BYOX_REPAIR_QUARANTINE_MAX_FILES,
        BYOX_REPAIR_QUARANTINE_MAX_ROOTS,
        BYOX_REPAIR_QUARANTINE_MAX_TOTAL_BYTES,
        BYOX_REPAIR_QUARANTINE_POLICY,
    )

    limits = {
        "max_roots": BYOX_REPAIR_QUARANTINE_MAX_ROOTS,
        "max_entries": BYOX_REPAIR_QUARANTINE_MAX_ENTRIES,
        "max_files": BYOX_REPAIR_QUARANTINE_MAX_FILES,
        "max_total_bytes": BYOX_REPAIR_QUARANTINE_MAX_TOTAL_BYTES,
        "max_file_bytes": BYOX_REPAIR_QUARANTINE_MAX_FILE_BYTES,
        "max_depth": BYOX_REPAIR_QUARANTINE_MAX_DEPTH,
    }
    if (
        quarantined_paths != sorted(set(quarantined_paths))
        or len(quarantined_paths) > limits["max_roots"]
    ):
        raise HandlerFailure(
            "BYOX repair quarantine has too many or duplicate roots",
            kind="unsafe_archive_projection",
            retryable=False,
        )
    forbidden_names = {
        value.casefold()
        for value in (
            set(BYOX_REPAIR_CONTROL_ROOTS)
            | set(BYOX_REPAIR_QUARANTINE_FORBIDDEN_NAMES)
        )
    }
    state = _ByoxRepairQuarantineScan()
    for name in quarantined_paths:
        _capture_byox_repair_quarantine_entry(
            workspace_descriptor,
            name,
            name,
            depth=1,
            state=state,
            limits=limits,
            forbidden_names=forbidden_names,
            source_scan=source_scan,
            cutover_limits=cutover_limits,
        )

    entries = sorted(state.entries, key=lambda item: str(item["path"]))
    body = {
        "schema_version": 1,
        "policy": BYOX_REPAIR_QUARANTINE_POLICY,
        "classification": "excluded-non-artifact-quarantine",
        "excluded_from_archive_projection": True,
        "evidence_scope": "capture-time-retired-source-only",
        "limits": limits,
        "roots": quarantined_paths,
        "entries": entries,
        "summary": {
            "roots": len(quarantined_paths),
            "entries": state.entry_count,
            "files": state.file_count,
            "directories": state.directory_count,
            "total_bytes": state.total_bytes,
            "max_depth": state.max_depth,
        },
    }
    return {
        **body,
        "manifest_sha256": hashlib.sha256(
            canonical_json(body).encode("utf-8")
        ).hexdigest(),
    }


def _capture_byox_repair_quarantine_entry(
    parent_descriptor: int,
    name: str,
    relative: str,
    *,
    depth: int,
    state: _ByoxRepairQuarantineScan,
    limits: dict[str, int],
    forbidden_names: set[str],
    source_scan: _ByoxRepairCutoverSourceScan,
    cutover_limits: dict[str, int],
) -> None:
    _validate_byox_repair_quarantine_name(name, forbidden_names)
    if depth > limits["max_depth"]:
        raise HandlerFailure(
            "BYOX repair quarantine exceeds maximum depth",
            kind="unsafe_archive_projection",
            retryable=False,
        )
    if state.entry_count >= limits["max_entries"]:
        raise HandlerFailure(
            "BYOX repair quarantine exceeds maximum entries",
            kind="unsafe_archive_projection",
            retryable=False,
        )
    flags = (
        os.O_RDONLY
        | os.O_NOFOLLOW
        | getattr(os, "O_NONBLOCK", 0)
        | getattr(os, "O_CLOEXEC", 0)
    )
    try:
        descriptor = os.open(name, flags, dir_fd=parent_descriptor)
    except OSError as error:
        raise HandlerFailure(
            "BYOX repair quarantine entry is unsafe or unreadable",
            kind="unsafe_archive_projection",
            retryable=False,
        ) from error
    try:
        before = os.fstat(descriptor)
        _register_byox_repair_source_entry(
            before,
            depth=depth,
            state=source_scan,
            limits=cutover_limits,
        )
        state.entry_count += 1
        state.max_depth = max(state.max_depth, depth)
        if stat.S_ISREG(before.st_mode):
            if before.st_nlink != 1:
                raise HandlerFailure(
                    "BYOX repair quarantine contains a multi-linked file",
                    kind="unsafe_archive_projection",
                    retryable=False,
                )
            _capture_byox_repair_quarantine_file(
                descriptor, before, relative, state=state, limits=limits
            )
            return
        if not stat.S_ISDIR(before.st_mode):
            raise HandlerFailure(
                "BYOX repair quarantine contains a special file",
                kind="unsafe_archive_projection",
                retryable=False,
            )
        state.directory_count += 1
        state.entries.append(
            {
                "path": relative,
                "kind": "directory",
                "mode": stat.S_IMODE(before.st_mode),
            }
        )
        children: list[str] = []
        folded_children: set[str] = set()
        try:
            with os.scandir(descriptor) as iterator:
                for item in iterator:
                    child = item.name
                    _validate_byox_repair_quarantine_name(
                        child, forbidden_names
                    )
                    folded = _byox_repair_security_name_key(child)
                    if folded in folded_children:
                        raise HandlerFailure(
                            "BYOX repair quarantine contains case-colliding names",
                            kind="unsafe_archive_projection",
                            retryable=False,
                        )
                    folded_children.add(folded)
                    children.append(child)
                    if state.entry_count + len(children) > limits["max_entries"]:
                        raise HandlerFailure(
                            "BYOX repair quarantine exceeds maximum entries",
                            kind="unsafe_archive_projection",
                            retryable=False,
                        )
        except HandlerFailure:
            raise
        except OSError as error:
            raise HandlerFailure(
                "BYOX repair quarantine directory is unreadable",
                kind="unsafe_archive_projection",
                retryable=False,
            ) from error
        for child in sorted(children):
            _capture_byox_repair_quarantine_entry(
                descriptor,
                child,
                f"{relative}/{child}",
                depth=depth + 1,
                state=state,
                limits=limits,
                forbidden_names=forbidden_names,
                source_scan=source_scan,
                cutover_limits=cutover_limits,
            )
        after = os.fstat(descriptor)
        if _byox_repair_stat_fingerprint(before) != _byox_repair_stat_fingerprint(
            after
        ):
            raise HandlerFailure(
                "BYOX repair quarantine directory changed during capture",
                kind="unsafe_archive_projection",
                retryable=False,
            )
    finally:
        os.close(descriptor)


def _capture_byox_repair_quarantine_file(
    descriptor: int,
    before: os.stat_result,
    relative: str,
    *,
    state: _ByoxRepairQuarantineScan,
    limits: dict[str, int],
) -> None:
    if before.st_size > limits["max_file_bytes"]:
        raise HandlerFailure(
            "BYOX repair quarantine file exceeds per-file bytes",
            kind="unsafe_archive_projection",
            retryable=False,
        )
    if state.file_count >= limits["max_files"]:
        raise HandlerFailure(
            "BYOX repair quarantine exceeds maximum files",
            kind="unsafe_archive_projection",
            retryable=False,
        )
    if state.total_bytes + before.st_size > limits["max_total_bytes"]:
        raise HandlerFailure(
            "BYOX repair quarantine exceeds maximum total bytes",
            kind="unsafe_archive_projection",
            retryable=False,
        )
    digest = hashlib.sha256()
    observed_size = 0
    while True:
        remaining = limits["max_file_bytes"] + 1 - observed_size
        chunk = os.read(descriptor, min(64 * 1024, remaining))
        if not chunk:
            break
        observed_size += len(chunk)
        if observed_size > limits["max_file_bytes"]:
            raise HandlerFailure(
                "BYOX repair quarantine file exceeds per-file bytes",
                kind="unsafe_archive_projection",
                retryable=False,
            )
        digest.update(chunk)
    after = os.fstat(descriptor)
    if (
        observed_size != before.st_size
        or _byox_repair_stat_fingerprint(before)
        != _byox_repair_stat_fingerprint(after)
    ):
        raise HandlerFailure(
            "BYOX repair quarantine file changed during capture",
            kind="unsafe_archive_projection",
            retryable=False,
        )
    state.file_count += 1
    state.total_bytes += observed_size
    state.entries.append(
        {
            "path": relative,
            "kind": "regular-file",
            "mode": stat.S_IMODE(before.st_mode),
            "size_bytes": observed_size,
            "checksum_algorithm": "file-sha256",
            "checksum": digest.hexdigest(),
        }
    )


def _validate_byox_repair_quarantine_name(
    name: object, forbidden_names: set[str]
) -> None:
    folded = _byox_repair_security_name_key(name)
    assert isinstance(name, str)
    tokens = {
        token for token in re.split(r"[^a-z0-9]+", folded) if token
    }
    if (
        not name
        or name in {".", ".."}
        or "/" in name
        or name.startswith(".")
        or folded in forbidden_names
        or tokens & forbidden_names
    ):
        raise HandlerFailure(
            "BYOX repair quarantine contains a forbidden or sensitive name",
            kind="unsafe_archive_projection",
            retryable=False,
        )


def _byox_repair_security_name_key(name: object) -> str:
    """Return a collision key, rejecting invisible and confusable Unicode."""

    if not isinstance(name, str):
        raise HandlerFailure(
            "BYOX repair quarantine contains a non-text name",
            kind="unsafe_archive_projection",
            retryable=False,
        )
    try:
        encoded = name.encode("ascii")
    except UnicodeEncodeError as error:
        raise HandlerFailure(
            "BYOX repair quarantine names must be ASCII",
            kind="unsafe_archive_projection",
            retryable=False,
        ) from error
    if len(encoded) > 255 or any(
        ord(character) < 32 or ord(character) == 127 for character in name
    ):
        raise HandlerFailure(
            "BYOX repair quarantine contains an unsafe name",
            kind="unsafe_archive_projection",
            retryable=False,
        )
    return name.casefold()


def _byox_repair_stat_fingerprint(value: os.stat_result) -> tuple[int, ...]:
    return (
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_nlink,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
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
        _enforce_mass_seed_backend(job, self.settings)
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
        artifact_type = str(job.payload.get("artifact_type", "codex-output"))
        validators = list(job.payload.get("validators", []))
        if not validators:
            raise HandlerFailure(
                "Codex task lacks an external validator", kind="permanent", retryable=False
            )
        validators = _with_byox_runtime_safety_validators(job, validators)
        has_byox_structural_gate = any(
            specification.get("type") == "byox_code_presence"
            for specification in validators
            if isinstance(specification, dict)
        )
        seed_policy = job.payload.get("seed_policy")
        is_backend_capability_gate = bool(
            artifact_type == "backend-capability-gate"
            and isinstance(seed_policy, dict)
            and seed_policy.get("kind") == "codex_backend_gate"
        )
        repair_quarantined_outputs = None
        validation_cutover: dict[str, Any] | None = None
        if repair_archive_paths is not None and repair_projection is not None:
            repair_quarantined_outputs = _validate_byox_repair_outputs(
                workspace,
                repair_archive_paths,
                repair_projection,
                staged_input_provenance,
            )
            cutover_candidate = repair_projection.get("authoritative_cutover")
            if not isinstance(cutover_candidate, dict):
                raise HandlerFailure(
                    "BYOX repair cutover evidence is missing",
                    kind="unsafe_archive_projection",
                    retryable=False,
                )
            validation_cutover = cutover_candidate
        elif has_byox_structural_gate or is_backend_capability_gate:
            validation_cutover = _cutover_byox_validation_workspace(workspace)
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
                **(
                    {
                        "repair_projection_quarantined_outputs":
                            repair_quarantined_outputs,
                        "repair_projection_authoritative_cutover":
                            repair_projection.get("authoritative_cutover"),
                    }
                    if repair_quarantined_outputs is not None
                    else {}
                ),
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
                **(
                    {
                        (
                            "byox_validation_cutover"
                            if has_byox_structural_gate
                            else "authoritative_validation_cutover"
                        ): validation_cutover
                    }
                    if validation_cutover is not None
                    else {}
                ),
            },
            result,
            backend.name,
            on_publish=publication.on_publish if publication is not None else None,
            publication_scope=(
                PublicationScope.LEARNER_EVIDENCE
                if publication is not None
                else None
            ),
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
            publication_scope=PublicationScope.SOURCE_INGESTION,
        )
