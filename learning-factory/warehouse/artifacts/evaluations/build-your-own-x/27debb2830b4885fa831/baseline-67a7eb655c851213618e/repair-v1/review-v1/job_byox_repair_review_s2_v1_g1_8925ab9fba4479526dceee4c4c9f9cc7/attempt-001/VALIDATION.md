# Independent validation evidence

Review date: 2026-09-03. `CANDIDATE/` was treated as immutable. Commands below ran from:

```text
/projects/se/pj34000401_refsys/users/yuali01/learn/learning-factory/warehouse/workspaces/job_byox_repair_review_s2_v1_g1_8925ab9fba4479526dceee4c4c9f9cc7/attempt-001/CANDIDATE
```

The sandbox launcher emitted `/usr/bin/id` name-resolution warnings for its numeric user/group before commands. They did not change exit statuses and are omitted from result excerpts.

## Pinned runtime

Exact command:

```bash
/usr/bin/timeout --signal=KILL 10s /arm/tools/nodejs/node/22.21.0/linux64/bin/node --version
```

Exit `0`; output:

```text
v22.21.0
```

This was the only relevant configured language runtime. The review did not substitute an ambient `node` binary.

## Syntax

Exact command:

```bash
/usr/bin/timeout --signal=KILL 30s /usr/bin/find starter public_tests environment sealed -type f -name '*.mjs' -exec /arm/tools/nodejs/node/22.21.0/linux64/bin/node --check '{}' ';'
```

Exit `0`; no JavaScript diagnostic output.

## Submitted reference tests

Exact commands:

```bash
/usr/bin/timeout --signal=KILL 30s /arm/tools/nodejs/node/22.21.0/linux64/bin/node --test sealed/reference_tests/*.test.mjs
/usr/bin/timeout --signal=KILL 30s /arm/tools/nodejs/node/22.21.0/linux64/bin/node sealed/reference_tests/reference.test.mjs
/usr/bin/timeout --signal=KILL 30s /arm/tools/nodejs/node/22.21.0/linux64/bin/node sealed/reference_tests/adversarial.test.mjs
```

All exited `0`. The aggregate run reported two file suites passed and zero failed. Direct runs reported 13/13 reference tests and 6/6 adversarial tests passed.

These are candidate-authored tests and therefore were corroborated with independent probes below; their success alone is not a `TESTED` or `REVIEWED` label.

## Independent semantic oracle matrix

Exact command:

```bash
/usr/bin/timeout --signal=KILL 30s /arm/tools/nodejs/node/22.21.0/linux64/bin/node --input-type=module --eval 'import assert from "node:assert/strict"; import { execute } from "./sealed/reference/src/pipeline.mjs"; const values=[-3,-1,0,2,5]; const ops=["+","-","*","/","==","!=","<","<=",">",">="]; const expected=(op,a,b)=>op==="+"?a+b:op==="-"?a-b:op==="*"?a*b:op==="/"?a/b:op==="=="?a===b:op==="!="?a!==b:op==="<"?a<b:op==="<="?a<=b:op===">"?a>b:a>=b; let executions=0; for(const a of values){for(const b of values){for(const op of ops){const source="("+a+") "+op+" ("+b+");"; for(const backend of ["tree","vm"]){if(op==="/"&&b===0){assert.throws(()=>execute(source,{backend}),e=>e?.code==="E_DIV_ZERO");}else{assert.deepEqual(execute(source,{backend}),{value:expected(op,a,b),output:[]});} executions+=1;}}}} const cases=[["",{value:null,output:[]}],["let a = 0; let b = 0; a = b = 4; a + b;",{value:8,output:[]}],["let x = 4; { let x = x + 1; print x; } x;",{value:4,output:["5"]}],["if (0) { 7; } else { 8; }",{value:7,output:[]}],["if (nil) { 7; } else { 8; }",{value:8,output:[]}],["print nil; print true; print false; print 2.5; \"a\" + \"b\";",{value:"ab",output:["nil","true","false","2.5"]}],["{ 1; 2; }",{value:2,output:[]}]]; for(const [source,want] of cases){for(const backend of ["tree","vm"]){assert.deepEqual(execute(source,{backend}),want); executions+=1;}} console.log(JSON.stringify({status:"PASS",executions,cases:cases.length,operatorPairs:values.length*values.length*ops.length}));'
```

Exit `0`; output:

```json
{"status":"PASS","executions":514,"cases":7,"operatorPairs":250}
```

This is a bounded deterministic matrix, not fuzzing.

## Independent mutation and malformed-bytecode probe

Exact command:

```bash
/usr/bin/timeout --signal=KILL 30s /arm/tools/nodejs/node/22.21.0/linux64/bin/node --input-type=module --eval 'import assert from "node:assert/strict"; import { tokenize } from "./sealed/reference/src/lexer.mjs"; import { parse } from "./sealed/reference/src/parser.mjs"; import { interpret } from "./sealed/reference/src/interpreter.mjs"; import { compile } from "./sealed/reference/src/compiler.mjs"; import { run } from "./sealed/reference/src/vm.mjs"; const tokens=tokenize("let x = 2; x + 3;"); const tokenCopy=structuredClone(tokens); const ast=parse(tokens); assert.deepEqual(tokens,tokenCopy); const astCopy=structuredClone(ast); interpret(ast); const chunk=compile(ast); assert.deepEqual(ast,astCopy); const chunkCopy=structuredClone(chunk); run(chunk); assert.deepEqual(chunk,chunkCopy); let getters=0; const accessorChunk={code:[{op:"HALT",arg:null,span:null}]}; Object.defineProperty(accessorChunk,"constants",{get(){getters+=1;return [];}}); const sparseConstants=[]; sparseConstants.length=1; const malformed=[accessorChunk,Object.create({constants:[],code:[{op:"HALT",arg:null,span:null}]}),{constants:sparseConstants,code:[{op:"CONSTANT",arg:0,span:null},{op:"HALT",arg:null,span:null}]},{constants:[],code:[{op:"LOAD",arg:"x",span:{start:{offset:2,line:1,column:3},end:{offset:1,line:1,column:2}}},{op:"HALT",arg:null,span:null}]}]; for(const value of malformed){assert.throws(()=>run(value),e=>e?.name==="MicaRuntimeError"&&e.code==="E_INVALID_BYTECODE"&&e.span===null);} assert.equal(getters,0); console.log(JSON.stringify({status:"PASS",inputNonMutation:true,malformedRejected:malformed.length,getterCalls:getters}));'
```

Exit `0`; output:

```json
{"status":"PASS","inputNonMutation":true,"malformedRejected":4,"getterCalls":0}
```

## CLI parity

Exact commands:

```bash
/usr/bin/printf %s 'let n = 4; if (n > 2) { print n * 2; n + 6; } else { 0; }' | /usr/bin/timeout --signal=KILL 10s /arm/tools/nodejs/node/22.21.0/linux64/bin/node sealed/reference/src/cli.mjs --backend tree
/usr/bin/printf %s 'let n = 4; if (n > 2) { print n * 2; n + 6; } else { 0; }' | /usr/bin/timeout --signal=KILL 10s /arm/tools/nodejs/node/22.21.0/linux64/bin/node sealed/reference/src/cli.mjs --backend vm
```

Both exited `0` and printed exactly `8` plus a newline.

## Untouched public starter baseline

Exact command:

```bash
/usr/bin/timeout --signal=KILL 30s /arm/tools/nodejs/node/22.21.0/linux64/bin/node --test public_tests/*.test.mjs
```

Exit `1`. Three file suites ran: `lexer.test.mjs` passed; `parser.test.mjs` and `execution.test.mjs` failed. This matches the documented TODO baseline and is not represented as a passing learner suite.

## Pack audit and metadata

Exact commands:

```bash
/usr/bin/timeout --signal=KILL 30s /arm/tools/nodejs/node/22.21.0/linux64/bin/node environment/verify-pack.mjs
/usr/bin/timeout --signal=KILL 10s /usr/bin/sha256sum MANIFEST.yaml PROVENANCE.json
/usr/bin/timeout --signal=KILL 10s /arm/tools/nodejs/node/22.21.0/linux64/bin/node --input-type=module --eval 'import assert from "node:assert/strict"; import {readFileSync} from "node:fs"; const m=JSON.parse(readFileSync("MANIFEST.yaml","utf8")); const p=JSON.parse(readFileSync("PROVENANCE.json","utf8")); assert.equal(m.project_id,p.project.project_id); assert.equal(m.source_id,p.source.source_id); assert.equal(m.source_commit,p.source.commit_hash); assert.equal(m.provenance_sha256,p.snapshot_sha256); assert.deepEqual(m.validation_labels,["GENERATED","PARTIAL"]); assert.equal(m.productionized,false); console.log(JSON.stringify({status:"PASS",project_id:m.project_id,source_id:m.source_id,source_commit:m.source_commit,labels:m.validation_labels,productionized:m.productionized}));'
```

All exited `0`. Audit output:

```json
{
  "status": "PASS",
  "requiredRegularFiles": 23,
  "forbiddenPathsPresent": 0,
  "symlinksOrSpecialFiles": 0,
  "credentialPatternMatches": 0,
  "scannedFiles": 57,
  "manifestStatus": "GENERATED",
  "validationLabels": ["GENERATED", "PARTIAL"]
}
```

Observed hashes:

```text
4d0c9b613b4efbce749d94fb1f337fc1ae861801802d16c7b174389f6af0d661  MANIFEST.yaml
be80da9777a7b3f1b6a4d2d40a2f3cde0f9212467b828a636140bc281ff94bdc  PROVENANCE.json
```

The metadata assertion printed `PASS`, the expected project/source/commit identifiers, labels `GENERATED`,`PARTIAL`, and `productionized:false`. This establishes internal consistency only; the upstream baseline was unavailable for comparison.

## Static boundary checks

Exact commands (run from the parent review workspace where shown paths are valid):

```bash
grep -R -nE '(^|[[:space:]])(import|export).*from[[:space:]]+"' CANDIDATE --include='*.mjs' | sort
grep -R -nE '(^|[^[:alnum:]_])(eval|Function|child_process|fetch|WebSocket)[[:space:]]*\(' CANDIDATE --include='*.mjs' || true
find CANDIDATE \( -type l -o \! -type d -a \! -type f \) -print
find CANDIDATE -path '*/sealed/*' -type f -printf '%m %p\n' | sort
```

All imports were Node built-ins or relative modules. The forbidden-API pattern and symlink/special-file scans printed no matches. Sealed files were regular, mode `444`, but remained readable in this submitted tree; no generated learner-view inventory was present.

## Documentation reproducer and Unicode observation

Exact commands:

```bash
/usr/bin/timeout --signal=KILL 10s /arm/tools/nodejs/node/22.21.0/linux64/bin/node starter/src/cli.mjs --backend tree examples.mica
/usr/bin/timeout --signal=KILL 10s /arm/tools/nodejs/node/22.21.0/linux64/bin/node --input-type=module --eval 'import {tokenize} from "./starter/src/lexer.mjs"; const token=tokenize("\"😀\"; print 1;").find(value=>value.type==="PRINT"); console.log(JSON.stringify({printStart:token.span.start,sourceCodeUnits:"\"😀\"; print 1;".length,sourceCodePoints:Array.from("\"😀\"; print 1;").length}));'
```

The documented CLI command exited `1`:

```text
ENOENT: ENOENT: no such file or directory, open 'examples.mica'
```

The Unicode observation exited `0`:

```json
{"printStart":{"offset":6,"line":1,"column":7},"sourceCodeUnits":14,"sourceCodePoints":13}
```

The implementation is self-consistent; the finding is that the required coordinate unit is not documented.

## Limitations and unclaimed labels

- The upstream snapshot/repository and external network were unavailable; no upstream content or license comparison was possible.
- Only Node.js `v22.21.0` was run. Other configured non-JavaScript toolchains were irrelevant and were not exercised. `rg` and `git` were absent from `PATH`, so `find`/`grep` were used.
- No benchmark harness was run. No fuzzing, formal proof, security certification, cross-runtime matrix, transfer verification, or production-readiness check was performed.
- No `REVIEWED` label is awarded here; publication remains controlled by the orchestrator acceptance validator.
