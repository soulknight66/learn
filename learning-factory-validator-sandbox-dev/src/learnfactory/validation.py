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
from .workspace import contained, safe_relative


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
_BYOX_CODE_POLICY_VERSION = 1


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
        return ValidationResult(
            name,
            "PASS" if not mismatches else "FAIL",
            {"checked": checked, "mismatches": mismatches},
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

    def _byox_code_presence(
        self, name: str, workspace: Path, spec: dict[str, Any]
    ) -> ValidationResult:
        """Require bounded code-bearing trees in a generic BYOX challenge pack.

        This gate intentionally proves only structural code presence.  It never
        emits BUILDS or TESTED; executable validators remain responsible for
        those stronger claims.  Evidence contains identities and hashes, not
        generated source contents.
        """

        limits: dict[str, int] = {}
        for key, default, hard_max in (
            ("max_entries", _BYOX_CODE_MAX_ENTRIES, _BYOX_CODE_MAX_ENTRIES),
            ("max_files", _BYOX_CODE_MAX_FILES, _BYOX_CODE_MAX_FILES),
            (
                "max_total_bytes",
                _BYOX_CODE_MAX_TOTAL_BYTES,
                _BYOX_CODE_MAX_TOTAL_BYTES,
            ),
            ("max_file_bytes", _BYOX_CODE_MAX_FILE_BYTES, _BYOX_CODE_MAX_FILE_BYTES),
        ):
            raw = spec.get(key, default)
            if isinstance(raw, bool) or not isinstance(raw, int) or not 0 < raw <= hard_max:
                return ValidationResult(
                    name,
                    "ERROR",
                    {"error": f"{key} must be a positive integer no greater than {hard_max}"},
                )
            limits[key] = raw

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
                root_relative = safe_relative(raw_root)
                root = workspace / root_relative
                root_state = _byox_directory_root_state(workspace, root_relative)
                if root_state == "missing":
                    missing_or_unsafe_roots.append(root_relative.as_posix())
                    continue
                if root_state != "safe" or not contained(workspace, root):
                    missing_or_unsafe_roots.append(root_relative.as_posix())
                    unsafe.append(
                        {
                            "path": root_relative.as_posix(),
                            "reason": f"unsafe-root:{root_state}",
                        }
                    )
                    continue
                pending = [root]
                while pending and limit_failure is None:
                    directory = pending.pop()
                    try:
                        entries = os.scandir(directory)
                    except OSError as error:
                        unsafe.append(
                            {
                                "path": directory.relative_to(workspace).as_posix(),
                                "reason": f"unreadable-directory:{error.__class__.__name__}",
                            }
                        )
                        continue
                    with entries:
                        for entry in entries:
                            counts["entries"] += 1
                            if counts["entries"] > limits["max_entries"]:
                                limit_failure = "max_entries_exceeded"
                                break
                            path = Path(entry.path)
                            relative = path.relative_to(workspace).as_posix()
                            try:
                                metadata = entry.stat(follow_symlinks=False)
                            except OSError as error:
                                unsafe.append(
                                    {
                                        "path": relative,
                                        "reason": f"unreadable-entry:{error.__class__.__name__}",
                                    }
                                )
                                continue
                            mode = metadata.st_mode
                            if stat.S_ISLNK(mode):
                                unsafe.append({"path": relative, "reason": "symlink"})
                                continue
                            if stat.S_ISDIR(mode):
                                pending.append(path)
                                continue
                            if not stat.S_ISREG(mode):
                                unsafe.append({"path": relative, "reason": "special-file"})
                                continue
                            counts["files"] += 1
                            counts["bytes"] += metadata.st_size
                            if counts["files"] > limits["max_files"]:
                                limit_failure = "max_files_exceeded"
                                break
                            if counts["bytes"] > limits["max_total_bytes"]:
                                limit_failure = "max_total_bytes_exceeded"
                                break
                            if metadata.st_size > limits["max_file_bytes"]:
                                oversized.append(
                                    {"path": relative, "size_bytes": metadata.st_size}
                                )
                                continue
                            basename = path.name.casefold()
                            if basename in _BYOX_BUILD_BASENAMES:
                                build_descriptors.append(relative)
                                continue
                            if metadata.st_size == 0 or not _is_byox_source_path(
                                path, mode, allow_test_only=group_name == "tests"
                            ):
                                continue
                            qualifying.append(
                                {
                                    "path": relative,
                                    "size_bytes": metadata.st_size,
                                    "sha256": file_sha256(path),
                                }
                            )
                if limit_failure is not None:
                    break

            qualifying.sort(key=lambda item: str(item["path"]))
            build_descriptors.sort()
            digest_material = canonical_json(qualifying).encode("utf-8")
            groups.append(
                {
                    "name": group_name,
                    "roots": list(raw_roots),
                    "qualifying_count": len(qualifying),
                    "qualifying_digest": hashlib.sha256(digest_material).hexdigest(),
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

        missing_groups = [
            str(group["name"])
            for group in groups
            if int(group["qualifying_count"]) == 0
            or len(group["missing_or_unsafe_roots"]) == len(group["roots"])
        ]
        # If a traversal bound stops us early, unvisited groups must also be
        # represented as missing rather than accidentally passing by omission.
        represented = {str(group["name"]) for group in groups}
        missing_groups.extend(
            group_name
            for group_name, _ in _BYOX_CODE_ROOT_GROUPS
            if group_name not in represented
        )
        evidence = {
            "schema_version": 1,
            "policy_version": _BYOX_CODE_POLICY_VERSION,
            "policy_digest": _byox_code_policy_digest(),
            "scope": "code-presence-structure-only",
            "claims_builds_or_tested": False,
            "limits": limits,
            "counts": counts,
            "groups": groups,
            "missing_groups": list(dict.fromkeys(missing_groups)),
            "unsafe_entries": sorted(unsafe, key=lambda item: item["path"])[
                :_BYOX_CODE_MAX_EVIDENCE_PATHS
            ],
            "unsafe_entries_truncated": max(
                0, len(unsafe) - _BYOX_CODE_MAX_EVIDENCE_PATHS
            ),
            "oversized_files": sorted(oversized, key=lambda item: item["path"])[
                :_BYOX_CODE_MAX_EVIDENCE_PATHS
            ],
            "oversized_files_truncated": max(
                0, len(oversized) - _BYOX_CODE_MAX_EVIDENCE_PATHS
            ),
            "limit_failure": limit_failure,
        }
        passed = not (
            missing_groups or unsafe or oversized or limit_failure is not None
        )
        return ValidationResult(name, "PASS" if passed else "FAIL", evidence)

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
        for raw in raw_roots:
            root_relative = safe_relative(str(raw))
            checked_roots.append(root_relative.as_posix())
            root = workspace / root_relative
            root_state = _byox_directory_root_state(workspace, root_relative)
            if root_state != "safe" or not contained(workspace, root):
                present.append(f"{root_relative.as_posix()} (missing-or-unsafe-root)")
                if root_state != "missing":
                    unsafe.append(
                        {
                            "path": root_relative.as_posix(),
                            "reason": f"unsafe-root:{root_state}",
                        }
                    )
                continue
            pending = [root]
            while pending and limit_failure is None:
                directory = pending.pop()
                try:
                    entries = os.scandir(directory)
                except OSError as error:
                    unsafe.append(
                        {
                            "path": directory.relative_to(workspace).as_posix(),
                            "reason": f"unreadable-directory:{error.__class__.__name__}",
                        }
                    )
                    continue
                with entries:
                    for entry in entries:
                        entry_count += 1
                        if entry_count > max_entries:
                            limit_failure = "max_entries_exceeded"
                            break
                        path = Path(entry.path)
                        relative = path.relative_to(workspace).as_posix()
                        try:
                            metadata = entry.stat(follow_symlinks=False)
                        except OSError as error:
                            unsafe.append(
                                {
                                    "path": relative,
                                    "reason": f"unreadable-entry:{error.__class__.__name__}",
                                }
                            )
                            continue
                        mode = metadata.st_mode
                        if stat.S_ISLNK(mode):
                            unsafe.append({"path": relative, "reason": "symlink"})
                            continue
                        folded = path.name.casefold()
                        tokens = {
                            token
                            for token in re.split(r"[^a-z0-9]+", folded)
                            if token
                        }
                        if folded in forbidden or tokens & forbidden:
                            present.append(relative)
                        if stat.S_ISDIR(mode):
                            pending.append(path)
                        elif not stat.S_ISREG(mode):
                            unsafe.append({"path": relative, "reason": "special-file"})
            if limit_failure is not None:
                break
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


def _byox_directory_root_state(workspace: Path, relative: Path) -> str:
    """lstat every workspace-to-root component before a BYOX traversal.

    ``Path.is_symlink`` checks only the leaf.  A symlinked ``sealed`` ancestor
    could otherwise make ``sealed/reference`` look like a normal directory and
    let an alias satisfy the code-presence gate.  Missing paths are distinct from
    unsafe aliases so the evidence remains useful without exposing OS errors.
    """

    current = workspace
    chain = [workspace]
    for part in relative.parts:
        current = current / part
        chain.append(current)
    for path in chain:
        try:
            metadata = os.lstat(path)
        except FileNotFoundError:
            return "missing"
        except OSError:
            return "unreadable-component"
        if stat.S_ISLNK(metadata.st_mode):
            return "symlink-component"
        if not stat.S_ISDIR(metadata.st_mode):
            return "non-directory-component"
    return "safe"


def _byox_code_policy_digest() -> str:
    material = {
        "version": _BYOX_CODE_POLICY_VERSION,
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
        },
    }
    return hashlib.sha256(canonical_json(material).encode("utf-8")).hexdigest()


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
