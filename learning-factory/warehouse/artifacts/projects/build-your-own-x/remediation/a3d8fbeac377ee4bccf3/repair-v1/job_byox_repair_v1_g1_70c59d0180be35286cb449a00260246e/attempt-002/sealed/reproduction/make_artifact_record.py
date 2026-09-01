#!/usr/bin/env python3
"""Create or verify the canonical self-excluding Mica artifact-tree record."""

import argparse
import hashlib
import json
import os
import stat
import sys


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUTPUT_RELATIVE = "sealed/reproduction/ARTIFACT_TREE.json"
ARTIFACT_ROOTS = (
    "AGENTS.md",
    "CONCEPTS.md",
    "DESIGN_QUESTIONS.md",
    "LICENSE_BOUNDARY.md",
    "MANIFEST.yaml",
    "PROVENANCE.json",
    "README.md",
    "REQUIREMENTS.md",
    "VALIDATION.md",
    "adversarial",
    "benchmarks",
    "debugging",
    "environment",
    "public_tests",
    "review_exercises",
    "sealed",
    "starter",
)


def file_sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(65536)
            if not chunk:
                return digest.hexdigest()
            digest.update(chunk)


def inspect_path(path, relative, directories, files):
    metadata = os.lstat(path)
    if stat.S_ISLNK(metadata.st_mode):
        raise ValueError("symbolic link is not archiveable: {}".format(relative))
    mode = "{:04o}".format(stat.S_IMODE(metadata.st_mode))
    if stat.S_ISDIR(metadata.st_mode):
        directories.append({"mode": mode, "path": relative})
        for name in sorted(os.listdir(path)):
            child_relative = relative + "/" + name
            if child_relative == OUTPUT_RELATIVE:
                continue
            inspect_path(
                os.path.join(path, name), child_relative, directories, files
            )
        return
    if stat.S_ISREG(metadata.st_mode):
        files.append(
            {
                "mode": mode,
                "path": relative,
                "sha256": file_sha256(path),
                "size": metadata.st_size,
            }
        )
        return
    raise ValueError("special filesystem node is not archiveable: {}".format(relative))


def build_record():
    directories = []
    files = []
    for relative in ARTIFACT_ROOTS:
        path = os.path.join(ROOT, relative)
        if not os.path.lexists(path):
            raise ValueError("artifact root is missing: {}".format(relative))
        inspect_path(path, relative, directories, files)
    directories.sort(key=lambda item: item["path"])
    files.sort(key=lambda item: item["path"])
    canonical = json.dumps(
        {"directories": directories, "files": files},
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return {
        "algorithm": "mica-artifact-tree-v1-json-sha256",
        "directories": directories,
        "excluded_paths": [OUTPUT_RELATIVE],
        "files": files,
        "schema_version": 1,
        "tree_sha256": hashlib.sha256(canonical).hexdigest(),
    }


def main():
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    expected = build_record()
    output = os.path.join(ROOT, OUTPUT_RELATIVE)

    if args.write:
        with open(output, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(expected, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
        print(
            "artifact record written: {} files, {} directories".format(
                len(expected["files"]), len(expected["directories"])
            )
        )
        return 0

    with open(output, "r", encoding="utf-8") as handle:
        observed = json.load(handle)
    if observed != expected:
        print("artifact record FAIL: current tree differs", file=sys.stderr)
        return 1
    print(
        "artifact record PASS: {} files, {} directories".format(
            len(expected["files"]), len(expected["directories"])
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
