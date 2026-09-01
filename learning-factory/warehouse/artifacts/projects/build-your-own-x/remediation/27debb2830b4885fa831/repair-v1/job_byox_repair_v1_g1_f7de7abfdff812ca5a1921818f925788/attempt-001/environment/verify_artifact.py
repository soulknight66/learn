#!/usr/bin/env python3
"""Deterministic, dependency-free structure and text checks for this artifact."""

import json
import os
import re
import stat
import sys

import learner_view

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

REQUIRED = [
    "README.md", "AGENTS.md", "MANIFEST.yaml", "PROVENANCE.json", "LICENSE_BOUNDARY.md",
    "REQUIREMENTS.md", "CONCEPTS.md", "DESIGN_QUESTIONS.md", "VALIDATION.md",
    "starter/README.md", "public_tests/README.md", "environment/README.md",
    "sealed/reference/README.md", "sealed/reference_tests/README.md", "sealed/DESIGN.md",
    "sealed/TRADEOFFS.md", "sealed/REVIEW.md", "sealed/alternatives/README.md",
    "sealed/production/PRODUCTIONIZATION.md", "adversarial/README.md", "debugging/README.md",
    "review_exercises/README.md", "benchmarks/README.md"
]

FORBIDDEN = [
    ".git", ".env", ".venv", "credentials.json", "secrets", "reference", "reference_tests",
    "hidden_tests", "solution", "solutions", "answers", "starter/sealed", "starter/reference",
    "starter/reference_tests", "starter/solution", "starter/solutions", "starter/answers",
    "public_tests/sealed", "public_tests/reference", "public_tests/hidden_tests",
    "environment/sealed"
]

EXPECTED_MANIFEST = {
    "independent_validation": "REQUIRED",
    "productionized": False,
    "project_id": "project_c305a6b70f268e23e2e48694e3604f28",
    "provenance_sha256": "81ac0cb81bde3bed837ffbb1fdcdec51b9743fa4ac9627802a3de420dd3f4758",
    "schema_version": 1,
    "source_commit": "aa17439b62f384511a5561ce308e9598b94d8989",
    "source_id": "source_eac489a34bed5db9a1f2a580b457bcef",
    "status": "GENERATED",
    "validation_labels": ["GENERATED", "PARTIAL"]
}

GENERATED_TOP_FILES = [
    "README.md", "AGENTS.md", "MANIFEST.yaml", "PROVENANCE.json", "LICENSE_BOUNDARY.md",
    "REQUIREMENTS.md", "CONCEPTS.md", "DESIGN_QUESTIONS.md", "VALIDATION.md"
]
GENERATED_DIRS = [
    "starter", "public_tests", "environment", "sealed", "adversarial", "debugging",
    "review_exercises", "benchmarks"
]

CREDENTIAL_PATTERNS = [
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{36,}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"(?:password|passwd|api_key|access_token|client_secret)\s*[:=]\s*['\"][^'\"]+['\"]", re.I),
    re.compile(r"[a-z][a-z0-9+.-]*://[^\s/:]+:[^\s/@]+@", re.I)
]


def fail(message):
    raise AssertionError(message)


def artifact_files():
    paths = [os.path.join(ROOT, item) for item in GENERATED_TOP_FILES]
    for directory in GENERATED_DIRS:
        base = os.path.join(ROOT, directory)
        for current, dirnames, filenames in os.walk(base, followlinks=False):
            for name in dirnames:
                full = os.path.join(current, name)
                if os.path.islink(full):
                    fail("symlink directory found: " + os.path.relpath(full, ROOT))
            paths.extend(os.path.join(current, name) for name in filenames)
    return sorted(set(paths))


def check_structure():
    for relative in REQUIRED:
        path = os.path.join(ROOT, relative)
        if not os.path.exists(path):
            fail("missing required path: " + relative)
        mode = os.lstat(path).st_mode
        if not stat.S_ISREG(mode) or stat.S_ISLNK(mode):
            fail("required path is not a regular file: " + relative)
    for relative in FORBIDDEN:
        if os.path.lexists(os.path.join(ROOT, relative)):
            fail("forbidden path exists: " + relative)
    for path in artifact_files():
        mode = os.lstat(path).st_mode
        if not stat.S_ISREG(mode) or stat.S_ISLNK(mode):
            fail("generated path is not a regular file: " + os.path.relpath(path, ROOT))


def load_json(relative):
    with open(os.path.join(ROOT, relative), "r", encoding="utf-8") as handle:
        return json.load(handle)


def check_json():
    if load_json("MANIFEST.yaml") != EXPECTED_MANIFEST:
        fail("MANIFEST.yaml does not equal the required object")
    provenance = load_json("PROVENANCE.json")
    if provenance.get("schema_version") != 1:
        fail("unexpected provenance schema")
    if provenance.get("snapshot_sha256") != EXPECTED_MANIFEST["provenance_sha256"]:
        fail("provenance snapshot does not match manifest")
    if provenance.get("project", {}).get("project_id") != EXPECTED_MANIFEST["project_id"]:
        fail("provenance project does not match manifest")
    if provenance.get("project", {}).get("source_id") != EXPECTED_MANIFEST["source_id"]:
        fail("provenance source does not match manifest")
    for relative in [
        "starter/package.json", "public_tests/package.json", "debugging/package.json",
        "review_exercises/package.json", "sealed/package.json", "sealed/reference/package.json",
        "adversarial/corpus/cases.json"
    ]:
        load_json(relative)


def check_module_scopes():
    checked = 0
    module_declaration = re.compile(r"^\s*(?:import|export)\b", re.M)
    for path in artifact_files():
        if not path.endswith(".js"):
            continue
        with open(path, "r", encoding="utf-8") as handle:
            source = handle.read()
        if not module_declaration.search(source):
            continue
        checked += 1
        directory = os.path.dirname(path)
        while True:
            marker = os.path.join(directory, "package.json")
            if os.path.isfile(marker):
                with open(marker, "r", encoding="utf-8") as handle:
                    package = json.load(handle)
                if package.get("type") != "module":
                    fail("import-bearing JavaScript lacks type=module scope: " + os.path.relpath(path, ROOT))
                break
            if directory == ROOT:
                fail("import-bearing JavaScript has no package scope: " + os.path.relpath(path, ROOT))
            parent = os.path.dirname(directory)
            if parent == directory or not (parent == ROOT or parent.startswith(ROOT + os.sep)):
                fail("module-scope search escaped artifact: " + os.path.relpath(path, ROOT))
            directory = parent
    return checked


def check_learner_source_boundaries():
    checked = 0
    import_specifier = re.compile(
        r"(?:\bfrom\s*|\bimport\s*(?:\(\s*)?)['\"]([^'\"]+)['\"]"
    )
    prohibited_import_parts = {
        "sealed", "reference", "reference_tests", "hidden_tests",
        "solution", "solutions", "answer", "answers"
    }
    prohibited_host_api = re.compile(
        r"\b(?:eval|Function|child_process|process\.env)\b|node:(?:fs|net|http|https)"
    )
    for relative_dir in ["starter/src", "public_tests"]:
        base = os.path.join(ROOT, relative_dir)
        for current, unused_dirnames, filenames in os.walk(base):
            del unused_dirnames
            for filename in sorted(filenames):
                if not filename.endswith((".js", ".mjs")):
                    continue
                checked += 1
                path = os.path.join(current, filename)
                with open(path, "r", encoding="utf-8") as handle:
                    source = handle.read()
                for specifier in import_specifier.findall(source):
                    parts = set(part.lower() for part in specifier.replace("\\", "/").split("/"))
                    if parts.intersection(prohibited_import_parts):
                        fail("learner source imports evaluator material: " + os.path.relpath(path, ROOT))
                if relative_dir == "starter/src" and prohibited_host_api.search(source):
                    fail("starter source uses a prohibited host API: " + os.path.relpath(path, ROOT))
    return checked


def check_credentials():
    for path in artifact_files():
        with open(path, "r", encoding="utf-8") as handle:
            text = handle.read()
        for pattern in CREDENTIAL_PATTERNS:
            if pattern.search(text):
                fail("credential-like content in " + os.path.relpath(path, ROOT))


def check_javascript_delimiters():
    checked = 0
    for path in artifact_files():
        if not path.endswith((".js", ".mjs")):
            continue
        checked += 1
        with open(path, "r", encoding="utf-8") as handle:
            source = handle.read()
        scan_delimiters(source, os.path.relpath(path, ROOT))
    return checked


def scan_delimiters(source, label):
    pairs = {")": "(", "]": "[", "}": "{"}
    stack = []
    state = "code"
    escaped = False
    index = 0
    while index < len(source):
        char = source[index]
        following = source[index + 1] if index + 1 < len(source) else ""
        if state in ("single", "double", "template"):
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif (state == "single" and char == "'") or (state == "double" and char == '"') or (state == "template" and char == "`"):
                state = "code"
            index += 1
            continue
        if state == "line-comment":
            if char in "\r\n":
                state = "code"
            index += 1
            continue
        if state == "block-comment":
            if char == "*" and following == "/":
                state = "code"
                index += 2
            else:
                index += 1
            continue
        if char == "/" and following == "/":
            state = "line-comment"
            index += 2
            continue
        if char == "/" and following == "*":
            state = "block-comment"
            index += 2
            continue
        if char == "'":
            state = "single"
        elif char == '"':
            state = "double"
        elif char == "`":
            state = "template"
        elif char in "([{":
            stack.append(char)
        elif char in ")]}":
            if not stack or stack.pop() != pairs[char]:
                fail("unbalanced delimiter in " + label)
        index += 1
    if state not in ("code", "line-comment"):
        fail("unterminated string or comment in " + label)
    if stack:
        fail("unclosed delimiter in " + label)


def main():
    check_structure()
    check_json()
    check_credentials()
    module_count = check_module_scopes()
    learner_source_count = check_learner_source_boundaries()
    view_policy = learner_view.check_policy()
    javascript_count = check_javascript_delimiters()
    print("artifact verification: PASS ({0} required paths, 0 forbidden paths)".format(len(REQUIRED)))
    print("JSON and credential-pattern scans: PASS")
    print("explicit ECMAScript module scopes: PASS ({0} import-bearing .js files)".format(module_count))
    print("learner source isolation/host-API scan: PASS ({0} files)".format(learner_source_count))
    print("learner-view allowlist policy: PASS ({0} files; 0 sealed hash collisions)".format(
        view_policy["learner_files"]
    ))
    print("lightweight JavaScript delimiter scan: PASS ({0} files; not a syntax check)".format(javascript_count))


if __name__ == "__main__":
    try:
        main()
    except (AssertionError, OSError, ValueError) as error:
        print("artifact verification: FAIL: " + str(error), file=sys.stderr)
        sys.exit(1)
