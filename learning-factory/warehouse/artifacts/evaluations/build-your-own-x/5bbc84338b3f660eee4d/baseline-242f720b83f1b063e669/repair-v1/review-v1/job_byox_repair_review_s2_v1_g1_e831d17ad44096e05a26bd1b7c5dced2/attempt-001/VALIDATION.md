# Independent validation evidence

Review date: 2026-09-02. Commands ran from the review workspace root unless a different working directory
is stated. The launcher prefixed outputs with user/group lookup warnings from `/usr/bin/id`; those warnings
were environmental and are omitted below.

`CANDIDATE/` was never modified. Tests that require writable temporary or learner-view directories ran in
an isolated copy named `.independent-review-sandbox`, which was deleted after validation.

## Toolchains

```bash
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
```

Observed, exit 0:

```text
Python 3.11.5
```

```bash
/arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11/bin/java -version
```

Observed, exit 0:

```text
openjdk version "21.0.5" 2024-10-15 LTS
OpenJDK Runtime Environment Temurin-21.0.5+11 (build 21.0.5+11-LTS)
OpenJDK 64-Bit Server VM Temurin-21.0.5+11 (build 21.0.5+11-LTS, mixed mode, sharing)
```

Java was available but not useful for this standard-library Python artifact. `rg` and `git` were not on
`PATH`; bounded `find`, `grep`, Python `pathlib`, and AST checks were used instead.

## Immutable inventory and metadata

The fingerprint command was run before and after all checks:

```bash
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 - <<'PY'
from pathlib import Path
import hashlib
root = Path('CANDIDATE')
h = hashlib.sha256()
files = sorted(path for path in root.rglob('*') if path.is_file())
for path in files:
    relative = path.relative_to(root).as_posix().encode()
    payload = path.read_bytes()
    h.update(len(relative).to_bytes(8, 'big'))
    h.update(relative)
    h.update(len(payload).to_bytes(8, 'big'))
    h.update(payload)
print(f'candidate_files={len(files)} content_tree_sha256={h.hexdigest()}')
PY
```

Both observations, exit 0:

```text
candidate_files=64 content_tree_sha256=0aac23585bf049ec3fad2e031d9aa4d140660bb8711cdf03118a53f2f63e340f
```

Canonical metadata hashing used parsed JSON with sorted compact encoding. Observed, exit 0:

```text
MANIFEST.yaml canonical_sha256=0a134783939d3d2bd9fc51f0ab33ef43cb40e4c86dc52feceb41248b0886b18e
PROVENANCE.json canonical_sha256=17238e9005ea6ad305702b2fd5f18b9693608e3ccf4bf89881f929bb46002422
manifest_provenance_link=7b06f5c8326e5b149cb21eca38df244194501c4ffb93c9a997e5e2f897a561bc
```

`find CANDIDATE` found no symbolic link, FIFO, socket, block device, or character device. An AST parse and
call scan observed:

```text
syntax_ok_files=33
forbidden_execution_calls=[]
```

A credential-pattern `grep` returned exit 1 with no matching path; in this use, exit 1 means no match.

## Isolated test setup and runtime preflight

```bash
test ! -e .independent-review-sandbox
cp -R CANDIDATE .independent-review-sandbox
chmod -R u+rwX .independent-review-sandbox
```

Each command exited 0. From `.independent-review-sandbox`:

```bash
TMPDIR=environment /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 environment/check_runtime.py
```

Observed, exit 0:

```text
runtime_ok python=3.11.5 tempdir=<review-workspace>/.independent-review-sandbox/environment
```

## Supplied suites

```bash
PYTHONDONTWRITEBYTECODE=1 TMPDIR=environment PYTHONPATH=sealed/reference \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  -m unittest discover -s public_tests -v
```

Observed, exit 0:

```text
Ran 23 tests in 0.547s
OK
```

```bash
PYTHONDONTWRITEBYTECODE=1 TMPDIR=environment PYTHONPATH=sealed/reference \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  -m unittest discover -s sealed/reference_tests -v
```

Observed, exit 0:

```text
Ran 63 tests in 1.057s
OK
```

The suite names showed coverage of artifact structure, CLI failures, compiler/VM boundaries, lexical
scope, 6,000 tail calls, deep runtime values, non-tail error translation, reader positions and limits,
learner-view isolation, and review exercises.

The intentionally incomplete starter was checked separately:

```bash
TMPDIR=environment PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=starter \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -c \
  'import io, unittest; suite=unittest.defaultTestLoader.discover("public_tests"); result=unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite); print(f"tests_run={result.testsRun} failures={len(result.failures)} errors={len(result.errors)} successful={result.wasSuccessful()}")'
```

Observed (the reporting command itself exited 0):

```text
tests_run=23 failures=5 errors=23 successful=False
```

## Independent boundary probes

This probe crossed all required tail-position forms and checked both integer boundaries without changing
host-wide settings:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 - <<'PY'
import sys
from pebble import Interpreter, ReaderError, format_value, read_one
interpreter = Interpreter(output=lambda _text: None)
before_recursion = sys.getrecursionlimit()
before_digits = sys.get_int_max_str_digits()
interpreter.eval_source('(def loop (fn (n) (do 0 (let ((done (= n 0))) (if done 0 (loop (- n 1)))))))')
tail_result = interpreter.eval_source('(loop 5500)')
digits = '8' * 10000
integer_boundary = format_value(read_one(digits)) == digits
try:
    read_one('8' * 10001)
except ReaderError:
    over_limit = 'ReaderError'
else:
    over_limit = 'accepted'
print(f'tail_result={tail_result} recursion_limit_unchanged={sys.getrecursionlimit() == before_recursion}')
print(f'integer_boundary={integer_boundary} over_limit={over_limit} int_limit_unchanged={sys.get_int_max_str_digits() == before_digits}')
PY
```

Observed, exit 0:

```text
tail_result=0 recursion_limit_unchanged=True
integer_boundary=True over_limit=ReaderError int_limit_unchanged=True
```

The uncovered `empty?` behavior was isolated with:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 - <<'PY'
from pebble import Interpreter, PebbleError, format_value
interpreter = Interpreter(output=lambda _text: None)
for source in ('(empty? 1)', '(empty? false)', '(empty? "")', '(empty? +)'):
    try:
        outcome = 'value:' + format_value(interpreter.eval_source(source))
    except PebbleError as error:
        outcome = type(error).__name__ + ':' + str(error)
    print(source + ' -> ' + outcome)
PY
```

Observed, exit 0:

```text
(empty? 1) -> value:false
(empty? false) -> value:false
(empty? "") -> value:false
(empty? +) -> value:false
```

## Learner-view audit

From `.independent-review-sandbox`:

```bash
PYTHONDONTWRITEBYTECODE=1 \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  sealed/production/learner_view.py . .learner-audit
```

Observed, exit 0:

```text
learner_view_files=20
```

An independent recursive comparison observed:

```text
learner_files=20 byte_mismatches=[] forbidden_paths=[]
```

All exported directories were mode 0755 and files mode 0644. The exact top-level list was:

```text
AGENTS.md,CONCEPTS.md,DESIGN_QUESTIONS.md,MANIFEST.yaml,README.md,REQUIREMENTS.md,environment,public_tests,starter
```

The disclosure-pointer probe observed:

```text
sealed_exists=False
PROVENANCE.json_exists=False
LICENSE_BOUNDARY.md_exists=False
readme_points_to_provenance=True
readme_points_to_license_boundary=True
```

The runtime preflight also exited 0 from the materialized view, confirming its normalized `environment/`
directory was writable.

## Limitations and label boundary

No network or upstream source was accessed. The source commit, catalog baseline, upstream non-copy claim,
and external license evidence therefore remain provenance assertions rather than independent observations.
`PRIOR_BUILD` was not supplied, so the builder's prior-tree preservation command could not be repeated.

No fuzzing, benchmark, security audit, performance test, transfer validation, or production validation was
run. Passing commands here do not promote the manifest or establish `TESTED`, `REVIEWED`,
`TRANSFER_VERIFIED`, or `PRODUCTIONIZED`; only the orchestrator-controlled acceptance validator can do so.
