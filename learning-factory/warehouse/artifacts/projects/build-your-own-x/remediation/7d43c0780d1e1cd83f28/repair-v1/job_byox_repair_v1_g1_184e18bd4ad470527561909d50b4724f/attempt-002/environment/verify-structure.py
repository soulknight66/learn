#!/usr/bin/env python3
"""Verify archive structure without traversing factory-control paths."""

import hashlib
import json
import os
import stat
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

REQUIRED = (
    'README.md',
    'AGENTS.md',
    'MANIFEST.yaml',
    'PROVENANCE.json',
    'LICENSE_BOUNDARY.md',
    'REQUIREMENTS.md',
    'CONCEPTS.md',
    'DESIGN_QUESTIONS.md',
    'VALIDATION.md',
    'starter/README.md',
    'public_tests/README.md',
    'environment/README.md',
    'sealed/reference/README.md',
    'sealed/reference_tests/README.md',
    'sealed/DESIGN.md',
    'sealed/TRADEOFFS.md',
    'sealed/REVIEW.md',
    'sealed/alternatives/README.md',
    'sealed/production/PRODUCTIONIZATION.md',
    'adversarial/README.md',
    'debugging/README.md',
    'review_exercises/README.md',
    'benchmarks/README.md',
)

FORBIDDEN = (
    '.git',
    '.env',
    '.venv',
    'credentials.json',
    'secrets',
    'reference',
    'reference_tests',
    'hidden_tests',
    'solution',
    'solutions',
    'answers',
    'starter/sealed',
    'starter/reference',
    'starter/reference_tests',
    'starter/solution',
    'starter/solutions',
    'starter/answers',
    'public_tests/sealed',
    'public_tests/reference',
    'public_tests/hidden_tests',
    'environment/sealed',
)

ROOT_FILES = (
    'README.md',
    'AGENTS.md',
    'MANIFEST.yaml',
    'PROVENANCE.json',
    'LICENSE_BOUNDARY.md',
    'REQUIREMENTS.md',
    'CONCEPTS.md',
    'DESIGN_QUESTIONS.md',
    'VALIDATION.md',
)

ARTIFACT_DIRECTORIES = (
    'starter',
    'public_tests',
    'environment',
    'sealed',
    'adversarial',
    'debugging',
    'review_exercises',
    'benchmarks',
)

EXPECTED_HASHES = {
    'MANIFEST.yaml': 'a4529eb3613733b2930841b447d4495d38f6945c54363fb61cee0132207c8dbd',
    'PROVENANCE.json': 'dc328469b4988520ffa7a9d9f58e207914721720b1a6d93bac854dcad0796f05',
}


def fail(messages):
    for message in messages:
        print('FAIL {}'.format(message), file=sys.stderr)
    return 1


def verify_required_and_forbidden():
    errors = []
    for relative in REQUIRED:
        path = ROOT / relative
        if not path.is_file() or path.is_symlink():
            errors.append('required regular file missing: {}'.format(relative))

    for relative in FORBIDDEN:
        if os.path.lexists(str(ROOT / relative)):
            errors.append('forbidden path exists: {}'.format(relative))
    return errors


def verify_node_types():
    errors = []
    file_count = 0
    directory_count = 0

    for relative in ROOT_FILES:
        mode = os.lstat(str(ROOT / relative)).st_mode
        if not stat.S_ISREG(mode):
            errors.append('artifact root is not a regular file: {}'.format(relative))
        else:
            file_count += 1

    for relative in ARTIFACT_DIRECTORIES:
        base = ROOT / relative
        base_mode = os.lstat(str(base)).st_mode
        if not stat.S_ISDIR(base_mode):
            errors.append('artifact root is not a directory: {}'.format(relative))
            continue
        directory_count += 1

        for current, directories, files in os.walk(str(base), followlinks=False):
            for name in directories + files:
                path = os.path.join(current, name)
                mode = os.lstat(path).st_mode
                if stat.S_ISDIR(mode):
                    directory_count += 1
                elif stat.S_ISREG(mode):
                    file_count += 1
                else:
                    errors.append('non-regular artifact node: {}'.format(
                        os.path.relpath(path, str(ROOT))))

    return errors, file_count, directory_count


def verify_metadata():
    errors = []
    for relative, expected in EXPECTED_HASHES.items():
        path = ROOT / relative
        data = path.read_bytes()
        observed = hashlib.sha256(data).hexdigest()
        if observed != expected:
            errors.append('{} SHA-256 mismatch'.format(relative))
        try:
            json.loads(data.decode('utf-8'))
        except (UnicodeDecodeError, ValueError) as error:
            errors.append('{} is not strict UTF-8 JSON: {}'.format(relative, error))
    return errors


def main():
    errors = verify_required_and_forbidden()
    node_errors, file_count, directory_count = verify_node_types()
    errors.extend(node_errors)
    errors.extend(verify_metadata())
    if errors:
        return fail(errors)

    print('PASS required paths: {} regular files'.format(len(REQUIRED)))
    print('PASS forbidden paths: {} absent'.format(len(FORBIDDEN)))
    print('PASS artifact node types: {} files, {} directories'.format(
        file_count, directory_count))
    print('PASS immutable metadata: strict JSON and expected SHA-256')
    return 0


if __name__ == '__main__':
    sys.exit(main())
