# Independent Examiner Rubric

Course ID: `course_94560b3a323bb4da6a3c762995a4958b`  
Unit ID: `kickoff_slp_interpreter_v1`  
Audience: worker-harness-controlled examiner only  
Validation label: `EXAMINER_ONLY_PREPARED_UNVALIDATED`

## Decision rule

Score the learner submission out of 100 using direct evidence. A passing unit requires at least 75 points and all mandatory gates below. Passing this rubric validates only `kickoff_slp_interpreter_v1`; it must not promote the whole course to complete.

Mandatory gates:

1. A fresh configure and build succeed without network retrieval.
2. CTest discovers at least one executable test and the submitted tests pass.
3. Examiner checks confirm correct left-to-right `Eseq` behavior, per-print buffering, and `max_print_arity` traversal through expressions.
4. Division by zero and signed-overflow cases are reported without invoking undefined behavior in the tested paths.
5. The submission contains no dependency on restricted course framework content or unverifiable claimed official solutions.

If a gate fails, record the score and evidence but return `NOT_YET_COMPLETE`. Preserve logs and the failed attempt.

## Scoring

### 1. Reproducible build and packaging — 10 points

- 4: CMake declares C++17, separates production code from tests, and downloads nothing.
- 4: a clean configure, build, and CTest run succeeds with documented commands.
- 2: the public target and demonstration/test fixture are usable without editing source or relying on generated files checked into the source tree.

### 2. AST design and invariants — 12 points

- 6: all required statement, expression, and operator forms are represented type-safely.
- 4: ownership is leak-safe and missing children, invalid names, and empty prints are prevented or reported consistently.
- 2: traversal-facing interfaces are const-correct or otherwise prevent accidental mutation, with syntax concerns separated from execution state.

### 3. Interpreter semantics — 25 points

- 5: compound sequencing, assignment, lookup, and final environment behavior are correct.
- 5: numeric and binary expressions implement the specified operations.
- 8: operands, print arguments, and `Eseq` state/output effects occur in the required left-to-right order.
- 5: exact print formatting and per-print all-values-before-line buffering are correct, including nested output.
- 2: output is injected and the public execution boundary returns inspectable success or error data.

### 4. Structural analysis — 13 points

- 8: `max_print_arity` finds prints in statements and every expression position, including nested `Eseq` and `Op` operands.
- 3: it emits no output, uses no environment, and gives repeatable results across repeated and interleaved calls.
- 2: documented bounds are justified and consistent with the implementation.

### 5. Error behavior and checked arithmetic — 12 points

- 8: distinct inspectable handling exists for invalid AST/name, unbound name, division by zero, and addition, subtraction, multiplication, and division overflow.
- 3: evaluation stops at the failing operation while effects completed earlier remain and the failing print emits no partial line.
- 1: errors include useful context and do not abort or cross the public boundary uncaught.

### 6. Automated test quality — 14 points

- 4: tests cover all AST forms and baseline environment/output behavior.
- 4: tests discriminate evaluation order and nested `Eseq` interactions.
- 4: tests cover error categories, boundary arithmetic, buffering, and retained earlier effects.
- 2: tests are deterministic, focused, assert exact observables, and do not depend only on private representation.

### 7. Engineering documentation — 8 points

- 2: README gives sufficient clean-build instructions.
- 4: DESIGN explains ownership, invariants, state/output separation, failure effects, and evaluation order in agreement with code.
- 2: complexity and the future-parser extension seam are credible without widening scope.

### 8. Comprehension responses — 6 points

- 3: traces in prompts 1–3 have correct output, state, analysis, and failure observations with reasoning.
- 1: arithmetic-overflow reasoning avoids performing undefined signed arithmetic as the check.
- 1: ownership and tests identify concrete invariants and discriminating observables.
- 1: complexity and extension responses distinguish AST traversal from parser/token concerns.

## Examiner oracle cases

Adapt these cases to the learner's public AST construction API. Do not accept submitted prose or tests as the only evidence.

### Ordered state effects

```text
Compound(
  Assign("a", Num(5)),
  Print([
    Id("a"),
    Eseq(Assign("a", Op(Id("a"), Add, Num(1))),
         Op(Id("a"), Multiply, Num(2))),
    Id("a")
  ])
)
```

Expected output is exactly `5 12 6\n`; final `a` is 6; `max_print_arity` is 3.

### Nested print ordering and analysis

```text
Print([
  Num(1),
  Eseq(Print([Num(2), Num(3), Num(4), Num(5)]), Num(6))
])
```

Expected output is exactly `2 3 4 5\n1 6\n`; `max_print_arity` is 4. Calling the analysis before or after interpretation must not alter either result.

### Buffered failing print

```text
Compound(
  Assign("x", Num(1)),
  Print([
    Eseq(Assign("x", Num(2)), Id("x")),
    Op(Eseq(Print([Num(9)]), Num(10)), Divide, Num(0)),
    Eseq(Assign("x", Num(99)), Id("x"))
  ])
)
```

Expected retained output is exactly `9\n`; the outer print emits no line; final `x` is 2; the final `Eseq` is not evaluated; the error category is division by zero.

### Boundary errors

Independently check unbound lookup; division by zero; `INT64_MAX + 1`; `INT64_MIN - 1`; overflowing positive and negative multiplication; and `INT64_MIN / -1`. Check nearby non-overflow boundaries too, so an implementation that rejects all boundary values does not pass. Where practical, use an undefined-behavior sanitizer as supplementary evidence, not as the sole oracle.

### Structural coverage

Check a statement with no print (result 0), sibling prints of different arity, a print nested in the left operand of an `Op` through `Eseq`, and a deeper print nested in a later operand. Repeat analysis across trees in high-low-high arity order to detect stale global or member state.

## Comprehension reference guidance

- Prompt 1: output `4 14 7\n`; final `x = 7`. The first read sees 4, the nested assignment reads 4 and writes 7, the multiplication reads 7, and the final print argument reads 7.
- Prompt 2: maximum arity 3; output order `2 3 4\n`, then `1 5\n`, then `6 7\n`; final `z = 8`. Analysis depends on tree shape, not runtime order.
- Prompt 3: output retained is `9\n`; final `x = 2`; division by zero stops evaluation; the outer line is discarded and its third argument is not evaluated.
- Prompt 4 should mention that evaluating overflowing signed arithmetic is already undefined in C++; acceptable strategies include sound precondition checks, compiler checked-overflow primitives behind a portable abstraction, or a wider exactly represented intermediate where available. The division-overflow pair is `INT64_MIN` and `-1`.
- Prompts 5–8 admit multiple designs. Credit internally consistent, testable choices that preserve the task's invariants and boundaries; do not require a particular class hierarchy, smart pointer, sum type, or error carrier.

## Evidence record

Record exact commands, exit statuses, captured test output, examiner-added case results, score by section, gate decisions, and a final unit label. A learner's statement that work is complete is not evidence. Do not expose this rubric, oracle cases, or reference guidance in learner-safe artifacts.

## Provenance

This independent rubric was manager-authored for the bounded kickoff specification using only the provided catalog topic. The catalog snapshot content hash is `c0b01a3547deab67a2c9ce70808ae093949cc577ef4b3208bb40f409922c4189` at source commit `adce8e13789dc16aa6d1fbe163e9541736defae4`. No external course material was retrieved. `EXAMINER_ONLY_PREPARED_UNVALIDATED` means the rubric itself has been prepared but no learner attempt has been judged.
