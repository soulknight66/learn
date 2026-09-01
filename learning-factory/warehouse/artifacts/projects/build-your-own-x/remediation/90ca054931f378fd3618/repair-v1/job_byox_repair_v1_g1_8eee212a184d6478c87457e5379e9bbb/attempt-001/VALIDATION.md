# Repair-generation validation

Status remains **GENERATED + PARTIAL**. These are builder-local observations from repair generation
1, not independent validation and not an award of BUILDS, TESTED, FUZZED, BENCHMARKED, REVIEWED,
TRANSFER_VERIFIED, or PRODUCTIONIZED.

Date: 2026-08-31 (America/Chicago)

Working directory:

```text
/projects/se/pj34000401_refsys/users/yuali01/learn/learning-factory/warehouse/workspaces/job_byox_repair_v1_g1_8eee212a184d6478c87457e5379e9bbb/attempt-001
```

The execution wrapper prefixed commands with unrelated UID/GID lookup warnings. Those three warning
lines are omitted from the output blocks below; test and program output is otherwise reported as
observed.

## Tool availability

Exact command:

```sh
command -v cc
command -v gcc
command -v clang
command -v make
command -v python3
python3 --version
cc --version | sed -n '1,2p'
ulimit -s
```

Observed output (there was no `clang` path):

```text
/usr/bin/cc
/usr/bin/gcc
/usr/bin/make
/usr/bin/python3
Python 3.6.8
cc (GCC) 8.5.0 20210514 (Red Hat 8.5.0-22)
Copyright (C) 2018 Free Software Foundation, Inc.
8192
```

The command exited 0 because later probes succeeded. The observed stack limit was 8,192 KiB.

## Process-control unit coverage

Exact command:

```sh
python3 -m unittest public_tests.test_process_control -v
```

Observed: exit 0; four tests passed in 2.313 seconds:

```text
test_capture_is_bounded ... ok
test_expired_aggregate_deadline_blocks_next_case ... ok
test_normal_parent_exit_still_cleans_descendant ... ok
test_timeout_kills_descendant_before_it_can_write ... ok

Ran 4 tests in 2.313s
OK
```

These tests use real forked descendants. They exercise the 65,536-byte capture bound, aggregate
deadline, process-group cleanup after a normal parent exit, and process-group cleanup after timeout.

## Strict builds

Exact command:

```sh
make -C starter clean all
make -C sealed/reference clean all
```

Observed: exit 0. The compiler commands were:

```text
cc -Iinclude -std=c11 -O2 -Wall -Wextra -Wpedantic -Werror -c src/main.c -o build/main.o
cc -Iinclude -std=c11 -O2 -Wall -Wextra -Wpedantic -Werror -c src/source.c -o build/source.o
cc -Iinclude -std=c11 -O2 -Wall -Wextra -Wpedantic -Werror -c src/interpreter.c -o build/interpreter.o
cc -std=c11 -O2 -Wall -Wextra -Wpedantic -Werror build/main.o build/source.o build/interpreter.o -o build/minic
cc -std=c11 -O2 -Wall -Wextra -Wpedantic -Werror src/minic.c -o build/minic
```

## Repaired reference suites and nested interpreter

Exact commands:

```sh
python3 public_tests/run_tests.py sealed/reference/build/minic
python3 sealed/reference_tests/run_tests.py sealed/reference/build/minic
sealed/reference/build/minic sealed/reference/examples/meta_vm.mc
```

All three commands exited 0. The public runner reported `18 passed; 0 failed`. It printed `PASS` for
the six prior smoke cases and for signed, whitespace-prefixed, whitespace-suffixed, zero, overflow,
empty, nondigit, missing-value, missing-source, unknown-option, and extra-argument CLI cases.

The sealed runner reported `34 passed; 0 failed`. Its complete case-name output was:

```text
PASS comments-zero
PASS forward-call
PASS evaluation-order
PASS signed-math
PASS recursive
PASS nested-interpreter
PASS add-overflow
PASS sub-overflow
PASS mul-overflow
PASS neg-overflow
PASS divide-overflow
PASS remainder-overflow
PASS divide-zero
PASS literal-overflow
PASS unterminated-comment
PASS undefined-function
PASS wrong-arity
PASS duplicate-local
PASS missing-main
PASS main-parameter
PASS frame-limit
PASS step-exact
PASS two-step-success
PASS budget-u64-exact
PASS usage-zero-budget
PASS missing-input
PASS token-exact-65536
PASS token-one-over
PASS expression-nesting-exact
PASS expression-nesting-one-over
PASS deep-parentheses-regression
PASS deep-unary-iterative
PASS statement-level-exact
PASS statement-level-one-over
34 passed; 0 failed
```

The nested interpreter command printed exactly:

```text
42
```

The runners generated boundary source only in temporary directories below this workspace, invoked
executables with argv arrays in new sessions, bounded each output stream and process resources,
killed the process group after timeout or direct-child exit, and enforced aggregate wall deadlines.

## Focused reproduction of the prior signal-11 input

Exact command:

```sh
python3 - <<'PY'
import os
import re
import tempfile
from public_tests.process_control import run_bounded

root = os.getcwd()
source = 'int main(){print(' + '(' * 32760 + '1' + ')' * 32760 + ');return 0;}'
tokens = re.findall(r'[A-Za-z_][A-Za-z0-9_]*|[0-9]+|==|!=|<=|>=|&&|\|\||[+*/%!<>=(){},;-]', source)
with tempfile.TemporaryDirectory(prefix='.deep-validation-', dir=root) as directory:
    path = os.path.join(directory, 'deep.mc')
    with open(path, 'w') as handle:
        handle.write(source)
    print('bytes={} language_tokens={}'.format(len(source), len(tokens)))
    for attempt in range(1, 4):
        result = run_bounded(
            [os.path.join(root, 'sealed/reference/build/minic'), path], 8, directory)
        diagnostic = result.stderr.rsplit(': ', 1)[-1].strip()
        print('attempt={} returncode={} timed_out={} stdout={!r} diagnostic={!r}'.format(
            attempt, result.returncode, result.timed_out, result.stdout, diagnostic))
PY
```

Observed: exit 0 from the probe. The reference itself returned the specified source-error category
on all three attempts, without timeout, signal termination, or language output:

```text
bytes=65550 language_tokens=65534
attempt=1 returncode=65 timed_out=False stdout='' diagnostic='expression nesting exceeds 512'
attempt=2 returncode=65 timed_out=False stdout='' diagnostic='expression nesting exceeds 512'
attempt=3 returncode=65 timed_out=False stdout='' diagnostic='expression nesting exceeds 512'
```

The sealed matrix separately observed success at exactly 512 parenthesized-expression levels and
exit 65 one over. It also observed success with exactly 65,536 source lexical tokens, excluding EOF,
and exit 65 at 65,537.

## Expected incomplete-starter result

Exact command:

```sh
python3 public_tests/run_tests.py starter/build/minic
```

Observed: runner exit 1 and `12 passed; 6 failed`. All twelve CLI validation cases passed, including
the budget spellings that the prior starter accepted incorrectly. The four successful-language
fixtures, syntax-diagnostic fixture, and step-limit fixture failed because the starter deliberately
reports `interpreter not implemented` with exit 65 after safe loading. This is retained evidence of
the scaffold's intended incompleteness, not a passing result.

## Structure, metadata, disclosure, and credential audit

Exact command:

```sh
python3 sealed/reference_tests/audit_pack.py
```

Observed: exit 0 with exact summary:

```text
STRICT_JSON MANIFEST.yaml sha256=90e92288880bdd67f39044ad703d031800dc5b25687309f42ad0f1df007bd71d
STRICT_JSON PROVENANCE.json sha256=7d163264fd18e6ecaf9a2efd9c23d95b0f16ad143aa02ac4eca6c14f26a89bb6
AUDIT required_paths=23 missing=0 forbidden=0 special_files=0 credential_hits=0 disclosure_violations=0
STATUS GENERATED labels=GENERATED,PARTIAL productionized=false
```

The audit parses both metadata files with duplicate-key rejection, compares the manifest object and
immutable provenance file, checks all required and forbidden paths, rejects special files, scans
pack files for common credential/private-key signatures, and checks solution-bearing placement.

## Staged-root integrity and scratch cleanup

The staged roots were hashed before copying and again after repairs with these exact commands:

```sh
find PRIOR_BUILD -type f -print0 | LC_ALL=C sort -z | xargs -0 sha256sum | sha256sum
find PRIOR_REVIEW -type f -print0 | LC_ALL=C sort -z | xargs -0 sha256sum | sha256sum
```

Both observations were identical:

```text
59bcda8d800d1ca18af315e986c2856c47817854dd71a2f17fc73759879bcdc8  -
be1ca91b6874448c252337cb3b68169189bc793b3f3d2a38ff95d31e51c3f0f9  -
```

Compiled scratch outputs were removed with:

```sh
make -C starter clean
make -C sealed/reference clean
```

Both targets exited 0. Exact-path Python bytecode caches created by validation were then deleted;
follow-up `find` queries produced no build files or `__pycache__` directories. Exact command:

```sh
find public_tests/__pycache__ sealed/reference_tests/__pycache__ -type f -delete
rmdir public_tests/__pycache__ sealed/reference_tests/__pycache__
find starter/build sealed/reference/build -mindepth 1 -print
find public_tests sealed/reference_tests -type d -name __pycache__ -print
```

## Limitations

No fuzz campaign, benchmark, sanitizer run, second compiler/architecture check, production sandbox
assessment, or transfer-view verification was performed. The linked upstream resource was not
accessed. POSIX rlimits are per-process, and a hostile descendant can deliberately leave a process
group by creating another session; the runner is bounded test containment, not a production security
boundary. Fresh independent review remains mandatory.
