#!/usr/bin/env python3
"""Deterministic structural checks for the generated challenge artifact.

This script intentionally supports Python 3.6 and newer so the documented
``python3`` command works on the factory's oldest validator host.
"""

import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys


ROOT = Path(__file__).resolve().parents[2]
CONTROL_NAMES = {
    ".git",
    ".agents",
    ".codex",
    ".factory-workspace",
    "JOB.md",
    "PRIOR_BUILD",
    "PRIOR_REVIEW",
}

REQUIRED_PATHS = (
    "README.md",
    "AGENTS.md",
    "MANIFEST.yaml",
    "PROVENANCE.json",
    "LICENSE_BOUNDARY.md",
    "REQUIREMENTS.md",
    "CONCEPTS.md",
    "DESIGN_QUESTIONS.md",
    "VALIDATION.md",
    "starter/README.md",
    "public_tests/README.md",
    "environment/README.md",
    "sealed/reference/README.md",
    "sealed/reference_tests/README.md",
    "sealed/DESIGN.md",
    "sealed/TRADEOFFS.md",
    "sealed/REVIEW.md",
    "sealed/alternatives/README.md",
    "sealed/production/PRODUCTIONIZATION.md",
    "adversarial/README.md",
    "debugging/README.md",
    "review_exercises/README.md",
    "benchmarks/README.md",
)

FORBIDDEN_ARTIFACT_PATHS = (
    ".env",
    ".venv",
    "credentials.json",
    "secrets",
    "reference",
    "reference_tests",
    "hidden_tests",
    "solution",
    "solutions",
    "answers",
    "starter/sealed",
    "starter/reference",
    "starter/reference_tests",
    "starter/solution",
    "starter/solutions",
    "starter/answers",
    "public_tests/sealed",
    "public_tests/reference",
    "public_tests/hidden_tests",
    "environment/sealed",
)

EXPECTED_LEARNER_PATHS = (
    "AGENTS.md",
    "CONCEPTS.md",
    "DESIGN_QUESTIONS.md",
    "MANIFEST.yaml",
    "README.md",
    "REQUIREMENTS.md",
    "environment/README.md",
    "environment/student-view-files.txt",
    "public_tests/README.md",
    "public_tests/run.sh",
    "public_tests/src/io/learningfactory/kafkalite/ContractTests.java",
    "starter/README.md",
    "starter/src/main/java/io/learningfactory/kafkalite/LogRecord.java",
    "starter/src/main/java/io/learningfactory/kafkalite/PartitionLog.java",
    "starter/src/main/java/io/learningfactory/kafkalite/ReplicatedPartition.java",
)

# These canonical hashes fingerprint the exact JSON objects supplied to this job.
EXPECTED_CANONICAL_HASHES = {
    "MANIFEST.yaml": "0189d1bdb1e7dc36f63c14bb6ff334a9bab5b0b182423a44a47d97a4b7a51df8",
    "PROVENANCE.json": "62094b8a14e6bcdd9deb3dd67888b4a96489872debc725ad2f96e04379168fb4",
}

PUBLIC_MILESTONE_GROUPS = (
    (
        "milestone-1",
        (
            "recordSnapshotsItsValue",
            "partitionAssignsOffsets",
            "partitionReadsByOffset",
            "partitionRejectsInvalidRequests",
        ),
    ),
    (
        "milestone-2",
        ("replicatedConfigurationIsValidated", "replicatedAppendCommits"),
    ),
    (
        "milestone-3",
        (
            "quorumLossRejectsWithoutMutation",
            "leaderFailoverIsDeterministic",
            "noAvailableLeader",
        ),
    ),
    (
        "milestone-4",
        (
            "recoveredReplicaCatchesUp",
            "recoveredFormerLeaderDoesNotPreempt",
            "allDownSingletonRecoversIdempotently",
        ),
    ),
)

HIGH_CONFIDENCE_CREDENTIAL_PATTERNS = (
    re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(rb"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(rb"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(rb"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
    re.compile(rb"(?i)\b(?:password|passwd|api[_-]?key|secret[_-]?key)\s*[:=]\s*['\"][^'\"\r\n]{8,}['\"]"),
)


class ValidationError(RuntimeError):
    pass


def strict_json(path):
    def pairs_hook(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValidationError(f"duplicate JSON key {key!r} in {path.name}")
            result[key] = value
        return result

    def reject_constant(value):
        raise ValidationError(f"non-finite JSON number {value!r} in {path.name}")

    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=pairs_hook,
            parse_constant=reject_constant,
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValidationError(f"invalid strict JSON in {path.name}: {error}") from error


def canonical_hash(value):
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_java_lexical_structure(paths):
    java_paths = [path for path in paths if path.is_file() and path.suffix == ".java"]
    opening_to_closing = {"(": ")", "[": "]", "{": "}"}
    for path in java_paths:
        source = path.read_text(encoding="utf-8")
        without_literals = re.sub(
            r"/\*.*?\*/|//[^\n]*|\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'",
            "",
            source,
            flags=re.DOTALL,
        )
        stack = []
        for character in without_literals:
            if character in opening_to_closing:
                stack.append(character)
            elif character in opening_to_closing.values():
                if not stack or opening_to_closing[stack.pop()] != character:
                    raise ValidationError(f"unbalanced delimiter in {path.relative_to(ROOT)}")
        if stack:
            raise ValidationError(f"unclosed delimiter in {path.relative_to(ROOT)}")
        public_class = re.search(r"public\s+final\s+class\s+(\w+)", without_literals)
        if public_class is None or public_class.group(1) != path.stem:
            raise ValidationError(f"public class/filename mismatch in {path.relative_to(ROOT)}")
    return len(java_paths)


def artifact_paths():
    paths = []
    for directory, directory_names, file_names in os.walk(ROOT, followlinks=False):
        relative_directory = Path(directory).relative_to(ROOT)
        if relative_directory == Path("."):
            directory_names[:] = [name for name in directory_names if name not in CONTROL_NAMES]
            file_names = [name for name in file_names if name not in CONTROL_NAMES]
        for name in directory_names:
            paths.append(Path(directory, name))
        for name in file_names:
            paths.append(Path(directory, name))
    return paths


def validate_learner_allowlist():
    allowlist_path = ROOT / "environment/student-view-files.txt"
    try:
        listed_paths = tuple(allowlist_path.read_text(encoding="utf-8").splitlines())
    except (OSError, UnicodeError) as error:
        raise ValidationError("cannot read learner-view allowlist: {}".format(error))
    if listed_paths != EXPECTED_LEARNER_PATHS:
        raise ValidationError("learner-view allowlist is not the exact sorted expected inventory")
    for relative_name in listed_paths:
        relative_path = Path(relative_name)
        if (relative_path.is_absolute() or ".." in relative_path.parts
                or "sealed" in relative_path.parts):
            raise ValidationError("unsafe learner-view path: {}".format(relative_name))
        target = ROOT / relative_path
        if not target.is_file() or target.is_symlink():
            raise ValidationError("learner-view entry is not a regular file: {}".format(relative_name))
    return len(listed_paths)


def java_test_method_sections(source):
    matches = list(re.finditer(r"^    private static void (\w+)\(", source, re.MULTILINE))
    sections = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(source)
        sections[match.group(1)] = source[match.start():end]
    return sections


def validate_public_milestone_isolation():
    path = ROOT / "public_tests/src/io/learningfactory/kafkalite/ContractTests.java"
    source = path.read_text(encoding="utf-8")
    sections = java_test_method_sections(source)

    for index, (milestone, expected_methods) in enumerate(PUBLIC_MILESTONE_GROUPS):
        marker = '        if (isSelected(selection, "{}")) {{'.format(milestone)
        start = source.find(marker)
        if start < 0:
            raise ValidationError("missing public selector block for " + milestone)
        if index + 1 < len(PUBLIC_MILESTONE_GROUPS):
            next_milestone = PUBLIC_MILESTONE_GROUPS[index + 1][0]
            end_marker = '        if (isSelected(selection, "{}")) {{'.format(next_milestone)
        else:
            end_marker = '        System.out.println("PASS: "'
        end = source.find(end_marker, start + len(marker))
        if end < 0:
            raise ValidationError("cannot bound public selector block for " + milestone)
        actual_methods = tuple(re.findall(r"ContractTests::(\w+)", source[start:end]))
        if actual_methods != expected_methods:
            raise ValidationError(
                "public selector {} has methods {}, expected {}".format(
                    milestone, actual_methods, expected_methods))
        missing_sections = [name for name in expected_methods if name not in sections]
        if missing_sections:
            raise ValidationError(
                "missing public test method(s): " + ", ".join(missing_sections))

    milestone_two_source = "\n".join(
        sections[name] for name in PUBLIC_MILESTONE_GROUPS[1][1])
    later_fault_calls = (
        "failReplica(",
        "recoverReplica(",
        "isReplicaAvailable(",
        "replicaEndOffset(",
    )
    unexpected = [call for call in later_fault_calls if call in milestone_two_source]
    if unexpected:
        raise ValidationError(
            "milestone-2 invokes later fault/recovery API(s): " + ", ".join(unexpected))

    milestone_three_source = "\n".join(
        sections[name] for name in PUBLIC_MILESTONE_GROUPS[2][1])
    if "recoverReplica(" in milestone_three_source:
        raise ValidationError("milestone-3 invokes milestone-4 recovery")

    return tuple(len(methods) for _, methods in PUBLIC_MILESTONE_GROUPS)


def validate_learner_document_consistency():
    requirements = (ROOT / "REQUIREMENTS.md").read_text(encoding="utf-8")
    expected_leader_rule = "chooses the lowest configured replica ID as the initial leader"
    if expected_leader_rule not in requirements:
        raise ValidationError("authoritative requirements omit the lowest-ID initial leader rule")

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    omitted_internal_documents = ("VALIDATION.md", "PROVENANCE.json", "LICENSE_BOUNDARY.md")
    dead_references = [name for name in omitted_internal_documents if name in readme]
    if dead_references:
        raise ValidationError(
            "exported README references omitted internal document(s): "
            + ", ".join(dead_references))
    for required_notice in ("NOASSERTION", "CC0-1.0", "SPDX-License-Identifier: CC0-1.0"):
        if required_notice not in readme:
            raise ValidationError(
                "exported README omits learner-safe notice fragment: " + required_notice)
    if "/projects/" in readme:
        raise ValidationError("exported README contains an internal absolute project path")


def validate():
    missing = [path for path in REQUIRED_PATHS if not (ROOT / path).is_file()]
    if missing:
        raise ValidationError("missing required regular files: " + ", ".join(missing))

    forbidden = [path for path in FORBIDDEN_ARTIFACT_PATHS if (ROOT / path).exists()]
    if forbidden:
        raise ValidationError("forbidden artifact paths exist: " + ", ".join(forbidden))

    paths = artifact_paths()
    irregular = []
    for path in paths:
        mode = path.lstat().st_mode
        if not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
            irregular.append(str(path.relative_to(ROOT)))
    if irregular:
        raise ValidationError("non-regular artifact entries: " + ", ".join(irregular))

    for name, expected_hash in EXPECTED_CANONICAL_HASHES.items():
        actual_hash = canonical_hash(strict_json(ROOT / name))
        if actual_hash != expected_hash:
            raise ValidationError(
                f"{name} object mismatch: expected {expected_hash}, got {actual_hash}"
            )

    manifest = strict_json(ROOT / "MANIFEST.yaml")
    if not isinstance(manifest, dict):
        raise ValidationError("manifest root is not an object")
    if manifest.get("status") != "GENERATED":
        raise ValidationError("manifest status is not GENERATED")
    if manifest.get("validation_labels") != ["GENERATED", "PARTIAL"]:
        raise ValidationError("manifest labels are not exactly GENERATED, PARTIAL")

    credential_hits = []
    for path in paths:
        if not stat.S_ISREG(path.lstat().st_mode):
            continue
        data = path.read_bytes()
        if any(pattern.search(data) for pattern in HIGH_CONFIDENCE_CREDENTIAL_PATTERNS):
            credential_hits.append(str(path.relative_to(ROOT)))
    if credential_hits:
        raise ValidationError(
            "possible credential material in: " + ", ".join(credential_hits)
        )

    build_products = [
        str(path.relative_to(ROOT))
        for path in paths
        if path.is_file() and path.suffix.lower() in {".class", ".jar", ".war"}
    ]
    if build_products:
        raise ValidationError("archived build products found: " + ", ".join(build_products))

    learner_path_count = validate_learner_allowlist()
    milestone_case_counts = validate_public_milestone_isolation()
    validate_learner_document_consistency()
    java_source_count = validate_java_lexical_structure(paths)

    print(f"PASS required regular files: {len(REQUIRED_PATHS)}")
    print("PASS forbidden generated artifact paths: 0")
    print("PASS artifact entry types: regular files/directories only")
    print("PASS strict manifest/provenance object fingerprints")
    print("PASS status and labels: GENERATED + PARTIAL")
    print("PASS high-confidence credential scan: 0 hits")
    print("PASS archived Java build products: 0")
    print(f"PASS learner-view exact allowlist: {learner_path_count} regular files, 0 sealed paths")
    print("PASS learner-visible contract: lowest-ID leader and self-contained license notice")
    print(
        "PASS public milestone isolation: {} cases".format(
            "/".join(str(count) for count in milestone_case_counts)))
    print(f"PASS Java lexical structure: {java_source_count} source files")
    if (ROOT / ".git").exists():
        print("NOTE pre-existing read-only factory control .git excluded from artifact scan")


if __name__ == "__main__":
    try:
        validate()
    except ValidationError as error:
        print(f"FAIL {error}", file=sys.stderr)
        raise SystemExit(1)
