# Independent review

Verdict: **REVISE**. No stronger validation label is justified. The submission is candid about its generated/partial state and contains a thoughtful challenge, but one learner test makes compliant completion impossible and the supplied sealed validation is neither connected to learner code nor demonstrably isolated from learners.

## Prioritized findings

### P0 — A correct learner implementation cannot pass the prescribed tests

`REQUIREMENTS.md:33` says an empty program is legal, so `Scan("")` must return a positioned EOF without error. `starter/types_test.go:8-16` instead permanently requires that call to return `SCAN/NOT_IMPLEMENTED`. Meanwhile `AGENTS.md:10` tells learners not to weaken, delete, or special-case tests, and the READMEs prescribe `go test ./...` in `starter/`.

Impact: implementing the first required stage correctly necessarily breaks the starter suite. This gives learners contradictory completion signals and makes the stated acceptance workflow unsatisfiable.

Required revision: replace the stub-state assertion with an invariant that remains true after implementation (or clearly designate and automatically remove a bootstrap-only test). Independently run both learner-facing suites against a completed implementation.

### P1 — Included “independent” tests do not test learner submissions

Every Go file in `sealed/reference_tests/` imports `example.com/pebble-reference`; its `go.mod` also replaces that module with `../reference`. The learner module is `example.com/pebble`. Thus these tests can assess the supplied oracle, but they cannot catch a faulty learner implementation. The only learner-targeted suite is the intentionally non-exhaustive public suite.

Impact: mandatory behavior such as forged-value robustness, deterministic precedence, concurrency, and boundary arithmetic has no harness-controlled learner acceptance evidence in this artifact.

Required revision: add a sealed validator module that imports the learner module through a harness-controlled, immutable replacement, and demonstrate it against both a known-good implementation and seeded bad implementations. Keep oracle self-tests separate and clearly labeled.

### P1 — Progressive disclosure is policy-by-prose, not an enforced boundary

The complete implementation, adversarial tests, design review, and exercise answers are readable under `CANDIDATE/sealed/`. `AGENTS.md` merely asks learners not to read them, and `MANIFEST.yaml` has no view allowlist, visibility class, or artifact mapping. The reviewer workspace must expose sealed material, but no supplied deterministic evidence shows that a separately constructed student view omits it.

Impact: if this archive is mounted or copied as the learner workspace, the solution and hidden material are immediately disclosed. A prose instruction is not an isolation control.

Required revision: define a machine-readable learner-view allowlist, construct that view in harness code, and add a validator that proves sealed/reference/answer paths are absent and unreadable from the learner process.

### P1 — The sealed parser's forged-token defense is incomplete

`sealed/reference/parser.go:191-200` checks only `lineDelta <= offsetDelta` when a gap crosses a line. It never bounds the next column. For example, an integer token starting at `(offset=1,line=2,column=99)` after the initial `(0,1,1)` position passes `possibleIgnoredGap`; a one-byte gap that advances to line 2 could only be LF and would put the token at column 1. With a matching one-byte token span and EOF, the rest of validation accepts the stream and parsing succeeds.

Impact: the reference contradicts the requirement that a stream which could not have been produced by `Scan` return `PARSE/INVALID_TOKEN_STREAM`. Tests do not cover this coordinate case, so the oracle is not yet trustworthy.

Required revision: enforce positional feasibility across line-changing gaps (including a maximum possible column), add the forged case, and independently execute it. Related AST containment checks should compare line/column ordering as well as offsets where that relationship is knowable.

### P2 — Recorded structural validation does not reproduce after packaging

The submitted `VALIDATION.md` records `79` archived entries. Running the same checker on the submitted tree reports `75` (`52` files and `23` directories below the root). The checker still exits zero because the count is informational.

Impact: the generation-host observation is not an exact transfer observation. This may be only omitted empty directories, but the submitted evidence does not identify the difference.

Required revision: validate the final transferred archive, record a canonical tree digest owned outside the archive, and explain whether directory-only differences are intentionally ignored.

### P2 — Provenance is candid but not fully self-verifying or redistributable

Project ID and source commit agree between manifest and provenance. The linked resource is conservatively marked `NOASSERTION`, which is good. However, manifest `provenance_sha256` (`89405d…`) matches the embedded `snapshot_sha256` but not the raw (`0ef563…`) or canonical (`c24359…`) digest of `PROVENANCE.json`; that distinction is undocumented. Also, “independently generated for personal educational use” is not an explicit license grant for the generated pack. The catalog's CC0 status does not automatically license newly generated code and prose.

Required revision: document the snapshot-hash preimage and add an actual provenance-file/archive digest. If redistribution or learner modification outside platform terms is intended, add an explicit license for generated material while preserving the linked-resource `NOASSERTION` boundary.

### P2 — Fuzz/adversarial inventories overstate executable depth

No fuzz claim is made, correctly. Still, `fuzz_test.go` derives both opcode and operand from the same byte. Valid non-operand opcodes (`OpAdd` through `OpHalt`) therefore always receive nonzero operands and are rejected before their operational validation branches. Even the nominal halt seed is rejected as a stray-operand case. The adversarial README also names negative/out-of-range slot operands and non-monotonic spans, but the table lacks direct cases for those claims.

Required revision: generate opcode, operand, span, and slot count independently; seed structurally valid streams; and make the prose inventory traceable to named tests.

## What is good

- Validation claims are appropriately restrained: `GENERATED`, `PARTIAL`, independent validation required, and not productionized.
- The normative contract, concepts, staged API, design questions, and diagnostics focus are pedagogically strong.
- Module files declare Go 1.21 and only standard-library or local module imports were observed.
- Production limitations, fuzz/benchmark non-execution, and the linked-resource license uncertainty are stated honestly.
- The submitted structural checker passes on the transferred files, strict JSON parsing succeeds, and no symlink or special entry was found.

## Promotion decision

Do not promote to BUILDS, TESTED, FUZZED, BENCHMARKED, REVIEWED, TRANSFER_VERIFIED, or PRODUCTIONIZED. Re-review after the P0 contradiction is removed, learner-targeted sealed validation and enforced view isolation are supplied, and Go-based checks run independently on the final archive.
