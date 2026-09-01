# Independent validation record

Review date: 2026-08-31. Commands ran from the review workspace root unless a different directory is
shown. The shell emitted repeated user/group lookup warnings before commands; those environmental
warnings are omitted below unless relevant. `CANDIDATE/` was not edited.

## Submission inventory and integrity

```sh
find CANDIDATE -type f | wc -l
find CANDIDATE -type d | wc -l
find CANDIDATE -type l | wc -l
find CANDIDATE -type f -print0 | LC_ALL=C sort -z | xargs -0 sha256sum | sha256sum
```

Observed: 61 files, 23 directories, zero symlinks, and aggregate digest:

```text
a890f7728420b39426d96ba632bdcbef630d16d389a7988da3e723372970f98c  -
```

The same aggregate digest was observed before and after all probes.

```sh
sha256sum CANDIDATE/PROVENANCE.json CANDIDATE/MANIFEST.yaml
```

```text
38d103ccd74dbebc95e4170aa8f166278e1394ee3f7dc7fcb6a961457bd6b8ee  CANDIDATE/PROVENANCE.json
008027c09f7371397b2b4061577c52df3d6a5dbe83a31caded2bd86304fbaf33  CANDIDATE/MANIFEST.yaml
```

The manifest `provenance_sha256` is an embedded snapshot identifier, not the byte hash of
`PROVENANCE.json`. It equals `PROVENANCE.json.snapshot_sha256`; the referenced source snapshot was
not available to recompute.

An independent JSON read observed:

```text
manifest_project=project_c305a6b70f268e23e2e48694e3604f28
manifest_status=GENERATED
validation_labels=GENERATED,PARTIAL
independent_validation=REQUIRED
productionized=false
binding_match=true
linked_resource_license=NOASSERTION
linked_content_copied=false
```

## Submitted structure checker

From `CANDIDATE/`:

```sh
timeout 30s python3 environment/verify_artifact.py
```

Exit 0:

```text
artifact verification: PASS (23 required paths, 0 forbidden paths)
JSON and credential-pattern scans: PASS
lightweight JavaScript delimiter scan: PASS (31 files; not a syntax check)
```

This is reproducible structural evidence from a candidate-supplied checker. It is not proof of a
build, JavaScript syntax, runtime correctness, secret absence beyond its patterns, or any validation
label.

## Toolchain and intended entry points

```sh
command -v node npm nodejs deno bun qjs js quickjs jjs d8 gjs
python3 --version
gjs --version
```

Only `/usr/bin/gjs` was found. Python reported 3.6.8 and GJS reported 1.56.2. Direct probes for
`node --version` and `npm --version` each exited 127 with `command not found`.

The documented commands were attempted independently with 30-second bounds:

```sh
cd CANDIDATE/starter && timeout 30s npm test
cd CANDIDATE/starter && timeout 30s npm run test:public
cd CANDIDATE/sealed/reference && timeout 30s npm test
cd CANDIDATE && timeout 30s node benchmarks/run.mjs ../sealed/reference/src/index.js
```

Each exited 127 because `npm` or `node` was absent. No test assertion and no benchmark workload ran.

Direct GJS attempts from `CANDIDATE/`:

```sh
timeout 30s gjs sealed/reference/src/index.js
timeout 30s gjs -m sealed/reference/src/index.js
```

The first exited 1 because GJS loaded a classic script and rejected the top-level import. The second
exited 133 because `-m` is unknown. Therefore GJS cannot validate original ESM linkage.

## Package-boundary inspection

```sh
find CANDIDATE -name package.json -type f -print | LC_ALL=C sort
```

```text
CANDIDATE/sealed/reference/package.json
CANDIDATE/starter/package.json
```

The import-bearing `.js` files in `public_tests/`, `sealed/reference_tests/`, and `debugging/` are
outside both `type=module` package trees. With Node unavailable, the resulting compatibility problem
could only be checked statically; see `REVIEW.md`.

## Static boundary scans

```sh
grep -RInE '\b(eval|Function|child_process|process\.env)\b|node:(fs|net|http|https)' \
  CANDIDATE/starter/src CANDIDATE/sealed/reference/src || true
grep -RInE 'sealed|reference|hidden|solution|answers' \
  CANDIDATE/public_tests CANDIDATE/starter --exclude=README.md || true
find CANDIDATE -type l -print
```

All three produced no matches. This supports, but does not prove, the claimed host-effect and
learner-import boundaries. The full artifact nevertheless contains sealed answers and no supplied
student-view constructor.

## Supplemental transformed execution

The submitted legacy-shell smoke was rerun:

```sh
cd CANDIDATE
set -o pipefail
timeout 30s python3 sealed/reference_tests/gjs_bundle.py | timeout 30s gjs /dev/stdin
```

Exit 0:

```text
GJS_TRANSPILED_SMOKE_PASS
```

A separate reviewer-authored inline harness loaded the mechanically transformed modules and made 28
assertions over arithmetic/operator behavior, loops, branches, scope, truthiness, typed source
errors, input non-mutation, and malformed bytecode. It exited 0 with:

```text
INDEPENDENT_TRANSFORMED_ASSERTIONS_PASS count=28
```

GJS also warned once about reading an undefined `line` property while constructing a deliberately
locationless error. Both runs executed transformed streams, not the original modules or `node:test`.
They earn no `BUILDS` or `TESTED` label.

## Focused correctness probes

Each probe appended reviewer code to the transformed module stream and was bounded by 30 seconds.
The transformations relevant to the first three probes do not change keyword lookup, compiler
recursion, or evaluation-step accounting.

### Valid inherited-name identifiers

Input names were `constructor`, `toString`, `hasOwnProperty`, and `__proto__`. Exit 0, observed:

```text
constructor: type-kind=function, identifier=false
toString: type-kind=function, identifier=false
hasOwnProperty: type-kind=function, identifier=false
__proto__: type-kind=object, identifier=false
constructor-program: ParseError stage=parse line=1 column=5
```

The responsible original expression is `KEYWORDS[text] ?? T.IDENTIFIER`; the transform preserves its
nullish semantics.

### Flat-expression engine parity

The inline probe generated `N` terms as `1+1+...+1;` and ran both engines with defaults. Exit 0:

```text
100 terms tree: value=100
100 terms vm: value=100
500 terms tree: value=500
500 terms vm: value=500
999 terms tree: value=999
999 terms vm: value=999
1000 terms tree: value=1000
1000 terms vm: CompileError stage=compile message=Compile depth exceeds 1000 at 1:1
1100 terms tree: value=1100
1100 terms vm: CompileError stage=compile message=Compile depth exceeds 1000 at 1:200
```

### Bytecode array prototypes

The normal submitted transformer rewrites `.at(-1)` to indexing, which would mask this question. For
this probe only, the reviewer reused its other mechanical downlevels but preserved the original
`program.code.at(-1)` and `code.at(-1)` calls, with the same `Array.prototype.at` polyfill. The test
used dense arrays with no extra own fields. Exit 0:

```text
custom-prototype: success result={"value":null,"output":[]} atCalls=1
null-prototype: TypeError stage=undefined message=program.code.at is not a function
```

Static inspection confirms the original calls at `sealed/reference/src/vm.js:65,138` and the absence
of a prototype check at lines 270-280.

### Step-limit contract edge

Input was `print 1;` with `{maxSteps: 2}`. Exit 0:

```text
tree: success {"value":1,"output":["1"]}
vm: RuntimeError stage=runtime message=Execution step limit 2 exceeded at 1:1
```

### Grouped assignment

Input was `let a=0; (a)=1; a;`. Exit 0:

```text
parse: success node=AssignmentExpression result={"value":1,"output":[]}
```

This differs from a literal reading of the formal assignment production and requires a contract
decision; it is not counted as runtime validation.

## Limitations and checks not performed

- No original JavaScript module, Node test, benchmark, profiler, coverage tool, mutation tool, or
  fuzzer ran because the compatible runtime/tooling was unavailable.
- GJS results concern transformed source and cannot establish original syntax, imports, Node APIs,
  or supported-release behavior.
- The source catalog checkout and linked upstream content were outside the review workspace and
  network access was unavailable. No-copy and external license assertions remain uncorroborated.
- There was no harness-controlled learner view to inspect, so sealed-content transfer isolation is
  inconclusive.
- No production, deployment, or transfer claim was evaluated or promoted.

