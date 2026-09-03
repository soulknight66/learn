# Independent validation evidence

Checks ran on 2026-09-03 from the review workspace. Commands below that use relative source paths
ran from `CANDIDATE/`. The launcher repeatedly printed numeric user/group name-resolution warnings;
they are omitted from short excerpts because they did not change any exit status. No dependency was
installed and no network operation ran.

## Pinned toolchain

```bash
/usr/bin/timeout --signal=KILL 10s /arm/tools/nodejs/node/22.21.0/linux64/bin/node --version
```

Exit `0`; output:

```text
v22.21.0
```

Node.js was the only configured language toolchain relevant to this JavaScript-only candidate.
`rg` was unavailable, so read-only discovery used `/usr/bin/find` and `/usr/bin/grep`.

## Syntax and submitted suites

```bash
/usr/bin/timeout --signal=KILL 30s /usr/bin/find starter public_tests environment sealed -type f -name '*.mjs' -exec /arm/tools/nodejs/node/22.21.0/linux64/bin/node --check '{}' ';'
/usr/bin/timeout --signal=KILL 30s /arm/tools/nodejs/node/22.21.0/linux64/bin/node sealed/reference_tests/reference.test.mjs
/usr/bin/timeout --signal=KILL 30s /arm/tools/nodejs/node/22.21.0/linux64/bin/node sealed/reference_tests/adversarial.test.mjs
/usr/bin/timeout --signal=KILL 30s /arm/tools/nodejs/node/22.21.0/linux64/bin/node sealed/reference_tests/learner-view.test.mjs
/usr/bin/timeout --signal=KILL 30s /arm/tools/nodejs/node/22.21.0/linux64/bin/node --test sealed/reference_tests/*.test.mjs
```

All exited `0`. Syntax checking emitted no diagnostics. Direct runs passed 14/14 reference tests,
6/6 adversarial tests, and 4/4 learner-view tests. The aggregate runner passed all 3 test-file
subtests.

The untouched learner baseline was checked separately:

```bash
/usr/bin/timeout --signal=KILL 30s /arm/tools/nodejs/node/22.21.0/linux64/bin/node --test public_tests/*.test.mjs
```

Exit `1`: 3 file subtests ran; `lexer.test.mjs` passed, while `parser.test.mjs` and
`execution.test.mjs` failed at the intentional TODO stages. This matches the documentation and is
not recorded as a passing implementation.

## Independent semantic matrix

The following bounded probe used an independent value/operator oracle, checked both backends, and
also required equal result-or-error observations and spans:

```bash
/usr/bin/timeout --signal=KILL 30s /arm/tools/nodejs/node/22.21.0/linux64/bin/node --input-type=module --eval '
import assert from "node:assert/strict";
import {execute} from "./sealed/reference/src/pipeline.mjs";
const values=[["nil",null],["false",false],["true",true],["0",0],["1",1],["-1",-1],["2.5",2.5],["\"\"",""],["\"a\"","a"]];
const operators=["+","-","*","/","==","!=","<","<=",">",">="];
function oracle(op,a,b){const nums=typeof a==="number"&&typeof b==="number";if(op==="+"){if(nums||(typeof a==="string"&&typeof b==="string")){const value=a+b;return typeof value==="number"&&!Number.isFinite(value)?{code:"E_NUMBER_RANGE"}:{value};}return{code:"E_TYPE"};}if(op==="=="||op==="!="){const equal=typeof a===typeof b&&a===b;return{value:op==="=="?equal:!equal};}if(!nums)return{code:"E_TYPE"};if(op==="/"&&b===0)return{code:"E_DIV_ZERO"};return{value:op==="-"?a-b:op==="*"?a*b:op==="/"?a/b:op==="<"?a<b:op==="<="?a<=b:op===">"?a>b:a>=b};}
let checks=0;
for(const [as,a] of values)for(const [bs,b] of values)for(const op of operators){const source="("+as+") "+op+" ("+bs+");";const expected=oracle(op,a,b);const seen=[];for(const backend of ["tree","vm"]){try{const result=execute(source,{backend});assert.equal(Object.hasOwn(expected,"value"),true);assert.deepEqual(result,{value:expected.value,output:[]});seen.push({result});}catch(error){assert.equal(error?.name,"MicaRuntimeError");assert.equal(error?.code,expected.code);seen.push({code:error.code,span:error.span});}checks+=1;}assert.deepEqual(seen[0],seen[1]);}
console.log(JSON.stringify({status:"PASS",checks}));
'
```

Exit `0`:

```json
{"status":"PASS","checks":1620}
```

A broader direct probe also checked 36 expected program/backend results and 12 expected runtime-error
observations. Its corrected run exited `0` with
`{"status":"PASS","directChecks":36,"matrixChecks":1620,"errorChecks":12,"totalChecks":1668}`.
An initial version of that reviewer probe exited `1` because its hand-written overflow literal was
already non-finite and correctly failed lexing; regenerating exactly `1` plus 308 zeros made the
intended finite-input runtime-overflow assertion valid. This was a reviewer fixture error, not a
candidate failure.

## Independent bytecode and mutation probes

The bytecode probe supplied malformed empty/sparse arrays, non-Mica constants, non-string and
unknown opcodes, bad operands/names/jumps, underflow, global-scope exit, a backward loop, malformed
spans, and an accessor-backed required field. It then ran a valid conditional chunk:

```bash
/usr/bin/timeout --signal=KILL 30s /arm/tools/nodejs/node/22.21.0/linux64/bin/node --input-type=module --eval '
import assert from "node:assert/strict";
import {run} from "./sealed/reference/src/vm.mjs";
const i=(op,arg=null,span=null)=>({op,arg,span});
const bad=[null,{}, {constants:[],code:[]},{constants:[,],code:[i("HALT")]},{constants:[undefined],code:[i("HALT")]},{constants:[NaN],code:[i("HALT")]},{constants:[Infinity],code:[i("HALT")]},{constants:[1n],code:[i("HALT")]},{constants:[],code:[i(Symbol("x"))]},{constants:[],code:[i("UNKNOWN")]},{constants:[],code:[i("HALT",0)]},{constants:[],code:[i("CONSTANT",0)]},{constants:[1],code:[i("CONSTANT",-1)]},{constants:[],code:[i("LOAD","bad-name"),i("HALT")]},{constants:[],code:[i("JUMP",2),i("HALT")]},{constants:[],code:[i("POP"),i("HALT")]},{constants:[],code:[i("EXIT_SCOPE"),i("HALT")]},{constants:[],code:[i("JUMP",0),i("HALT")]},{constants:[],code:[i("HALT",null,{})]}];
for(const chunk of bad)assert.throws(()=>run(chunk),error=>error?.name==="MicaRuntimeError"&&error.code==="E_INVALID_BYTECODE");
let getterCalls=0;const accessor={arg:null,span:null};Object.defineProperty(accessor,"op",{get(){getterCalls+=1;return"HALT";}});assert.throws(()=>run({constants:[],code:[accessor]}),error=>error?.code==="E_INVALID_BYTECODE");assert.equal(getterCalls,0);
const good={constants:[false,1,2],code:[i("CONSTANT",0),i("JUMP_IF_FALSE",4),i("CONSTANT",1),i("JUMP",5),i("CONSTANT",2),i("HALT")]};assert.deepEqual(run(good),{value:2,output:[]});
console.log(JSON.stringify({status:"PASS",invalidChecks:bad.length+1,accessorGetterCalls:getterCalls,validChecks:1}));
'
```

Exit `0`:

```json
{"status":"PASS","invalidChecks":20,"accessorGetterCalls":0,"validChecks":1}
```

A separate structured-clone probe passed four non-mutation comparisons covering parser tokens,
interpreter AST input, compiler AST input, and VM chunk input. It observed 22 tokens, 2 top-level
statements, and 20 emitted instructions, ending in `HALT`.

## CLI and packaging observations

```bash
/usr/bin/timeout --signal=KILL 10s /arm/tools/nodejs/node/22.21.0/linux64/bin/node sealed/reference/src/cli.mjs --backend tree starter/example.mica
/usr/bin/timeout --signal=KILL 10s /arm/tools/nodejs/node/22.21.0/linux64/bin/node sealed/reference/src/cli.mjs --backend vm starter/example.mica
/usr/bin/timeout --signal=KILL 10s /arm/tools/nodejs/node/22.21.0/linux64/bin/node starter/src/cli.mjs --backend tree starter/example.mica
```

The reference commands exited `0` and each printed `12`. The starter command exited `1` and printed
`TODO: implement parse(tokens) according to REQUIREMENTS.md`, confirming that the sample exists and
the failure is the documented completion point rather than file resolution.

```bash
/usr/bin/timeout --signal=KILL 30s /arm/tools/nodejs/node/22.21.0/linux64/bin/node environment/verify-pack.mjs
/usr/bin/timeout --signal=KILL 30s /arm/tools/nodejs/node/22.21.0/linux64/bin/node environment/verify-learner-view.mjs
```

Both exited `0`. The pack result reported `PASS`, 23 required files, 61 scanned files, zero forbidden
paths/special files/credential matches, labels `GENERATED` + `PARTIAL`, and learner projection
`PASS`. The source inventory reported 25 learner files, 4 directories, 36 excluded instructor files,
29 static module specifiers, zero import escapes, and digest
`9122c9f6206a5d3df1964ed50dd261272b9dbf00bc5d6b8957b8b52134790d43`.

The verifier scripts were not accepted as self-proving. I independently copied only the policy's
six top-level files and three included directories to a sibling `REVIEW_PROJECTION_CHECK/`, then ran:

```bash
/usr/bin/timeout --signal=KILL 30s /arm/tools/nodejs/node/22.21.0/linux64/bin/node CANDIDATE/environment/verify-learner-view.mjs --projected-root REVIEW_PROJECTION_CHECK
```

Exit `0` reported materialized-projection `PASS`, 25 files, 4 directories, the same digest, and zero
excluded-component matches. A sorted independent file listing contained no `sealed` component. The
scratch projection was removed after the check; `CANDIDATE/` was never written.

The static source and filesystem checks were:

```bash
if /usr/bin/grep -R -nE '(^|[^[:alnum:]_])(eval|Function|child_process|fetch|WebSocket)[[:space:]]*\(' starter public_tests environment sealed --include='*.mjs'; then exit 1; else review_scan_status=$?; if [ "$review_scan_status" -eq 1 ]; then /usr/bin/printf '%s\n' 'PASS: no forbidden API call pattern'; else exit "$review_scan_status"; fi; fi
/usr/bin/find . \( -type l -o \! -type d -a \! -type f \) -print
```

Both exited `0`; the scan printed `PASS: no forbidden API call pattern`, and the special-file query
printed nothing. Manual import inspection found only `node:` built-ins and repository-relative
modules.

## Metadata and immutability

```bash
/usr/bin/sha256sum MANIFEST.yaml PROVENANCE.json
```

Exit `0`:

```text
4d0c9b613b4efbce749d94fb1f337fc1ae861801802d16c7b174389f6af0d661  MANIFEST.yaml
be80da9777a7b3f1b6a4d2d40a2f3cde0f9212467b828a636140bc281ff94bdc  PROVENANCE.json
```

Independent JSON assertions confirmed equal project/source/commit/snapshot identifiers across the
two files, `linked_content_copied: false`, labels exactly `GENERATED` + `PARTIAL`, and
`productionized: false`. These establish internal consistency only; the unavailable upstream and
catalog snapshot prevent external provenance confirmation.

From the review-workspace root, before and after all checks:

```bash
find CANDIDATE -type f -print0 | LC_ALL=C sort -z | xargs -0 sha256sum | sha256sum
```

Both observations were identical:

```text
e68dd5a1574d00470f94c8bd4110254e98f7267d91b10997318c533e345ee9f5  -
```

The candidate retained 61 regular files and no symlinks.

## Limitations

- No upstream fetch, immutable source-snapshot comparison, or independent authorship/no-copy proof
  was possible.
- The generated material has no affirmative redistribution license; transfer remains blocked.
- Only pinned Node.js v22.21.0 on this host was exercised.
- No benchmark qualification, fuzzing qualification, formal proof, security certification,
  resource-exhaustion campaign, or production assessment was performed.
- The materialized comparison was reviewer evidence, not the orchestrator's acceptance/transfer
  validator and not an award of `REVIEWED`.
