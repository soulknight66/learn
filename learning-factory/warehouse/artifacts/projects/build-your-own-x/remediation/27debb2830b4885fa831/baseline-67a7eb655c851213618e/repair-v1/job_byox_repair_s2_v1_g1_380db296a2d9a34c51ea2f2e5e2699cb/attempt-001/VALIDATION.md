# Repair validation evidence

This records fresh generation-1 repair checks run on 2026-09-02 from:

```text
/projects/se/pj34000401_refsys/users/yuali01/learn/learning-factory/warehouse/workspaces/job_byox_repair_s2_v1_g1_380db296a2d9a34c51ea2f2e5e2699cb/attempt-001
```

It is builder evidence, not an independently awarded validation label. The launcher emitted ambient
`/usr/bin/id` name-resolution warnings for the sandbox's numeric user and group before commands;
those warnings did not alter command exit statuses and are omitted from the result snippets below.
No external dependency was fetched or installed.

## Pinned toolchain

Exact command:

```bash
/usr/bin/timeout --signal=KILL 10s /arm/tools/nodejs/node/22.21.0/linux64/bin/node --version
```

Observed exit status `0` and standard output:

```text
v22.21.0
```

## Syntax check

Exact command:

```bash
/usr/bin/timeout --signal=KILL 30s /usr/bin/find starter public_tests environment sealed -type f -name '*.mjs' -exec /arm/tools/nodejs/node/22.21.0/linux64/bin/node --check '{}' ';'
```

Observed exit status `0` with no standard output. This checked every JavaScript module in those four
generated trees.

## Sealed reference and repair regressions

Exact commands:

```bash
/usr/bin/timeout --signal=KILL 30s /arm/tools/nodejs/node/22.21.0/linux64/bin/node --test sealed/reference_tests/*.test.mjs
/usr/bin/timeout --signal=KILL 30s /arm/tools/nodejs/node/22.21.0/linux64/bin/node sealed/reference_tests/reference.test.mjs
/usr/bin/timeout --signal=KILL 30s /arm/tools/nodejs/node/22.21.0/linux64/bin/node sealed/reference_tests/adversarial.test.mjs
```

All three commands exited `0`. The aggregate run reported two file suites passed and zero failed.
The direct runs reported 13/13 reference tests and 6/6 adversarial tests passed. The adversarial
tests include non-string opcodes, an opcode with a throwing coercion hook, malformed source spans,
and an accessor-backed instruction field.

The independent review's three concrete failing inputs were also replayed directly:

```bash
/usr/bin/timeout --signal=KILL 10s /arm/tools/nodejs/node/22.21.0/linux64/bin/node --input-type=module --eval 'import { run } from "./sealed/reference/src/vm.mjs"; const results = []; let coercions = 0; for (const op of [Symbol("bad"), { toString() { coercions += 1; throw new Error("attacker coercion executed"); } }]) { try { run({ constants: [], code: [{ op, arg: null, span: null }] }); } catch (error) { results.push({ name: error.name, code: error.code ?? null, span: error.span ?? null }); } } try { run({ constants: [], code: [{ op: "LOAD", arg: "missing", span: "not-a-span" }, { op: "HALT", arg: null, span: null }] }); } catch (error) { results.push({ name: error.name, code: error.code ?? null, span: error.span ?? null }); } console.log(JSON.stringify({ results, coercions }));'
```

Observed exit status `0` and output:

```json
{"results":[{"name":"MicaRuntimeError","code":"E_INVALID_BYTECODE","span":null},{"name":"MicaRuntimeError","code":"E_INVALID_BYTECODE","span":null},{"name":"MicaRuntimeError","code":"E_INVALID_BYTECODE","span":null}],"coercions":0}
```

The probe catches errors to report their stable type, code, and span; its process exit alone is not
the assertion. The output shows that all three inputs reached the required error and that the
hostile object's coercion hook was not called.

## Input non-mutation

Exact command:

```bash
/usr/bin/timeout --signal=KILL 10s /arm/tools/nodejs/node/22.21.0/linux64/bin/node --input-type=module --eval 'import assert from "node:assert/strict"; import { tokenize } from "./sealed/reference/src/lexer.mjs"; import { parse } from "./sealed/reference/src/parser.mjs"; import { interpret } from "./sealed/reference/src/interpreter.mjs"; import { compile } from "./sealed/reference/src/compiler.mjs"; import { run } from "./sealed/reference/src/vm.mjs"; const tokens = tokenize("let x = 2; x + 3;"); const tokenSnapshot = structuredClone(tokens); const ast = parse(tokens); assert.deepEqual(tokens, tokenSnapshot); const astSnapshot = structuredClone(ast); interpret(ast); const chunk = compile(ast); assert.deepEqual(ast, astSnapshot); const chunkSnapshot = structuredClone(chunk); run(chunk); assert.deepEqual(chunk, chunkSnapshot); console.log(JSON.stringify({ status: "PASS", tokenInputUnchanged: true, astInputUnchanged: true, chunkInputUnchanged: true }));'
```

Observed exit status `0` and output:

```json
{"status":"PASS","tokenInputUnchanged":true,"astInputUnchanged":true,"chunkInputUnchanged":true}
```

## CLI smoke parity

Exact commands:

```bash
/usr/bin/printf %s 'let n = 4; if (n > 2) { print n * 2; n + 6; } else { 0; }' | /usr/bin/timeout --signal=KILL 10s /arm/tools/nodejs/node/22.21.0/linux64/bin/node sealed/reference/src/cli.mjs --backend tree
/usr/bin/printf %s 'let n = 4; if (n > 2) { print n * 2; n + 6; } else { 0; }' | /usr/bin/timeout --signal=KILL 10s /arm/tools/nodejs/node/22.21.0/linux64/bin/node sealed/reference/src/cli.mjs --backend vm
```

Both commands exited `0` and printed exactly `8` followed by a newline.

## Untouched learner baseline

Exact command:

```bash
/usr/bin/timeout --signal=KILL 30s /arm/tools/nodejs/node/22.21.0/linux64/bin/node --test public_tests/*.test.mjs
```

Observed exit status `1`: three file suites ran, with one pass and two failures. `lexer.test.mjs`
passed; `parser.test.mjs` and `execution.test.mjs` failed at the documented starter TODO stages.
This expected, informative baseline failure is not represented as a passing learner suite.

## Immutable metadata and pack audit

Exact command:

```bash
/usr/bin/timeout --signal=KILL 10s /usr/bin/sha256sum MANIFEST.yaml PROVENANCE.json
```

Observed exit status `0` and output:

```text
4d0c9b613b4efbce749d94fb1f337fc1ae861801802d16c7b174389f6af0d661  MANIFEST.yaml
be80da9777a7b3f1b6a4d2d40a2f3cde0f9212467b828a636140bc281ff94bdc  PROVENANCE.json
```

Exact command:

```bash
/usr/bin/timeout --signal=KILL 30s /arm/tools/nodejs/node/22.21.0/linux64/bin/node environment/verify-pack.mjs
```

Observed exit status `0`. The JSON result reported `PASS`, 23 required regular files, 57 generated
files scanned, no forbidden paths, no symlinks or special files, and no credential-pattern matches.
It confirmed manifest status `GENERATED` and validation labels `GENERATED`, `PARTIAL`. Controller
workspace entries and the two read-only staged roots are excluded from the generated-file walk.

## Explicitly unclaimed work

The optional benchmark harness was not run for recorded evidence. No fuzzing, benchmark
qualification, transfer verification, security certification, cross-runtime compatibility matrix,
or production-readiness claim was performed. The pack remains `GENERATED` + `PARTIAL`, and a fresh
independent review remains mandatory.
