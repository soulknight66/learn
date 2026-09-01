#!/usr/bin/env python3
"""Deterministic structure and disclosure audit for this generated pack."""

from __future__ import print_function

import hashlib
import json
import os
import re
import stat
import sys


REQUIRED_FILES = [
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

FORBIDDEN_PATHS = [
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

EXPECTED_MANIFEST = {
    "independent_validation": "REQUIRED",
    "productionized": False,
    "project_id": "project_a39dec7bd5caf7524c0e9df3e14a2c8b",
    "provenance_sha256":
        "d0519a745a473dfc950b8a63f36eef2888db9ee8432ad93b7eb2b431dd128b3b",
    "schema_version": 1,
    "source_commit": "aa17439b62f384511a5561ce308e9598b94d8989",
    "source_id": "source_eac489a34bed5db9a1f2a580b457bcef",
    "status": "GENERATED",
    "validation_labels": ["GENERATED", "PARTIAL"],
}

# SHA-256 of the immutable provenance object serialized as sorted compact JSON.
EXPECTED_PROVENANCE_CANONICAL_SHA256 = (
    "0343524004b914e47b5ad2522b50dedc30016985a996823676752128998bf4d9"
)

LEARNER_VIEW_ALLOWLIST_PATH = (
    "sealed/reference_tests/learner_view_allowlist.json"
)
EXPECTED_LEARNER_VIEW_ALLOWLIST = {
    "files": [
        "AGENTS.md",
        "CONCEPTS.md",
        "DESIGN_QUESTIONS.md",
        "MANIFEST.yaml",
        "README.md",
        "REQUIREMENTS.md",
        "environment/README.md",
        "environment/check_toolchain.sh",
        "public_tests/Makefile",
        "public_tests/README.md",
        "public_tests/test_baseline.c",
        "public_tests/test_cli.py",
        "public_tests/test_parser_milestones.c",
        "starter/Makefile",
        "starter/README.md",
        "starter/include/byosh.h",
        "starter/src/execute.c",
        "starter/src/main.c",
        "starter/src/parser.c",
        "starter/src/pipeline.c",
    ],
    "learner_roots": ["environment", "public_tests", "starter"],
    "schema_version": 1,
}

GENERATED_TOP_FILES = [
    "README.md",
    "AGENTS.md",
    "MANIFEST.yaml",
    "PROVENANCE.json",
    "LICENSE_BOUNDARY.md",
    "REQUIREMENTS.md",
    "CONCEPTS.md",
    "DESIGN_QUESTIONS.md",
    "VALIDATION.md",
]

GENERATED_DIRECTORIES = [
    "starter",
    "public_tests",
    "environment",
    "sealed",
    "adversarial",
    "debugging",
    "review_exercises",
    "benchmarks",
]

CREDENTIAL_PATTERNS = [
    re.compile(br"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"),
    re.compile(br"AKIA[0-9A-Z]{16}"),
    re.compile(br"gh[pousr]_[A-Za-z0-9]{30,}"),
    re.compile(
        br"(?i)\b(?:password|passwd|api[_-]?key|access[_-]?token|secret)"
        br"\s*[:=]\s*[\"'][^\"'\r\n]+"
    ),
]

LEARNER_PATH_LEAKS = (
    b"sealed/",
    b"sealed\\",
    b"reference_tests",
    b"ANSWER.md",
    b"PRODUCTIONIZATION.md",
    b"wait_for_foreground_job",
    b"shell_initialize",
)


def fail(message):
    print("pack audit: FAIL: {0}".format(message), file=sys.stderr)
    raise SystemExit(1)


def normalized_json_sha256(value):
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def generated_files():
    paths = list(GENERATED_TOP_FILES)
    for base in GENERATED_DIRECTORIES:
        for root, directories, files in os.walk(base):
            for name in files:
                path = os.path.join(root, name)
                if os.path.isfile(path):
                    paths.append(path)
    return sorted(set(paths))


def check_structure():
    missing = [path for path in REQUIRED_FILES if not os.path.isfile(path)]
    if missing:
        fail("missing regular required files: {0}".format(missing))
    present = [path for path in FORBIDDEN_PATHS if os.path.lexists(path)]
    if present:
        fail("forbidden paths exist: {0}".format(present))

    special = []
    for root, directories, files in os.walk("."):
        for name in directories + files:
            path = os.path.join(root, name)
            mode = os.lstat(path).st_mode
            if stat.S_ISLNK(mode) or not (
                    stat.S_ISDIR(mode) or stat.S_ISREG(mode)):
                special.append(path)
    if special:
        fail("symlinks or special files exist: {0}".format(special))


def check_metadata():
    try:
        with open("MANIFEST.yaml", "r") as stream:
            manifest = json.load(stream)
        with open("PROVENANCE.json", "r") as stream:
            provenance = json.load(stream)
    except (OSError, ValueError) as error:
        fail("metadata is not strict readable JSON: {0}".format(error))
    if manifest != EXPECTED_MANIFEST:
        fail("MANIFEST.yaml differs from its authoritative object")
    digest = normalized_json_sha256(provenance)
    if digest != EXPECTED_PROVENANCE_CANONICAL_SHA256:
        fail("PROVENANCE.json differs from its authoritative object")


def check_learner_view_allowlist():
    try:
        with open(LEARNER_VIEW_ALLOWLIST_PATH, "r") as stream:
            allowlist = json.load(stream)
    except (OSError, ValueError) as error:
        fail("learner-view allowlist is not strict readable JSON: {0}".format(
            error
        ))
    if allowlist != EXPECTED_LEARNER_VIEW_ALLOWLIST:
        fail("learner-view allowlist differs from the disclosure contract")

    projected_files = allowlist["files"]
    missing = [path for path in projected_files if not os.path.isfile(path)]
    if missing:
        fail("learner-view allowlist references missing files: {0}".format(
            missing
        ))

    actual_root_files = []
    for base in allowlist["learner_roots"]:
        if not os.path.isdir(base):
            fail("learner-view directory root is missing: " + base)
        for root, directories, files in os.walk(base):
            directories.sort()
            for name in sorted(files):
                path = os.path.join(root, name)
                if not os.path.isfile(path):
                    fail("learner-view member is not a regular file: " + path)
                actual_root_files.append(path)
    expected_root_files = [
        path for path in projected_files if os.sep in path
    ]
    if sorted(actual_root_files) != sorted(expected_root_files):
        fail("learner roots differ from the explicit learner-view allowlist")
    return len(projected_files)


def check_answer_placement():
    answer_files = []
    for exercise_base in ("debugging", "review_exercises"):
        for root, directories, files in os.walk(exercise_base):
            for name in files:
                upper_name = name.upper()
                if upper_name.startswith("ANSWER") or upper_name.startswith(
                        "SOLUTION"):
                    path = os.path.join(root, name)
                    answer_files.append(path)
                    if os.sep + "sealed" + os.sep not in path:
                        fail("exercise answer is not locally sealed: " + path)
    if len(answer_files) != 6:
        fail("expected 6 locally sealed exercise answers, found {0}".format(
            len(answer_files)
        ))


def check_text():
    # Scan every regular generated file, not only familiar text suffixes. This
    # catches keys or assignments hidden under neutral extensions/names.
    paths = generated_files()
    for path in paths:
        with open(path, "rb") as stream:
            content = stream.read()
        for pattern in CREDENTIAL_PATTERNS:
            if pattern.search(content):
                fail("credential-like assignment or key in " + path)

    learner_files = [
        "README.md",
        "AGENTS.md",
        "MANIFEST.yaml",
        "REQUIREMENTS.md",
        "CONCEPTS.md",
        "DESIGN_QUESTIONS.md",
    ]
    for base in (
            "starter", "public_tests", "environment", "debugging",
            "review_exercises"):
        for root, directories, files in os.walk(base):
            directories[:] = [
                name for name in directories
                if name not in ("__pycache__", "sealed")
            ]
            for name in files:
                path = os.path.join(root, name)
                if os.path.isfile(path):
                    learner_files.append(path)
    for path in learner_files:
        with open(path, "rb") as stream:
            content = stream.read()
        for marker in LEARNER_PATH_LEAKS:
            if marker in content:
                fail("sealed implementation marker leaked into " + path)

    markdown_link = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
    broken = []
    for path in paths:
        if not path.endswith(".md"):
            continue
        with open(path, "r") as stream:
            content = stream.read()
        for target in markdown_link.findall(content):
            target = target.strip("<>")
            if "://" in target or target.startswith("#"):
                continue
            local_target = target.split("#", 1)[0]
            resolved = os.path.normpath(os.path.join(
                os.path.dirname(path), local_target
            ))
            if local_target and not os.path.exists(resolved):
                broken.append((path, target))
    if broken:
        fail("broken local Markdown links: {0}".format(broken))

    return len(paths)


def main():
    check_structure()
    check_metadata()
    learner_file_count = check_learner_view_allowlist()
    check_answer_placement()
    text_count = check_text()
    print("pack audit: PASS")
    print("required files: {0}".format(len(REQUIRED_FILES)))
    print("forbidden paths: 0")
    print("locally sealed exercise answers: 6")
    print("allowlisted learner-view files: {0}".format(learner_file_count))
    print("symlinks or special files: 0")
    print("credential-scanned generated files: {0}".format(text_count))
    print("manifest labels: GENERATED, PARTIAL")
    return 0


if __name__ == "__main__":
    sys.exit(main())
