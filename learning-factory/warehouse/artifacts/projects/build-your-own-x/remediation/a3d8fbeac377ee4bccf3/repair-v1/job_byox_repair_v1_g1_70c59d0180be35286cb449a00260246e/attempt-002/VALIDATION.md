# Repair generation validation record

Artifact status: **GENERATED + PARTIAL**  
Independent validation: **REQUIRED**  
Productionized: **no**  
Repair generation: **1**  
Validation date: **2026-09-01**

This record contains commands executed in the allocated repair workspace. The
archived prior validation was treated only as review input and is not claimed as
fresh evidence. Shell startup repeatedly printed account-name lookup warnings
from `/usr/bin/id`; those host warnings are not candidate diagnostics.

No `BUILDS`, `TESTED`, `FUZZED`, `BENCHMARKED`, `REVIEWED`,
`TRANSFER_VERIFIED`, or `PRODUCTIONIZED` label is claimed.

## Repair coverage

The process boundary is implemented once in `environment/harness.py` and used by
the public suite, sealed suite, and sealed benchmark. It launches argv arrays in
a new POSIX session, continuously drains but quota-limits both captured streams,
applies a wall deadline, terminates the process group on timeout or normal leader
exit, and reaps the direct child. Mica fixtures and attempt directories are made
read-only while a candidate runs.

Command:

```bash
timeout 20s env PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest environment.test_harness -v
```

Observed: exit 0.

```text
test_captured_logs_are_bounded_while_pipes_are_drained ... ok
test_nonzero_status_and_output_are_preserved ... ok
test_source_and_attempt_directory_are_read_only ... ok
test_timeout_signals_and_reaps_descendant_group ... ok
test_overflow_acceptance_rejects_stdout_even_with_runtime_exit ... ok

Ran 5 tests in 0.561s
OK
```

The fifth test specifically establishes that the public addition-overflow test
rejects non-empty stdout even when the candidate reports runtime exit status 70
and a correctly located runtime diagnostic.

Commands:

```bash
python3 -B environment/run_with_limits.py --timeout 2 --max-output-bytes 64 -- python3 -c "print('bounded runner smoke')"
python3 -B environment/run_with_limits.py --timeout 0.1 --max-output-bytes 64 -- python3 -c "import time; time.sleep(5)"
```

Observed: the first command exited 0 and printed `bounded runner smoke`. The
second exited 124 after printing `worker deadline exceeded after 0.100s`.

These tests exercise ordinary POSIX descendant cleanup. They are not evidence of
container, cgroup, separate-identity, or hostile native-code isolation.

## Toolchain and host discovery

Command:

```bash
python3 -B - <<'PY'
import platform
import shutil
import sys
for name in ('fpc', 'ppcx64', 'make', 'python3', 'codex'):
    print('{}: {}'.format(name, shutil.which(name) or 'NOT FOUND'))
print('python: {}'.format(sys.version.splitlines()[0]))
print('platform: {}'.format(platform.platform()))
PY
```

Observed: exit 0.

```text
fpc: NOT FOUND
ppcx64: NOT FOUND
make: /usr/bin/make
python3: /usr/bin/python3
codex: NOT FOUND
python: 3.6.8 (default, Apr 25 2024, 09:54:46)
platform: Linux-4.18.0-553.el8_10.x86_64-x86_64-with-redhat-8.10-Ootpa
```

Commands:

```bash
/home/yuali01/.local/bin/x86_64/codex --version
make --version
```

Observed: the explicit Codex executable exited 0 and reported
`codex-cli 0.146.0`; it was not on `PATH`. That invocation also emitted host
account/path-alias warnings and transient profile fork retries before completing.
GNU Make exited 0 and reported version 4.2.1.

The exact hosted model identifier and factory-side worker invocation were not
exposed to this workspace. They are not guessed.

## Native build attempts and blocker

Commands:

```bash
make -n -C starter
make -n -C sealed/reference
```

Observed: both exited 0 and resolved the expected `mkdir -p bin units` followed
by an `fpc -Mobjfpc -Sh ... src/mica.pas` invocation. These were GNU Make dry
runs and are not build evidence.

Commands:

```bash
make -C starter
make -C sealed/reference
```

Observed: each exited 2. The relevant outputs were:

```text
fpc -Mobjfpc -Sh -O1 -g -gl -Fusrc -FUunits -FEbin src/mica.pas
make: fpc: Command not found
make: *** [Makefile:10: bin/mica] Error 127

fpc -Mobjfpc -Sh -O2 -g -gl -Fusrc -FUunits -FEbin src/mica.pas
make: fpc: Command not found
make: *** [Makefile:10: bin/mica] Error 127
```

The failed recipes created only four empty scratch directories. After confirming
each was empty, this exact cleanup command exited 0:

```bash
rmdir starter/bin starter/units sealed/reference/bin sealed/reference/units
```

No native executable or compiler/test log was produced. Missing Free Pascal is
the blocker that requires `PARTIAL`.

## Published entry points

Commands:

```bash
timeout 10s environment/check.sh
timeout 10s env PYTHONDONTWRITEBYTECODE=1 python3 -B public_tests/run_tests.py
timeout 10s env PYTHONDONTWRITEBYTECODE=1 python3 -B sealed/reference_tests/run_reference_tests.py
```

Observed:

- `environment/check.sh` exited 2 with
  `PARTIAL: Pascal compiler 'fpc' is unavailable and MICA_BIN is not executable`.
- The public entry point exited 1 in `setUpClass`, reported the missing
  `starter/bin/mica`, and recorded `Ran 0 tests` plus `FAILED (errors=1)`.
- The sealed entry point exited 1 in `setUpClass`, reported the missing
  `sealed/reference/bin/mica`, and recorded `Ran 0 tests` plus
  `FAILED (errors=1)`.

The two setup failures are preserved as dependency evidence. They are neither
passing nor failing Mica behavioral results.

## Static syntax and subprocess-boundary checks

Command:

```bash
bash -n environment/check.sh
python3 -B - <<'PY'
import ast
import json
import os
python_roots = ('environment', 'public_tests', 'sealed/benchmarks', 'sealed/reference_tests', 'sealed/reproduction')
paths = []
for root in python_roots:
    for directory, _, files in os.walk(root):
        for name in files:
            if name.endswith('.py'):
                paths.append(os.path.join(directory, name))
for path in sorted(paths):
    with open(path, 'r', encoding='utf-8') as handle:
        ast.parse(handle.read(), filename=path)
print('AST parse PASS: {} Python files'.format(len(paths)))
json_paths = ('MANIFEST.yaml', 'PROVENANCE.json', 'environment/learner_view_allowlist.json', 'sealed/adversarial/cases.json', 'sealed/reproduction/ARTIFACT_TREE.json')
for path in json_paths:
    with open(path, 'r', encoding='utf-8') as handle:
        json.load(handle)
print('JSON parse PASS: {} files'.format(len(json_paths)))
process_calls = []
for path in sorted(paths):
    with open(path, 'r', encoding='utf-8') as handle:
        tree = ast.parse(handle.read(), filename=path)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            owner = node.func.value
            if isinstance(owner, ast.Name) and owner.id == 'subprocess':
                process_calls.append((path, node.func.attr))
expected = [('environment/harness.py', 'Popen')]
if process_calls != expected:
    raise AssertionError(process_calls)
print('subprocess boundary PASS: {}'.format(process_calls))
PY
sha256sum MANIFEST.yaml PROVENANCE.json
```

Observed: all commands exited 0.

```text
AST parse PASS: 9 Python files
JSON parse PASS: 5 files
subprocess boundary PASS: [('environment/harness.py', 'Popen')]
ae785b7b18135dfce203f576beb7db5c012920046b52d851b33fa8a5b50932cc  MANIFEST.yaml
8dec1885294f3e1e88f20ce3eaaec0d6c3cf80e4831e5cb702b07bba4db4a7e4  PROVENANCE.json
```

The single parsed subprocess call is the bounded shared wrapper. The child
creation text used by its deterministic regression test is inert test input, not
an unwrapped harness call.

## Prior-pack preservation

Command:

```bash
python3 -B - <<'PY'
import os
prior_files = []
for directory, _, files in os.walk('PRIOR_BUILD'):
    for name in files:
        prior_files.append(os.path.relpath(os.path.join(directory, name), 'PRIOR_BUILD'))
missing_files = [name for name in sorted(prior_files) if not os.path.isfile(name)]
prior_top = sorted(os.listdir('PRIOR_BUILD'))
missing_top = [name for name in prior_top if not os.path.lexists(name)]
print('prior preservation PASS: {} prior files present; {} prior top-level entries present'.format(len(prior_files), len(prior_top)))
print('missing prior files: {}'.format(missing_files))
print('missing prior top-level entries: {}'.format(missing_top))
PY
```

Observed: exit 0.

```text
prior preservation PASS: 51 prior files present; 17 prior top-level entries present
missing prior files: []
missing prior top-level entries: []
```

Presence does not imply byte identity for repaired files; the reviewed harnesses
and documents were intentionally changed. Neither staged root was modified.

## Structure, metadata, disclosure, and credential audit

Command:

```bash
python3 -B sealed/reproduction/audit_pack.py
```

Observed: exit 0.

```text
pack audit PASS: 23 required files, 21 forbidden paths absent, 60 UTF-8 regular files, 0 credential-pattern hits
```

The deterministic audit requires each authoritative path to be a non-symlink
regular file, rejects every forbidden path, parses JSON with duplicate-key and
non-standard-constant rejection, compares `MANIFEST.yaml` to the exact
authoritative object, checks immutable provenance bytes, compares the learner
allowlist to policy, rejects symlinks/special artifact nodes, rejects literal NUL
bytes and UTF-8 failures, and scans generated regular files for private-key
headers, AWS/GitHub/OpenAI token shapes, and quoted credential assignments.

`environment/learner_view_allowlist.json` is machine-readable. In accordance
with this repair job's instruction, no student workspace was created. Therefore
no transfer claim is made; a worker-controlled validator must materialize and
inspect the learner view later.

Generated-material terms are now explicitly identified as
`LicenseRef-LearningFactory-Personal-Educational-Use` in
`LICENSE_BOUNDARY.md`. This does not apply CC0 to generated material or grant any
rights in the linked `NOASSERTION` resource.

## Canonical repaired-artifact record

After all artifact edits and mode normalization, commands:

```bash
python3 -B sealed/reproduction/make_artifact_record.py --write
python3 -B sealed/reproduction/make_artifact_record.py --verify
```

Observed: both exited 0.

```text
artifact record written: 59 files, 27 directories
artifact record PASS: 59 files, 27 directories
```

`sealed/reproduction/ARTIFACT_TREE.json` records the resulting canonical
`mica-artifact-tree-v1-json-sha256` digest plus each included path, permission
mode, file size, and file SHA-256. The record covers every explicit pack root and
excludes only its own bytes. Factory staging and workspace-control entries are
not part of this artifact digest.

## Remaining independent work

An independent worker with a recorded Free Pascal 3.2.x toolchain must copy build
inputs into worker scratch, compile starter and reference trees, retain exact
compiler version/flags/platform and executable digests, run all 12 public and 17
sealed behavioral tests, and separately execute adversarial seeds. The worker
must also materialize the allowlisted learner view and inspect it before granting
`TRANSFER_VERIFIED`.

No native compilation, Mica behavior, adversarial execution, fuzzing, benchmark,
platform transfer, or production validation occurred in this repair attempt.
The manifest therefore remains exactly `GENERATED + PARTIAL`, with independent
validation required and `productionized: false`.
