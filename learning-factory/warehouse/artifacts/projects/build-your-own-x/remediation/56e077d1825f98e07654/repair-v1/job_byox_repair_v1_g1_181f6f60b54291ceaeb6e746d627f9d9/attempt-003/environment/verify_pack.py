"""Deterministic structural and metadata checks for this challenge pack."""

from pathlib import Path
import hashlib
import json
import re
import stat


ROOT = Path(__file__).resolve().parent.parent

REQUIRED = [
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
]

FORBIDDEN = [
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
]

PACK_ROOTS = [
    "README.md",
    "AGENTS.md",
    "MANIFEST.yaml",
    "PROVENANCE.json",
    "LICENSE_BOUNDARY.md",
    "REQUIREMENTS.md",
    "CONCEPTS.md",
    "DESIGN_QUESTIONS.md",
    "VALIDATION.md",
    "starter",
    "public_tests",
    "environment",
    "sealed",
    "adversarial",
    "debugging",
    "review_exercises",
    "benchmarks",
]

EXPECTED_MANIFEST = {
    "independent_validation": "REQUIRED",
    "productionized": False,
    "project_id": "project_fc8ca1dbad4baba3bd2d54dbb42c1a98",
    "provenance_sha256":
        "4c4ee1a12a83ca9b6e3e8dffc3ea228bff3b778ce3d90c615a9df70dc81fe02f",
    "schema_version": 1,
    "source_commit": "aa17439b62f384511a5561ce308e9598b94d8989",
    "source_id": "source_eac489a34bed5db9a1f2a580b457bcef",
    "status": "GENERATED",
    "validation_labels": ["GENERATED", "PARTIAL"],
}

EXPECTED_MANIFEST_FILE_SHA256 = (
    "0009c3049301ee75de62cd3f2940fd3d0fac99656a925a24bc08c8dc01feeef9"
)
EXPECTED_PROVENANCE_FILE_SHA256 = (
    "4e1c553ea5c2d770f1701b6556230f609c1c30f188482c3aa1b60b3979567817"
)

CREDENTIAL_SIGNATURES = [
    re.compile(rb"-----BEGIN(?: [A-Z0-9]+)? PRIVATE KEY-----"),
    re.compile(rb"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    re.compile(rb"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    re.compile(rb"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
    re.compile(
        rb"(?ix)\b(?:password|passwd|secret|api[_-]?key|access[_-]?token)\b"
        rb"\s*[:=]\s*[\"']?[A-Za-z0-9/+_.-]{8,}"
    ),
]


def strict_object(pairs):
    """Reject duplicate JSON object keys while decoding."""
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def main():
    for name in REQUIRED:
        path = ROOT / name
        if not path.is_file() or path.is_symlink():
            raise RuntimeError(f"required regular file missing: {name}")

    for name in FORBIDDEN:
        path = ROOT / name
        if path.exists() or path.is_symlink():
            raise RuntimeError(f"forbidden path exists: {name}")

    files = []
    directories = []
    others = []
    for name in PACK_ROOTS:
        root = ROOT / name
        nodes = [root]
        if root.is_dir():
            nodes.extend(root.rglob("*"))
        for path in nodes:
            mode = path.lstat().st_mode
            if stat.S_ISREG(mode):
                files.append(path)
            elif stat.S_ISDIR(mode):
                directories.append(path)
            else:
                others.append(path)
    if others:
        names = ", ".join(str(path.relative_to(ROOT)) for path in others)
        raise RuntimeError(f"non-regular pack objects: {names}")

    manifest_bytes = (ROOT / "MANIFEST.yaml").read_bytes()
    manifest = json.loads(manifest_bytes, object_pairs_hook=strict_object)
    if manifest != EXPECTED_MANIFEST:
        raise RuntimeError("MANIFEST.yaml does not equal the required object")
    if sha256(manifest_bytes) != EXPECTED_MANIFEST_FILE_SHA256:
        raise RuntimeError("MANIFEST.yaml serialized digest changed")

    provenance_bytes = (ROOT / "PROVENANCE.json").read_bytes()
    json.loads(provenance_bytes, object_pairs_hook=strict_object)
    if sha256(provenance_bytes) != EXPECTED_PROVENANCE_FILE_SHA256:
        raise RuntimeError("PROVENANCE.json immutable snapshot digest changed")

    credential_matches = []
    for path in files:
        data = path.read_bytes()
        if any(pattern.search(data) for pattern in CREDENTIAL_SIGNATURES):
            credential_matches.append(str(path.relative_to(ROOT)))
    if credential_matches:
        raise RuntimeError(
            "credential signatures found in: " + ", ".join(credential_matches)
        )

    print(f"required paths: {len(REQUIRED)} regular files")
    print(f"forbidden paths: {len(FORBIDDEN)} absent")
    print(
        f"pack objects: {len(files)} regular files, "
        f"{len(directories)} directories, 0 other"
    )
    print("manifest: exact required object; status GENERATED; labels GENERATED, PARTIAL")
    print("provenance: valid strict JSON; immutable serialized digest matched")
    print(f"credential signature matches: {len(credential_matches)}")


if __name__ == "__main__":
    main()
