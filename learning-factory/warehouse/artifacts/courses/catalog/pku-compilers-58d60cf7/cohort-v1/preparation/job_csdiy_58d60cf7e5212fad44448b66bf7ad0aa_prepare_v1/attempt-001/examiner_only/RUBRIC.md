# Examiner Rubric: A Testable Compiler Vertical Slice

This rubric is validator-facing and independent of learner self-report. Score only durable submitted artifacts and behavior reproduced with the documented commands. Do not infer whole-course completion from this assessment.

## Decision rule

The unit passes only when all critical gates pass and the submission earns at least **80/100**. Preserve command logs, exit statuses, relevant output hashes or bytes, and failure evidence with the attempt record. A learner-authored `EVIDENCE.md` is useful provenance but is not a substitute for validator-controlled execution.

## Critical gates

Fail the unit regardless of score if any of these is true:

- a clean build or documented test command cannot be reproduced within the harness timeout;
- the implementation lacks a runnable command compatible with `COMPILER INPUT --emit mini-ir -o OUTPUT`;
- either boundary value (`0` or `2147483647`) cannot be compiled to the exact canonical bytes;
- malformed source is accepted as success, or a valid-prefix/trailing-token case is not rejected;
- source failure creates partial output or changes the bytes of a pre-existing output;
- the implementation is materially hard-coded to named examples rather than recognizing the grammar;
- required source, tests, `README.md`, `DECISIONS.md`, `EVIDENCE.md`, or comprehension responses are absent;
- the submission claims that MiniMain-0/MiniIR-0 is official SysY/Koopa IR, or claims completion of the PKU course;
- the submission contains hidden tests, examiner material, secrets, another learner's files, or unauthorized fetched content.

## Scored criteria

### 1. Language recognition and canonical emission — 30 points

- **12:** Accepts precisely the specified structure and legal whitespace, consumes the entire file, and rejects missing/reordered tokens and trailing bytes.
- **8:** Enforces the canonical integer grammar and inclusive range without overflow-dependent behavior, including a very long digit sequence.
- **7:** Emits exact MiniIR-0 bytes for arbitrary accepted values, including spacing and final newline; output is repeatable.
- **3:** Cleanly rejects non-ASCII bytes, signs, comments, alternate spellings, and empty input.

Award no more than 15 in this section if recognition and rendering are fused into example-specific substring/template logic without a program representation.

### 2. Process and filesystem contract — 20 points

- **6:** Implements the required argument interface and exit classes: `0` success, `2` source error, another nonzero value for operational/CLI failure.
- **5:** Source diagnostics are deterministic, one line, and contain an accurate zero-based byte offset plus a useful reason.
- **7:** Success safely replaces output; every failure path avoids partial output and preserves existing bytes. Temporary artifacts are safely scoped and cleaned.
- **2:** Normal behavior keeps IR off stdout and diagnostics free of timestamps, random data, stack traces, and absolute workspace paths.

### 3. Engineering design and changeability — 15 points

- **6:** Process/input handling, parsing, representation, and emission have identifiable responsibilities and explicit handoff invariants.
- **4:** The representation is real and typed/structured enough to support a future expression node rather than merely holding copied output text.
- **3:** Numeric parsing, error propagation, and resource handling are robust and idiomatic for the chosen language.
- **2:** The proposed addition extension in `DECISIONS.md` follows existing boundaries and does not pretend to implement out-of-scope work.

### 4. Automated verification — 20 points

- **8:** Tests cover every minimum partition in the task, with meaningful assertions on bytes, exit status, diagnostics, and filesystem effects.
- **5:** Black-box subprocess tests exercise the documented entry point; smaller unit tests supplement rather than replace them.
- **4:** Tests are deterministic, bounded, network-free, independent of absolute paths, and isolate temporary files.
- **3:** Tests would detect prefix acceptance, host-overflow dependence, nondeterministic output, and destructive failure writes; assertions are not vacuous.

### 5. Reproducibility and documentation — 8 points

- **3:** `README.md` enables a clean build/run/test without undocumented local state.
- **3:** `EVIDENCE.md` records environment/tool versions, exact commands, outcomes, and a useful test summary that validator logs can corroborate.
- **2:** `DECISIONS.md` states the requested invariants and conventions accurately and matches the implementation.

### 6. Comprehension — 7 points

Assess the learner's own implementation-specific reasoning, not memorized terminology.

- **1:** Q1 traces all stages, states a useful invariant at each handoff, and assigns range validation unambiguously to parsing or semantic construction.
- **1:** Q2 explains whole-input consumption with a concrete trailing-input case and the actual rejection mechanism.
- **1:** Q3 identifies the representation's contents and explains why representation-first design localizes an addition extension.
- **1:** Q4 states a no-visible-change-before-success invariant and cites an automated pre-existing-output byte comparison; merely mentioning temporary files is incomplete.
- **1:** Q5 defines offsets in input bytes, treats non-ASCII deterministically as an invalid byte, and avoids locale/code-point ambiguity.
- **1:** Q6 gives sensible equivalence/boundary classes and explains that pre-checking digit accumulation, bounded conversion, or equivalent logic prevents host overflow; a crash-free claim alone is insufficient.
- **1:** Q7 and Q8 together identify plausible grammar/AST/parser/emitter/test impacts, preserve at least one sound boundary such as CLI orchestration, and limit the achievement to the local vertical slice. Unsupported claims include official SysY conformance, Koopa IR conformance, RISC-V generation, official sequence progress, or whole-course completion.

## Examiner probes

In addition to the learner's suite, use fresh temporary paths and values not named in the study task. Include at least one ordinary accepted value, mixed legal whitespace, a valid program followed by one extra byte, an integer far longer than the host word size, and simulated output failure where the harness can do so safely. Run one valid case twice and compare exact output bytes. Record probes as validator evidence; do not copy them into learner-visible artifacts.

## Outcome labels

- `PASS_UNIT`: all gates pass and score is at least 80.
- `REVISE_UNIT`: no integrity/safety violation, but a gate fails or score is below 80.
- `INVALID_ATTEMPT`: examiner material, hidden checks, unauthorized content, or falsified evidence is present.

No label here means `COURSE_COMPLETE`. Later units require separately verified materials and validation.
