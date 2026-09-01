#!/usr/bin/env python3

"""Conservative credential-pattern scan over generated regular text files."""

import os
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[2]
PATTERNS = {
    "private_key": re.compile(
        r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"
    ),
    "aws_access_key": re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    "openai_key": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    "github_token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    "bearer_token": re.compile(
        r"(?i)\bauthorization\s*:\s*bearer\s+[A-Za-z0-9._~+/-]{12,}"
    ),
    "credential_assignment": re.compile(
        r"(?i)\b(?:password|passwd|api[_-]?key|secret[_-]?key|"
        r"access[_-]?token)\s*[:=]\s*[\"']?[^\s\"']{8,}"
    ),
}


def main():
    hits = []
    scanned = 0
    excluded_files = {"JOB.md", ".factory-workspace"}
    excluded_directories = {".agents", ".codex"}

    for current_root, directories, files in os.walk(str(ROOT)):
        directories[:] = [
            name for name in directories if name not in excluded_directories
        ]
        for name in files:
            path = Path(current_root) / name
            relative = str(path.relative_to(ROOT))
            if relative in excluded_files:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                hits.append((relative, "non_utf8_generated_file"))
                continue
            scanned += 1
            for label, pattern in PATTERNS.items():
                if pattern.search(text) is not None:
                    hits.append((relative, label))

    print("credential_scan_files=" + str(scanned))
    print("credential_pattern_hits=" + repr(hits))
    return 0 if not hits else 1


if __name__ == "__main__":
    sys.exit(main())
