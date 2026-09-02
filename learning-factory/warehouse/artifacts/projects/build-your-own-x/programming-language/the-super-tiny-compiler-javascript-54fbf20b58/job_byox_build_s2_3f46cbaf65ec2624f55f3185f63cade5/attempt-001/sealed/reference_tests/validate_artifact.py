#!/usr/bin/env python3
"""Deterministic archive-boundary checks; compatible with Python 3.6+."""

import hashlib
import json
import os
import re
import stat


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

REQUIRED = [
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
]

FORBIDDEN = [
    '.git', '.env', '.venv', 'credentials.json', 'secrets', 'reference',
    'reference_tests', 'hidden_tests', 'solution', 'solutions', 'answers',
    'starter/sealed', 'starter/reference', 'starter/reference_tests',
    'starter/solution', 'starter/solutions', 'starter/answers',
    'public_tests/sealed', 'public_tests/reference',
    'public_tests/hidden_tests', 'environment/sealed',
]

EXPECTED_MANIFEST = {
    'independent_validation': 'REQUIRED',
    'productionized': False,
    'project_id': 'project_77599834cfe38f15a3b1a4564b1c5efb',
    'provenance_sha256': '493eb70bcc7388b6cc299d8c45efadd1ce96f0ad838eca2403fa42ce02ffcacd',
    'schema_version': 1,
    'source_commit': 'aa17439b62f384511a5561ce308e9598b94d8989',
    'source_id': 'source_eac489a34bed5db9a1f2a580b457bcef',
    'status': 'GENERATED',
    'validation_labels': ['GENERATED', 'PARTIAL'],
}

EXPECTED_PROVENANCE_CANONICAL_SHA256 = (
    '00c0f1953c40ad885d5f54109afec5975f816ee6403ff8414d7e81639bade85e'
)

CREDENTIAL_PATTERNS = [
    re.compile(br'-----BEGIN (?:RSA|EC|OPENSSH|DSA) PRIVATE KEY-----'),
    re.compile(br'AKIA[0-9A-Z]{16}'),
    re.compile(br'gh[pousr]_[A-Za-z0-9]{20,}'),
    re.compile(br'sk-[A-Za-z0-9]{20,}'),
    re.compile(
        br'(?:api[_-]?key|access[_-]?token|password|passwd)'
        br'[ \t]*[:=][ \t]*[A-Za-z0-9/+_=.-]{12,}',
        re.IGNORECASE,
    ),
]


class DuplicateKeyError(ValueError):
    pass


def strict_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError('duplicate JSON key: {}'.format(key))
        result[key] = value
    return result


def load_json(relative):
    with open(os.path.join(ROOT, relative), 'r', encoding='utf-8') as stream:
        return json.load(stream, object_pairs_hook=strict_object)


def canonical_sha256(value):
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(',', ':'),
    ).encode('utf-8')
    return hashlib.sha256(encoded).hexdigest()


def generated_files():
    excluded = {'.agents', '.codex'}
    for directory, names, filenames in os.walk(ROOT, topdown=True, followlinks=False):
        names[:] = [name for name in names if name not in excluded]
        for filename in filenames:
            absolute = os.path.join(directory, filename)
            relative = os.path.relpath(absolute, ROOT)
            if relative == '.factory-workspace':
                continue
            yield relative, absolute


def main():
    failures = []

    for relative in REQUIRED:
        absolute = os.path.join(ROOT, relative)
        if not os.path.isfile(absolute) or os.path.islink(absolute):
            failures.append('required path is not a regular file: {}'.format(relative))

    for relative in FORBIDDEN:
        absolute = os.path.join(ROOT, relative)
        if os.path.lexists(absolute):
            failures.append('forbidden path exists: {}'.format(relative))

    manifest = load_json('MANIFEST.yaml')
    if manifest != EXPECTED_MANIFEST:
        failures.append('manifest does not equal the mandated object')

    provenance = load_json('PROVENANCE.json')
    if canonical_sha256(provenance) != EXPECTED_PROVENANCE_CANONICAL_SHA256:
        failures.append('provenance snapshot content changed')
    if provenance.get('snapshot_sha256') != EXPECTED_MANIFEST['provenance_sha256']:
        failures.append('provenance snapshot ID does not match manifest')

    file_count = 0
    credential_matches = []
    for relative, absolute in generated_files():
        file_count += 1
        mode = os.lstat(absolute).st_mode
        if not stat.S_ISREG(mode):
            failures.append('generated path is not a regular file: {}'.format(relative))
            continue
        with open(absolute, 'rb') as stream:
            content = stream.read()
        for pattern in CREDENTIAL_PATTERNS:
            if pattern.search(content):
                credential_matches.append(relative)
                break

    if credential_matches:
        failures.append('credential pattern matches: {}'.format(', '.join(credential_matches)))

    if failures:
        for failure in failures:
            print('ARTIFACT_CHECK_FAILURE {}'.format(failure))
        return 1

    print(
        'ARTIFACT_CHECK_OK required={} forbidden={} generated_files={} '
        'credential_matches=0 manifest_status={} labels={}'.format(
            len(REQUIRED),
            len(FORBIDDEN),
            file_count,
            manifest['status'],
            ','.join(manifest['validation_labels']),
        )
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
