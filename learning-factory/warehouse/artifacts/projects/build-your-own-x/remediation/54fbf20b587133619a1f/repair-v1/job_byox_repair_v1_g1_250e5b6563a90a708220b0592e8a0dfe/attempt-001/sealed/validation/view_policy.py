#!/usr/bin/env python3
"""Audit and project deterministic, default-deny learner views."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import sys


ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "environment" / "view-policy.json"
BASE = (
    "README.md",
    "AGENTS.md",
    "MANIFEST.yaml",
    "REQUIREMENTS.md",
    "CONCEPTS.md",
    "DESIGN_QUESTIONS.md",
    "starter",
    "public_tests",
    "environment",
)
STAGES = (
    ("core", ()),
    ("debugging", ("debugging",)),
    ("review", ("review_exercises",)),
    ("adversarial", ("adversarial",)),
    ("benchmarks", ("benchmarks",)),
)
DENY_PREFIXES = ("sealed",)
POLICY_KEYS = {
    "schema_version",
    "default_action",
    "follow_symlinks",
    "deny_prefixes",
    "learner_base",
    "stages",
}
LEARNER_TOP_LEVEL = set(BASE) | {
    "debugging",
    "review_exercises",
    "adversarial",
    "benchmarks",
}


def reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key: {}".format(key))
        result[key] = value
    return result


def load_policy():
    return json.loads(
        POLICY_PATH.read_text(encoding="utf-8"),
        object_pairs_hook=reject_duplicate_keys,
    )


def validate_policy(policy):
    if not isinstance(policy, dict) or set(policy) != POLICY_KEYS:
        raise AssertionError("view policy has unexpected top-level fields")
    if policy["schema_version"] != 1:
        raise AssertionError("unsupported view policy schema")
    if policy["default_action"] != "deny":
        raise AssertionError("view policy must be default-deny")
    if policy["follow_symlinks"] is not False:
        raise AssertionError("view policy must not follow symlinks")
    if policy["deny_prefixes"] != list(DENY_PREFIXES):
        raise AssertionError("sealed/ must be an explicit denied prefix")
    if policy["learner_base"] != list(BASE):
        raise AssertionError("learner base differs from the authoritative allowlist")

    expected = [
        {"name": name, "reveal": list(reveal)}
        for name, reveal in STAGES
    ]
    if policy["stages"] != expected:
        raise AssertionError("stage order or reveal roots differ from the authoritative policy")


def ensure_relative(relative):
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts or str(candidate) in ("", "."):
        raise AssertionError("invalid view root: {!r}".format(relative))
    return candidate


def files_under(relative):
    relative_path = ensure_relative(relative)
    absolute = ROOT / relative_path
    try:
        mode = absolute.lstat().st_mode
    except OSError as error:
        raise AssertionError("missing view root {}: {}".format(relative, error))

    if stat.S_ISREG(mode):
        return [relative_path.as_posix()]
    if not stat.S_ISDIR(mode):
        raise AssertionError("view root is not a regular file or directory: {}".format(relative))

    result = []
    for directory, dirnames, filenames in os.walk(str(absolute), followlinks=False):
        dirnames.sort()
        filenames.sort()
        for name in list(dirnames):
            child = Path(directory) / name
            child_mode = child.lstat().st_mode
            if not stat.S_ISDIR(child_mode):
                raise AssertionError("view contains a symlink or special directory: {}".format(
                    child.relative_to(ROOT).as_posix()
                ))
        for name in filenames:
            child = Path(directory) / name
            child_mode = child.lstat().st_mode
            if not stat.S_ISREG(child_mode):
                raise AssertionError("view contains a symlink or special file: {}".format(
                    child.relative_to(ROOT).as_posix()
                ))
            result.append(child.relative_to(ROOT).as_posix())
    return result


def digest_paths(paths, root=ROOT):
    records = []
    for relative in sorted(paths):
        content = (root / relative).read_bytes()
        records.append([relative, hashlib.sha256(content).hexdigest()])
    encoded = json.dumps(records, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def audit_views():
    policy = load_policy()
    validate_policy(policy)
    cumulative_roots = list(BASE)
    previous = set()
    audits = []

    for name, reveal in STAGES:
        cumulative_roots.extend(reveal)
        paths = set()
        for root in cumulative_roots:
            paths.update(files_under(root))
        if not previous.issubset(paths):
            raise AssertionError("stage {} is not cumulative".format(name))
        previous = paths

        for relative in paths:
            top = relative.split("/", 1)[0]
            if top not in LEARNER_TOP_LEVEL:
                raise AssertionError("stage {} exposes non-learner path {}".format(name, relative))
            if any(relative == denied or relative.startswith(denied + "/") for denied in DENY_PREFIXES):
                raise AssertionError("stage {} exposes denied path {}".format(name, relative))

        revealed = set(cumulative_roots)
        for later_root in {item for _, additions in STAGES for item in additions} - revealed:
            if any(path == later_root or path.startswith(later_root + "/") for path in paths):
                raise AssertionError("stage {} exposes unrevealed root {}".format(name, later_root))

        ordered = sorted(paths)
        audits.append({
            "name": name,
            "roots": list(cumulative_roots),
            "paths": ordered,
            "files": len(ordered),
            "algorithm": "path-content-sha256-v1",
            "sha256": digest_paths(ordered),
        })
    return audits


def select_view(name):
    for audit in audit_views():
        if audit["name"] == name:
            return audit
    raise ValueError("unknown view {!r}".format(name))


def export_view(name, output_text):
    audit = select_view(name)
    output = Path(os.path.abspath(output_text))
    root_text = str(ROOT)
    output_text = str(output)
    if output_text == root_text or output_text.startswith(root_text + os.sep):
        raise ValueError("output must be outside the complete administrator pack")
    if output.exists() or output.is_symlink():
        raise ValueError("output path already exists")

    output.mkdir(parents=True)
    try:
        for relative in audit["paths"]:
            destination = output / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(ROOT / relative), str(destination))
        copied = []
        for directory, dirnames, filenames in os.walk(str(output), followlinks=False):
            dirnames.sort()
            filenames.sort()
            for filename in filenames:
                copied.append((Path(directory) / filename).relative_to(output).as_posix())
        copied.sort()
        if copied != audit["paths"] or digest_paths(copied, output) != audit["sha256"]:
            raise AssertionError("exported view does not match its audited identity")
    except Exception:
        shutil.rmtree(str(output))
        raise
    return audit


def main(arguments=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("audit", help="audit every view without materializing it")
    list_parser = subparsers.add_parser("list", help="list one view's regular files")
    list_parser.add_argument("view", choices=[name for name, _ in STAGES])
    export_parser = subparsers.add_parser("export", help="materialize one new view outside this pack")
    export_parser.add_argument("view", choices=[name for name, _ in STAGES])
    export_parser.add_argument("output")
    options = parser.parse_args(arguments)

    if options.command is None:
        parser.error("a command is required")
    if options.command == "audit":
        for audit in audit_views():
            print("{} files={} sha256={}".format(audit["name"], audit["files"], audit["sha256"]))
        print("VIEW POLICY AUDIT PASS")
        return 0
    if options.command == "list":
        audit = select_view(options.view)
        for relative in audit["paths"]:
            print(relative)
        print("{} files={} sha256={}".format(audit["name"], audit["files"], audit["sha256"]))
        return 0

    audit = export_view(options.view, options.output)
    print("exported {} files={} sha256={}".format(audit["name"], audit["files"], audit["sha256"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
