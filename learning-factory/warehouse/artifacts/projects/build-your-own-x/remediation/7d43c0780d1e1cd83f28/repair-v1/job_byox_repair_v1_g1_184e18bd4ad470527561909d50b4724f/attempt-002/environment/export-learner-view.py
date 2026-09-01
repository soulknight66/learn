#!/usr/bin/env python3
"""Verify or materialize the exact learner-visible file allowlist.

The verify command reads source files and computes the prospective view digest;
it does not create a learner workspace. The export command is for an authorized
delivery layer and refuses to overwrite or write inside the production pack.
"""

import argparse
import hashlib
import json
import os
import shutil
import stat
import sys
import tempfile
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parent.parent
POLICY_PATH = ROOT / 'environment' / 'learner-view-policy.json'
POLICY_KEYS = {
    'allowed_files',
    'denied_prefixes',
    'digest_algorithm',
    'schema_version',
}
ROOT_ALLOWLIST = {
    'README.md',
    'AGENTS.md',
    'MANIFEST.yaml',
    'REQUIREMENTS.md',
    'CONCEPTS.md',
    'DESIGN_QUESTIONS.md',
}
DIRECTORY_ALLOWLIST = {'starter', 'public_tests', 'environment'}
SOLUTION_COMPONENTS = {
    'sealed',
    'reference',
    'reference_tests',
    'hidden_tests',
    'solution',
    'solutions',
    'answer',
    'answers',
}


class PolicyError(Exception):
    pass


def validate_relative_path(relative):
    if not isinstance(relative, str) or not relative:
        raise PolicyError('policy paths must be non-empty strings')
    pure = PurePosixPath(relative)
    if pure.is_absolute() or str(pure) != relative:
        raise PolicyError('path is not normalized relative POSIX text: {}'.format(relative))
    if any(part in ('', '.', '..') for part in pure.parts):
        raise PolicyError('path contains an unsafe component: {}'.format(relative))
    if any(part.lower() in SOLUTION_COMPONENTS for part in pure.parts):
        raise PolicyError('solution-bearing component is learner-visible: {}'.format(relative))
    if len(pure.parts) == 1:
        if relative not in ROOT_ALLOWLIST:
            raise PolicyError('root file is outside the learner contract: {}'.format(relative))
    elif pure.parts[0] not in DIRECTORY_ALLOWLIST:
        raise PolicyError('directory is outside the learner contract: {}'.format(relative))


def denied(relative, prefix):
    if prefix.endswith('/'):
        return relative.startswith(prefix)
    return relative == prefix


def load_policy():
    try:
        with POLICY_PATH.open('r', encoding='utf-8') as handle:
            policy = json.load(handle)
    except (OSError, ValueError) as error:
        raise PolicyError('cannot read strict policy JSON: {}'.format(error))

    if not isinstance(policy, dict) or set(policy) != POLICY_KEYS:
        raise PolicyError('policy fields do not match the fixed schema')
    if policy['schema_version'] != 1:
        raise PolicyError('unsupported policy schema version')
    if policy['digest_algorithm'] != 'learner-view-sha256-v1':
        raise PolicyError('unsupported digest algorithm')

    allowed = policy['allowed_files']
    denied_prefixes = policy['denied_prefixes']
    if not isinstance(allowed, list) or allowed != sorted(set(allowed)):
        raise PolicyError('allowed_files must be a sorted list without duplicates')
    if not isinstance(denied_prefixes, list) or denied_prefixes != sorted(set(denied_prefixes)):
        raise PolicyError('denied_prefixes must be a sorted list without duplicates')

    for relative in allowed:
        validate_relative_path(relative)
        for prefix in denied_prefixes:
            if denied(relative, prefix):
                raise PolicyError('allowed path intersects denied prefix: {}'.format(relative))
    return policy


def collect_files(root, allowed):
    records = []
    for relative in allowed:
        path = root.joinpath(*PurePosixPath(relative).parts)
        try:
            mode = os.lstat(str(path)).st_mode
        except OSError as error:
            raise PolicyError('allowed file is unavailable: {} ({})'.format(relative, error))
        if not stat.S_ISREG(mode):
            raise PolicyError('allowed path is not a regular file: {}'.format(relative))
        try:
            data = path.read_bytes()
        except OSError as error:
            raise PolicyError('cannot read allowed file: {} ({})'.format(relative, error))
        records.append((relative, data))
    return records


def view_digest(records):
    digest = hashlib.sha256()
    digest.update(b'learner-view-sha256-v1\0')
    for relative, data in records:
        encoded = relative.encode('utf-8')
        digest.update(len(encoded).to_bytes(8, byteorder='big'))
        digest.update(encoded)
        digest.update(len(data).to_bytes(8, byteorder='big'))
        digest.update(data)
    return digest.hexdigest()


def receipt(policy, records):
    return {
        'digest_algorithm': policy['digest_algorithm'],
        'file_count': len(records),
        'sha256': view_digest(records),
    }


def ensure_exact_inventory(root, allowed):
    observed = []
    for current, directories, files in os.walk(str(root), followlinks=False):
        for name in directories:
            path = os.path.join(current, name)
            if not stat.S_ISDIR(os.lstat(path).st_mode):
                raise PolicyError('export contains a non-directory node: {}'.format(path))
        for name in files:
            path = os.path.join(current, name)
            if not stat.S_ISREG(os.lstat(path).st_mode):
                raise PolicyError('export contains a non-regular file: {}'.format(path))
            observed.append(Path(path).relative_to(root).as_posix())
    if sorted(observed) != allowed:
        raise PolicyError('export inventory differs from the exact allowlist')


def export_view(destination, policy, records):
    destination = Path(os.path.abspath(destination)).resolve()
    source_root = ROOT.resolve()
    try:
        destination.relative_to(source_root)
    except ValueError:
        pass
    else:
        raise PolicyError('destination must be outside the production pack')

    if os.path.lexists(str(destination)):
        raise PolicyError('destination already exists; refusing to overwrite it')
    parent = destination.parent
    if not parent.is_dir():
        raise PolicyError('destination parent must already be a directory')

    temporary = Path(tempfile.mkdtemp(prefix='.learner-view-', dir=str(parent)))
    completed = False
    try:
        for relative, data in records:
            target = temporary.joinpath(*PurePosixPath(relative).parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('wb') as handle:
                handle.write(data)
            os.chmod(str(target), 0o644)
        ensure_exact_inventory(temporary, policy['allowed_files'])
        copied = collect_files(temporary, policy['allowed_files'])
        if view_digest(copied) != view_digest(records):
            raise PolicyError('export digest differs from its source plan')
        os.rename(str(temporary), str(destination))
        completed = True
    finally:
        if not completed and os.path.lexists(str(temporary)):
            shutil.rmtree(str(temporary))


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest='command')
    subparsers.required = True
    subparsers.add_parser('verify', help='verify the policy and print its prospective digest')
    export_parser = subparsers.add_parser('export', help='materialize a new allowlisted view')
    export_parser.add_argument('destination')
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    try:
        policy = load_policy()
        records = collect_files(ROOT, policy['allowed_files'])
        result = receipt(policy, records)
        if args.command == 'export':
            export_view(args.destination, policy, records)
        print(json.dumps(result, sort_keys=True))
        return 0
    except PolicyError as error:
        print('FAIL learner view: {}'.format(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
