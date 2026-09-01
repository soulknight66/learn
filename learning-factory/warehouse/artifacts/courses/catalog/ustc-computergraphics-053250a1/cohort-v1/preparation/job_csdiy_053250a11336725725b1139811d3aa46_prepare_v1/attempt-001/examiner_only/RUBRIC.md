# Independent Examiner Rubric — Testable 2D Transform Pipeline

This document is examiner-only. Assess the submitted artifact, not the learner's assertion of completion. Use a clean build directory and keep the examiner's cases separate from learner-authored tests.

## Decision rule

Score out of 100. A passing unit requires **75 or more**, plus all critical gates:

1. a fresh CMake configure and build succeeds using an available C++17 compiler;
2. CTest runs and reports no learner-test failures;
3. the canonical ordered-composition check passes within the tolerance below;
4. a late malformed command produces no standard output and the specified failure result; and
5. required source, test, README, design, and comprehension artifacts are present and inspectable.

A critical-gate failure means `NOT_YET_PASSED` regardless of points. Passing this rubric validates only this kickoff unit, never the whole course.

## Examiner procedure

1. Copy or inspect the submission without altering its sources. Configure into a new examiner-owned build directory.
2. Run the documented build and CTest commands. Record exit codes and logs.
3. Locate `transform2d` from the generated build rather than accepting a submitted binary.
4. Run fixed black-box cases for the categories below. Parse successful numeric output and compare using

   `abs(actual - expected) <= 1e-12 + 1e-10 * max(abs(actual), abs(expected))`.

5. Inspect the implementation, tests, and documentation independently. A claim in `DESIGN.md` earns credit only when source or rerunnable evidence supports it.
6. Read all eight comprehension responses for reasoning. Do not award credit for merely restating the prompt.

## Scoring

### A. Mathematical and black-box correctness — 36 points

- 6: identity plus translation behave correctly.
- 6: scaling, including a reflection through a negative scale, behaves correctly.
- 6: counterclockwise rotation in radians behaves correctly.
- 10: composition uses file order and actual matrix composition, including a noncommuting case.
- 4: multiple points retain input order and identifiers.
- 4: finite arithmetic is checked and exact negative zero is normalized before formatting.

Withhold composition credit if the program only mutates each point once per command and never builds a composite matrix, even when examples happen to match.

### B. Input contract and transactional failure — 14 points

- 4: blank lines/comments, exponent-form finite numbers, and valid boundary IDs are handled.
- 4: section ordering, IDs, arity, unknown commands, and trailing tokens are validated.
- 4: all seven diagnostics have the specified exit code and stream behavior.
- 2: a duplicate or other late error emits no partial standard output.

### C. Software design — 12 points

- 5: a reusable math module is separated from parsing and CLI presentation.
- 3: interfaces express the matrix/point model without global mutable state or I/O coupling.
- 2: errors cross module boundaries deliberately; exact process text is owned at the CLI boundary.
- 2: bounded resource use and non-finite arithmetic are handled without undefined behavior.

### D. Learner-authored tests — 14 points

- 4: direct tests cover identity and every elementary operation.
- 4: order-sensitive and three-operation composition tests would detect a multiplication-order mutation.
- 3: a deterministic inverse round-trip set states nonzero-scale/domain preconditions and uses a documented tolerance.
- 3: malformed-input tests cover every error class and assert exit code plus both output streams.

Tests that merely invoke the program without assertions receive no credit. Deduct within this section for time-dependent or unseeded-random behavior.

### E. Reproducibility and hygiene — 10 points

- 4: the documented three-command CMake/CTest workflow works from a clean directory.
- 2: C++17 is requested explicitly and reasonable warnings are enabled conditionally for the compiler.
- 2: no generated build tree, prebuilt executable, machine-specific absolute path, or external undeclared dependency is required.
- 2: README invocation and diagnostic documentation agree with observed behavior.

### F. Design reasoning — 6 points

- 2: `DESIGN.md` states column-vector order and the running-composite invariant correctly.
- 1: it explains validation-before-output as an observable atomicity choice.
- 1: it gives defensible `O(t + p)` time for composition/application and auxiliary space consistent with the actual buffering strategy.
- 1: it distinguishes exact structural checks from approximate computed-number checks.
- 1: a genuine tradeoff/rejected alternative is connected to this implementation.

### G. Comprehension — 8 points

Award one point per response when it contains the essential reasoning below:

1. `C * B * A * p`, with left-prepending `M <- O * M` under the declared convention.
2. A numerically correct noncommuting example, normally involving translation with scale or rotation, plus a geometric explanation.
3. A 2-by-2 linear map fixes the origin; the added homogeneous coordinate allows translation terms to contribute to points.
4. A stated combined tolerance; exact use on discrete structure/text and approximate use on trigonometric or composed results.
5. A late error such as duplicate ID or transform-after-point would otherwise leave success-looking partial output; buffering makes failure atomic to observers.
6. Applying a finite, invertible composite and its inverse approximately recovers a point; scale components are nonzero; a sampled property is not a proof for all doubles or a guarantee of numerical stability.
7. A coherent boundary trace: parser/validator classifies the fault, a typed result or error crosses boundaries, and CLI presentation selects text/streams/exit status.
8. A plan that first minimizes/reproduces, tests parser interpretation and pure multiplication separately, inspects the running invariant, and checks numeric output only after math is isolated.

## Fixed examiner cases

Use temporary input files; comments may be added separately to ensure comment parsing does not change the result.

1. **Translation:** `translate 3 -2` and `point p 1 4` must yield `p` at `(4, 2)`.
2. **Scale then translate:** `scale 2 3`, `translate 5 -1`, `point q 1 2` must yield `(7, 5)`.
3. **Translate then rotate:** `translate 2 0`, `rotate 1.5707963267948966`, `point r 1 0` must yield approximately `(0, 3)`. Reversing those two operations must yield approximately `(2, 1)`.
4. **Multiple/reflection:** `scale -2 0.5` with points `a 3 -4` and `_b-1 -1 8` must preserve IDs/order and yield `(-6, -2)` and `(2, 4)`.
5. **Exponent input:** identity composition with `point exp 1e2 -2.5e-1` must yield `(100, -0.25)`.
6. **Transactional failure:** a valid point followed by `translate 1 1` must exit `2`, emit no stdout, and emit only `error: syntax` plus newline.
7. **Late duplicate:** two valid point lines sharing an ID must exit `2`, emit no stdout, and emit only `error: duplicate-id` plus newline.
8. **Non-finite/range:** textual `nan`, `inf`, and overflowed numeric tokens are `number`; finite tokens whose arithmetic overflows are `range`.

Add independent cases for usage, I/O failure, missing point, wrong arity, invalid/overlength IDs, trailing tokens, and operation order. Examiner cases should not be copied into the learner's repository.

## Reporting boundary

Report the score, each gate result, commands and exit codes, failed observations, and artifact locations. The only positive terminal label this rubric can support is `UNIT_PASSED` for `managed_u1_testable_2d_transforms`. It cannot support `COURSE_COMPLETED`.
