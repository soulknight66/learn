# Validation evidence

Status remains `GENERATED` + `PARTIAL`. These are repair-builder observations from generation 1, not
independent validation and not claims of `BUILDS`, `TESTED`, `FUZZED`, `BENCHMARKED`, `REVIEWED`,
`TRANSFER_VERIFIED`, or `PRODUCTIONIZED` labels.

Commands were run from the repaired pack root on 2026-09-02. The container launcher prefixed command
output with `/usr/bin/id: cannot find name for user ID 532319` and analogous group/user lookup warnings.
Those environment warnings did not come from Pebble.

## Toolchains and runtime preflight

Exact Python command:

```bash
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
```

Observed stdout, exit 0:

```text
Python 3.11.5
```

Exact Java command:

```bash
/arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11/bin/java -version
```

Observed stderr, exit 0:

```text
openjdk version "21.0.5" 2024-10-15 LTS
OpenJDK Runtime Environment Temurin-21.0.5+11 (build 21.0.5+11-LTS)
OpenJDK 64-Bit Server VM Temurin-21.0.5+11 (build 21.0.5+11-LTS, mixed mode, sharing)
```

Java is available but is not useful to this Python pack. The new learner-facing preflight was run with:

```bash
TMPDIR=environment /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 environment/check_runtime.py
```

Observed stdout, exit 0:

```text
runtime_ok python=3.11.5 tempdir=/projects/se/pj34000401_refsys/users/yuali01/learn/learning-factory/warehouse/workspaces/job_byox_repair_s2_v1_g1_13ce421f86c7a98ed2012e2b5efe4489/attempt-002/environment
```

## Syntax check

Exact command (staged prior artifacts and factory-control entries were excluded from the repaired-pack
file count):

```bash
PYTHONDONTWRITEBYTECODE=1 /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -c 'from pathlib import Path; excluded={"PRIOR_BUILD","PRIOR_REVIEW",".agents",".codex"}; paths=sorted(p for p in Path(".").rglob("*.py") if p.parts[0] not in excluded); [compile(p.read_text(encoding="utf-8"), str(p), "exec") for p in paths]; print(f"syntax_ok files={len(paths)}")'
```

Observed stdout, exit 0:

```text
syntax_ok files=33
```

This host `compile` invocation checked Python artifact syntax only. Pebble does not use Python `eval`,
`exec`, or `compile` to implement language semantics.

## Public contract against the sealed reference

Exact command:

```bash
PYTHONDONTWRITEBYTECODE=1 TMPDIR=environment PYTHONPATH=sealed/reference /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m unittest discover -s public_tests -v
```

Observed summary, exit 0:

```text
Ran 23 tests in 0.760s

OK
```

The added public regressions cover 5,000-digit API/CLI round trips and controlled rejection at the
documented nesting boundary.

## Sealed reference, repair regressions, and learner view

Exact command:

```bash
PYTHONDONTWRITEBYTECODE=1 TMPDIR=environment PYTHONPATH=sealed/reference /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m unittest discover -s sealed/reference_tests -v
```

Observed summary, exit 0:

```text
Ran 63 tests in 1.541s

OK
```

Observed passing cases included large signed decimal parsing/printing without changing Python's process
setting, positioned rejection above 10,000 digits, list and quote rejection beyond 256 levels, controlled
CLI resource errors, and invalid `JUMP_IF_FALSE` targets with both true and false conditions. The repaired
tail-position exercise passed focused checks for Pebble truthiness, optional `if` else behavior, empty
`do`, evaluation order, and arity validation.

Additional boundary cases constructed a 1,500-level list in a shallow tail-recursive program, then
formatted and compared it through iterative data walkers. Non-tail stack exhaustion was observed as a
controlled `EvalError` through both the API and CLI, without a Python traceback.

The suite also materialized the actual pack through `sealed/production/learner_view.py` into a temporary
harness-controlled directory. It observed exactly the nine learner-visible allowlisted roots, compared
every copied regular file with its source, found no `sealed/` or `PROVENANCE.json` in that view, verified
that an answer component blocks export, and removed the temporary view on context exit. This tests the
filter mechanism; a delivery harness must still expose only its output to learners.

## Focused prior-finding probe

Exact command:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 - <<'PY'
import os
import subprocess
import sys

from pebble import ReaderError, format_value, read_one

before = sys.get_int_max_str_digits()
digits = "9" * 5000
parsed = read_one(digits)
print(f"integer_api_round_trip={format_value(parsed) == digits}")
print(f"int_max_str_digits_unchanged={sys.get_int_max_str_digits() == before} value={before}")
try:
    read_one("(" * 1100 + "0" + ")" * 1100)
except ReaderError as error:
    print(f"nesting_api_error={error}")
else:
    print("nesting_api_error=NONE")

environment = os.environ.copy()
environment["PYTHONPATH"] = "sealed/reference"
large = subprocess.run(
    [sys.executable, "-m", "pebble.cli", "-e", digits],
    cwd=".",
    env=environment,
    text=True,
    capture_output=True,
    timeout=5,
    check=False,
)
print(
    f"integer_cli_returncode={large.returncode} "
    f"stdout_matches={large.stdout == digits + chr(10)} "
    f"stderr_empty={large.stderr == ''}"
)
deep_source = "(" * 1100 + "0" + ")" * 1100
deep = subprocess.run(
    [sys.executable, "-m", "pebble.cli", "-e", deep_source],
    cwd=".",
    env=environment,
    text=True,
    capture_output=True,
    timeout=5,
    check=False,
)
print(
    f"nesting_cli_returncode={deep.returncode} "
    f"error_prefix={deep.stderr.startswith('error: maximum nesting depth 256')} "
    f"has_traceback={'Traceback' in deep.stderr}"
)
PY
```

Observed stdout, exit 0:

```text
integer_api_round_trip=True
int_max_str_digits_unchanged=True value=4300
nesting_api_error=maximum nesting depth 256 exceeded at 1:257
integer_cli_returncode=0 stdout_matches=True stderr_empty=True
nesting_cli_returncode=2 error_prefix=True has_traceback=False
```

## CLI smoke and incomplete starter

Exact smoke command:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m pebble.cli -e '(let ((x 6) (y 7)) (* x y))'
```

Observed stdout, exit 0:

```text
42
```

The starter was not represented as complete. Exact compact observation command:

```bash
TMPDIR=environment PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=starter /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -c 'import io, unittest; suite=unittest.defaultTestLoader.discover("public_tests"); result=unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite); print(f"tests_run={result.testsRun} failures={len(result.failures)} errors={len(result.errors)} successful={result.wasSuccessful()}")'
```

Observed stdout, command exit 0:

```text
tests_run=23 failures=5 errors=23 successful=False
```

The reporting command itself exits 0; the printed result shows the intentionally incomplete TODO
scaffold does not pass the public contract.

## Final structure, provenance, and credential audit

Exact command:

```bash
PYTHONDONTWRITEBYTECODE=1 TMPDIR=environment PYTHONPATH=sealed/reference /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m unittest discover -s sealed/reference_tests -p 'test_artifact_structure.py' -v
```

Observed summary, exit 0:

```text
test_archive_tree_contains_only_regular_files_and_directories ... ok
test_authoritative_required_paths_are_regular_files ... ok
test_forbidden_paths_do_not_exist_even_as_dangling_links ... ok
test_manifest_is_exact_and_keeps_partial_status ... ok
test_no_credential_shaped_content ... ok
test_provenance_snapshot_is_frozen ... ok

Ran 6 tests

OK
```

These tests checked every authoritative required and forbidden path, filesystem entry types, strict
manifest content, the frozen provenance digest/linkage, and credential-shaped patterns. The manifest
remained `GENERATED` + `PARTIAL` with `productionized: false`. Canonical digests independently observed
during the repair were `0a134783939d3d2bd9fc51f0ab33ef43cb40e4c86dc52feceb41248b0886b18e`
for the manifest and `17238e9005ea6ad305702b2fd5f18b9693608e3ccf4bf89881f929bb46002422`
for the provenance document.

An additional top-level preservation audit used this exact command:

```bash
PYTHONDONTWRITEBYTECODE=1 /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -c 'from pathlib import Path; root=Path("."); controls={"PRIOR_BUILD","PRIOR_REVIEW",".agents",".codex",".factory-workspace"}; prior={p.name for p in (root/"PRIOR_BUILD").iterdir()}; current={p.name for p in root.iterdir()}; unsafe=sorted(p.name for p in (root/"PRIOR_BUILD").iterdir() if not p.is_file() and not p.is_dir()); print(f"unsafe_prior_top={unsafe}"); print(f"prior_top_missing={sorted(prior-current)}"); print(f"unexpected_top={sorted(current-prior-controls)}")'
```

Observed stdout, exit 0:

```text
unsafe_prior_top=[]
prior_top_missing=[]
unexpected_top=[]
```

## Limitations

No network or upstream resource was accessed. No fuzzing, benchmark, transfer, security, or production
validation was run or inferred. The source/catalog snapshot assertions remain the immutable provenance
record rather than a new external observation. Production gaps remain documented under
`sealed/production/PRODUCTIONIZATION.md`, and only a fresh independent validator may promote labels.
