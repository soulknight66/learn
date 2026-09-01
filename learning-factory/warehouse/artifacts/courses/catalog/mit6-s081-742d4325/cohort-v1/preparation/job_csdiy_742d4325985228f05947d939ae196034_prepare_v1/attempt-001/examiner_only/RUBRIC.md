# Independent Examiner Rubric: `vmwalk` Kickoff

> **EXAMINER ONLY — do not copy this file or its contents into `student_safe/`.**  
> Course: `course_742d4325985228f05947d939ae196034`  
> Unit: `unit_kickoff_vmwalk_v1`  
> Artifact provenance: course-manager-authored from the supplied CSDIY catalog snapshot; no external course material was retrieved.  
> Validation label: **EXAMINER SPECIFICATION / NOT A VALIDATION RESULT**

## Scope and decision rule

This rubric independently evaluates only the manager-authored kickoff. It does not certify an MIT lab, another graph node, or the course as a whole.

Recommend unit completion only when all blocking checks pass, the submission earns at least 80 of 100 points, and a worker-harness-controlled run records `HARNESS-VALIDATED`. Learner logs and prose are supporting evidence only. Even a completed unit leaves the course `IN_PROGRESS`.

## Controlled evaluation

Evaluate an exact, clean copy of the submitted artifacts. Record its identity and compiler version. Invoke subprocesses with argument arrays, captured logs, a process group, and bounded timeouts; do not use shell command strings. Disable network access and supply no catalog-linked content.

Run these required targets from the submission root:

1. `make clean all`
2. `make check`

Allow at most 60 seconds for each target unless the local harness defines a stricter bound. Then run independent fixtures directly against `build/vmwalk`. Keep harness fixtures and expected results outside the learner view.

Blocking conditions are:

- any required submission path, including `COMPREHENSION_RESPONSES.md`, is absent;
- `make clean all` or `make check` returns nonzero, times out, or requires interaction;
- the required executable is not produced from submitted source;
- any independent must-pass fixture listed below observes behavior contrary to the learner contract;
- execution requires network access, restricted material, downloaded dependencies, or privileged operation; or
- the evaluator cannot obtain deterministic results from a clean rerun.

A blocked submission is not unit-complete regardless of its numeric score. Preserve the failed run and evidence.

## Independent fixture minimum

The examiner suite must not rely only on learner tests. Every case in this minimum suite is a must-pass completion fixture:

- `(L1,L2,PPN)=(0x1,0x2,0x34)` with read access to `0x1234`, expecting physical address `0x3434`;
- the address extrema `0x0000` and `0xffff`;
- all three access modes and several permission-letter orders;
- an unmapped lookup and a mapped-but-disallowed lookup;
- two distinct virtual pages mapped to one PPN, with distinct offsets;
- duplicate mapping, `map` after `access`, invalid keyword/mode, missing and extra tokens, an inline comment, a signed number, missing `0x`, and every numeric range violation;
- duplicate or unknown permission letters, an overlong logical line, a fully populated 256-entry mapping table, too many accesses, and too many logical lines;
- an empty trace, a comments-only trace, and a map-only trace;
- missing and extra CLI arguments plus an unreadable file; and
- a trace with a valid early access followed by invalid input, verifying exit `2` and empty standard output.

For valid input, compare every output byte and require exit `0`, including modeled faults. For a trace error, require exit `2`, empty standard output, and a `line N:` diagnostic naming the correct one-based line. Require exit `1` for an unreadable trace file.

## Scoring (100 points)

For a point-valued bullet, award its points in proportion to the independently observed cases that pass; do not infer unobserved behavior. For qualitative document or design criteria, award all points when fully satisfied, half when substantively but incompletely satisfied, and zero when absent, contradicted, or not reproducible. Round only the final score to the nearest whole point.

### 1. Reproducible build and evidence — 10 points

- 4: Clean build creates `build/vmwalk`, confines build products to `build/`, and uses all required C11 warning flags.
- 3: `make check` is deterministic, noninteractive, and returns failure when a check fails.
- 3: Logs preserve commands, versions, output, and exit statuses; `SELF_CHECK.md` uses an allowed label and never claims harness authority.

### 2. Address decomposition and translation — 25 points

- 8: Both indices and the offset are extracted correctly across ordinary and boundary addresses.
- 8: Lookup selects the correct entry and combines PPN with offset without truncation or signedness defects.
- 5: Success output is exact, canonical, and remains in input access order.
- 4: Multiple mappings and physical-page aliasing behave independently and correctly.

### 3. Fault and permission semantics — 15 points

- 5: Absent mappings produce exactly `UNMAPPED`.
- 6: Each access mode is checked against the selected mapping and denials produce exactly `PERMISSION`.
- 4: Modeled faults produce one output line each and do not change a valid trace's exit status from `0`.

### 4. Input, bounds, diagnostics, and exits — 15 points

- 5: Token counts, keywords, hexadecimal syntax, ranges, modes, and permission sets are checked exactly.
- 4: Duplicate maps, command ordering, line syntax, and full-file validation are enforced before output.
- 3: Line, access, and total-line bounds are enforced, and a full mapping table is accepted without truncation or out-of-bounds access.
- 3: Exit statuses, empty output on invalid traces, usage text, and line-number diagnostics follow the contract.

### 5. Defensive C and module design — 10 points

- 3: Trace and model behavior use the documented `vmwalk` interface while `main.c` remains focused on CLI handling and orchestration.
- 3: Numeric conversion, buffer handling, allocation, and cleanup avoid undefined behavior and unchecked partial results.
- 2: Representations make uniqueness, presence, permissions, and count invariants explicit.
- 2: Error paths are deterministic and keep modeled, input, and internal failures distinct.

### 6. Learner test quality — 15 points

- 6: Tests assert successful translation, both address extrema, all modes, both fault kinds, and aliasing.
- 5: Tests assert malformed input, ordering, duplicates, bounds, exact result output, required diagnostic prefix/line/stream behavior, and exit statuses.
- 3: Expected values are independent assertions rather than values copied from program output at runtime.
- 1: The suite is isolated, repeatable, and leaves `make check` nonzero when one of its own checks fails.

### 7. Design note and comprehension — 10 points

- 4: `DESIGN.md` stays within 400 words and accurately identifies representation, an enforced invariant, error-layer separation, and a deliberate omission.
- 6: The eight responses are concise, traceable where requested, and correctly explain decomposition, status semantics, invariants, fault discrimination, aliasing, defensive parsing, scope effects, and validation authority.

## Examiner interpretation notes

For the comprehension responses, accept equivalent terminology but require reasoning tied to this implementation. In particular:

- address decomposition must use bits 15–12, 11–8, and 7–0, and translation must preserve the offset;
- a modeled fault is a successful evaluation result, whereas malformed input violates the program contract;
- an invariant response must connect enforcement to an externally observable failure;
- aliasing changes the virtual-page indices, not the PPN, while each offset remains part of its physical address;
- the parsing defense must prevent, detect, or reject the named truncation/overflow path; and
- controlled validator evidence overrides a stale or inaccurate learner-produced log.

Do not infer correctness from style, learner confidence, source provenance, or a passing learner suite. Award behavior points from controlled observations and preserve counterevidence.
