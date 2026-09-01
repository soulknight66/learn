#!/usr/bin/env python3

"""Verify immutable metadata, required paths, and archive-safe file types."""

import json
import os
from pathlib import Path
import re
import stat
import sys


ROOT = Path(__file__).resolve().parents[2]


def tagged_json(job_text, name):
    match = re.search(
        r"<" + re.escape(name) + r">\s*(.*?)\s*</" + re.escape(name) + r">",
        job_text,
        re.DOTALL,
    )
    if match is None:
        raise ValueError("missing data block: " + name)
    return json.loads(match.group(1))


def main():
    job_text = (ROOT / "JOB.md").read_text(encoding="utf-8")
    required = tagged_json(job_text, "required-paths")
    forbidden = tagged_json(job_text, "forbidden-paths")
    expected_manifest = tagged_json(job_text, "manifest-data")
    expected_provenance = tagged_json(job_text, "provenance-data")

    missing = [path for path in required if not (ROOT / path).is_file()]
    present_forbidden = [
        path for path in forbidden if os.path.lexists(str(ROOT / path))
    ]
    actual_manifest = json.loads(
        (ROOT / "MANIFEST.yaml").read_text(encoding="utf-8")
    )
    actual_provenance = json.loads(
        (ROOT / "PROVENANCE.json").read_text(encoding="utf-8")
    )

    non_regular = []
    for current_root, directories, files in os.walk(str(ROOT), followlinks=False):
        for name in directories + files:
            path = Path(current_root) / name
            mode = os.lstat(str(path)).st_mode
            if not (stat.S_ISDIR(mode) or stat.S_ISREG(mode)):
                non_regular.append(str(path.relative_to(ROOT)))

    checks = {
        "required_regular_files": not missing,
        "forbidden_paths_absent": not present_forbidden,
        "manifest_exact_object": actual_manifest == expected_manifest,
        "provenance_exact_object": actual_provenance == expected_provenance,
        "only_regular_files_and_directories": not non_regular,
        "status_generated": actual_manifest.get("status") == "GENERATED",
        "labels_generated_partial_only": actual_manifest.get("validation_labels")
        == ["GENERATED", "PARTIAL"],
        "productionized_false": actual_manifest.get("productionized") is False,
        "public_header_matches_reference":
            (ROOT / "starter/include/pebble.h").read_bytes()
            == (ROOT / "sealed/reference/include/pebble.h").read_bytes(),
    }
    for name, passed in checks.items():
        print(name + "=" + ("PASS" if passed else "FAIL"))
    print("required_count=" + str(len(required)))
    print("missing=" + repr(missing))
    print("present_forbidden=" + repr(present_forbidden))
    print("non_regular=" + repr(non_regular))
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
