# Independent Examiner Rubric: Rust Dependency Planner Kickoff

## Boundary and evidence rules

This rubric evaluates only `unit_01_dependency_planner`. It must never be used to mark the full CS220 course complete. Learner prose is supporting evidence, not proof that commands passed or behavior works. Only the worker-harness-controlled validator may promote the unit after inspecting durable source, captured command logs, and test results.

Score out of 100. A unit passes at **75 or above** only if every gate below also passes.

### Mandatory gates

- The submitted package builds with stable Rust and contains no third-party dependency.
- Harness-controlled functional tests pass for valid planning, invalid input, cycle reporting, determinism, and CLI stream/exit behavior.
- No expected user-input case aborts or panics.
- Learner tests, reflection, and comprehension responses are present and materially learner-specific.
- No supplied hidden test, sealed reference, examiner file, or another learner's work appears in the learner submission.

If a gate fails, record the score for diagnostic value but cap the result below passing. Do not substitute a prose claim for a missing command log. Formatter or linter failure alone does not trigger a gate, but it loses the corresponding quality points.

## Scored criteria

### 1. Contract correctness and graph behavior — 30 points

- 8: accepts empty input, standalone declarations, and referenced tasks exactly as specified;
- 8: returns a valid topological order and applies lexicographically smallest-ready tie-breaking at every step;
- 5: treats duplicate declarations and identical edges idempotently, with consistent adjacency and indegree state;
- 5: returns all and only unscheduled tasks, sorted, for self-loops, cycles, and downstream blocking;
- 4: the CLI prints exactly one task per line on success, including truly empty output for an empty plan.

Use additional examiner-owned fixtures, including disconnected components, ready tasks that become available mid-run, duplicate edges, a self-loop, a cycle with an acyclic downstream tail, and non-ASCII invalid identifiers. Do not expose these fixtures as hidden files in the learner view.

### 2. Parsing and failure contract — 15 points

- 6: trimming, blanks, comments, standalone tasks, and exactly-one-arrow rules are implemented correctly;
- 4: the identifier grammar is enforced at both edge endpoints and standalone declarations;
- 3: the first invalid line is returned with its correct one-based physical input line and a useful diagnostic;
- 2: CLI failures use standard error only for the diagnostic, leave standard output empty, and exit with status 2.

### 3. Rust ownership and API design — 15 points

- 5: `plan(&str)` and the public comparable error enum match the declared boundary;
- 4: borrowing and ownership choices are sound and reasonably economical, with no lifetime trick that makes returned results depend on the input buffer;
- 3: parsing/domain logic and process I/O have clear boundaries;
- 3: expected failures use `Result` and typed variants rather than panic paths or ambiguous sentinels.

### 4. Learner tests and engineering loop — 15 points

- 7: learner tests cover the specified success, invalid-input, duplicate, cycle, deterministic, and CLI cases with meaningful assertions;
- 3: test names and fixtures make the protected contract legible;
- 2: `cargo fmt --check` passes;
- 2: `cargo clippy --all-targets --locked -- -D warnings` passes;
- 1: the locked build/test commands are reproducible and generated build output is not submitted.

Examiner-owned tests establish correctness independently; high learner-test points require useful learner-authored tests even when examiner tests pass.

### 5. Maintainability and documentation — 10 points

- 4: implementation is readable, avoids needless complexity, and gives domain concepts useful names;
- 3: `README.md` accurately states the grammar, usage, and two original examples;
- 3: important invariants and non-obvious choices are documented near the relevant interface or code without narrating obvious syntax.

### 6. Reflection and comprehension — 15 points

- 5: reflection addresses all five prompts with concrete references to submitted work, stays within the requested range, and honestly discloses assistance;
- 10: comprehension responses are technically correct and well justified, using the guide below (partial credit allowed).

## Comprehension guide

1. A strong response notes that the caller may drop or mutate the input after the call because the result owns its names. Borrowed output would require output lifetimes tied to the input and a representation based on slices; parsing/normalization and storage choices would be constrained. Merely defining `String` as “mutable text” is insufficient.

2. The exact order is `docs`, `fetch`, `compile`, `lint`, `test`. Ready sets before selection are `{docs, fetch, lint}`, `{fetch, lint}`, `{compile, lint}`, `{lint}`, and `{test}`. The response must notice that `compile` becomes ready after `fetch` and sorts before the already-ready `lint`.

3. The result is the invalid-line variant containing physical line number 7 and a useful multiple-arrow diagnostic. The line number comes from enumerating all physical lines before/while filtering blanks and comments. Invalid external input is recoverable and belongs in `Result`; panic would violate the public and CLI failure contract.

4. A distinct edge contributes exactly one adjacency relation and exactly one indegree increment. If adjacency deduplicates while indegree increments twice, the destination may never reach zero; the reverse inconsistency can schedule it before all real prerequisites are processed.

5. Report `["a", "b", "c"]` in sorted order. `a` and `b` form the cycle; `c` is not in that cycle but cannot be scheduled because its prerequisite remains blocked. Thus the specified list is the remainder of Kahn-style processing, not a strongly connected component computation.

6. Accept any coherent pair. Parser examples should normally be library-level assertions on a returned value/error; CLI examples should launch the binary and assert status plus separated stdout/stderr. Full credit requires naming the regression each test detects rather than saying only that tests improve quality.

7. Grade against the submitted structures. A typical ordered-ready-set solution is at least `O((V + E) log V)` time (or a more precise justified bound) and `O(V + E)` space. Accept a different bound when it correctly accounts for all chosen ordered maps/sets, sorting, cloning, and adjacency operations. Do not award full credit for an unsupported `O(V + E)` claim when ready selection uses a comparison tree.

8. Accept a concrete, accurate analysis tied to submitted code. Strong examples include isolating CLI I/O from `plan`, using a typed error enum so a new error category is localized, or owning returned names so caller input lifetime changes do not propagate. The claimed future change must actually be helped—or the response must candidly explain where coupling remains.

Allocate the 10 comprehension points holistically: responses 1, 2, 4, 5, and 7 carry the most technical weight; responses 3, 6, and 8 still require concrete reasoning. Evidence of copied stock prose without linkage to the submitted design earns no credit for that response.

## Result recording

Record criterion scores, gate outcomes, exact validator labels, command/log artifact locations, and the validated source revision. A passing record should say `KICKOFF_UNIT_VALIDATED_ONLY`; it must not say or imply `COURSE_COMPLETED`. Preserve failed-attempt evidence according to the harness policy.
