# Independent validation record

Review date: 2026-09-02. Commands were run from `CANDIDATE/` unless stated otherwise. The candidate
was treated as read-only; every bounded execution used the submitted code without modification.

## Toolchain and immutable inventory

```bash
/arm/tools/nodejs/node/22.21.0/linux64/bin/node --version
```

Exit `0`; output: `v22.21.0`.

```bash
find . -type f | sort | /usr/bin/wc -l
find . -type f -print0 | sort -z | xargs -0 /usr/bin/sha256sum | /usr/bin/sha256sum
find . -type l -print
```

Observed 57 regular files, digest
`3fbf6052f35643da7d15f335abd14c661443545ef3bbccac788746e2b6124ccf`, and no symlink output. The
same digest was observed after all checks.

## Syntax and submitted tests

```bash
/usr/bin/timeout --signal=KILL 30s find starter public_tests environment sealed -type f -name '*.mjs' -exec /arm/tools/nodejs/node/22.21.0/linux64/bin/node --check '{}' ';'
```

Exit `0`; no output.

```bash
/usr/bin/timeout --signal=KILL 30s /arm/tools/nodejs/node/22.21.0/linux64/bin/node --test public_tests/*.test.mjs
```

Exit `1`; file-suite summary: tests 3, pass 1, fail 2. `lexer.test.mjs` passed;
`parser.test.mjs` and `execution.test.mjs` failed at the documented starter TODOs. This is an
expected baseline observation, not a passing test claim.

```bash
/usr/bin/timeout --signal=KILL 30s /arm/tools/nodejs/node/22.21.0/linux64/bin/node --test sealed/reference_tests/*.test.mjs
/usr/bin/timeout --signal=KILL 30s /arm/tools/nodejs/node/22.21.0/linux64/bin/node sealed/reference_tests/reference.test.mjs
/usr/bin/timeout --signal=KILL 30s /arm/tools/nodejs/node/22.21.0/linux64/bin/node sealed/reference_tests/adversarial.test.mjs
```

All exited `0`. Results were respectively 2/2 file suites, 13/13 direct reference tests, and 3/3
direct adversarial tests.

## CLI and pack audit

```bash
printf %s 'let n = 4; if (n > 2) { print n * 2; n + 6; } else { 0; }' | /usr/bin/timeout --signal=KILL 10s /arm/tools/nodejs/node/22.21.0/linux64/bin/node sealed/reference/src/cli.mjs --backend tree
printf %s 'let n = 4; if (n > 2) { print n * 2; n + 6; } else { 0; }' | /usr/bin/timeout --signal=KILL 10s /arm/tools/nodejs/node/22.21.0/linux64/bin/node sealed/reference/src/cli.mjs --backend vm
```

Both exited `0` and printed exactly `8` followed by a newline.

```bash
/usr/bin/timeout --signal=KILL 30s /arm/tools/nodejs/node/22.21.0/linux64/bin/node environment/verify-pack.mjs
```

Exit `0`. The JSON result reported `PASS`, 23 required regular files, 57 scanned files, zero
forbidden paths, zero symlinks/special files, zero credential-pattern matches, status `GENERATED`,
and labels `GENERATED`, `PARTIAL`.

## Independent behavior matrix

The exact matrix source is retained below. It was extracted from this file and piped to the pinned
runtime with this bounded command from `CANDIDATE/`:

```bash
/usr/bin/awk '/^\/\/ REVIEW_MATRIX_BEGIN$/{capture=1;next} /^\/\/ REVIEW_MATRIX_END$/{capture=0} capture' ../VALIDATION.md | /usr/bin/timeout --signal=KILL 20s /arm/tools/nodejs/node/22.21.0/linux64/bin/node --input-type=module
```

Exit `0`; output:

```json
{"status":"PASS","assertions":99,"validProgramsAcrossBothBackends":28,"runtimeErrorProgramsAcrossBothBackends":14,"syntaxErrorPrograms":6,"malformedChunks":12}
```

```js
// REVIEW_MATRIX_BEGIN
import assert from "node:assert/strict";
import { execute } from "./sealed/reference/src/pipeline.mjs";
import { run } from "./sealed/reference/src/vm.mjs";
let assertions = 0;
const eq = (actual, expected, label) => {
  assert.deepEqual(actual, expected, label);
  assertions += 1;
};
const valid = [
  ["", null, []],
  ["1 + 2 * 3;", 7, []],
  ["-4 + 10 / 2;", 1, []],
  ["!nil == true;", true, []],
  ["0 == -0;", true, []],
  ["\"a\" + \"b\";", "ab", []],
  ["1 < 2 == true;", true, []],
  ["let a = 1; let b = 2; a = b = 9; a + b;", 18, []],
  ["let x = 4; { let x = x + 1; print x; } x;", 4, ["5"]],
  ["if (false) { missing; } else { 8; }", 8, []],
  ["if (0) { 1; } else { 2; }", 1, []],
  ["if (\"\") { 1; } else { 2; }", 1, []],
  ["{ let inner = 3; inner * 2; }", 6, []],
  ["print nil; print true; print false; print -0;", null, ["nil", "true", "false", "0"]],
];
for (const [source, value, output] of valid) {
  for (const backend of ["tree", "vm"]) eq(execute(source, { backend }), { value, output }, backend + source);
}
const runtimeErrors = [
  ["missing;", "E_UNDEFINED_NAME"],
  ["1 + \"x\";", "E_TYPE"],
  ["\"x\" - 1;", "E_TYPE"],
  ["1 / 0;", "E_DIV_ZERO"],
  ["let x = 1; let x = 2;", "E_DUPLICATE_BINDING"],
  ["x = 3;", "E_UNDEFINED_NAME"],
  ["-\"x\";", "E_TYPE"],
];
for (const [source, code] of runtimeErrors) {
  const spans = [];
  for (const backend of ["tree", "vm"]) {
    let caught;
    try { execute(source, { backend }); } catch (error) { caught = error; }
    eq(caught?.name, "MicaRuntimeError", backend + source);
    eq(caught?.code, code, backend + source);
    spans.push(caught?.span);
  }
  eq(spans[0], spans[1], source);
}
const quote = String.fromCharCode(34);
const slash = String.fromCharCode(92);
const syntaxErrors = [
  ["@", "E_UNEXPECTED_CHARACTER"],
  [quote + "bad" + slash + "q" + quote + ";", "E_INVALID_ESCAPE"],
  [quote + "unfinished", "E_UNTERMINATED_STRING"],
  ["1 = 2;", "E_INVALID_ASSIGNMENT"],
  ["print 1", "E_EXPECTED_TOKEN"],
  ["(x) = 1;", "E_INVALID_ASSIGNMENT"],
];
for (const [source, code] of syntaxErrors) {
  let caught;
  try { execute(source); } catch (error) { caught = error; }
  eq(caught?.name, "MicaSyntaxError", source);
  eq(caught?.code, code, source);
}
const malformed = [
  null,
  {},
  { constants: [], code: [] },
  { constants: [Infinity], code: [{ op: "HALT", arg: null, span: null }] },
  { constants: [], code: [{ op: "CONSTANT", arg: 0, span: null }] },
  { constants: [], code: [{ op: "MYSTERY", arg: null, span: null }] },
  { constants: [], code: [{ op: "POP", arg: null, span: null }, { op: "HALT", arg: null, span: null }] },
  { constants: [true], code: [{ op: "CONSTANT", arg: 0, span: null }, { op: "JUMP", arg: 4, span: null }] },
  { constants: [null], code: [{ op: "CONSTANT", arg: 0, span: null }, { op: "HALT", arg: 1, span: null }] },
  { constants: [null], code: [{ op: "CONSTANT", arg: 0, span: null }, { op: "LOAD", arg: "bad-name", span: null }] },
  { constants: [null], code: [{ op: "CONSTANT", arg: 0, span: null }, { op: "ENTER_SCOPE", arg: null, span: null }, { op: "HALT", arg: null, span: null }] },
  { constants: [], code: [{ op: "JUMP", arg: 0, span: null }, { op: "HALT", arg: null, span: null }] },
];
for (const chunk of malformed) {
  let caught;
  try { run(chunk); } catch (error) { caught = error; }
  eq(caught?.name, "MicaRuntimeError", "malformed type");
  eq(caught?.code, "E_INVALID_BYTECODE", "malformed code");
}
console.log(JSON.stringify({
  status: "PASS",
  assertions,
  validProgramsAcrossBothBackends: valid.length * 2,
  runtimeErrorProgramsAcrossBothBackends: runtimeErrors.length * 2,
  syntaxErrorPrograms: syntaxErrors.length,
  malformedChunks: malformed.length,
}));
// REVIEW_MATRIX_END
```

## Input non-mutation probe

```bash
/usr/bin/timeout --signal=KILL 10s /arm/tools/nodejs/node/22.21.0/linux64/bin/node --input-type=module --eval 'import assert from "node:assert/strict"; import { tokenize } from "./sealed/reference/src/lexer.mjs"; import { parse } from "./sealed/reference/src/parser.mjs"; import { interpret } from "./sealed/reference/src/interpreter.mjs"; import { compile } from "./sealed/reference/src/compiler.mjs"; import { run } from "./sealed/reference/src/vm.mjs"; const tokens = tokenize("let x = 2; x + 3;"); const tokenSnapshot = structuredClone(tokens); const ast = parse(tokens); assert.deepEqual(tokens, tokenSnapshot); const astSnapshot = structuredClone(ast); interpret(ast); const chunk = compile(ast); assert.deepEqual(ast, astSnapshot); const chunkSnapshot = structuredClone(chunk); run(chunk); assert.deepEqual(chunk, chunkSnapshot); console.log(JSON.stringify({ status: "PASS", tokenInputUnchanged: true, astInputUnchanged: true, chunkInputUnchanged: true }));'
```

Exit `0`; output confirmed token, AST, and chunk inputs remained unchanged.

## Reproduced VM contract defect

```bash
/usr/bin/timeout --signal=KILL 10s /arm/tools/nodejs/node/22.21.0/linux64/bin/node --input-type=module --eval 'import { run } from "./sealed/reference/src/vm.mjs"; const results = []; for (const op of [Symbol("bad"), { toString() { throw new Error("attacker coercion executed"); } }]) { try { run({ constants: [], code: [{ op, arg: null, span: null }] }); } catch (error) { results.push({ name: error.name, code: error.code ?? null, message: error.message }); } } console.log(JSON.stringify(results));'
```

Exit `0`; observed probe output:

```json
[{"name":"TypeError","code":null,"message":"Cannot convert a Symbol value to a string"},{"name":"Error","code":null,"message":"attacker coercion executed"}]
```

The process exit is from the probe catching and reporting the errors; the returned error types are the
failed contract observation.

```bash
/usr/bin/timeout --signal=KILL 10s /arm/tools/nodejs/node/22.21.0/linux64/bin/node --input-type=module --eval 'import { run } from "./sealed/reference/src/vm.mjs"; try { run({ constants: [], code: [{ op: "LOAD", arg: "missing", span: "not-a-span" }, { op: "HALT", arg: null, span: null }] }); } catch (error) { console.log(JSON.stringify({ name: error.name, code: error.code ?? null, span: error.span })); }'
```

Exit `0`; observed `{"name":"MicaRuntimeError","code":"E_UNDEFINED_NAME","span":"not-a-span"}`.
The VM accepted malformed span metadata instead of rejecting the chunk as `E_INVALID_BYTECODE`.

## Static and provenance checks

All inspected imports are relative paths or these Node built-ins: `node:assert/strict`, `node:fs`,
`node:fs/promises`, `node:path`, `node:perf_hooks`, `node:test`, and `node:url`. A bounded grep over all
submitted `.mjs` files found no calls to `eval` or `Function` and no imports of Node network or
subprocess modules.

```bash
/usr/bin/sha256sum PROVENANCE.json MANIFEST.yaml
```

Observed file hashes:

```text
be80da9777a7b3f1b6a4d2d40a2f3cde0f9212467b828a636140bc281ff94bdc  PROVENANCE.json
4d0c9b613b4efbce749d94fb1f337fc1ae861801802d16c7b174389f6af0d661  MANIFEST.yaml
```

An independent JSON parse confirmed matching project IDs, source IDs, source commits, and the
manifest-to-provenance snapshot link. It also confirmed `linked_content_copied: false`, linked
resource license `NOASSERTION`, labels `GENERATED` and `PARTIAL`, `productionized: false`, and
`independent_validation: REQUIRED`.

## Limitations

- The upstream/catalog material needed to recompute recorded source hashes or compare the no-copy
  assertion is absent, and network access is restricted.
- This is the full reviewer bundle. No materialized student view was supplied to prove that external
  packaging excludes every `sealed/` path.
- Only the pinned Node 22.21.0 runtime was exercised. No fuzzing, qualified benchmark, transfer
  verification, security certification, or production-readiness claim was made.
- `git` and `rg` are unavailable on `PATH`; hashes plus `find`, `grep`, and direct inspection were
  used. Other configured language toolchains were irrelevant to this dependency-free JavaScript
  artifact and were not invoked.

No `REVIEWED` label is awarded by this record.
