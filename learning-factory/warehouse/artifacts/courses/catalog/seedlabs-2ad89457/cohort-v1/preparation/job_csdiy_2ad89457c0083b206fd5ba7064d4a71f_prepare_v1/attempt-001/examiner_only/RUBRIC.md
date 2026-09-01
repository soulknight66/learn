# Independent Rubric: Boundary-Safe Binary Frame Encoder

Artifact classification: examiner-only, manager-authored assessment and answer guidance  
Validation label: PREPARED_UNVALIDATED

This rubric evaluates only `unit_kickoff_secure_binary_frame_v1`. It is not an official SEEDLabs rubric and cannot establish completion of the broader course. Score the submitted artifacts and reproducible validator evidence; do not accept the learner's prose assertion that a command passed as proof that it did.

## Decision rule

Total: 100 points. Pass requires at least 75 points, all required work products, and no critical-failure condition. A controlled validator must independently build and test the submission before promoting the unit.

Critical failure conditions:

- any demonstrated out-of-bounds access, integer-wrap-dependent capacity decision, or read from an invalid source on a case the contract requires the function to reject;
- any reachable error path that changes destination bytes;
- nondeterministic, networked, privileged, setuid, or external-target activity;
- fabricated test or sanitizer evidence; or
- changing the public contract so the required cases no longer apply.

If normal tests cannot build or execute, cap the score at 49. If they execute but independent validation finds a functional failure, cap at 69. An honestly unavailable sanitizer does not trigger either cap when normal validation passes and the limitation is documented.

## Scoring

### 1. Contract and reasoning — 18 points

- 5: Header and `DESIGN.md` state all pointer rules, non-overlap precondition, status meanings, validation precedence, binary semantics, and failure atomicity consistently.
- 7: The size argument prevents overflow before computing or storing the total length and connects each validated condition to the subsequent two-byte prefix and payload writes.
- 3: Invariants are concise, reviewable, and distinguish caller preconditions from function-checked errors.
- 3: Design scope stays bounded and records limitations without inventing external course facts.

Expected reasoning: validate `written` and other required pointers first; zero valid `written`; reject values above `UINT16_MAX`; establish that adding two is representable (or use an equivalent portable argument); then compare capacity using checked addition or `dst_cap >= 2` followed by `src_len <= dst_cap - 2`. Only after all checks may destination writes occur. Equivalent rigorously justified orderings earn full credit.

### 2. Implementation correctness — 24 points

- 8: Correct two-byte unsigned big-endian prefix for the full accepted range, with byte-exact payload preservation including embedded zeros.
- 6: Correct status and `written` behavior for every specified invalid, oversized, and insufficient-capacity case, including mixed errors under the precedence rule.
- 6: Destination is untouched on all failures; validation precedes every destination write and rejected huge lengths are not dereferenced.
- 4: C11 code is small, warning-clean, has no hidden I/O/allocation/global mutation, and does not rely on undefined or implementation-specific behavior without justification.

### 3. Deterministic tests — 24 points

- 8: Covers empty, one-byte, embedded-zero, 255/256, maximum, above-maximum, exact-capacity, and one-short cases with byte-level assertions.
- 6: Covers pointer rules, error precedence, and a huge `size_t` rejection without causing a source read.
- 6: Uses sentinel-filled destinations to verify non-mutation for every reachable failure category; assertions would catch both prefix and payload-region changes.
- 4: Includes a deterministic multi-length loop, useful failure diagnostics, nonzero failure exit, and no order/environment dependence.

Tests receive credit for defects they can actually detect, not merely for suggestive case names.

### 4. Software-engineering evidence — 18 points

- 5: `Makefile` supplies working `all`, `test`, `sanitize`, and `clean` targets; a clean normal build is reproducible with strict warnings.
- 5: Independent normal and sanitizer validation passes, or sanitizer unavailability is reproduced and accurately recorded without a pass claim.
- 4: `TEST_EVIDENCE.txt` contains exact commands, compiler version, exit statuses, and concise outputs consistent with generated evidence.
- 4: Layout, public documentation, design record, and diff are reviewable; no generated binaries, downloaded material, credentials, or absolute local paths are submitted.

### 5. Comprehension — 16 points

Score two points per response:

1. Identifies overflow-safe ordering/subtraction or checked-addition logic and explains why later prefix, payload, and `written` operations are in range.
2. Explains failure atomicity as preserving prior valid state and simplifying retry/rollback, not just preventing an out-of-bounds write.
3. Distinguishes nullable empty `src` from always-needed `dst` and `written`, and names status, zeroed `written` where possible, and destination observations.
4. Maps four genuine boundary cases to different plausible defects rather than restating expected outputs.
5. Separates deductive reasoning, selected-case evidence, static diagnostics, and dynamic instrumentation; notes that a clean run alone is not a universal correctness or safety proof.
6. Recognizes that overlap changes the API precondition, copy semantics/ordering, alias analysis, and tests; a sound answer does not casually assume ordinary copying remains valid.
7. Explains the distinction among catalog record, link availability, verified content, official unit identity, and newly authored scaffolding.
8. Names a reproducible command/result claim and limits broader claims; proposes targeted independent validation, additional platforms/configurations, analysis, or proof as appropriate.

## Examiner record

Record per-section points, critical-condition checks, independent command outputs, and the final unit decision in durable validator-controlled evidence. If passed, label only the kickoff unit complete; leave course completion false.

Provenance: independently authored from the bounded task and the provided CSDIY catalog snapshot at commit `adce8e13789dc16aa6d1fbe163e9541736defae4`. No external SEEDLabs material or hidden reference was used.
