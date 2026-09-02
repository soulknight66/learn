# Validation record

Artifact status: `GENERATED` + `PARTIAL`.

All commands were run from the repository root on 2026-09-02. Commands below were invoked with a
non-login Bash shell so unrelated workspace identity warnings were excluded from the captured
result.

## Toolchain discovery

Command:

```sh
node --version
```

Observed result: exit 127, stderr exactly:

```text
/bin/bash: node: command not found
```

Command:

```sh
npm --version
```

Observed result: exit 127, stderr exactly:

```text
/bin/bash: npm: command not found
```

## JavaScript test attempts

Command:

```sh
node --test public_tests/*.test.js
```

Observed result: exit 127, stderr exactly:

```text
/bin/bash: node: command not found
```

Command:

```sh
SUBMISSION_ROOT=sealed/reference node --test public_tests/*.test.js
```

Observed result: exit 127, stderr exactly:

```text
/bin/bash: node: command not found
```

Command:

```sh
node --test sealed/reference_tests/*.test.js
```

Observed result: exit 127, stderr exactly:

```text
/bin/bash: node: command not found
```

No JavaScript implementation or test was executed. No `BUILDS`, `TESTED`, `FUZZED`, `BENCHMARKED`,
`REVIEWED`, `TRANSFER_VERIFIED`, or `PRODUCTIONIZED` claim is made. Static structure and metadata
checks below cannot substitute for runtime validation.

## Deterministic artifact checks

Command:

```sh
python3 environment/verify_artifact.py
```

Observed result: exit 0, stdout exactly:

```text
required_paths: PASS (23/23)
forbidden_paths: PASS (0 present)
file_types: PASS (50 regular files, 18 directories, 0 special entries)
metadata_values: PASS (manifest and provenance canonical hashes)
credential_scan: PASS (50 regular files scanned)
```

The script checks the authoritative required and forbidden path lists, limits artifact entries to
regular files/directories, compares parsed metadata against fixed canonical value hashes, asserts
`GENERATED` + `PARTIAL` and `productionized: false`, and scans every generated regular file for
private-key and common access-token/secret-assignment patterns.

Command:

```sh
python3 - <<'PY'
import json
paths = ['MANIFEST.yaml', 'PROVENANCE.json', 'starter/package.json', 'sealed/reference/package.json']
for path in paths:
    with open(path, 'r') as handle:
        json.load(handle)
print('json_parse: PASS ({} files)'.format(len(paths)))
PY
```

Observed result: exit 0, stdout exactly:

```text
json_parse: PASS (4 files)
```

Command:

```sh
if grep -R -n 'TODO' sealed/reference sealed/reference_tests; then
  exit 1
else
  printf 'sealed_reference_todos: PASS (0 found)\n'
fi
```

Observed result: exit 0, stdout exactly:

```text
sealed_reference_todos: PASS (0 found)
```

## Additional parser discovery

Command:

```sh
python3 - <<'PY'
try:
    import esprima
except ImportError:
    print('javascript_parser: UNAVAILABLE (Python esprima module not installed)')
else:
    print('javascript_parser: AVAILABLE {}'.format(getattr(esprima, '__version__', 'unknown')))
PY
```

Observed result: exit 0, stdout exactly:

```text
javascript_parser: UNAVAILABLE (Python esprima module not installed)
```

The Python check validates only whether another JavaScript parser is present; it does not parse or
execute the implementation.
