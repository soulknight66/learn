# Validation evidence

Status remains `GENERATED` + `PARTIAL`. These are builder-observed results, not independent validation and
not claims of `BUILDS`, `TESTED`, `FUZZED`, `BENCHMARKED`, `REVIEWED`, `TRANSFER_VERIFIED`, or
`PRODUCTIONIZED` labels.

Commands were run from the repository root on 2026-09-02. The container launcher emitted
`/usr/bin/id: cannot find name for user ID 532319` and analogous group/user lookup warnings before command
output; these environment warnings did not come from Pebble.

## Toolchain observation

Exact command:

```bash
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
```

Observed stdout, exit 0:

```text
Python 3.11.5
```

The configured but unused Java binary was also invoked as
`/arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11/bin/java -version`; it reported OpenJDK
`21.0.5` Temurin build `21.0.5+11-LTS`, exit 0. Python is the useful build/runtime toolchain for this pack.

## Syntax check

Exact command (the here-document iterated over sorted `Path('.').rglob('*.py')` entries and called host
`compile(source, path, 'exec')` without writing bytecode):

```bash
PYTHONDONTWRITEBYTECODE=1 /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 - <<'PY'
from pathlib import Path
paths = sorted(Path('.').rglob('*.py'))
for path in paths:
    compile(path.read_text(encoding='utf-8'), str(path), 'exec')
print(f'syntax_ok files={len(paths)}')
PY
```

Observed stdout, exit 0:

```text
syntax_ok files=29
```

This host `compile` call checks artifact syntax only; the Pebble implementation never uses Python
`eval`, `exec`, or `compile` to execute learner source.

## Public contract against the sealed reference

Exact command:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m unittest discover -s public_tests -v
```

Observed summary, exit 0:

```text
Ran 19 tests in 0.518s

OK
```

The starter was not represented as passing: it intentionally contains `NotImplementedError` TODOs for
the learner. The public suite was run against the sealed reference to validate the public contract.

## Sealed reference and artifact audit

Exact command:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m unittest discover -s sealed/reference_tests -v
```

Observed summary, exit 0:

```text
Ran 49 tests in 0.679s

OK
```

The 49 checks include positioned reader errors, special-form validation, lexical capture, built-in type
boundaries, 6,000 tail-recursive calls without changing the recursion limit, evaluator/VM differential
cases, malformed bytecode, CLI errors, every required path, every forbidden path, regular-file/directory
types, exact manifest content, the frozen canonical provenance digest, and credential-shaped patterns.

## CLI smoke check

Exact command:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m pebble.cli -e '(let ((x 6) (y 7)) (* x y))'
```

Observed stdout, exit 0:

```text
42
```

## Cleanup and limitations

Three test-created cache directories were explicitly removed:
`public_tests/__pycache__`, `sealed/reference/pebble/__pycache__`, and
`sealed/reference_tests/__pycache__`. Subsequent commands set `PYTHONDONTWRITEBYTECODE=1`.

No network or upstream resource was accessed. No benchmark or fuzz command was run. Production gaps are
recorded under `sealed/production/PRODUCTIONIZATION.md`; independent validation remains mandatory.
