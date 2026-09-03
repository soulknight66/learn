# Repair generation 2 validation evidence

Fresh checks were run on 2026-09-03 from:

```text
/projects/se/pj34000401_refsys/users/yuali01/learn/learning-factory/warehouse/workspaces/job_byox_repair_s2_v1_g2_35e8fff6296915ff1ce18d77eeb3c510/attempt-001
```

This is builder evidence, not an independently awarded validation label. The sandbox launcher
printed `/usr/bin/id` name-resolution warnings for its numeric user and group before commands. They
did not alter exit statuses and are omitted from the excerpts below. No dependency was fetched or
installed.

## Pinned toolchain

Exact command:

```bash
/usr/bin/timeout --signal=KILL 10s /arm/tools/nodejs/node/22.21.0/linux64/bin/node --version
```

Observed exit `0` and output:

```text
v22.21.0
```

No ambient `node` executable was substituted.

## JavaScript syntax

Exact command:

```bash
/usr/bin/timeout --signal=KILL 30s /usr/bin/find starter public_tests environment sealed -type f -name '*.mjs' -exec /arm/tools/nodejs/node/22.21.0/linux64/bin/node --check '{}' ';'
```

Observed exit `0` with no JavaScript diagnostic output.

## Sealed reference and repair regressions

Exact commands:

```bash
/usr/bin/timeout --signal=KILL 30s /arm/tools/nodejs/node/22.21.0/linux64/bin/node --test sealed/reference_tests/*.test.mjs
/usr/bin/timeout --signal=KILL 30s /arm/tools/nodejs/node/22.21.0/linux64/bin/node sealed/reference_tests/reference.test.mjs
/usr/bin/timeout --signal=KILL 30s /arm/tools/nodejs/node/22.21.0/linux64/bin/node sealed/reference_tests/adversarial.test.mjs
/usr/bin/timeout --signal=KILL 30s /arm/tools/nodejs/node/22.21.0/linux64/bin/node sealed/reference_tests/learner-view.test.mjs
```

All exited `0`. The aggregate run passed all three file suites. Direct runs passed 14/14 reference
tests, 6/6 adversarial tests, and 4/4 learner-boundary tests. The new checks establish that the
sample program has tree/VM parity, path traversal and unknown roots are rejected, the source
projection contains no `sealed` component, and an incomplete existing tree is rejected by the
materialized-view comparator.

## Supplied CLI input

Exact commands:

```bash
/usr/bin/timeout --signal=KILL 10s /arm/tools/nodejs/node/22.21.0/linux64/bin/node sealed/reference/src/cli.mjs --backend tree starter/example.mica
/usr/bin/timeout --signal=KILL 10s /arm/tools/nodejs/node/22.21.0/linux64/bin/node sealed/reference/src/cli.mjs --backend vm starter/example.mica
/usr/bin/timeout --signal=KILL 10s /arm/tools/nodejs/node/22.21.0/linux64/bin/node starter/src/cli.mjs --backend tree starter/example.mica
```

The two sealed-reference commands exited `0` and each printed:

```text
12
```

The learner starter command resolved the same file, then exited `1` with its intentional baseline
completion point:

```text
TODO: implement parse(tokens) according to REQUIREMENTS.md
```

This is not an `ENOENT` failure; `starter/example.mica` is present and reference-validated.

## Unicode coordinate contract

Exact commands:

```bash
/usr/bin/timeout --signal=KILL 30s /arm/tools/nodejs/node/22.21.0/linux64/bin/node public_tests/lexer.test.mjs
/usr/bin/timeout --signal=KILL 10s /arm/tools/nodejs/node/22.21.0/linux64/bin/node --input-type=module --eval 'import {tokenize} from "./starter/src/lexer.mjs"; const sources=["\"😀\"; print 1;","\r\nprint 1;","\rprint 1;"]; const starts=sources.map(source=>tokenize(source).find(token=>token.type==="PRINT").span.start); console.log(JSON.stringify({status:"PASS",starts}));'
```

Both exited `0`. The direct lexer run passed 3/3 tests, including the new UTF-16 and line-ending
case. The probe printed:

```json
{"status":"PASS","starts":[{"offset":6,"line":1,"column":7},{"offset":2,"line":2,"column":1},{"offset":1,"line":1,"column":2}]}
```

## Deterministic learner projection inventory

Exact command:

```bash
/usr/bin/timeout --signal=KILL 30s /arm/tools/nodejs/node/22.21.0/linux64/bin/node environment/verify-learner-view.mjs
```

Observed exit `0`. The JSON result reported `PASS`, strict top-level allowlist mode, 4 selected
directories, 25 selected regular files, 36 instructor files excluded, zero selected excluded-path
components, 29 static module specifiers, and zero imports escaping the learner inventory. The
selected path-and-content inventory was:

```text
30254c2fb9b928a9e42d2965fee366a622339367e0e2eb4118b24043459e8fa4  AGENTS.md
536ce96faa2dd8b1d5a9d8a358fd02fc7866300462696a19eea817e29f6d6534  CONCEPTS.md
2c7ffcc038223e5a25cc6a358dc16072f06611aae43f551fdfa4d35681c86fce  DESIGN_QUESTIONS.md
4d0c9b613b4efbce749d94fb1f337fc1ae861801802d16c7b174389f6af0d661  MANIFEST.yaml
14dac41ac729f0368eab5af0720511491eeb822e91bfe71d9eaf443d2d678d67  README.md
fb444eff0eb5bfa119ce8b9ed717f0f8e5debe92f7a927677c355208b7135fc2  REQUIREMENTS.md
27c6b897b6aa5b35db89165ac1897f6ad99102813a7a6902ca06d161cb54967a  environment/README.md
b813d8d464ab285bc51409c29c9c9e0518b99f02822b639ea4e5f9424f14ebbe  environment/learner-view-policy.json
f6551209f8b55d7d7f27d59dce0d821fa70b2aaad990b4fb6cc0a3df8f46c695  environment/verify-learner-view.mjs
6dd3319d0b165641661d8b52c85c73e390f0d592f8043f30ef7cf87e4d1e9692  environment/verify-pack.mjs
5dcacdfca698ff4e7fecd885e25294808e1d3c9ca98d3332fadbd215699d8b7f  public_tests/README.md
8e16c9bf34d0be74c05b94d2eea1dcece2c0f05c1dd1f4c3230a293e801b0e72  public_tests/execution.test.mjs
e9d18fdb59a176a1f1254c22cf80a90afe166b8b6b42114ce9ca9230f1c71e13  public_tests/lexer.test.mjs
f17d3d181c5eeaea277e3c7f062a538f102df82d13a3ad38d2a7094302c8a9ce  public_tests/parser.test.mjs
dad4b0985465720cac97123526d3c7ba99bfb0f2fe9c2e233049dc8ff79cde86  starter/README.md
2552000d1e89e17ea96b5255899dd96eb803d14763575c5a6d88ce900a699373  starter/example.mica
c91a64690bce7c9b8c954327840edebc191ada4ffa8d1bba2a3b76ae496553dd  starter/src/cli.mjs
f7b3db029bd7abad7d0920c8b01ae8760e9421aeaecb656533fdc47d62f3da33  starter/src/compiler.mjs
902b109a8adccee604e92073c9c79630204f1a7546cf9beab68f5af359e1b50c  starter/src/diagnostics.mjs
c8f695eb27525924c61bcfaad148c586f3352e5438fbc2b1f4d5a0ce1c7ff1ec  starter/src/interpreter.mjs
ec03af1258a645a4a4748120fffe717eb6fccbf6800c1bcb709c260240d176f0  starter/src/lexer.mjs
5066a9bece24f03c923b15242e907a4a56217f0a1f30d77c0f30779bc04ad070  starter/src/parser.mjs
eb5d5462f29e64fbb47be1a00360dcd34778715d5b5a65ec104e85016da049df  starter/src/pipeline.mjs
e0cebbd4cd215338fb94007956afd92cb191dec929d70c72d98486750cdf1388  starter/src/tokens.mjs
97443e9d0c4c59d2901e5634c7529962a2b6d6b5cd7d2d49bfa88096de81e516  starter/src/vm.mjs
```

The ordered inventory SHA-256 was
`9122c9f6206a5d3df1964ed50dd261272b9dbf00bc5d6b8957b8b52134790d43`.
No learner workspace was created in this production area. Consequently, the optional
`--projected-root PATH` success mode was not run; a controlling harness must materialize a view
outside this workspace and use that read-only comparison mode before publication.

## Untouched learner implementation baseline

Exact command:

```bash
/usr/bin/timeout --signal=KILL 30s /arm/tools/nodejs/node/22.21.0/linux64/bin/node --test public_tests/*.test.mjs
```

Observed exit `1`: three file suites ran, `lexer.test.mjs` passed, and `parser.test.mjs` plus
`execution.test.mjs` failed at the starter's explicit TODO stages. This intentional failure is not
represented as a passing learner suite.

## Immutable metadata

Exact commands:

```bash
/usr/bin/timeout --signal=KILL 10s /usr/bin/sha256sum MANIFEST.yaml PROVENANCE.json
/usr/bin/timeout --signal=KILL 10s /arm/tools/nodejs/node/22.21.0/linux64/bin/node --input-type=module --eval 'import assert from "node:assert/strict"; import {readFileSync} from "node:fs"; const m=JSON.parse(readFileSync("MANIFEST.yaml","utf8")); const p=JSON.parse(readFileSync("PROVENANCE.json","utf8")); assert.equal(m.project_id,p.project.project_id); assert.equal(m.source_id,p.source.source_id); assert.equal(m.source_commit,p.source.commit_hash); assert.equal(m.provenance_sha256,p.snapshot_sha256); assert.deepEqual(m.validation_labels,["GENERATED","PARTIAL"]); assert.equal(m.productionized,false); console.log(JSON.stringify({status:"PASS",project_id:m.project_id,labels:m.validation_labels,productionized:m.productionized}));'
```

Both exited `0`. Observed hashes:

```text
4d0c9b613b4efbce749d94fb1f337fc1ae861801802d16c7b174389f6af0d661  MANIFEST.yaml
be80da9777a7b3f1b6a4d2d40a2f3cde0f9212467b828a636140bc281ff94bdc  PROVENANCE.json
```

The assertion output was:

```json
{"status":"PASS","project_id":"project_c305a6b70f268e23e2e48694e3604f28","labels":["GENERATED","PARTIAL"],"productionized":false}
```

Byte comparisons against the checksum-bound staged copies also exited `0` and reported
`manifest_cmp=0 provenance_cmp=0`.

## Final pack and static audits

Exact pack command:

```bash
/usr/bin/timeout --signal=KILL 30s /arm/tools/nodejs/node/22.21.0/linux64/bin/node environment/verify-pack.mjs
```

Observed exit `0` and output:

```json
{
  "status": "PASS",
  "requiredRegularFiles": 23,
  "forbiddenPathsPresent": 0,
  "symlinksOrSpecialFiles": 0,
  "credentialPatternMatches": 0,
  "scannedFiles": 61,
  "manifestStatus": "GENERATED",
  "validationLabels": ["GENERATED", "PARTIAL"],
  "learnerProjectionStatus": "PASS",
  "learnerFileCount": 25,
  "learnerInventorySha256": "9122c9f6206a5d3df1964ed50dd261272b9dbf00bc5d6b8957b8b52134790d43",
  "learnerImportEscapes": 0
}
```

This audit enforces the canonical top-level roots, required regular files, forbidden paths,
immutable provenance bytes, manifest contents, credential-pattern scan, special-file exclusion,
and learner projection audit.

Exact static commands:

```bash
if /usr/bin/grep -R -nE '(^|[^[:alnum:]_])(eval|Function|child_process|fetch|WebSocket)[[:space:]]*\(' starter public_tests environment sealed --include='*.mjs'; then exit 1; else scan_status=$?; if [ "$scan_status" -eq 1 ]; then /usr/bin/printf '%s\n' 'PASS: no forbidden API call pattern'; else exit "$scan_status"; fi; fi
matches=$(/usr/bin/find AGENTS.md CONCEPTS.md DESIGN_QUESTIONS.md LICENSE_BOUNDARY.md MANIFEST.yaml PROVENANCE.json README.md REQUIREMENTS.md VALIDATION.md adversarial benchmarks debugging environment public_tests review_exercises sealed starter \( -type l -o \! -type d -a \! -type f \) -print); if [ -n "$matches" ]; then /usr/bin/printf '%s\n' "$matches"; exit 1; fi; /usr/bin/printf '%s\n' 'PASS: regular files and directories only'
```

Both exited `0`, respectively printing `PASS: no forbidden API call pattern` and
`PASS: regular files and directories only`.

## Explicit limitations and unclaimed labels

- No learner workspace was created or materialized-view success claimed; external projection and
  independent acceptance remain mandatory.
- The generated material still has no affirmative redistribution license. Publication or transfer
  awaits an authorized license decision.
- Validation used only the pinned Node.js v22.21.0 runtime. No cross-runtime/platform matrix ran.
- The upstream linked repository was not fetched or compared.
- The optional benchmark was not run. No fuzzing, benchmark qualification, formal verification,
  security certification, transfer verification, review acceptance, or production-readiness claim
  was performed.

The pack remains `GENERATED` + `PARTIAL` and subject to fresh independent review.
