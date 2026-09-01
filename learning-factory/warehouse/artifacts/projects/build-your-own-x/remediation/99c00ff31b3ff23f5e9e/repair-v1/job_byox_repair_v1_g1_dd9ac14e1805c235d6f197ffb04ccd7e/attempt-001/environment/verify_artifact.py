#!/usr/bin/env python3
"""Deterministically verify complete-pack structure, content, and hygiene."""

import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys


ROOT = Path(__file__).resolve().parents[1]
REQUIRED = (
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
    "starter/Makefile",
    "starter/src/mica.c",
    "starter/include/mica_limits.h",
    "starter/examples/countdown.mica",
    "public_tests/README.md",
    "public_tests/test_public.py",
    "environment/README.md",
    "environment/check_environment.py",
    "environment/verify_artifact.py",
    "environment/materialize_student_view.py",
    "environment/verify_student_view.py",
    "environment/STUDENT_VIEW_INVENTORY.json",
    "sealed/reference/README.md",
    "sealed/reference/Makefile",
    "sealed/reference/src/mica.c",
    "sealed/reference/include/mica_limits.h",
    "sealed/reference/examples/fibonacci.mica",
    "sealed/reference_tests/README.md",
    "sealed/reference_tests/test_reference.py",
    "sealed/DESIGN.md",
    "sealed/TRADEOFFS.md",
    "sealed/REVIEW.md",
    "sealed/alternatives/README.md",
    "sealed/production/PRODUCTIONIZATION.md",
    "sealed/debugging/exercise-01/ANSWER.md",
    "sealed/review_exercises/exercise-01/ANSWER.md",
    "sealed/integrity/update_inventories.py",
    "sealed/ARTIFACT_INVENTORY.json",
    "adversarial/README.md",
    "adversarial/cases/arithmetic_edges.mica",
    "adversarial/cases/skipped_declaration.mica",
    "adversarial/cases/runtime_error.mica",
    "debugging/README.md",
    "review_exercises/README.md",
    "benchmarks/README.md",
)
FORBIDDEN = (
    ".git",
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
ARTIFACT_ROOT_FILES = (
    "README.md",
    "AGENTS.md",
    "MANIFEST.yaml",
    "PROVENANCE.json",
    "LICENSE_BOUNDARY.md",
    "REQUIREMENTS.md",
    "CONCEPTS.md",
    "DESIGN_QUESTIONS.md",
    "VALIDATION.md",
)
ARTIFACT_DIRECTORIES = (
    "starter",
    "public_tests",
    "environment",
    "sealed",
    "adversarial",
    "debugging",
    "review_exercises",
    "benchmarks",
)
ARTIFACT_INVENTORY = "sealed/ARTIFACT_INVENTORY.json"
EXPECTED_PROVENANCE_CANONICAL_SHA256 = (
    "89e2d6b2fddf6b8cd2a643e8f9290374bad176c3bc446ecbd23a7f9b21358808"
)
EXPECTED_MANIFEST = {
    "independent_validation": "REQUIRED",
    "productionized": False,
    "project_id": "project_bd342fcec50cb8a15740cbb98e57bc1e",
    "provenance_sha256": "16c1f2fa7154cfbf9531c6d77cf7024fd08511e5def5b6488d364f550056629b",
    "schema_version": 1,
    "source_commit": "aa17439b62f384511a5561ce308e9598b94d8989",
    "source_id": "source_eac489a34bed5db9a1f2a580b457bcef",
    "status": "GENERATED",
    "validation_labels": ["GENERATED", "PARTIAL"],
}
PATTERNS = (
    re.compile(br"AKIA[0-9A-Z]{16}"),
    re.compile(br"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(br"gh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(br"sk-[A-Za-z0-9]{20,}"),
    re.compile(br"(?:password|passwd)\s*=\s*[^\s]+", re.IGNORECASE),
)


def fail(message):
    print("FAIL: {}".format(message))
    return False


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            block = handle.read(65536)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def artifact_paths():
    for relative in ARTIFACT_ROOT_FILES:
        path = ROOT / relative
        if path.exists() or path.is_symlink():
            yield path
    for directory in ARTIFACT_DIRECTORIES:
        base = ROOT / directory
        if not base.exists() or base.is_symlink():
            if base.is_symlink():
                yield base
            continue
        yield base
        for current, directories, files in os.walk(str(base), followlinks=False):
            directories.sort()
            files.sort()
            current_path = Path(current)
            for name in directories:
                yield current_path / name
            for name in files:
                yield current_path / name


def regular_artifact_files():
    files = {}
    for path in artifact_paths():
        mode = path.lstat().st_mode
        if stat.S_ISREG(mode) and not path.is_symlink():
            files[str(path.relative_to(ROOT))] = path
    return files


def verify_metadata():
    try:
        with (ROOT / "MANIFEST.yaml").open("r", encoding="utf-8") as handle:
            manifest = json.load(handle)
        with (ROOT / "PROVENANCE.json").open("r", encoding="utf-8") as handle:
            provenance = json.load(handle)
    except (OSError, ValueError) as error:
        return fail("cannot load immutable metadata: {}".format(error))
    canonical = json.dumps(
        provenance, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    if (
        manifest != EXPECTED_MANIFEST
        or hashlib.sha256(canonical).hexdigest()
        != EXPECTED_PROVENANCE_CANONICAL_SHA256
        or provenance.get("snapshot_sha256") != manifest["provenance_sha256"]
    ):
        return fail("metadata does not match immutable expected objects")
    print("metadata: strict JSON and exact expected objects")
    print(
        "provenance-identifiers: manifest value is snapshot id; canonical-json sha256 {}".format(
            EXPECTED_PROVENANCE_CANONICAL_SHA256
        )
    )
    return True


def verify_inventory(regular):
    inventory_path = ROOT / ARTIFACT_INVENTORY
    try:
        with inventory_path.open("r", encoding="utf-8") as handle:
            inventory = json.load(handle)
    except (OSError, ValueError) as error:
        return fail("cannot load artifact inventory: {}".format(error))
    keys = {"algorithm", "excluded_from_hashes", "files", "schema_version", "scope"}
    if (
        set(inventory) != keys
        or inventory.get("algorithm") != "sha256"
        or inventory.get("excluded_from_hashes") != [ARTIFACT_INVENTORY]
        or inventory.get("schema_version") != 1
        or inventory.get("scope")
        != "complete challenge pack except this self-referential inventory"
        or not isinstance(inventory.get("files"), list)
    ):
        return fail("malformed artifact inventory metadata")

    entries = inventory["files"]
    entry_paths = [entry.get("path") for entry in entries if isinstance(entry, dict)]
    actual_paths = sorted(path for path in regular if path != ARTIFACT_INVENTORY)
    if (
        len(entry_paths) != len(entries)
        or entry_paths != sorted(entry_paths)
        or entry_paths != actual_paths
    ):
        return fail("artifact inventory path set differs from complete pack")
    for entry in entries:
        if set(entry) != {"path", "sha256", "size", "type"}:
            return fail("malformed inventory entry for {}".format(entry.get("path")))
        path = regular[entry["path"]]
        if (
            entry["type"] != "regular-file"
            or entry["size"] != path.stat().st_size
            or entry["sha256"] != sha256_file(path)
        ):
            return fail("artifact content mismatch: {}".format(entry["path"]))
    print(
        "artifact-content-inventory: {0}/{0} regular files match sha256".format(
            len(entries)
        )
    )
    print(
        "provenance-file-sha256: {} (content-inventory checked)".format(
            sha256_file(ROOT / "PROVENANCE.json")
        )
    )
    return True


def main():
    if not (ROOT / "sealed").exists():
        sys.dont_write_bytecode = True
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from verify_student_view import verify
        return verify(ROOT)

    ok = True
    missing = [relative for relative in REQUIRED if not (ROOT / relative).is_file()]
    if missing:
        ok = fail("missing required operational paths: {}".format(", ".join(missing))) and ok
    else:
        print(
            "required-operational-paths: {0}/{0} regular files present".format(
                len(REQUIRED)
            )
        )

    present = [relative for relative in FORBIDDEN if (ROOT / relative).exists()]
    if present:
        ok = fail("forbidden paths present: {}".format(", ".join(present))) and ok
    else:
        print("forbidden-paths: absent")

    unusual = []
    for path in artifact_paths():
        mode = path.lstat().st_mode
        if not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)) or path.is_symlink():
            unusual.append(str(path.relative_to(ROOT)))
    if unusual:
        ok = fail("symlinks or special files: {}".format(", ".join(unusual))) and ok
    else:
        print("symlinks-or-special-files: 0")

    learner_forbidden = []
    bad_names = {
        "sealed", "reference", "reference_tests", "hidden_tests",
        "solution", "solutions", "answers",
    }
    for base_name in ("starter", "public_tests", "environment"):
        base = ROOT / base_name
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            if path.name in bad_names:
                learner_forbidden.append(str(path.relative_to(ROOT)))
    if learner_forbidden:
        ok = fail(
            "forbidden learner names: {}".format(", ".join(learner_forbidden))
        ) and ok
    else:
        print("learner-directory-forbidden-names: 0")

    ok = verify_metadata() and ok
    regular = regular_artifact_files()
    ok = verify_inventory(regular) and ok

    matches = []
    for relative, path in sorted(regular.items()):
        content = path.read_bytes()
        if any(pattern.search(content) for pattern in PATTERNS):
            matches.append(relative)
    if matches:
        ok = fail("credential-shaped content: {}".format(", ".join(matches))) and ok
    else:
        print("credential-pattern-scan: no matches")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
