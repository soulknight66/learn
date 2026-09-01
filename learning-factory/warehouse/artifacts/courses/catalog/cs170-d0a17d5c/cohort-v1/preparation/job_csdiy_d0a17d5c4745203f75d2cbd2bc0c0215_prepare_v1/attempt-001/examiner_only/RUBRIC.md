# Independent rubric: inversion-counting kickoff

This rubric is examiner-only. Evaluate preserved artifacts and rerunnable behavior; do not award credit for unsupported learner claims. The task is manager-authored and self-contained, so unavailable external CS170 materials must not affect the result.

## Validation procedure

1. Confirm that all required artifact paths exist and that no third-party dependency is needed.
2. Run the learner's documented test command in Python 3.11.
3. Run independent API cases, including empty input, duplicates, negative values, a mutable input, rejected values, and generated small cases checked against an examiner-controlled oracle.
4. Exercise the CLI as a subprocess with a valid array and with malformed JSON, a non-array top level, and an invalid element. Inspect exit codes and both output channels.
5. Inspect the production path for worst-case complexity, hidden quadratic work, mutation, global state, and agreement with the design note.
6. Regenerate a small benchmark, validate both JSON files structurally, and compare recorded provenance with the invoked settings.
7. Read the design note and comprehension responses independently of test success.

Record commands, exit statuses, and relevant output as validation evidence.

## Scoring (100 points)

### 1. Functional contract and correctness — 25 points

- 12: returns the correctly sorted new list and exact strict inversion count across ordinary, empty, negative, ordered, reverse-ordered, and duplicate-heavy cases;
- 5: leaves all accepted input sequences unchanged and has no observable mutable global state;
- 4: implements and documents a consistent integer/`bool`/invalid-element policy;
- 4: handles boundary cases without a special path that violates the contract.

Expected semantic fact: an inversion is exactly an index pair `i < j` with a strict `values[i] > values[j]`; equality never contributes.

### 2. Algorithm, proof, and resource analysis — 20 points

- 7: production code has a genuine worst-case `O(n log n)` design and no quadratic counting or checking pass;
- 5: the combine invariant is stated precisely and corresponds to code state;
- 5: the correctness argument partitions inversions into within-left, within-right, and cross-boundary cases and establishes exhaustive, unique counting;
- 3: the recurrence and peak-space analysis are correct and mapped to implementation operations.

Expected reasoning: each split recursively accounts for inversions internal to its two parts. During an order-preserving linear combine, choosing a right-side value before remaining larger left-side values accounts for exactly those remaining cross inversions. A representative recurrence is `T(n) = T(floor(n/2)) + T(ceil(n/2)) + Theta(n)`, yielding `Theta(n log n)`; the reusable/cumulative live buffers and result require `O(n)` auxiliary space for a careful implementation, with recursion depth `O(log n)`.

### 3. Test design and determinism — 20 points

- 6: focused examples cover all required input categories and assert both outputs;
- 4: mutation and output-object independence are directly tested;
- 4: the quadratic oracle is test-only, visibly bounded to small inputs, and used with a fixed-seed generator;
- 3: at least one valid metamorphic relation is documented and tested;
- 3: tests are deterministic, isolated, and runnable through the documented discovery command.

Agreement with a learner-written oracle is supporting evidence only. Inspect the oracle for the same strict comparison, independent control flow, bounded input size, and shared-assumption defects.

### 4. CLI and failure engineering — 15 points

- 6: valid JSON-array input produces only a JSON object with exactly `sorted` and `inversions` on stdout and exits `0`;
- 6: all three required failure classes exit `2`, emit a concise stderr diagnostic, emit no stdout result, and expose no traceback;
- 3: subprocess tests assert exit code and channel separation rather than calling CLI helpers only in-process.

### 5. Performance evidence and reproducibility — 10 points

- 4: benchmark parameters are configurable and default generation is seeded; at least four geometric sizes and three repeats are preserved;
- 3: saved JSON contains individual timings, settings, Python/platform provenance, and the required empirical-evidence label;
- 3: analysis cautiously compares scaling with the proof and names at least two concrete noise or bias sources.

Timing ratios need not be monotone and must not be graded against a fixed speed threshold. Source analysis establishes the bound; timing only checks for gross inconsistencies.

### 6. Communication and comprehension — 10 points

- 4: README commands are exact, sufficient, and consistent with observed behavior;
- 3: design note is concise, internally consistent, and ties its claims to named code;
- 3: comprehension responses correctly address all nine prompts with concrete artifact references and explicit limits.

## Critical caps and deductions

- No runnable production implementation: cap total at 20.
- Production counting is quadratic in the worst case, or delegates the count to a quadratic pass: cap total at 55.
- Tests cannot be discovered with the required command: no points in section 3 until examiner evidence shows an environment-only issue.
- Missing design note or comprehension responses: score the corresponding communication items as zero; do not infer reasoning from correct code.
- Fabricated, non-JSON, or irreproducible benchmark results: zero for section 5 and flag the evidence issue.
- A traceback, result data on stdout during a required failure, or incorrect failure exit status loses the applicable CLI points even if an in-process helper behaves correctly.
- Use of a third-party runtime dependency loses 3 points under communication/reproducibility and must be reported as a contract violation.

## Decision labels

- `UNIT_VALIDATED`: at least 80 points, no critical cap below 80, all independent functional cases pass, and no fabricated evidence.
- `UNIT_REVISION_REQUIRED`: below 80, any independent functional failure, any unmet required failure behavior, or any evidence-integrity issue.

Either label applies only to `unit_manager_kickoff_inversion_counting_v1`. It is never evidence that the course is complete or that later CS170 topics have been studied.
