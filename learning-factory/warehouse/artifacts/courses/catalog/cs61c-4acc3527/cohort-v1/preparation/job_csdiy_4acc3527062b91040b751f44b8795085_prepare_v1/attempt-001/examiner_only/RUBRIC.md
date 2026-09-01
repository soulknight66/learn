# Independent Examiner Rubric: C Systems Kickoff

> **Artifact label:** Manager-authored examiner-only criteria; awaiting worker-harness validation. Source basis: the supplied CSDIY catalog snapshot; no external course content was retrieved.

Keep this file examiner-only. It contains scoring criteria and expected-answer guidance and must not be copied into a learner view.

## Scope and evidence rules

This rubric assesses only `kickoff_c_index_v1`, a manager-authored C11 unit in which the learner builds a sorted `int32_t` index and the `rankq DATA_FILE QUERY...` CLI. It is not an official UC Berkeley assignment and cannot establish completion of CS61C.

Grade the files and validator-produced evidence from the current attempt. Learner prose may direct the examiner to evidence but is not proof that a command passed. Do not use external course solutions, a previous learner's files, or network material. Preserve failure logs and the submitted attempt.

Run builds and tests in a clean validator-controlled environment with bounded timeouts. Invoke subprocesses with argument arrays and captured logs. The examiner may add adversarial data and a separate harness that calls the public API.

## Critical gates

A submission cannot pass the unit if any of these is true:

- a required source or evidence file is missing;
- the clean ordinary build fails, emits a required-diagnostic warning, or does not produce the specified CLI;
- validator tests expose a contract violation, crash, hang, out-of-bounds access, use-after-free, double free, leak on an exercised path, or undefined behavior;
- the implementation uses network access, a shell command for program logic/tests, unreviewed external assignment code, or another learner's work;
- successful and malformed inputs cannot be distinguished by the specified exit status, or failure produces query results on standard output; or
- the submitted work is not attributable to this attempt.

A sanitizer unavailable for a documented platform reason may be replaced by an equivalent validator-controlled memory/UB check. A sanitizer finding is not waivable by documentation.

## Scoring (100 points)

### A. Reproducible build and interface — 12 points

- 4: Required layout and public names/types match the contract; the header is self-contained.
- 4: Separate C11 compilation, strict required diagnostics, and override-friendly build variables work from a clean tree.
- 4: `all`, `test`, `sanitize`, and narrowly scoped `clean` targets behave as documented.

### B. Index correctness and complexity — 20 points

- 6: Build makes an ascending owned copy, preserves duplicates and caller input, and handles the empty case.
- 7: Lower bound is correct for empty, singleton, duplicate, extreme, below-range, between-value, and above-range queries.
- 3: Membership never dereferences the one-past-end position and agrees with lower bound.
- 2: Query complexity is logarithmic; construction is no worse than `O(n log n)`.
- 2: Destruction frees ownership, restores the canonical empty state, and is repeatable for initialized objects.

### C. Defensive C and resource handling — 20 points

- 5: Argument validation and the `length * sizeof(int32_t)` overflow guard happen before unsafe use/allocation; failures leave `out` empty.
- 5: Full-domain comparisons avoid signed subtraction overflow and other undefined or implementation-dependent assumptions.
- 5: Dynamic parser growth has checked arithmetic, observes the record cap, and cleans partial state on every failure.
- 5: File, parser, index, and temporary-resource ownership is released exactly once on all validator-exercised paths.

### D. CLI parsing and behavior — 18 points

- 6: Exact whole-token decimal and `int32_t` range validation works for data and queries; partial parses are rejected.
- 4: Blank lines, allowed whitespace, LF/CRLF, and a missing final newline work; overlong lines and excess records fail.
- 4: Output is exact, ordered, canonical, and delayed until all queries and the entire data file have validated.
- 4: Status 0/64/65/66/70 categorization and stderr/stdout separation match the specification, including read failure.

### E. Deterministic verification — 12 points

- 5: C tests cover the required structural, boundary, duplicate, extreme, non-mutation, invalid-argument, and destruction cases with meaningful assertions.
- 4: Python standard-library integration tests cover successful output and all required input/error categories, using argv arrays, timeouts, captured streams, and isolated temporary files.
- 3: Strict and dynamic-analysis runs are reproducible and clean; checked-in source contains no generated large fixture or build product.

### F. Engineering record — 8 points

- 3: `DESIGN.md` accurately gives module boundaries, invariants, ownership transitions, failure cleanup, numeric risks, and complexity.
- 3: `TESTING.md` records tool versions, commands, a specific expected/observed matrix, evidence locations, and honest limitations consistent with validator results.
- 2: `README.md` lets a new reviewer build, test, and run the program without hidden assumptions.

### G. Comprehension — 10 points

Award up to 1.25 points per response. A correct response must connect the concept to the learner's actual implementation. Expected substance:

1. Parser storage belongs to the parsing/CLI layer until freed; the index owns a separate copy only after successful build; the opened stream is owned from successful `fopen` until one `fclose`; temporary test files belong to their temporary-directory context. No ownership silently transfers from input to index.
2. Both paths release parser storage and close an opened stream; a failed build leaves the initialized index canonical and safe to destroy. Validation-before-output makes stdout empty, preventing a partial result from resembling success.
3. A valid invariant describes a half-open candidate interval, commonly `[lo, hi)`, with excluded positions before it known to be `< key` and excluded positions after it known to be `>= key`. Progress terminates at the first qualifying position. The explanation must cover empty and boundary cases, not merely cite binary search.
4. Subtraction in `int32_t` (or after an unsafe conversion to `int`) can overflow or misrepresent ordering. Safe comparators use relational comparisons producing negative/zero/positive without subtracting the operands.
5. Text parsing must detect no digits, trailing junk, and range errors before narrowing. Signed values narrow only after bounds checks. Counts and capacity arithmetic must be checked in the `size_t` domain before multiplication/addition and allocation.
6. Preprocessing supplies declarations/macros; each source file is compiled/assembled into an object containing machine code, symbols, and relocations; the linker resolves the CLI object's reference to the library object's definition and combines required runtime/library code into the executable. A declaration itself is not the linked definition.
7. Tests compare selected expected behavior; sanitizers dynamically detect classes such as exercised out-of-bounds access or signed UB. Neither proves correctness for all inputs or absence of defects on unexecuted paths; good answers name actual cases and limitations.
8. Passing evidence supports the bounded contract under validator coverage and can complete only this kickoff. It neither proves universal correctness nor covers architecture topics such as assembly, datapaths, caches, virtual memory, or concurrency, so it cannot complete the course.

## Decision

- **Pass:** all critical gates pass and the score is at least 75/100.
- **Revise:** no integrity/safety violation, but a critical gate fails or the score is below 75. Retain evidence and issue bounded corrective work for this unit.
- **Invalid attempt:** attribution, prohibited-source, secret, hidden-reference, or cross-learner isolation failure. Preserve evidence and route through the harness policy.

On Pass, record only `kickoff_c_index_v1` as completed. Keep the course status in progress; later units require their own sourced materials, manifests, learner-safe tasks, examiner criteria, and validator promotion.
