# Validation evidence

This records one generation-host run from the repository root:

```text
/projects/se/pj34000401_refsys/users/yuali01/learn/learning-factory/warehouse/workspaces/job_byox_build_s2_aace1e25a85a7f45f3e8b88474341820/attempt-001
```

It is reproducibility evidence, not an independently awarded validation label. The launcher printed
`/usr/bin/id` name-resolution warnings for the sandbox's numeric user and group before commands;
those ambient warnings did not change command exit statuses and are omitted from the concise result
snippets below.

## Toolchain

Exact command:

```bash
/arm/tools/nodejs/node/22.21.0/linux64/bin/node --version
```

Observed exit status: `0`. Observed standard output:

```text
v22.21.0
```

No external dependencies were fetched or installed.

## Syntax check

Exact command:

```bash
find starter public_tests environment sealed -type f -name '*.mjs' -exec /arm/tools/nodejs/node/22.21.0/linux64/bin/node --check '{}' ';'
```

Observed exit status: `0`; no standard output. This checked every JavaScript module in those trees.

## Sealed reference tests

Exact command:

```bash
/arm/tools/nodejs/node/22.21.0/linux64/bin/node --test sealed/reference_tests/*.test.mjs
```

Observed exit status: `0`. Node's isolated file-level TAP summary was:

```text
tests 2
pass 2
fail 0
```

The two entries were `adversarial.test.mjs` and `reference.test.mjs`. A direct run exposed the
individual reference assertions:

```bash
/arm/tools/nodejs/node/22.21.0/linux64/bin/node sealed/reference_tests/reference.test.mjs
```

Observed exit status: `0`, with `tests 13`, `pass 13`, and `fail 0`.

The adversarial file was also run directly:

```bash
/arm/tools/nodejs/node/22.21.0/linux64/bin/node sealed/reference_tests/adversarial.test.mjs
```

Observed exit status: `0`, with `tests 3`, `pass 3`, and `fail 0`.

## CLI smoke parity

Exact commands:

```bash
printf 'let n = 4; if (n > 2) { print n * 2; n + 6; } else { 0; }' | /arm/tools/nodejs/node/22.21.0/linux64/bin/node sealed/reference/src/cli.mjs --backend tree
printf 'let n = 4; if (n > 2) { print n * 2; n + 6; } else { 0; }' | /arm/tools/nodejs/node/22.21.0/linux64/bin/node sealed/reference/src/cli.mjs --backend vm
```

Both commands exited `0` and printed exactly:

```text
8
```

The CLI deliberately prints language `print` output, not the program's final expression value.

## Untouched learner baseline

Exact command:

```bash
/arm/tools/nodejs/node/22.21.0/linux64/bin/node --test public_tests/*.test.mjs
```

Observed exit status: `1`. Node's isolated file-level TAP summary was:

```text
tests 3
pass 1
fail 2
```

`lexer.test.mjs` passed. `parser.test.mjs` and `execution.test.mjs` failed because the corresponding
starter stages throw their documented `TODO` errors. This is the intended progressively revealable
baseline and the informative failure is preserved; it is not represented as a passing learner
suite.

## Structure and credential audit

Exact command:

```bash
/arm/tools/nodejs/node/22.21.0/linux64/bin/node environment/verify-pack.mjs
```

Observed exit status: `0`. The audit reported `PASS`, 23 required regular files, zero forbidden
paths, zero symlinks or special files, zero credential-pattern matches, 57 generated files scanned,
manifest
status `GENERATED`, and validation labels `GENERATED` and `PARTIAL`.

## Explicitly unclaimed work

The optional benchmark harness was not run for recorded evidence. No fuzzing, performance target,
transfer verification, security certification, or production-readiness claim was performed. The
artifact remains `GENERATED` + `PARTIAL`, and independent validators remain mandatory.
