from __future__ import annotations

import hashlib
import json
import math
import os
import re
import signal
import stat
import subprocess
import threading
import time
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from .db import Database
from .retained_logs import (
    DEFAULT_STREAM_LIMIT_BYTES,
    BoundedBinaryCapture,
    CaptureError,
)
from .util import canonical_json, file_sha256, new_id, now, redact, tree_sha256
from .workspace import WorkspaceError, contained, fresh_inode_evidence, safe_relative


VALIDATION_LABELS = {
    "BUILDS",
    "TESTED",
    "FUZZED",
    "BENCHMARKED",
    "REVIEWED",
    "TRANSFER_VERIFIED",
    "PRODUCTIONIZED",
    "PARTIAL",
}


# This is deliberately an explicit, conservative structural allowlist.  It is
# not a language parser and therefore cannot prove correctness, but it prevents
# prose-only BYOX packs from being promoted as code-bearing artifacts.  Build
# descriptors are recognized separately for evidence but cannot stand in for
# implementation or test source.
_BYOX_SOURCE_EXTENSIONS = frozenset(
    {
        ".adb", ".ads", ".agda", ".als", ".asm", ".bash", ".bat",
        ".c", ".cc", ".cbl", ".cl", ".clj", ".cljc", ".cljs", ".cmd",
        ".cob", ".cpp", ".cr", ".cs", ".css", ".cu", ".cuh", ".cxx",
        ".dart", ".dats", ".elm", ".erl", ".ex", ".exs", ".f", ".fish", ".f90",
        ".f95", ".forth", ".fs", ".fsx", ".go", ".groovy",
        ".h", ".hats", ".hh", ".hpp", ".hrl", ".hs", ".html", ".hxx", ".idr",
        ".java", ".jl", ".js", ".jsx", ".kt", ".kts", ".l", ".lean",
        ".lex", ".lhs", ".lisp", ".lua", ".m", ".mjs", ".ml", ".mli",
        ".mm", ".nim", ".nix", ".odin", ".pas", ".php", ".pl", ".pm",
        ".pony", ".pp", ".proto", ".ps1", ".py", ".pyi", ".r", ".rb",
        ".rkt", ".rs", ".s", ".sats", ".scala", ".scm", ".sh", ".sol", ".sql",
        ".svelte", ".sv", ".swift", ".t", ".tcl", ".tf", ".thrift",
        ".thy", ".ts", ".tsx", ".vala", ".v", ".vhd", ".vhdl", ".vue",
        ".wat", ".zig",
    }
)
_BYOX_TEST_ONLY_EXTENSIONS = frozenset({".bats", ".feature", ".spec"})
_BYOX_TEST_BASENAMES = frozenset(
    {
        "check", "runtests", "run-tests", "run_tests", "test", "testrunner",
        "test-runner", "test_runner", "tests", "verify",
    }
)
_BYOX_BUILD_BASENAMES = frozenset(
    {
        "build", "build.bazel", "build.gradle", "build.gradle.kts", "build.xml",
        "cargo.toml", "cmakelists.txt", "dockerfile", "gemfile",
        "go.mod", "gnumakefile", "justfile", "makefile", "meson.build",
        "mix.exs", "package.json", "pom.xml", "pyproject.toml", "rakefile",
        "rebar.config", "setup.py", "workspace", "workspace.bazel",
    }
)
_BYOX_CODE_ROOT_GROUPS = (
    ("reference_implementation", ("sealed/reference",)),
    ("learner_starter", ("starter",)),
    ("tests", ("public_tests", "sealed/reference_tests")),
)
_BYOX_CODE_MAX_ENTRIES = 20_000
_BYOX_CODE_MAX_FILES = 10_000
_BYOX_CODE_MAX_TOTAL_BYTES = 256 * 1024 * 1024
_BYOX_CODE_MAX_FILE_BYTES = 32 * 1024 * 1024
_BYOX_CODE_MAX_EVIDENCE_PATHS = 50
# Directory depth is measured below each declared traversal root.  A directory
# exactly at this depth is accepted; discovering another child directory fails
# closed before it is queued or reopened.
BYOX_TREE_MAX_DEPTH = 100
_BYOX_CODE_POLICY_VERSION = 2
_BYOX_CODE_MANIFEST_VERSION = 1


def _reject_json_constant(value: str) -> object:
    raise ValueError(f"non-standard JSON numeric constant: {value}")


@dataclass(frozen=True)
class ValidationResult:
    name: str
    status: str
    evidence: dict[str, Any]
    command: list[str] | None = None
    exit_code: int | None = None
    stdout_path: Path | None = None
    stderr_path: Path | None = None
    kind: str | None = None
    claims: tuple[str, ...] = ()

    @property
    def passed(self) -> bool:
        return self.status == "PASS"


@dataclass(frozen=True)
class ByoxCodeManifestEntry:
    """One immutable filesystem observation used by the BYOX structural gate."""

    path: str
    kind: str
    mode: int = 0
    size_bytes: int = 0
    sha256: str | None = None
    reason: str | None = None


@dataclass(frozen=True)
class ByoxCodeManifest:
    """A bounded immutable input to the pure BYOX structural policy."""

    entries: tuple[ByoxCodeManifestEntry, ...]
    scope: str
    capture_limit_failure: str | None = None
    version: int = _BYOX_CODE_MANIFEST_VERSION


class Validator:
    def __init__(
        self, db: Database, *, log_limit_bytes: int = DEFAULT_STREAM_LIMIT_BYTES
    ):
        self.db = db
        self.log_limit_bytes = log_limit_bytes

    def run(
        self,
        job_id: str,
        workspace: Path,
        specifications: list[dict[str, Any]],
        log_dir: Path,
        *,
        attempt_number: int | None = None,
        cancel_event: threading.Event | None = None,
    ) -> list[ValidationResult]:
        with self.db.connect() as connection:
            row = connection.execute(
                "SELECT attempt_count,payload_json FROM jobs WHERE job_id=?", (job_id,)
            ).fetchone()
        if row is None:
            raise ValueError(f"cannot validate unknown job: {job_id}")
        if attempt_number is None:
            attempt_number = int(row["attempt_count"])
        try:
            job_payload = json.loads(str(row["payload_json"]))
        except (TypeError, ValueError, json.JSONDecodeError):
            job_payload = {}
        policy = job_payload.get("seed_policy") if isinstance(job_payload, dict) else None
        is_byox_review = bool(
            isinstance(job_payload, dict)
            and (
                job_payload.get("artifact_type") == "byox-independent-review"
                or (
                    isinstance(policy, dict)
                    and policy.get("kind") == "byox_reference_review"
                )
            )
        )
        results: list[ValidationResult] = []
        for index, spec in enumerate(specifications, start=1):
            kind = spec.get("type")
            name = str(spec.get("name") or f"{kind}-{index}")
            started = now()
            tracks_mutations = kind == "command" or (
                kind == "review_acceptance" and spec.get("mode") == "command"
            )
            before = _tree_manifest(workspace) if tracks_mutations else None
            try:
                if kind == "required_paths":
                    result = self._required_paths(name, workspace, spec)
                elif kind == "forbidden_paths":
                    result = self._forbidden_paths(name, workspace, spec)
                elif kind == "json_fields":
                    result = self._json_fields(name, workspace, spec)
                elif kind == "json_schema":
                    result = self._json_schema(name, workspace, spec)
                elif kind == "review_verdict":
                    result = self._review_verdict(name, workspace, spec)
                elif kind == "review_acceptance":
                    result = self._review_acceptance(
                        name, workspace, spec, log_dir, index, cancel_event
                    )
                elif kind == "command":
                    result = self._command(
                        name, workspace, spec, log_dir, index, cancel_event
                    )
                elif kind == "tree_checksum":
                    result = ValidationResult(name, "PASS", {"sha256": tree_sha256(workspace)})
                elif kind == "input_integrity":
                    result = self._input_integrity(name, workspace, spec)
                elif kind == "regular_files":
                    result = self._regular_files(name, workspace, spec)
                elif kind == "byox_code_presence":
                    result = self._byox_code_presence(name, workspace, spec)
                elif kind == "forbidden_tree_names":
                    result = self._forbidden_tree_names(name, workspace, spec)
                elif kind == "allowed_root_paths":
                    result = self._allowed_root_paths(name, workspace, spec)
                elif kind == "handler_evidence":
                    passed = bool(spec.get("passed"))
                    result = ValidationResult(
                        name, "PASS" if passed else "FAIL", dict(spec.get("evidence", {}))
                    )
                else:
                    result = ValidationResult(name, "ERROR", {"error": f"unknown validator: {kind}"})
            except Exception as error:  # validator errors are evidence, not controller crashes
                result = ValidationResult(name, "ERROR", {"error": redact(str(error))})
            after = _tree_manifest(workspace) if tracks_mutations else None
            changed = (
                sorted(
                    path
                    for path in before.keys() | after.keys()
                    if before.get(path) != after.get(path)
                )
                if before is not None and after is not None
                else []
            )
            mutation_error = _unexpected_mutations(changed, spec)
            if mutation_error:
                result = ValidationResult(
                    name,
                    "FAIL",
                    {
                        "error": mutation_error,
                        "changed_paths": changed[:100],
                        "changed_count": len(changed),
                    },
                    result.command,
                    result.exit_code,
                    result.stdout_path,
                    result.stderr_path,
                )
            elif changed:
                result = replace(
                    result,
                    evidence={**result.evidence, "declared_output_changes": changed},
                )
            # review_acceptance interprets its declared claim as authorization to
            # emit only after its command passes; never merge that declaration as
            # if it were evidence by itself.
            raw_claims = (
                spec.get("claims", [])
                if result.passed and kind != "review_acceptance"
                else []
            )
            if not isinstance(raw_claims, list):
                raw_claims = []
            claim_values = (*result.claims, *raw_claims) if result.passed else ()
            claims = tuple(
                dict.fromkeys(
                    label for label in (str(value).upper() for value in claim_values)
                    if label in VALIDATION_LABELS
                    and not (
                        label == "REVIEWED"
                        and (
                            kind == "review_verdict"
                            or (is_byox_review and kind != "review_acceptance")
                        )
                    )
                )
            )
            result = replace(result, kind=str(kind), claims=claims)
            self._record(job_id, attempt_number, result, started, now())
            results.append(result)
            if not result.passed and bool(spec.get("fail_fast", True)):
                break
        return results

    def _required_paths(self, name: str, workspace: Path, spec: dict[str, Any]) -> ValidationResult:
        missing: list[str] = []
        for raw in spec.get("paths", []):
            path = workspace / safe_relative(str(raw))
            if not contained(workspace, path) or not path.exists():
                missing.append(str(raw))
        return ValidationResult(
            name, "PASS" if not missing else "FAIL", {"missing": missing, "checked": spec.get("paths", [])}
        )

    def _forbidden_paths(self, name: str, workspace: Path, spec: dict[str, Any]) -> ValidationResult:
        present: list[str] = []
        for raw in spec.get("paths", []):
            path = workspace / safe_relative(str(raw))
            if path.exists() or path.is_symlink():
                present.append(str(raw))
        return ValidationResult(
            name, "PASS" if not present else "FAIL", {"present": present, "checked": spec.get("paths", [])}
        )

    def _input_integrity(
        self, name: str, workspace: Path, spec: dict[str, Any]
    ) -> ValidationResult:
        records = spec.get("inputs")
        if not isinstance(records, list) or not records or len(records) > 10_000:
            return ValidationResult(
                name, "ERROR", {"error": "inputs must be a nonempty bounded array"}
            )
        checked: list[str] = []
        mismatches: list[dict[str, str]] = []
        seen: set[str] = set()
        require_fresh_inodes = spec.get("require_fresh_inodes", False)
        if not isinstance(require_fresh_inodes, bool):
            return ValidationResult(
                name, "ERROR", {"error": "require_fresh_inodes must be boolean"}
            )
        for record in records:
            if not isinstance(record, dict):
                return ValidationResult(
                    name, "ERROR", {"error": "input integrity record must be an object"}
                )
            try:
                relative = safe_relative(str(record["path"]))
            except (KeyError, ValueError, TypeError) as error:
                return ValidationResult(name, "ERROR", {"error": str(error)})
            rendered = relative.as_posix()
            if rendered in seen:
                return ValidationResult(
                    name, "ERROR", {"error": f"duplicate input path: {rendered}"}
                )
            seen.add(rendered)
            checked.append(rendered)
            algorithm = record.get("checksum_algorithm")
            expected = record.get("checksum")
            kind = record.get("kind")
            if (
                algorithm not in {"file-sha256", "tree-sha256-v2"}
                or not isinstance(expected, str)
                or len(expected) != 64
                or any(character not in "0123456789abcdef" for character in expected)
                or kind not in {"file", "directory"}
            ):
                return ValidationResult(
                    name,
                    "ERROR",
                    {"error": f"invalid input integrity record: {rendered}"},
                )
            path = workspace / relative
            if not contained(workspace, path) or path.is_symlink():
                mismatches.append({"path": rendered, "reason": "missing-or-symlink"})
                continue
            if algorithm == "file-sha256":
                if kind != "file" or not path.is_file():
                    mismatches.append({"path": rendered, "reason": "wrong-kind"})
                    continue
                actual = file_sha256(path)
            else:
                if kind != "directory" or not path.is_dir():
                    mismatches.append({"path": rendered, "reason": "wrong-kind"})
                    continue
                actual = tree_sha256(path)
            if actual != expected:
                mismatches.append({"path": rendered, "reason": "checksum-mismatch"})
                continue
            inode_fields = (
                "fresh_inode_policy",
                "root_device",
                "root_inode",
                "root_change_time_ns",
                "regular_file_count",
                "inode_manifest_sha256",
            )
            has_inode_evidence = any(field in record for field in inode_fields)
            if require_fresh_inodes and not has_inode_evidence:
                mismatches.append(
                    {"path": rendered, "reason": "fresh-inode-evidence-missing"}
                )
                continue
            if has_inode_evidence:
                if (
                    record.get("fresh_inode_policy")
                    != "regular-files-nlink-one-unique-v1"
                    or not isinstance(record.get("root_device"), int)
                    or isinstance(record.get("root_device"), bool)
                    or not isinstance(record.get("root_inode"), int)
                    or isinstance(record.get("root_inode"), bool)
                    or not isinstance(record.get("root_change_time_ns"), int)
                    or isinstance(record.get("root_change_time_ns"), bool)
                    or not isinstance(record.get("regular_file_count"), int)
                    or isinstance(record.get("regular_file_count"), bool)
                    or not isinstance(record.get("inode_manifest_sha256"), str)
                    or len(record.get("inode_manifest_sha256", "")) != 64
                    or any(
                        character not in "0123456789abcdef"
                        for character in record.get("inode_manifest_sha256", "")
                    )
                ):
                    return ValidationResult(
                        name,
                        "ERROR",
                        {"error": f"invalid fresh inode evidence: {rendered}"},
                    )
                try:
                    inode_evidence = fresh_inode_evidence(path)
                except (OSError, WorkspaceError):
                    mismatches.append(
                        {"path": rendered, "reason": "fresh-inode-policy-failed"}
                    )
                    continue
                if any(
                    inode_evidence.get(field) != record.get(field)
                    for field in inode_fields
                ):
                    mismatches.append(
                        {"path": rendered, "reason": "inode-identity-mismatch"}
                    )
        return ValidationResult(
            name,
            "PASS" if not mismatches else "FAIL",
            {"checked": checked, "mismatches": mismatches},
        )

    def _allowed_root_paths(
        self, name: str, workspace: Path, spec: dict[str, Any]
    ) -> ValidationResult:
        """Require every workspace root to belong to an exact structural set."""

        raw_paths = spec.get("paths")
        if not isinstance(raw_paths, list) or not raw_paths:
            return ValidationResult(
                name, "ERROR", {"error": "paths must be a nonempty array"}
            )
        allowed: set[str] = set()
        try:
            for raw in raw_paths:
                if not isinstance(raw, str):
                    raise WorkspaceError("allowed root must be a string")
                relative = safe_relative(raw)
                if len(relative.parts) != 1:
                    raise WorkspaceError("allowed root must have one path component")
                allowed.add(relative.as_posix())
        except WorkspaceError as error:
            return ValidationResult(name, "ERROR", {"error": str(error)})
        if len(allowed) != len(raw_paths):
            return ValidationResult(
                name, "ERROR", {"error": "allowed root paths must be unique"}
            )
        try:
            observed = sorted(path.name for path in workspace.iterdir())
        except OSError as error:
            return ValidationResult(
                name, "ERROR", {"error": f"cannot enumerate workspace: {error}"}
            )
        unexpected = sorted(set(observed) - allowed)
        return ValidationResult(
            name,
            "PASS" if not unexpected else "FAIL",
            {
                "allowed": sorted(allowed),
                "observed": observed,
                "unexpected": unexpected,
            },
        )

    def _regular_files(
        self, name: str, workspace: Path, spec: dict[str, Any]
    ) -> ValidationResult:
        raw_paths = spec.get("paths")
        minimum_bytes = spec.get("minimum_bytes", 1)
        if (
            not isinstance(raw_paths, list)
            or not raw_paths
            or isinstance(minimum_bytes, bool)
            or not isinstance(minimum_bytes, int)
            or minimum_bytes < 0
        ):
            return ValidationResult(name, "ERROR", {"error": "invalid regular-files spec"})
        failures: list[dict[str, str]] = []
        checked: list[str] = []
        for raw in raw_paths:
            relative = safe_relative(str(raw))
            rendered = relative.as_posix()
            checked.append(rendered)
            path = workspace / relative
            if (
                not contained(workspace, path)
                or path.is_symlink()
                or not path.is_file()
            ):
                failures.append({"path": rendered, "reason": "not-regular-file"})
            elif path.stat().st_size < minimum_bytes:
                failures.append({"path": rendered, "reason": "too-small"})
        return ValidationResult(
            name,
            "PASS" if not failures else "FAIL",
            {"checked": checked, "minimum_bytes": minimum_bytes, "failures": failures},
        )

    @staticmethod
    def _byox_code_presence(
        name: str, workspace: Path, spec: dict[str, Any]
    ) -> ValidationResult:
        """Require bounded code-bearing trees in a generic BYOX challenge pack.

        This gate intentionally proves only structural code presence.  It never
        emits BUILDS or TESTED; executable validators remain responsible for
        those stronger claims.  Filesystem capture and policy evaluation are
        separate so archive maintenance can evaluate an immutable checksum-bound
        manifest instead of a path that can change during the gate.
        """
        manifest = capture_byox_code_manifest(workspace)
        return evaluate_byox_code_manifest(manifest, spec, name=name)

    def _forbidden_tree_names(
        self, name: str, workspace: Path, spec: dict[str, Any]
    ) -> ValidationResult:
        raw_roots = spec.get("roots")
        raw_names = spec.get("names")
        max_entries = spec.get("max_entries", _BYOX_CODE_MAX_ENTRIES)
        if (
            not isinstance(raw_roots, list)
            or not raw_roots
            or not isinstance(raw_names, list)
            or not raw_names
            or isinstance(max_entries, bool)
            or not isinstance(max_entries, int)
            or not 0 < max_entries <= _BYOX_CODE_MAX_ENTRIES
        ):
            return ValidationResult(name, "ERROR", {"error": "invalid forbidden-tree-names spec"})
        forbidden = {
            str(value).strip().casefold()
            for value in raw_names
            if isinstance(value, str) and value.strip()
        }
        if not forbidden:
            return ValidationResult(name, "ERROR", {"error": "forbidden names are empty"})
        present: list[str] = []
        unsafe: list[dict[str, str]] = []
        checked_roots: list[str] = []
        entry_count = 0
        limit_failure: str | None = None
        try:
            workspace_descriptor = _open_workspace_directory(workspace)
        except _DirectoryBoundaryError as error:
            return ValidationResult(
                name,
                "FAIL",
                {
                    "roots": [safe_relative(str(raw)).as_posix() for raw in raw_roots],
                    "forbidden": sorted(forbidden),
                    "max_entries": max_entries,
                    "entry_count": 0,
                    "present": ["workspace (missing-or-unsafe-root)"],
                    "present_truncated": 0,
                    "unsafe_entries": [
                        {"path": ".", "reason": f"unsafe-workspace:{error.reason}"}
                    ],
                    "unsafe_entries_truncated": 0,
                    "limit_failure": None,
                },
            )
        try:
            # The try/finally begins before the first fstat so even an injected
            # metadata failure cannot leak the opened workspace descriptor.
            workspace_before = os.fstat(workspace_descriptor)
            for raw in raw_roots:
                root_relative = safe_relative(str(raw))
                rendered_root = root_relative.as_posix()
                root_parts = tuple(root_relative.parts)
                checked_roots.append(rendered_root)
                try:
                    root_descriptor = _open_relative_directory(
                        workspace_descriptor, root_parts
                    )
                except _DirectoryBoundaryError as error:
                    present.append(f"{rendered_root} (missing-or-unsafe-root)")
                    if error.reason != "missing":
                        unsafe.append(
                            {
                                "path": rendered_root,
                                "reason": f"unsafe-root:{error.reason}",
                            }
                        )
                    continue
                try:
                    root_expected = os.fstat(root_descriptor)
                finally:
                    os.close(root_descriptor)
                pending: list[tuple[tuple[str, ...], os.stat_result]] = [
                    (root_parts, root_expected)
                ]
                while pending and limit_failure is None:
                    directory_parts, expected = pending.pop()
                    depth = len(directory_parts) - len(root_parts)
                    if depth > BYOX_TREE_MAX_DEPTH:
                        limit_failure = "max_depth_exceeded"
                        break
                    rendered_directory = "/".join(directory_parts)
                    try:
                        directory_descriptor = _open_relative_directory(
                            workspace_descriptor,
                            directory_parts,
                            expected=expected,
                        )
                    except _DirectoryBoundaryError as error:
                        unsafe.append(
                            {
                                "path": rendered_directory,
                                "reason": f"unsafe-directory:{error.reason}",
                            }
                        )
                        continue
                    try:
                        # Enter cleanup before the initial fstat.
                        before = os.fstat(directory_descriptor)
                        try:
                            with os.scandir(directory_descriptor) as entries:
                                entry_names: list[str] = []
                                for entry in entries:
                                    entry_names.append(entry.name)
                                    if entry_count + len(entry_names) > max_entries:
                                        entry_count += len(entry_names)
                                        limit_failure = "max_entries_exceeded"
                                        break
                        except OSError as error:
                            unsafe.append(
                                {
                                    "path": rendered_directory,
                                    "reason": (
                                        "unreadable-directory:"
                                        f"{error.__class__.__name__}"
                                    ),
                                }
                            )
                            continue
                        if limit_failure is not None:
                            break
                        entry_names.sort()
                        child_directories: list[
                            tuple[tuple[str, ...], os.stat_result]
                        ] = []
                        for entry_name in entry_names:
                            entry_count += 1
                            if entry_count > max_entries:
                                limit_failure = "max_entries_exceeded"
                                break
                            child_parts = (*directory_parts, entry_name)
                            relative = "/".join(child_parts)
                            try:
                                metadata = os.stat(
                                    entry_name,
                                    dir_fd=directory_descriptor,
                                    follow_symlinks=False,
                                )
                            except OSError as error:
                                unsafe.append(
                                    {
                                        "path": relative,
                                        "reason": (
                                            "unreadable-entry:"
                                            f"{error.__class__.__name__}"
                                        ),
                                    }
                                )
                                continue
                            mode = metadata.st_mode
                            if stat.S_ISLNK(mode):
                                unsafe.append({"path": relative, "reason": "symlink"})
                                continue
                            folded = entry_name.casefold()
                            tokens = {
                                token
                                for token in re.split(r"[^a-z0-9]+", folded)
                                if token
                            }
                            if folded in forbidden or tokens & forbidden:
                                present.append(relative)
                            if stat.S_ISDIR(mode):
                                if depth >= BYOX_TREE_MAX_DEPTH:
                                    limit_failure = "max_depth_exceeded"
                                    break
                                child_directories.append((child_parts, metadata))
                            elif not stat.S_ISREG(mode):
                                unsafe.append(
                                    {"path": relative, "reason": "special-file"}
                                )
                            else:
                                if metadata.st_nlink != 1:
                                    unsafe.append(
                                        {"path": relative, "reason": "hardlink"}
                                    )
                        pending.extend(reversed(child_directories))
                        after = os.fstat(directory_descriptor)
                        if not _same_stat_snapshot(before, after):
                            unsafe.append(
                                {
                                    "path": rendered_directory,
                                    "reason": "directory-changed-during-capture",
                                }
                            )
                    finally:
                        os.close(directory_descriptor)
                    try:
                        rebound = _open_relative_directory(
                            workspace_descriptor,
                            directory_parts,
                            expected=before,
                        )
                    except _DirectoryBoundaryError:
                        unsafe.append(
                            {
                                "path": rendered_directory,
                                "reason": "directory-binding-changed",
                            }
                        )
                    else:
                        os.close(rebound)
                if limit_failure is not None:
                    break
            try:
                _revalidate_workspace_binding(
                    workspace,
                    workspace_descriptor,
                    workspace_before,
                )
            except (OSError, _DirectoryBoundaryError) as error:
                reason = (
                    error.reason
                    if isinstance(error, _DirectoryBoundaryError)
                    else "workspace-binding-changed"
                )
                unsafe.append(
                    {"path": ".", "reason": f"workspace-binding:{reason}"}
                )
        finally:
            os.close(workspace_descriptor)
        present.sort()
        unsafe.sort(key=lambda item: item["path"])
        return ValidationResult(
            name,
            "PASS"
            if not present and not unsafe and limit_failure is None
            else "FAIL",
            {
                "roots": checked_roots,
                "forbidden": sorted(forbidden),
                "max_entries": max_entries,
                "max_depth": BYOX_TREE_MAX_DEPTH,
                "entry_count": entry_count,
                "present": present[:200],
                "present_truncated": max(0, len(present) - 200),
                "unsafe_entries": unsafe[:_BYOX_CODE_MAX_EVIDENCE_PATHS],
                "unsafe_entries_truncated": max(
                    0, len(unsafe) - _BYOX_CODE_MAX_EVIDENCE_PATHS
                ),
                "limit_failure": limit_failure,
            },
        )

    def _json_fields(self, name: str, workspace: Path, spec: dict[str, Any]) -> ValidationResult:
        path = workspace / safe_relative(str(spec["path"]))
        if not contained(workspace, path) or not path.is_file():
            return ValidationResult(name, "FAIL", {"error": "JSON file missing", "path": str(spec["path"])})
        try:
            value = json.loads(
                path.read_text(encoding="utf-8"), parse_constant=_reject_json_constant
            )
        except (json.JSONDecodeError, ValueError) as error:
            return ValidationResult(name, "FAIL", {"error": str(error)})
        if not isinstance(value, dict):
            return ValidationResult(name, "FAIL", {"error": "JSON root must be an object"})
        missing = [field for field in spec.get("required", []) if field not in value]
        return ValidationResult(name, "PASS" if not missing else "FAIL", {"missing": missing})

    def _json_schema(
        self, name: str, workspace: Path, spec: dict[str, Any]
    ) -> ValidationResult:
        schema = spec.get("schema")
        if not isinstance(schema, dict):
            return ValidationResult(name, "ERROR", {"error": "schema must be an object"})
        contract_errors: list[str] = []
        _validate_schema_contract(schema, "$", contract_errors)
        if contract_errors:
            return ValidationResult(
                name,
                "ERROR",
                {
                    "errors": contract_errors[:50],
                    "error_count": len(contract_errors),
                },
            )
        path = workspace / safe_relative(str(spec["path"]))
        if not contained(workspace, path) or not path.is_file():
            return ValidationResult(name, "FAIL", {"error": "JSON file missing"})
        try:
            value = json.loads(
                path.read_text(encoding="utf-8"), parse_constant=_reject_json_constant
            )
        except (json.JSONDecodeError, ValueError) as error:
            return ValidationResult(name, "FAIL", {"error": str(error)})
        errors: list[str] = []
        _validate_schema_subset(value, schema, "$", errors)
        return ValidationResult(
            name,
            "PASS" if not errors else "FAIL",
            {"errors": errors[:50], "error_count": len(errors)},
        )

    def _review_verdict(
        self, name: str, workspace: Path, spec: dict[str, Any]
    ) -> ValidationResult:
        """Extract an independent-review outcome without discarding negative evidence.

        Validator PASS means the outcome was structurally and semantically recorded. It
        does not mean the reviewed candidate passed. A reviewer-authored ``PASS`` is a
        recommendation only and can never emit an authoritative validation claim.
        """

        relative = safe_relative(str(spec.get("path", "EVALUATION.json")))
        path = workspace / relative
        if (
            not contained(workspace, path)
            or path.is_symlink()
            or not path.is_file()
        ):
            return ValidationResult(
                name,
                "FAIL",
                {
                    "error": "review evaluation is missing or unsafe",
                    "path": relative.as_posix(),
                },
            )
        try:
            value = json.loads(
                path.read_text(encoding="utf-8"), parse_constant=_reject_json_constant
            )
        except (json.JSONDecodeError, ValueError) as error:
            return ValidationResult(name, "FAIL", {"error": str(error)})
        if not isinstance(value, dict):
            return ValidationResult(
                name, "FAIL", {"error": "review evaluation root must be an object"}
            )
        verdict = value.get("verdict")
        if not isinstance(verdict, str) or verdict not in {"PASS", "REVISE", "FAIL"}:
            return ValidationResult(
                name,
                "FAIL",
                {
                    "error": "review verdict must be exactly PASS, REVISE, or FAIL",
                    "verdict": verdict,
                },
            )
        return ValidationResult(
            name,
            "PASS",
            {
                "path": relative.as_posix(),
                "verdict": verdict,
                "reviewer_recommends_acceptance": verdict == "PASS",
                "workflow_accepted": False,
            },
        )

    def _review_acceptance(
        self,
        name: str,
        workspace: Path,
        spec: dict[str, Any],
        log_dir: Path,
        index: int,
        cancel_event: threading.Event | None,
    ) -> ValidationResult:
        """Apply a control-plane-owned, fail-closed independent review gate.

        ``closed`` records that no acceptance policy is installed and deliberately
        emits no claim. ``command`` may emit ``REVIEWED`` only after the reviewer
        recommended PASS and a separately configured command produced its expected
        exit code. A command rejection remains a recorded review outcome rather than
        causing the useful review artifact itself to be discarded.
        """

        mode = spec.get("mode", "closed")
        raw_claims = spec.get("claims", [])
        if mode == "closed":
            if raw_claims not in (None, []):
                return ValidationResult(
                    name,
                    "ERROR",
                    {"error": "closed review acceptance gate cannot declare claims"},
                )
            return ValidationResult(
                name,
                "PASS",
                {
                    "mode": "closed",
                    "acceptance_authority": "orchestrator",
                    "workflow_accepted": False,
                    "reason": "no independent acceptance command configured",
                },
            )
        if mode != "command":
            return ValidationResult(
                name,
                "ERROR",
                {"error": "review acceptance mode must be closed or command"},
            )
        if raw_claims != ["REVIEWED"]:
            return ValidationResult(
                name,
                "ERROR",
                {
                    "error": (
                        "command review acceptance gate must explicitly declare only "
                        "the REVIEWED claim"
                    )
                },
            )

        verdict_relative = safe_relative(
            str(spec.get("verdict_path", "EVALUATION.json"))
        )
        verdict_path = workspace / verdict_relative
        if (
            not contained(workspace, verdict_path)
            or verdict_path.is_symlink()
            or not verdict_path.is_file()
        ):
            return ValidationResult(
                name,
                "ERROR",
                {
                    "error": "review evaluation is missing or unsafe",
                    "path": verdict_relative.as_posix(),
                },
            )
        try:
            evaluation = json.loads(
                verdict_path.read_text(encoding="utf-8"),
                parse_constant=_reject_json_constant,
            )
        except (json.JSONDecodeError, ValueError) as error:
            return ValidationResult(name, "ERROR", {"error": str(error)})
        reviewer_verdict = (
            evaluation.get("verdict") if isinstance(evaluation, dict) else None
        )
        if reviewer_verdict not in {"PASS", "REVISE", "FAIL"}:
            return ValidationResult(
                name,
                "ERROR",
                {"error": "review verdict is unavailable to acceptance gate"},
            )
        if reviewer_verdict != "PASS":
            return ValidationResult(
                name,
                "PASS",
                {
                    "mode": "command",
                    "acceptance_authority": "orchestrator-captured-command",
                    "reviewer_verdict": reviewer_verdict,
                    "command_executed": False,
                    "workflow_accepted": False,
                },
            )

        command_result = self._command(
            name, workspace, spec, log_dir, index, cancel_event
        )
        if command_result.status == "ERROR":
            return replace(
                command_result,
                evidence={
                    **command_result.evidence,
                    "mode": "command",
                    "acceptance_authority": "orchestrator-captured-command",
                    "reviewer_verdict": reviewer_verdict,
                    "command_executed": command_result.command is not None,
                    "workflow_accepted": False,
                },
            )
        accepted = command_result.passed
        return replace(
            command_result,
            status="PASS",
            evidence={
                **command_result.evidence,
                "mode": "command",
                "acceptance_authority": "orchestrator-captured-command",
                "reviewer_verdict": reviewer_verdict,
                "acceptance_check_status": command_result.status,
                "command_executed": True,
                "workflow_accepted": accepted,
            },
            claims=("REVIEWED",) if accepted else (),
        )

    def _command(
        self,
        name: str,
        workspace: Path,
        spec: dict[str, Any],
        log_dir: Path,
        index: int,
        cancel_event: threading.Event | None,
    ) -> ValidationResult:
        argv = spec.get("argv")
        if not isinstance(argv, list) or not argv or not all(isinstance(item, str) for item in argv):
            return ValidationResult(name, "ERROR", {"error": "command argv must be a nonempty string list"})
        try:
            timeout_seconds = _validated_timeout(spec.get("timeout_seconds", 120))
            expected_exit = _validated_expected_exit(spec.get("expected_exit", 0))
            extra_env = _validated_environment(spec.get("env", {}))
        except (TypeError, ValueError) as error:
            return ValidationResult(name, "ERROR", {"error": str(error)}, argv)
        relative_cwd = safe_relative(str(spec.get("cwd", "."))) if spec.get("cwd", ".") != "." else Path(".")
        cwd = (workspace / relative_cwd).resolve()
        if not contained(workspace, cwd) or not cwd.is_dir():
            return ValidationResult(name, "ERROR", {"error": "command cwd escapes or is missing"})
        log_dir.mkdir(parents=True, exist_ok=True)
        stdout_path = log_dir / f"validation-{index:02d}.stdout.log"
        stderr_path = log_dir / f"validation-{index:02d}.stderr.log"
        env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "PYTHONDONTWRITEBYTECODE": "1",
        }
        env.update(extra_env)
        stdout_capture = BoundedBinaryCapture(self.log_limit_bytes)
        stderr_capture = BoundedBinaryCapture(self.log_limit_bytes)
        process: subprocess.Popen[bytes] | None = None
        interrupted: str | None = None
        exit_code: int | None = None
        try:
            process = subprocess.Popen(
                argv,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                start_new_session=True,
            )
            assert process.stdout is not None
            assert process.stderr is not None
            stdout_capture.start(
                process.stdout, name=f"validator-{index}-stdout-capture"
            )
            stderr_capture.start(
                process.stderr, name=f"validator-{index}-stderr-capture"
            )
            deadline = time.monotonic() + timeout_seconds
            while process.poll() is None:
                if cancel_event is not None and cancel_event.wait(0.05):
                    interrupted = "validator cancelled"
                    break
                if time.monotonic() >= deadline:
                    interrupted = "validator timed out"
                    break
                time.sleep(0.01)
            if interrupted is None:
                exit_code = process.wait()
        except (OSError, ValueError) as error:
            return ValidationResult(name, "ERROR", {"error": redact(str(error))}, argv)
        finally:
            if process is not None:
                _terminate_process_group(
                    process, parent_already_reaped=process.poll() is not None
                )

        capture_errors: list[str] = []
        for capture, path in (
            (stdout_capture, stdout_path),
            (stderr_capture, stderr_path),
        ):
            try:
                capture.finish()
            except CaptureError as error:
                capture_errors.append(str(error))
            capture.persist_redacted(path)
        if capture_errors:
            return ValidationResult(
                name,
                "ERROR",
                {"error": "; ".join(capture_errors)},
                argv,
                exit_code,
                stdout_path,
                stderr_path,
            )
        if interrupted is not None:
            return ValidationResult(
                name, "FAIL", {"error": interrupted}, argv, None,
                stdout_path, stderr_path,
            )
        assert exit_code is not None
        return ValidationResult(
            name, "PASS" if exit_code == expected_exit else "FAIL",
            {
                "expected_exit": expected_exit,
                "stdout_bytes": stdout_capture.total_bytes,
                "stderr_bytes": stderr_capture.total_bytes,
                "retained_log_limit_bytes": self.log_limit_bytes,
            },
            argv,
            exit_code,
            stdout_path,
            stderr_path,
        )

    def _record(
        self,
        job_id: str,
        attempt_number: int,
        result: ValidationResult,
        started: float,
        finished: float,
    ) -> None:
        with self.db.transaction(immediate=True) as connection:
            connection.execute(
                """
                INSERT INTO validations(
                    validation_id,job_id,validator,status,command_json,exit_code,stdout_path,
                    stderr_path,evidence_json,started_at,finished_at,attempt_number,claims_json
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    new_id("validation"),
                    job_id,
                    result.name,
                    result.status,
                    canonical_json(result.command) if result.command else None,
                    result.exit_code,
                    str(result.stdout_path) if result.stdout_path else None,
                    str(result.stderr_path) if result.stderr_path else None,
                    canonical_json(result.evidence),
                    started,
                    finished,
                    attempt_number,
                    canonical_json(result.claims),
                ),
            )
            self.db.emit_event(
                "validator", "VALIDATION_COMPLETED", job_id=job_id,
                payload={
                    "validator": result.name,
                    "status": result.status,
                    "attempt": attempt_number,
                    "claims": list(result.claims),
                    "evidence": result.evidence,
                },
                connection=connection,
            )


def _terminate_process_group(
    process: subprocess.Popen[bytes], *, parent_already_reaped: bool = False
) -> None:
    """Terminate validator descendants even when their direct parent exited."""

    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        if process.poll() is None:
            try:
                process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                pass
        return
    if not parent_already_reaped:
        try:
            process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            pass
    deadline = time.monotonic() + 0.2
    while time.monotonic() < deadline:
        try:
            os.killpg(process.pid, 0)
        except ProcessLookupError:
            return
        time.sleep(0.01)
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    if process.poll() is None:
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            pass


def _validated_timeout(value: object) -> float:
    if isinstance(value, bool):
        raise TypeError("validator timeout_seconds must be a finite positive number")
    try:
        timeout = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as error:
        raise TypeError(
            "validator timeout_seconds must be a finite positive number"
        ) from error
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("validator timeout_seconds must be a finite positive number")
    return timeout


def _validated_expected_exit(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("validator expected_exit must be an integer")
    return value


def _validated_environment(value: object) -> dict[str, str]:
    if not isinstance(value, dict):
        raise TypeError("validator env must be an object")
    result: dict[str, str] = {}
    for raw_name, raw_value in value.items():
        if not isinstance(raw_name, str) or not raw_name or "=" in raw_name or "\0" in raw_name:
            raise ValueError("validator env names must be nonempty strings without '=' or NUL")
        if isinstance(raw_value, float) and not math.isfinite(raw_value):
            raise ValueError(f"validator env value for {raw_name!r} must be finite")
        if not isinstance(raw_value, (str, int, float, bool)):
            raise TypeError(
                f"validator env value for {raw_name!r} must be a safe scalar"
            )
        rendered = str(raw_value)
        if "\0" in rendered:
            raise ValueError(f"validator env value for {raw_name!r} contains NUL")
        result[raw_name] = rendered
    return result


_SUPPORTED_SCHEMA_TYPES = {
    "object",
    "array",
    "string",
    "number",
    "integer",
    "boolean",
    "null",
}
_SUPPORTED_SCHEMA_KEYWORDS = {
    "type",
    "enum",
    "minimum",
    "maximum",
    "properties",
    "required",
    "additionalProperties",
    "items",
}


def _validate_schema_contract(
    schema: dict[str, Any], path: str, errors: list[str]
) -> None:
    unknown = sorted(set(schema) - _SUPPORTED_SCHEMA_KEYWORDS)
    for keyword in unknown:
        errors.append(f"{path}: unsupported schema keyword {keyword!r}")

    declared_type = schema.get("type")
    if "type" in schema and (
        not isinstance(declared_type, str)
        or declared_type not in _SUPPORTED_SCHEMA_TYPES
    ):
        errors.append(f"{path}.type: must be one supported type string")

    enum = schema.get("enum")
    if "enum" in schema and (not isinstance(enum, list) or not enum):
        errors.append(f"{path}.enum: must be a nonempty array")

    for keyword in ("minimum", "maximum"):
        if keyword not in schema:
            continue
        value = schema[keyword]
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
        ):
            errors.append(f"{path}.{keyword}: must be a finite number")
        if declared_type not in {"number", "integer"}:
            errors.append(
                f"{path}.{keyword}: requires type 'number' or 'integer'"
            )
    minimum = schema.get("minimum")
    maximum = schema.get("maximum")
    if (
        isinstance(minimum, (int, float))
        and not isinstance(minimum, bool)
        and math.isfinite(minimum)
        and isinstance(maximum, (int, float))
        and not isinstance(maximum, bool)
        and math.isfinite(maximum)
        and minimum > maximum
    ):
        errors.append(f"{path}: minimum cannot exceed maximum")

    properties = schema.get("properties")
    if "properties" in schema:
        if not isinstance(properties, dict):
            errors.append(f"{path}.properties: must be an object")
        else:
            for name, child in properties.items():
                if not isinstance(name, str) or not name:
                    errors.append(
                        f"{path}.properties: property names must be nonempty strings"
                    )
                    continue
                if not isinstance(child, dict):
                    errors.append(f"{path}.properties.{name}: must be an object")
                    continue
                _validate_schema_contract(child, f"{path}.properties.{name}", errors)
        if declared_type != "object":
            errors.append(f"{path}.properties: requires type 'object'")

    required = schema.get("required")
    if "required" in schema:
        if (
            not isinstance(required, list)
            or not all(isinstance(name, str) and name for name in required)
            or len(set(required)) != len(required)
        ):
            errors.append(
                f"{path}.required: must be an array of unique nonempty strings"
            )
        if declared_type != "object":
            errors.append(f"{path}.required: requires type 'object'")

    if "additionalProperties" in schema:
        if not isinstance(schema["additionalProperties"], bool):
            errors.append(f"{path}.additionalProperties: must be boolean")
        if declared_type != "object":
            errors.append(f"{path}.additionalProperties: requires type 'object'")

    if "items" in schema:
        items = schema["items"]
        if not isinstance(items, dict):
            errors.append(f"{path}.items: must be an object")
        else:
            _validate_schema_contract(items, f"{path}.items", errors)
        if declared_type != "array":
            errors.append(f"{path}.items: requires type 'array'")


def _validate_schema_subset(
    value: object, schema: dict[str, Any], path: str, errors: list[str]
) -> None:
    """Validate the JSON-Schema subset used by factory worker contracts."""

    expected = schema.get("type")
    matches = {
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
        "string": isinstance(value, str),
        "number": isinstance(value, (int, float)) and not isinstance(value, bool),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
        "null": value is None,
    }
    if isinstance(expected, str) and not matches.get(expected, False):
        errors.append(f"{path}: expected {expected}")
        return
    enum = schema.get("enum")
    if isinstance(enum, list) and not any(
        _json_values_equal(value, candidate) for candidate in enum
    ):
        errors.append(f"{path}: value is outside enum")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if not math.isfinite(value):
            errors.append(f"{path}: number must be finite")
            return
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path}: below minimum")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{path}: above maximum")
    if isinstance(value, dict):
        required = schema.get("required", [])
        for key in required if isinstance(required, list) else []:
            if key not in value:
                errors.append(f"{path}: missing {key}")
        properties = schema.get("properties", {})
        if isinstance(properties, dict):
            for key, child_schema in properties.items():
                if key in value and isinstance(child_schema, dict):
                    _validate_schema_subset(value[key], child_schema, f"{path}.{key}", errors)
            if schema.get("additionalProperties") is False:
                for key in value.keys() - properties.keys():
                    errors.append(f"{path}: unexpected property {key}")
    if isinstance(value, list) and isinstance(schema.get("items"), dict):
        for index, item in enumerate(value):
            _validate_schema_subset(item, schema["items"], f"{path}[{index}]", errors)


def _json_values_equal(left: object, right: object) -> bool:
    """Compare JSON values without Python's bool/int equality aliasing."""

    if left is None or right is None:
        return left is None and right is None
    if isinstance(left, bool) or isinstance(right, bool):
        return isinstance(left, bool) and isinstance(right, bool) and left is right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return left == right
    if isinstance(left, str) or isinstance(right, str):
        return isinstance(left, str) and isinstance(right, str) and left == right
    if isinstance(left, list) or isinstance(right, list):
        return (
            isinstance(left, list)
            and isinstance(right, list)
            and len(left) == len(right)
            and all(_json_values_equal(a, b) for a, b in zip(left, right))
        )
    if isinstance(left, dict) or isinstance(right, dict):
        return (
            isinstance(left, dict)
            and isinstance(right, dict)
            and left.keys() == right.keys()
            and all(_json_values_equal(left[key], right[key]) for key in left)
        )
    return False


def _is_byox_source_path(
    path: Path, mode: int, *, allow_test_only: bool
) -> bool:
    """Return whether a regular file has an explicitly code-like identity."""

    basename = path.name.casefold()
    suffix = path.suffix.casefold()
    return (
        suffix in _BYOX_SOURCE_EXTENSIONS
        or (
            allow_test_only
            and (
                suffix in _BYOX_TEST_ONLY_EXTENSIONS
                or (basename in _BYOX_TEST_BASENAMES and bool(mode & 0o111))
            )
        )
    )


class _DirectoryBoundaryError(RuntimeError):
    """A descriptor-relative tree walk could not preserve its boundary."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def _directory_open_flags() -> int:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
    flags |= getattr(os, "O_DIRECTORY", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    flags |= getattr(os, "O_NONBLOCK", 0)
    return flags


def _open_workspace_directory(workspace: Path) -> int:
    """Open every absolute workspace component without following symlinks."""

    absolute = Path(os.path.abspath(workspace))
    if not absolute.is_absolute() or absolute != workspace:
        raise _DirectoryBoundaryError("noncanonical-workspace")
    try:
        current = os.open(Path(absolute.anchor), _directory_open_flags())
    except OSError as error:
        raise _DirectoryBoundaryError("unreadable-component") from error
    try:
        for part in absolute.parts[1:]:
            try:
                expected = os.stat(
                    part,
                    dir_fd=current,
                    follow_symlinks=False,
                )
            except FileNotFoundError as error:
                raise _DirectoryBoundaryError("missing") from error
            except OSError as error:
                raise _DirectoryBoundaryError("unreadable-component") from error
            if stat.S_ISLNK(expected.st_mode):
                raise _DirectoryBoundaryError("symlink-component")
            if not stat.S_ISDIR(expected.st_mode):
                raise _DirectoryBoundaryError("non-directory-component")
            try:
                child = os.open(
                    part,
                    _directory_open_flags(),
                    dir_fd=current,
                )
            except OSError as error:
                raise _DirectoryBoundaryError(
                    "changed-or-unreadable-component"
                ) from error
            try:
                actual = os.fstat(child)
                if not _same_stat_snapshot(expected, actual):
                    raise _DirectoryBoundaryError("changed-component")
            except Exception:
                os.close(child)
                raise
            os.close(current)
            current = child
        return current
    except Exception:
        os.close(current)
        raise


def _open_relative_directory(
    workspace_descriptor: int,
    parts: tuple[str, ...],
    *,
    expected: os.stat_result | None = None,
) -> int:
    """Open ``parts`` beneath a pinned workspace, rejecting every symlink.

    Only the current descriptor and the next child are open at once, so a deep
    but bounded tree cannot exhaust one descriptor per queued directory.
    """

    current = os.dup(workspace_descriptor)
    try:
        for part in parts:
            try:
                child_expected = os.stat(
                    part,
                    dir_fd=current,
                    follow_symlinks=False,
                )
            except FileNotFoundError as error:
                raise _DirectoryBoundaryError("missing") from error
            except OSError as error:
                raise _DirectoryBoundaryError("unreadable-component") from error
            if stat.S_ISLNK(child_expected.st_mode):
                raise _DirectoryBoundaryError("symlink-component")
            if not stat.S_ISDIR(child_expected.st_mode):
                raise _DirectoryBoundaryError("non-directory-component")
            try:
                child = os.open(
                    part,
                    _directory_open_flags(),
                    dir_fd=current,
                )
            except OSError as error:
                raise _DirectoryBoundaryError(
                    "changed-or-unreadable-component"
                ) from error
            try:
                child_actual = os.fstat(child)
            except OSError as error:
                os.close(child)
                raise _DirectoryBoundaryError(
                    "changed-or-unreadable-component"
                ) from error
            if not _same_stat_snapshot(child_expected, child_actual):
                os.close(child)
                raise _DirectoryBoundaryError("changed-component")
            os.close(current)
            current = child
        if expected is not None and not _same_stat_snapshot(
            expected, os.fstat(current)
        ):
            raise _DirectoryBoundaryError("changed-directory")
        return current
    except Exception:
        os.close(current)
        raise


def _revalidate_workspace_binding(
    workspace: Path,
    workspace_descriptor: int,
    expected: os.stat_result,
) -> None:
    """Detect a final absolute-path replacement as defense in depth.

    This one observation does not turn a mutable tree into an atomic snapshot.
    Authoritative runtime callers first install a fresh-inode workspace cutover;
    this check only detects an additional gross pathname replacement.
    """

    descriptor_matches = _same_stat_snapshot(
        expected, os.fstat(workspace_descriptor)
    )
    # Reopen the absolute path even when the held descriptor already drifted;
    # both observations must still name the cutover object at this final check.
    rebound = _open_workspace_directory(workspace)
    try:
        actual = os.fstat(rebound)
    finally:
        os.close(rebound)
    if not descriptor_matches:
        raise _DirectoryBoundaryError("workspace-descriptor-changed")
    if not _same_stat_snapshot(expected, actual):
        raise _DirectoryBoundaryError("workspace-binding-changed")


def capture_byox_code_manifest(workspace: Path) -> ByoxCodeManifest:
    """Capture a bounded policy-root view through pinned no-follow dirfds.

    This function deliberately makes no atomic-snapshot claim for an arbitrary
    mutable input path.  Runtime authority comes from the handler's fresh-inode
    cutover; archive replay authority comes from a private checksum-bound copy.
    """

    captured: dict[str, ByoxCodeManifestEntry] = {}
    capture_entries = 0
    capture_files = 0
    capture_bytes = 0
    limit_failure: str | None = None

    def retain(entry: ByoxCodeManifestEntry) -> None:
        existing = captured.get(entry.path)
        if existing is None:
            captured[entry.path] = entry
        elif entry.kind == "unsafe":
            captured[entry.path] = entry
        elif existing.kind == "unsafe":
            return
        elif existing != entry:
            captured[entry.path] = ByoxCodeManifestEntry(
                entry.path,
                "unsafe",
                reason="conflicting-capture",
            )

    roots = tuple(
        dict.fromkeys(root for _, raw_roots in _BYOX_CODE_ROOT_GROUPS for root in raw_roots)
    )
    try:
        workspace_descriptor = _open_workspace_directory(workspace)
    except _DirectoryBoundaryError as error:
        return ByoxCodeManifest(
            entries=tuple(
                ByoxCodeManifestEntry(
                    root,
                    "unsafe",
                    reason=f"unsafe-workspace:{error.reason}",
                )
                for root in roots
            ),
            scope="policy-roots",
        )
    try:
        # The cleanup scope starts before fstat so this descriptor cannot leak
        # when metadata acquisition itself fails.
        workspace_before = os.fstat(workspace_descriptor)
        for raw_root in roots:
            if limit_failure is not None:
                break
            root_relative = safe_relative(raw_root)
            rendered_root = root_relative.as_posix()
            root_parts = tuple(root_relative.parts)
            try:
                root_descriptor = _open_relative_directory(
                    workspace_descriptor, root_parts
                )
            except _DirectoryBoundaryError as error:
                if error.reason != "missing":
                    retain(
                        ByoxCodeManifestEntry(
                            rendered_root,
                            "unsafe",
                            reason=f"unsafe-root:{error.reason}",
                        )
                    )
                continue
            try:
                root_metadata = os.fstat(root_descriptor)
            finally:
                os.close(root_descriptor)
            retain(
                ByoxCodeManifestEntry(
                    rendered_root,
                    "directory",
                    mode=root_metadata.st_mode & 0o777,
                )
            )
            pending: list[tuple[tuple[str, ...], os.stat_result]] = [
                (root_parts, root_metadata)
            ]
            while pending and limit_failure is None:
                directory_parts, expected = pending.pop()
                depth = len(directory_parts) - len(root_parts)
                if depth > BYOX_TREE_MAX_DEPTH:
                    limit_failure = "max_depth_exceeded"
                    break
                rendered_directory = "/".join(directory_parts)
                try:
                    directory_descriptor = _open_relative_directory(
                        workspace_descriptor,
                        directory_parts,
                        expected=expected,
                    )
                except _DirectoryBoundaryError as error:
                    retain(
                        ByoxCodeManifestEntry(
                            rendered_directory,
                            "unsafe",
                            reason=f"unsafe-directory:{error.reason}",
                        )
                    )
                    continue
                try:
                    # Enter cleanup before the initial fstat.
                    before = os.fstat(directory_descriptor)
                    try:
                        with os.scandir(directory_descriptor) as iterator:
                            directory_entries: list[str] = []
                            for item in iterator:
                                directory_entries.append(item.name)
                                if (
                                    capture_entries + len(directory_entries)
                                    > _BYOX_CODE_MAX_ENTRIES
                                ):
                                    limit_failure = "max_entries_exceeded"
                                    break
                    except OSError as error:
                        retain(
                            ByoxCodeManifestEntry(
                                rendered_directory,
                                "unsafe",
                                reason=(
                                    "unreadable-directory:"
                                    f"{error.__class__.__name__}"
                                ),
                            )
                        )
                        continue
                    if limit_failure is not None:
                        break
                    directory_entries.sort()
                    child_directories: list[
                        tuple[tuple[str, ...], os.stat_result]
                    ] = []
                    for entry_name in directory_entries:
                        capture_entries += 1
                        child_parts = (*directory_parts, entry_name)
                        relative = "/".join(child_parts)
                        if (
                            capture_entries > _BYOX_CODE_MAX_ENTRIES
                        ):
                            limit_failure = "max_entries_exceeded"
                            break
                        try:
                            metadata = os.stat(
                                entry_name,
                                dir_fd=directory_descriptor,
                                follow_symlinks=False,
                            )
                        except OSError as error:
                            retain(
                                ByoxCodeManifestEntry(
                                    relative,
                                    "unsafe",
                                    reason=(
                                        "unreadable-entry:"
                                        f"{error.__class__.__name__}"
                                    ),
                                )
                            )
                            continue
                        mode = metadata.st_mode
                        if stat.S_ISLNK(mode):
                            retain(
                                ByoxCodeManifestEntry(
                                    relative, "symlink", reason="symlink"
                                )
                            )
                            continue
                        if stat.S_ISDIR(mode):
                            if depth >= BYOX_TREE_MAX_DEPTH:
                                limit_failure = "max_depth_exceeded"
                                break
                            retain(
                                ByoxCodeManifestEntry(
                                    relative, "directory", mode=mode & 0o777
                                )
                            )
                            child_directories.append((child_parts, metadata))
                            continue
                        if not stat.S_ISREG(mode):
                            retain(
                                ByoxCodeManifestEntry(
                                    relative, "special", reason="special-file"
                                )
                            )
                            continue
                        if metadata.st_nlink != 1:
                            retain(
                                ByoxCodeManifestEntry(
                                    relative,
                                    "unsafe",
                                    mode=mode & 0o777,
                                    size_bytes=metadata.st_size,
                                    reason="hardlink",
                                )
                            )
                            continue
                        capture_files += 1
                        capture_bytes += metadata.st_size
                        if capture_files > _BYOX_CODE_MAX_FILES:
                            limit_failure = "max_files_exceeded"
                        elif capture_bytes > _BYOX_CODE_MAX_TOTAL_BYTES:
                            limit_failure = "max_total_bytes_exceeded"
                        if limit_failure is not None:
                            retain(
                                ByoxCodeManifestEntry(
                                    relative,
                                    "file",
                                    mode=mode & 0o777,
                                    size_bytes=metadata.st_size,
                                )
                            )
                            break
                        if metadata.st_size > _BYOX_CODE_MAX_FILE_BYTES:
                            retain(
                                ByoxCodeManifestEntry(
                                    relative,
                                    "file",
                                    mode=mode & 0o777,
                                    size_bytes=metadata.st_size,
                                )
                            )
                            continue
                        try:
                            digest = _capture_byox_regular_file_at(
                                directory_descriptor,
                                entry_name,
                                metadata,
                            )
                        except OSError as error:
                            retain(
                                ByoxCodeManifestEntry(
                                    relative,
                                    "file-error",
                                    mode=mode & 0o777,
                                    size_bytes=metadata.st_size,
                                    reason=(
                                        "unreadable-file:"
                                        f"{error.__class__.__name__}"
                                    ),
                                )
                            )
                            continue
                        retain(
                            ByoxCodeManifestEntry(
                                relative,
                                "file",
                                mode=mode & 0o777,
                                size_bytes=metadata.st_size,
                                sha256=digest,
                            )
                        )
                    pending.extend(reversed(child_directories))
                    after = os.fstat(directory_descriptor)
                    if not _same_stat_snapshot(before, after):
                        retain(
                            ByoxCodeManifestEntry(
                                rendered_directory,
                                "unsafe",
                                reason="directory-changed-during-capture",
                            )
                        )
                finally:
                    os.close(directory_descriptor)
                try:
                    rebound = _open_relative_directory(
                        workspace_descriptor,
                        directory_parts,
                        expected=before,
                    )
                except _DirectoryBoundaryError:
                    retain(
                        ByoxCodeManifestEntry(
                            rendered_directory,
                            "unsafe",
                            reason="directory-binding-changed",
                        )
                    )
                else:
                    os.close(rebound)
        try:
            _revalidate_workspace_binding(
                workspace,
                workspace_descriptor,
                workspace_before,
            )
        except (OSError, _DirectoryBoundaryError) as error:
            reason = (
                error.reason
                if isinstance(error, _DirectoryBoundaryError)
                else "workspace-binding-changed"
            )
            for root in roots:
                retain(
                    ByoxCodeManifestEntry(
                        root,
                        "unsafe",
                        reason=f"workspace-binding:{reason}",
                    )
                )
    finally:
        os.close(workspace_descriptor)

    return ByoxCodeManifest(
        entries=tuple(sorted(captured.values(), key=lambda entry: entry.path)),
        scope="policy-roots",
        capture_limit_failure=limit_failure,
    )


def _capture_byox_regular_file_at(
    directory_descriptor: int,
    name: str,
    expected: os.stat_result,
) -> str:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    flags |= getattr(os, "O_NONBLOCK", 0)
    descriptor = os.open(name, flags, dir_fd=directory_descriptor)
    digest = hashlib.sha256()
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or not _same_stat_snapshot(expected, before)
        ):
            raise OSError("file changed before manifest capture")
        read_bytes = 0
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            read_bytes += len(chunk)
            if read_bytes > _BYOX_CODE_MAX_FILE_BYTES:
                raise OSError("file exceeded manifest capture bound")
            digest.update(chunk)
        after = os.fstat(descriptor)
        if read_bytes != before.st_size or not _same_stat_snapshot(before, after):
            raise OSError("file changed during manifest capture")
    finally:
        os.close(descriptor)
    return digest.hexdigest()


def _same_stat_snapshot(left: os.stat_result, right: os.stat_result) -> bool:
    return (
        left.st_dev,
        left.st_ino,
        left.st_mode,
        left.st_nlink,
        left.st_size,
        left.st_mtime_ns,
        left.st_ctime_ns,
    ) == (
        right.st_dev,
        right.st_ino,
        right.st_mode,
        right.st_nlink,
        right.st_size,
        right.st_mtime_ns,
        right.st_ctime_ns,
    )


def byox_code_manifest_digest(manifest: ByoxCodeManifest) -> str:
    material = {
        "version": manifest.version,
        "scope": manifest.scope,
        "capture_limit_failure": manifest.capture_limit_failure,
        "entries": [
            {
                "path": entry.path,
                "kind": entry.kind,
                "mode": entry.mode,
                "size_bytes": entry.size_bytes,
                "sha256": entry.sha256,
                "reason": entry.reason,
            }
            for entry in sorted(manifest.entries, key=lambda item: item.path)
        ],
    }
    return hashlib.sha256(canonical_json(material).encode("utf-8")).hexdigest()


def byox_code_policy_manifest_digest(manifest: ByoxCodeManifest) -> str:
    """Hash only the immutable manifest projection consumed by this policy."""

    roots = tuple(
        dict.fromkeys(root for _, raw_roots in _BYOX_CODE_ROOT_GROUPS for root in raw_roots)
    )
    projected = [
        entry
        for entry in manifest.entries
        if any(entry.path == root or entry.path.startswith(root + "/") for root in roots)
    ]
    material = {
        "version": manifest.version,
        "capture_limit_failure": manifest.capture_limit_failure,
        "entries": [
            {
                "path": entry.path,
                "kind": entry.kind,
                "mode": entry.mode,
                "size_bytes": entry.size_bytes,
                "sha256": entry.sha256,
                "reason": entry.reason,
            }
            for entry in sorted(projected, key=lambda item: item.path)
        ],
    }
    return hashlib.sha256(canonical_json(material).encode("utf-8")).hexdigest()


def byox_code_manifest_tree_sha256(manifest: ByoxCodeManifest) -> str:
    """Return a V2 tree checksum only for a complete safe full-tree manifest."""

    error = _byox_manifest_error(manifest, require_full_tree=True)
    if error is not None:
        raise ValueError(error)
    digest = hashlib.sha256()
    digest.update(b"learnfactory-tree-sha256-v2\0")
    for entry in sorted(manifest.entries, key=lambda item: item.path):
        path = entry.path.encode("utf-8")
        if entry.kind == "directory":
            digest.update(b"D")
            _hash_validation_field(digest, path)
            continue
        assert entry.sha256 is not None
        digest.update(b"F")
        _hash_validation_field(digest, path)
        _hash_validation_field(digest, entry.mode.to_bytes(4, "big"))
        _hash_validation_field(digest, bytes.fromhex(entry.sha256))
    return digest.hexdigest()


def _hash_validation_field(digest: Any, value: bytes) -> None:
    digest.update(len(value).to_bytes(8, "big"))
    digest.update(value)


def _byox_manifest_error(
    manifest: ByoxCodeManifest, *, require_full_tree: bool = False
) -> str | None:
    if not isinstance(manifest, ByoxCodeManifest):
        return "BYOX manifest has the wrong type"
    if manifest.version != _BYOX_CODE_MANIFEST_VERSION:
        return "BYOX manifest version is unsupported"
    if manifest.scope not in {"policy-roots", "full-tree"}:
        return "BYOX manifest scope is unsupported"
    if require_full_tree and manifest.scope != "full-tree":
        return "BYOX tree checksum requires a full-tree manifest"
    if manifest.capture_limit_failure not in {
        None,
        "max_entries_exceeded",
        "max_files_exceeded",
        "max_total_bytes_exceeded",
        "max_depth_exceeded",
    }:
        return "BYOX manifest capture limit result is invalid"
    seen: set[str] = set()
    allowed_kinds = {"directory", "file", "symlink", "special", "unsafe", "file-error"}
    for entry in manifest.entries:
        if not isinstance(entry, ByoxCodeManifestEntry):
            return "BYOX manifest entry has the wrong type"
        try:
            relative = safe_relative(entry.path)
        except Exception:
            return "BYOX manifest contains an unsafe path"
        if relative.as_posix() != entry.path or entry.path in seen:
            return "BYOX manifest contains a duplicate or noncanonical path"
        seen.add(entry.path)
        if entry.kind not in allowed_kinds:
            return "BYOX manifest contains an unsupported entry kind"
        if (
            isinstance(entry.mode, bool)
            or not isinstance(entry.mode, int)
            or not 0 <= entry.mode <= 0o777
            or isinstance(entry.size_bytes, bool)
            or not isinstance(entry.size_bytes, int)
            or entry.size_bytes < 0
        ):
            return "BYOX manifest contains invalid file metadata"
        if entry.kind == "file":
            digest_required = require_full_tree or entry.size_bytes <= _BYOX_CODE_MAX_FILE_BYTES
            if entry.sha256 is None:
                if digest_required:
                    return "BYOX manifest lacks a bounded file digest"
            elif (
                not isinstance(entry.sha256, str)
                or re.fullmatch(r"[0-9a-f]{64}", entry.sha256) is None
            ):
                return "BYOX manifest contains an invalid file digest"
        elif entry.sha256 is not None:
            return "BYOX manifest has a digest on a non-file entry"
        if require_full_tree and entry.kind not in {"directory", "file"}:
            return "full-tree BYOX manifest contains an unsafe entry"
    return None


def evaluate_byox_code_manifest(
    manifest: ByoxCodeManifest,
    specification: dict[str, Any],
    *,
    name: str = "byox-authoritative-code-bearing-tree",
) -> ValidationResult:
    """Evaluate the BYOX policy over immutable metadata and content hashes."""

    manifest_error = _byox_manifest_error(manifest)
    if manifest_error is not None:
        return ValidationResult(name, "ERROR", {"error": manifest_error})
    limits: dict[str, int] = {}
    for key, default, hard_max in (
        ("max_entries", _BYOX_CODE_MAX_ENTRIES, _BYOX_CODE_MAX_ENTRIES),
        ("max_files", _BYOX_CODE_MAX_FILES, _BYOX_CODE_MAX_FILES),
        ("max_total_bytes", _BYOX_CODE_MAX_TOTAL_BYTES, _BYOX_CODE_MAX_TOTAL_BYTES),
        ("max_file_bytes", _BYOX_CODE_MAX_FILE_BYTES, _BYOX_CODE_MAX_FILE_BYTES),
    ):
        raw = specification.get(key, default)
        if isinstance(raw, bool) or not isinstance(raw, int) or not 0 < raw <= hard_max:
            return ValidationResult(
                name,
                "ERROR",
                {"error": f"{key} must be a positive integer no greater than {hard_max}"},
            )
        limits[key] = raw
    limits["max_depth"] = BYOX_TREE_MAX_DEPTH

    entries = {entry.path: entry for entry in manifest.entries}
    counts = {"entries": 0, "files": 0, "bytes": 0}
    unsafe: list[dict[str, str]] = []
    oversized: list[dict[str, Any]] = []
    groups: list[dict[str, Any]] = []
    limit_failure: str | None = None
    for group_name, raw_roots in _BYOX_CODE_ROOT_GROUPS:
        qualifying: list[dict[str, Any]] = []
        build_descriptors: list[str] = []
        missing_or_unsafe_roots: list[str] = []
        for raw_root in raw_roots:
            root = entries.get(raw_root)
            if root is None:
                missing_or_unsafe_roots.append(raw_root)
                continue
            if root.kind != "directory":
                missing_or_unsafe_roots.append(raw_root)
                unsafe.append(
                    {
                        "path": raw_root,
                        "reason": root.reason or f"unsafe-root:{root.kind}",
                    }
                )
                continue
            descendants = sorted(
                (
                    entry
                    for entry in manifest.entries
                    if entry.path.startswith(raw_root + "/")
                ),
                key=lambda entry: entry.path,
            )
            for entry in descendants:
                counts["entries"] += 1
                if counts["entries"] > limits["max_entries"]:
                    limit_failure = "max_entries_exceeded"
                    break
                if entry.kind == "directory":
                    continue
                if entry.kind != "file":
                    unsafe.append(
                        {
                            "path": entry.path,
                            "reason": entry.reason or entry.kind,
                        }
                    )
                    continue
                counts["files"] += 1
                counts["bytes"] += entry.size_bytes
                if counts["files"] > limits["max_files"]:
                    limit_failure = "max_files_exceeded"
                    break
                if counts["bytes"] > limits["max_total_bytes"]:
                    limit_failure = "max_total_bytes_exceeded"
                    break
                if entry.size_bytes > limits["max_file_bytes"]:
                    oversized.append(
                        {"path": entry.path, "size_bytes": entry.size_bytes}
                    )
                    continue
                basename = Path(entry.path).name.casefold()
                if basename in _BYOX_BUILD_BASENAMES:
                    build_descriptors.append(entry.path)
                    continue
                if entry.size_bytes == 0 or not _is_byox_source_path(
                    Path(entry.path),
                    entry.mode,
                    allow_test_only=group_name == "tests",
                ):
                    continue
                assert entry.sha256 is not None
                qualifying.append(
                    {
                        "path": entry.path,
                        "size_bytes": entry.size_bytes,
                        "sha256": entry.sha256,
                    }
                )
            if limit_failure is not None:
                break
        qualifying.sort(key=lambda item: str(item["path"]))
        build_descriptors.sort()
        groups.append(
            {
                "name": group_name,
                "roots": list(raw_roots),
                "qualifying_count": len(qualifying),
                "qualifying_digest": hashlib.sha256(
                    canonical_json(qualifying).encode("utf-8")
                ).hexdigest(),
                "qualifying_files": qualifying[:_BYOX_CODE_MAX_EVIDENCE_PATHS],
                "qualifying_files_truncated": max(
                    0, len(qualifying) - _BYOX_CODE_MAX_EVIDENCE_PATHS
                ),
                "build_descriptor_count": len(build_descriptors),
                "build_descriptors": build_descriptors[:_BYOX_CODE_MAX_EVIDENCE_PATHS],
                "missing_or_unsafe_roots": missing_or_unsafe_roots,
            }
        )
        if limit_failure is not None:
            break
    if limit_failure is None:
        limit_failure = manifest.capture_limit_failure

    missing_groups = [
        str(group["name"])
        for group in groups
        if int(group["qualifying_count"]) == 0
        or len(group["missing_or_unsafe_roots"]) == len(group["roots"])
    ]
    represented = {str(group["name"]) for group in groups}
    missing_groups.extend(
        group_name
        for group_name, _ in _BYOX_CODE_ROOT_GROUPS
        if group_name not in represented
    )
    evidence = {
        "schema_version": 2,
        "policy_version": _BYOX_CODE_POLICY_VERSION,
        "policy_digest": _byox_code_policy_digest(),
        "manifest_version": manifest.version,
        "manifest_digest": byox_code_policy_manifest_digest(manifest),
        "scope": "code-presence-structure-only",
        "claims_builds_or_tested": False,
        "limits": limits,
        "counts": counts,
        "groups": groups,
        "missing_groups": list(dict.fromkeys(missing_groups)),
        "unsafe_entries": sorted(unsafe, key=lambda item: item["path"])[
            :_BYOX_CODE_MAX_EVIDENCE_PATHS
        ],
        "unsafe_entries_truncated": max(0, len(unsafe) - _BYOX_CODE_MAX_EVIDENCE_PATHS),
        "oversized_files": sorted(oversized, key=lambda item: item["path"])[
            :_BYOX_CODE_MAX_EVIDENCE_PATHS
        ],
        "oversized_files_truncated": max(
            0, len(oversized) - _BYOX_CODE_MAX_EVIDENCE_PATHS
        ),
        "limit_failure": limit_failure,
    }
    passed = not (missing_groups or unsafe or oversized or limit_failure is not None)
    return ValidationResult(name, "PASS" if passed else "FAIL", evidence)


def _byox_code_policy_digest() -> str:
    material = {
        "version": _BYOX_CODE_POLICY_VERSION,
        "manifest_version": _BYOX_CODE_MANIFEST_VERSION,
        "evaluation": "immutable-manifest-v1",
        "root_groups": [
            {"name": name, "roots": list(roots)}
            for name, roots in _BYOX_CODE_ROOT_GROUPS
        ],
        "source_extensions": sorted(_BYOX_SOURCE_EXTENSIONS),
        "test_only_extensions": sorted(_BYOX_TEST_ONLY_EXTENSIONS),
        "test_basenames": sorted(_BYOX_TEST_BASENAMES),
        "build_basenames": sorted(_BYOX_BUILD_BASENAMES),
        "hard_limits": {
            "max_entries": _BYOX_CODE_MAX_ENTRIES,
            "max_files": _BYOX_CODE_MAX_FILES,
            "max_total_bytes": _BYOX_CODE_MAX_TOTAL_BYTES,
            "max_file_bytes": _BYOX_CODE_MAX_FILE_BYTES,
            "max_depth": BYOX_TREE_MAX_DEPTH,
        },
        "regular_file_nlink": 1,
        "absolute_workspace_components": "no-follow",
        "capture_atomicity": "not-claimed",
        "runtime_authority": "fresh-inode-workspace-cutover-and-checksum-binding-v1",
    }
    return hashlib.sha256(canonical_json(material).encode("utf-8")).hexdigest()


def byox_code_policy_digest() -> str:
    """Return the stable digest embedded by the current BYOX code gate."""

    return _byox_code_policy_digest()


def evaluate_byox_code_presence(
    workspace: Path,
    specification: dict[str, Any],
    *,
    name: str = "byox-authoritative-code-bearing-tree",
) -> ValidationResult:
    """Capture then evaluate the BYOX structural gate without recording a row.

    Runtime validation uses this wrapper only after the handler's detached
    workspace cutover. Archive maintenance evaluates a manifest captured from
    its own private checksum-bound copy. Direct callers must not treat this
    convenience wrapper as an atomic snapshot of a concurrently mutable tree.
    """

    return Validator._byox_code_presence(name, workspace, specification)


def _tree_manifest(root: Path) -> dict[str, tuple[str, str, int]]:
    manifest: dict[str, tuple[str, str, int]] = {}
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            manifest[relative] = ("symlink", path.readlink().as_posix(), 0)
        elif path.is_file():
            manifest[relative] = (
                "file",
                file_sha256(path),
                path.stat().st_mode & 0o777,
            )
        elif path.is_dir():
            manifest[relative] = (
                "directory",
                "",
                path.stat().st_mode & 0o777,
            )
    return manifest


def _unexpected_mutations(changed: list[str], spec: dict[str, Any]) -> str | None:
    if not changed:
        return None
    raw_outputs = spec.get("produces", [])
    if not isinstance(raw_outputs, list):
        return "validator produces must be a list of evidence paths"
    allowed: list[str] = []
    for raw in raw_outputs:
        try:
            path = safe_relative(str(raw))
        except Exception:
            return "validator declares an unsafe produced path"
        # Evidence generation is intentionally separate from candidate code.
        if path.parts[0] not in {"evaluations", "benchmarks", "reports", "validation-output"}:
            return "validator may only produce files in designated evidence directories"
        allowed.append(path.as_posix())
    unexpected = [
        path for path in changed
        if not any(
            path == prefix
            or path.startswith(prefix + "/")
            or prefix.startswith(path + "/")
            for prefix in allowed
        )
    ]
    if unexpected:
        return "validator mutated candidate paths outside its declared evidence outputs"
    return None
