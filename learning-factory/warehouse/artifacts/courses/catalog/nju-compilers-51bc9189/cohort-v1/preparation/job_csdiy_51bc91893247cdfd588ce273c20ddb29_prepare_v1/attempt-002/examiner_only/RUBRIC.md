# Examiner-Only Rubric: Expression Front-End Kickoff

> Access classification: examiner-only; do not copy into a learner view  
> Validation label: independent evaluation specification, not execution evidence  
> Provenance: course-manager-authored for `managed_unit_01_expression_front_end` from catalog snapshot commit `adce8e13789dc16aa6d1fbe163e9541736defae4`

## Evaluation boundary

Evaluate only the bounded kickoff specified in the learner-safe task. This is not an official NJU assignment rubric. A pass may promote this unit only; it must never promote the whole course.

Use submission artifacts and harness-captured observations. Do not accept a README claim, screenshot, prebuilt binary, checked-in generated parser, or learner-reported test result as a substitute for execution. Run the documented build and tests from a clean copy with bounded time and captured stdout, stderr, and exit status. Do not require access to the catalog website, recordings, textbook, community, or official assignments.

## Critical gates

Mark the unit **not complete**, regardless of point total, if any of these applies:

- there is no authored grammar and Java path that can be built and exercised;
- the documented clean build or automated test command fails for a submission-caused reason;
- generation depends on unrecorded local files, an IDE, or hand-edited generated code;
- valid-prefix-plus-trailing-input is accepted;
- invalid input can produce a success status or an AST presented as successful output;
- no repeatable automated tests execute; or
- `RESPONSES.md` is absent or plainly unrelated to the submitted implementation.

Infrastructure unavailability is not a learner defect. Record it as blocked validation and do not award a completion label.

## Scored rubric (100 points)

### 1. Reproducible build and command interface — 15 points

- 6: Maven or Gradle metadata pins explicit, compatible ANTLR generation and runtime versions; dependency generation is wired into the build.
- 4: the documented clean build/test command works outside an IDE and a repeat run has no hidden-state dependency.
- 3: the documented application command accepts a named UTF-8 file and uses meaningful exit status, stdout, and stderr.
- 2: generated sources and disposable output remain in the build-output tree and are not hand-authored.

### 2. Lexical and syntactic contract — 20 points

- 5: integer, identifier, whitespace, punctuation, and operator tokenization match the ASCII contract.
- 5: all binary forms, prefix negation, and parentheses accept valid input.
- 6: empty, incomplete, unmatched, invalid-character, and trailing-input cases are rejected.
- 4: the start rule consumes EOF and the application does not silently recover into a successful result.

### 3. Precedence, associativity, and AST output — 20 points

- 8: unary, multiplicative, and additive precedence are correct.
- 5: binary operators at the same level associate left; explicit parentheses regroup correctly.
- 5: output follows the exact leaf/unary/binary parenthesized representation and omits grouping nodes.
- 2: output is stable across repeated runs and preserves literal/identifier spelling.

### 4. Controlled diagnostics — 10 points

- 4: lexical and syntax failures are distinguished by the required stable category.
- 3: a diagnostic includes a correct one-based line and column for the offending location.
- 3: invalid input emits no AST to stdout, emits one owned diagnostic to stderr, and exits nonzero.

### 5. Automated test design — 15 points

- 6: behavior-named assertions cover precedence, associativity, unary negation, and parenthesized regrouping.
- 5: negative assertions cover lexical and multiple syntax boundaries, including trailing input.
- 2: process-level assertions check exit status and stream separation.
- 2: deterministic-repeat behavior and a clean build path are exercised or credibly automated.

### 6. Software-engineering quality — 10 points

- 3: authored and generated responsibilities are visibly separated; no generated code is manually patched.
- 2: the entry point, parsing adapter, and AST/rendering responsibility have understandable boundaries.
- 2: names and source layout make the small project easy to navigate; failures are not swallowed.
- 3: `README.md` is executable documentation and `DESIGN.md` concisely connects claims to implementation and records a genuinely deferred extension.

### 7. Comprehension responses — 10 points

- 2: parse-tree versus AST explanation is accurate and grounded in the submission.
- 2: the supplied mixed-precedence expression is structured correctly and tied to grammar choices.
- 1: EOF/prefix acceptance reasoning is correct and cites a relevant test.
- 1: lexical versus syntax detection and suppression of partial output are explained.
- 1: associativity is distinguished from precedence.
- 1: version pinning and generated-source reproducibility are explained.
- 1: the exponentiation extension identifies grammar, AST/test, and unary-precedence decisions without scope expansion.
- 1: the selected negative test names a plausible false implementation that it detects.

## Reference behavior for independent checks

The examiner should add or run equivalent black-box cases; do not rely exclusively on learner-selected examples.

| Input | Required stdout |
| --- | --- |
| `1 + 2 * 3` | `(+ 1 (* 2 3))` |
| `a - b - c` | `(- (- a b) c)` |
| `-a * b` | `(* (- a) b)` |
| `-(a + b)` | `(- (+ a b))` |
| `a / (b / c)` | `(/ a (/ b c))` |
| `_x + 007` | `(+ _x 007)` |

At minimum, independently reject an empty file, `1 +`, `(1 + 2`, `1 2`, and an input containing `@`. Confirm that invalid runs have nonzero status and empty stdout. Use multiline input to verify that the reported coordinates are one-based and not fixed constants.

For question 2, the required AST shape is `(- (- alpha beta) (* gamma (- delta)))`. Strong responses explain that multiplicative grouping and prefix negation form before the left-associated subtraction chain. For question 3, the essential point is that EOF prevents acceptance of an otherwise valid prefix such as the `1` in `1 2`. For question 4, distinguish a character that cannot form a token from a legal token in an illegal syntactic position, and require AST emission only after an error-free parse.

For question 5, accept implementation-specific mechanisms only when the observed tree is left-associated. For question 6, expect recognition that generator/runtime skew can cause compile-time or runtime incompatibility and that regeneration from declared inputs is evidence of reproducibility. For question 7, require an explicit choice about the relative binding of exponentiation and unary negation as well as right associativity. For question 8, award credit for any concrete negative case tied to a realistic faulty implementation and a named assertion.

## Decision and evidence record

Award **unit pass** only at 75 points or higher, with every critical gate satisfied and at least 12/20 in section 2, 12/20 in section 3, and 6/10 in section 4. Otherwise record **unit not complete** with observed evidence and preserve the failed attempt.

The validator record should include the submission identity, exact argv used for build/tests and black-box runs, bounded execution outcomes, captured log locations, rubric section scores, critical-gate results, and the final label. The only valid success label is for `managed_unit_01_expression_front_end`; no result here supports a whole-course completion claim.
