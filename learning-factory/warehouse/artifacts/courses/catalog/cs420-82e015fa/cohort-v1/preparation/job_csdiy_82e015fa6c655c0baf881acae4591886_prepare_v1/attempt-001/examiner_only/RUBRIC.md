# Independent examiner rubric: AST Traversal as an Engineering Component

This rubric applies only to the manager-authored kickoff. It must not be used to certify completion of CS420 or any official KAIST assignment. Inspect the submitted files and rerun checks in the controlled harness; learner prose and pasted command output are supporting evidence, not proof by themselves. Do not retrieve external course content while grading.

## Evaluation procedure

1. Confirm that the submission is a bounded, standalone Rust crate and does not claim KECC compatibility or whole-course completion.
2. Build and test it with the harness's bounded subprocess policy.
3. Inspect the implementation rather than relying only on the demonstration output.
4. Add examiner-authored trees when the public API permits, especially empty, wide, and deeply nested cases within safe limits.
5. Compare DESIGN.md and comprehension responses with observable behavior.
6. Preserve command results and failures as assessment evidence.

## Scoring

### Functional traversal and output — 25 points

- 10: Every required node variant is representable and is visited exactly once on representative trees.
- 6: Depth-first pre-order and source-order sibling traversal are correct for functions, parameters, blocks, branches, calls, and expression operands.
- 5: Outline structure and scalar labels are deterministic and follow one documented indentation and line-ending policy.
- 4: Empty collections and absent optional branches behave deliberately without phantom visits or ordinary-path panics.

Hard-coded output that is not derived from the submitted tree earns zero in this section.

### Separation and API design — 20 points

- 8: Traversal is genuinely reusable by a non-rendering consumer without copying the recursive walk.
- 5: Public responsibilities and invariants are coherent and appropriately documented.
- 4: Ownership and borrowing avoid gratuitous cloning and unsafe lifetime workarounds.
- 3: The design can add syntax or consumers without unrelated rewrites; tradeoffs are acknowledged rather than hidden.

Award partial credit for a clean recursive implementation even if its abstraction is modest. Do not require a particular visitor-trait pattern.

### Tests — 20 points

- 5: Tests cover the empty translation unit and preserve sibling order.
- 5: A nested fixture combines a function, conditional with else, loop, and nested expression.
- 4: All required node kinds and optional-branch behavior are exercised.
- 3: Exact-output assertions catch indentation, ordering, and label regressions.
- 3: A non-rendering reuse test or equivalent evidence detects duplicate or missing visits.

Tests that only assert that execution does not panic earn little credit. Examiner-added tests may supply evidence where learner tests are weak, but missing learner tests still lose the corresponding points.

### Rust quality and reproducibility — 15 points

- 4: The crate builds with a conventional layout and no unnecessary dependency.
- 4: Routine output failures are propagated; global mutable state and ordinary-path panics are absent.
- 4: Available formatting, lint, and test checks pass when rerun by the harness.
- 3: Behavior is independent of addresses, randomized iteration, and debug-only representations.

Do not deduct for an unavailable optional local component when EVIDENCE.md records the failure honestly and harness-visible code quality is otherwise sound.

### Design and evidence record — 10 points

- 4: DESIGN.md accurately states invariants, responsibility boundaries, ownership, errors, and limitations.
- 2: A plausible alternative and its tradeoff are considered.
- 2: External-integration assumptions are explicitly unverified and identify facts that must be inspected.
- 2: EVIDENCE.md records working directory, versions, commands, statuses, and honest failures consistently with examiner reruns.

### Comprehension — 10 points

Award one point per prompt when the answer is technically sound, specific to the submission, and internally consistent. Expected indicators include explicit pre-order mechanics, a testable order failure, a meaningful traversal/rendering boundary, borrowing consequences, exhaustive-change signals, error propagation, complementary exact and structural tests, bounded generation with property oracles, concrete integration unknowns, and a clear unit-versus-course boundary.

## Decision

- Ready: at least 75 points, with at least 13/25 in functional traversal, 10/20 in tests, and no critical failure.
- Revise: below a section floor or below 75 points, with actionable findings recorded.

Critical failures are: no inspectable implementation; no runnable tests; output wholly hard-coded rather than traversed; use or exposure of restricted, sealed, secret, or another learner's material; fabricated evidence; or representation of this kickoff as proof of an official assignment or full-course completion. A critical failure requires revision regardless of total score.
