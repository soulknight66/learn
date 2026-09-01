# Independent Evaluation Rubric: Lexical Contracts Kickoff

Course ID: `course_23fa038d619a5b3482e8c8eadb3e2d78`  
Unit ID: `kickoff_01_lexical_contracts`  
Visibility: `EXAMINER_ONLY`  
Validation label: `EXAMINER_SPECIFICATION_PENDING_HARNESS_VALIDATION`  
Provenance: independently authored for the manager-created kickoff using only the supplied CSDIY catalog snapshot; no official assignment, solution, test, or restricted content was fetched.

## Evaluation authority and boundary

Evaluate a fresh copy of the learner submission. Do not accept the learner's transcript or prose claim as proof: configure, build, run the submitted tests, add independent black-box cases, and inspect the source. Do not require any external URL, official framework, or network access.

This evaluation can promote only `kickoff_01_lexical_contracts`. A passing result must leave the course `IN_PROGRESS`; it cannot award credit for an official USTC lab or any later compiler topic.

Record the exact submitted revision or artifact hash, toolchain, commands, exit statuses, score by section, cap applied, and relevant stdout/stderr in validator-controlled evidence.

## Preflight and score rule

Run from a clean build directory:

```bash
cmake -S . -B build
cmake --build build
ctest --test-dir build --output-on-failure
```

Then exercise both standard-input and file-input CLI paths with examiner-created cases. Award 100 points total. A score of at least 80, no critical cap below 80, and credible evidence in every section is required for unit completion. Otherwise retain the attempt and report actionable findings.

## 1. Reproducible build and interface — 10 points

- 4: clean CMake configure and C++17 build succeed without a network fetch or undeclared dependency;
- 3: submitted tests are registered with CTest, run deterministically, and propagate failure by exit status;
- 2: both CLI input modes, stdout/stderr separation, and exit statuses follow the task contract;
- 1: README commands and recorded tool versions are sufficient to reproduce the run.

Full credit requires examiner execution, not merely a matching transcript. Deduct for environment-specific absolute paths, generated binaries in source, or instructions that require manual repair.

## 2. Core tokenization semantics — 24 points

- 6: all six keywords use exact whole-identifier recognition; keyword prefixes and suffixes remain identifiers;
- 4: identifier and integer regular forms are complete and retain exact lexemes without numeric overflow conversion;
- 6: every fixed spelling maps to the specified kind, with correct maximal munch for `==`, `!=`, `<=`, and `>=`;
- 4: adjacent tokens and end-of-input behavior are correct, including exactly one `EOF` at the next-byte position;
- 4: no valid byte is skipped or duplicated at token boundaries.

Use combinations not copied from the learner's tests. Inspect boundary logic for accidental overread even if examples pass.

## 3. Comments, positions, and failure semantics — 18 points

- 5: slash, line comment, and non-nesting block comment precedence is correct at ordinary and end-of-input boundaries;
- 5: token and `EOF` positions are correct across spaces, tabs, `LF`, `CRLF`, lone `CR`, and multiline comments;
- 4: unexpected bytes and a lone `!` produce `UNEXPECTED_CHARACTER` at the bad byte;
- 4: unterminated block comments produce `UNTERMINATED_BLOCK_COMMENT` at the opening slash, and lexical errors yield nonzero status, stderr diagnostics, and no token stdout.

Check an unterminated comment whose opening slash is not on line 1 and check a non-ASCII byte. The latter must be rejected without relying on signed-`char` behavior.

## 4. Library design and implementation quality — 13 points

- 4: reusable lexer code is free of argument parsing, printing, and process termination;
- 3: token and structured-error types make success versus failure unambiguous and have safe ownership/lifetimes;
- 3: scanner states or equivalent control flow are readable, bounded, and preserve position/consumption invariants;
- 3: implementation avoids global mutable state, undefined byte-classification behavior, needless coupling, and unexplained complexity.

Style preference alone earns no deduction. Score observable maintainability, contract fidelity, and specific defect risk.

## 5. Test quality — 20 points

- 5: at least 12 meaningful library cases and 2 CLI cases exist and make precise assertions;
- 5: the suite covers all token families, keyword boundaries, adjacency, comments, and the overlapping fixed tokens;
- 4: positions cover every specified newline form, tabs, multiline comments, layout-only input, and `EOF`;
- 4: both lexical errors are asserted for code and position, while CLI tests assert atomic output and stderr/status behavior;
- 2: at least one named mutation test would genuinely fail for the identified faulty implementation.

Do not award coverage points for tests that only print results, repeat the same path, depend on order or network, or calculate their oracle by calling the production behavior being tested.

## 6. Engineering record and honest evidence — 8 points

- 3: DESIGN identifies states/control structure, ownership, position invariants, error flow, and protection against consuming the next token;
- 2: README accurately documents build, test, CLI usage, versions, and known limitations;
- 2: the saved transcript is consistent with a clean run and is corroborated by examiner execution;
- 1: a deferred extension is explicit and the submission stays within the unit timebox/scope.

Fabricated or materially altered evidence earns zero in this section and triggers the integrity cap below.

## 7. Comprehension — 7 points

Judge explanations and cited evidence, not wording. Allocate up to 0.7 per response, then round the section once to the nearest whole point. Expected substance:

1. Kind selects grammar behavior, lexeme preserves source spelling/value input, and position supports diagnostics/source mapping; the response gives distinct downstream uses.
2. Expected sequence: `(1:1, KW_INT, int)`, `(1:5, IDENTIFIER, ifx)`, `(1:8, ASSIGN, =)`, `(1:9, KW_IF, if)`, `(1:11, EQ_EQ, ==)`, `(1:13, INTEGER, 0)`, `(1:14, SEMICOLON, ;)`, `(1:15, EOF, empty)`. It explains whole-identifier keyword classification and longest fixed-token matching.
3. Expected tokens: `IDENTIFIER a` at `1:1`, `EQ_EQ ==` at `2:5`, `IDENTIFIER b` at `2:7`, and `EOF` at `2:8`. Comment state suppresses token interpretation while position tracking continues until the first closing delimiter.
4. The lone `!` is at `1:11`; result is nonzero with `UNEXPECTED_CHARACTER` on stderr and empty stdout, even though earlier lexemes are valid, because output is committed only after complete success.
5. Before bytes: `a` at `1:1`, tab at `1:2`, `b` at `1:3`; `CRLF` is one newline; `c` is at `2:1` and the following position is `2:2`. A cited focused test must assert this rather than merely execute it.
6. Atomic output prevents consumers from mistaking a prefix for a valid complete stream; cost is buffering/latency. A credible streaming alternative makes partial/error/final states explicit rather than retaining the same atomic promise.
7. Cases must expose at least the four two-character spellings versus their one-character prefixes; `!=` also distinguishes the only valid use of `!`. Assertions cover kind, lexeme, count/position, and error where relevant.
8. A nesting depth (or stack) changes on open/close delimiters; successful end requires depth zero, while EOF with positive depth reports the outer opening position under a clearly stated policy. Tests include nested success, multiple levels/adjacency, and EOF before all levels close, with current behavior contrasted.
9. Compatibility includes kinds, exact lexemes, maximal munch, comment handling, positions/newlines, error codes/locations, `EOF`, and atomic CLI behavior. It cites a focused regression test; generated scanners commonly drift on position or error behavior.
10. The claim is limited to evidence actually run for this lexer. It names a real gap and a proportionate next independent test/review, with no official-lab or whole-course claim.

## Critical caps and invalid evidence

Apply the lowest applicable cap after scoring:

- clean configure or build fails: maximum 35;
- no runnable automated tests, or tests cannot detect a deliberately introduced obvious token defect: maximum 55;
- the implementation requires network access or unavailable official course content to build/test: maximum 55;
- systematic failure of maximal munch or whole-identifier keyword recognition: maximum 69;
- invalid characters are silently dropped, block-comment EOF is accepted, or lexical failure emits a partial stdout token stream: maximum 69;
- missing comprehension responses or responses unrelated to the submitted implementation: maximum 79;
- fabricated evidence, copied sealed examiner material, hidden grader exfiltration, or another learner's work: maximum 0 and preserve incident evidence.

A cap is not an automatic score; award section points first, then lower the total if necessary. Do not compensate a critical contract failure with polish elsewhere.
