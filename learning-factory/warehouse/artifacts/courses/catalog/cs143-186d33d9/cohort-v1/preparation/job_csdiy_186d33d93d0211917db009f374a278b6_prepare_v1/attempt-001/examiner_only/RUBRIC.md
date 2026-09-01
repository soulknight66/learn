---
course_id: course_186d33d93d0211917db009f374a278b6
unit_id: unit_01_minicool_lexer_engineering
audience: examiner_only
provenance: manager-authored independent rubric; not sourced from or claimed to be Stanford CS143 material
validation_label: EXAMINER_ONLY_UNAPPLIED
---

# Independent rubric: MiniCOOL-0 lexer kickoff

Apply this rubric to repository evidence and fresh command output. Do not accept prose claims as substitutes for files, executable behavior, or tests. Record the toolchain, commands, exit statuses, and any environmental limitation in the validation report.

## Validation procedure

1. Confirm the submission contains no examiner-only files copied into its learner deliverables.
2. Follow only the documented local clean-build and test commands. Do not download dependencies or use external course content.
3. Run the learner tests, then independently exercise the scanner API or CLI with small temporary ASCII files covering ordinary tokens, adjacent longest-match operators, nesting, string recovery, invalid characters, positions, and EOF.
4. Inspect implementation and tests for the complexity, progress, separation, and determinism claims.
5. Read the comprehension responses and verify every requested code/test citation against the repository.
6. Preserve captured output and assign an explicit result label: `PASS`, `FAIL`, or `BLOCKED`. Only `PASS` may promote this unit; no result promotes the whole course.

If the documented toolchain is unavailable but the submission is otherwise inspectable, mark `BLOCKED`, not `PASS`. A validator may use an equivalent already-installed compiler only when that substitution is recorded and cannot change semantics.

## Essential gates

All gates must pass, regardless of numeric score:

- The project builds and its automated tests run offline from the documented commands.
- A real scanner consumes finite input with deterministic output and exactly one final `EOF`; it is not a table of hard-coded fixture outputs.
- Nested comments, strings, lexical errors, and source positions are implemented rather than merely discussed.
- The submission is in Java or C++ and includes source code, tests, documentation, and comprehension responses.
- No official-course-completion or full-COOL-compatibility claim is presented as validated fact.

A failed essential gate makes the result `FAIL`. A genuinely unavailable required toolchain may instead produce `BLOCKED` as described above.

## Scoring (100 points)

### A. Lexical contract and observable behavior — 35 points

- 8: Reserved words, `TYPE_ID`, `OBJECT_ID`, and `INT` obey priority, spelling, and raw-lexeme rules.
- 7: Single- and multi-character operators use longest match and correct positions.
- 8: Whitespace, line comments, and arbitrarily nested block comments behave as specified.
- 8: Valid strings and all four escapes behave as specified, with raw spelling preserved.
- 4: CLI output escaping, standard-output discipline, invocation handling, and final `EOF` conform exactly.

Award each item from direct runs and code inspection. A feature that exists only in a mocked test receives no credit.

### B. Errors, recovery, and progress — 15 points

- 5: Invalid characters yield one-character errors and scanning resumes at the next character.
- 5: Invalid escapes and unterminated strings use the stated boundaries and do not create a spurious `STRING`.
- 3: An unterminated nested comment reports from the unmatched outermost opener through EOF.
- 2: Every branch either consumes input, changes state toward consumption, or emits final EOF; no finite input can loop forever.

### C. Engineering design — 15 points

- 5: Scanner, token/diagnostic data, CLI/file I/O, and tests have clear, narrow boundaries.
- 4: State and position updates are centralized enough to audit; duplicated edge-case logic is controlled.
- 3: Names and data structures reveal intent, with comments reserved for non-obvious invariants or choices.
- 3: The README/DESIGN gives reproducible commands, tool versions, architecture, complexity, and honest limitations.

### D. Automated verification — 20 points

- 10: Independently named tests cover every behavior required by the study task, including all token tables and recovery cases.
- 4: Assertions check kinds, exact raw lexemes, positions, ordering, and the single final EOF—not merely token counts or process success.
- 3: At least one process-level CLI test verifies serialization and stream/exit behavior.
- 3: Tests are deterministic, offline, isolated, and include a generated long case that checks output/operation consequences rather than a wall-clock threshold.

### E. Reasoning and comprehension — 15 points

- 3: Pipeline answer accurately separates lexing from parsing and later phases and discusses removed, preserved, and added information.
- 3: Longest-match trace matches actual control flow and a discriminating test.
- 3: The loop invariant establishes correct current position, prefix consumption, progress, and one EOF.
- 2: Nested-comment analysis gives `O(n)` time and implementation-appropriate auxiliary space (normally `O(1)` for a depth counter or `O(d)` for an explicit stack), with valid justification.
- 2: Recovery analysis uses the contract boundary and two tests that exclude realistic off-by-one, premature-resume, or overconsumption faults.
- 2: Evolution answer proposes a structured scanner interface independent of CLI serialization and identifies credible regression protection; command evidence and limitation reporting are honest.

## Independent probes

Use fresh fixtures rather than revealing or requiring any sealed reference. Suitable probes include:

- empty input;
- `class classroom Class x X 007`;
- `<-<==> @` with no separating whitespace;
- `a(* outer (* inner *) tail *)b`;
- a valid string containing each supported escape;
- a string with an invalid escape followed by a closing quote and then `class`;
- an unterminated string followed by LF and a valid identifier;
- nested block comment openers with only the inner closer present;
- invalid `_` or a non-ASCII byte followed by `if`;
- a multi-line fixture whose tokens begin immediately after LF and after a tab.

Derive expected records directly from the published MiniCOOL-0 contract. Keep the validator's actual fixtures and captured outputs as durable evidence; do not place them in the learner view.

## Result rule

`PASS` requires all essential gates and at least 70/100. Report category scores, gate outcomes, commands, environment, and evidence paths. A pass validates only `unit_01_minicool_lexer_engineering`; the course remains incomplete and later units remain unprepared.
