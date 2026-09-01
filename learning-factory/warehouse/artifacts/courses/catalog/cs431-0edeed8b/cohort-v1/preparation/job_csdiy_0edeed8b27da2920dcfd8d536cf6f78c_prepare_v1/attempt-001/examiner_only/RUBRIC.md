# Examiner Rubric — Kickoff Unit 1

This rubric is examiner-only. Evaluate the submitted crate and prose directly; do not award credit for an agent or learner's completion claim. Do not require access to any external CS431 link. Run validation in an isolated copy with bounded process time and captured output.

## Completion decision

Score out of 100. Mark this unit complete only at 80 or above, with at least 14/20 in both Concurrency correctness and Test quality, at least 6/10 in Comprehension, all required files present, and no critical failure below. A passing unit decision is not a course-completion decision.

Critical failures:

- Code that does not compile under stable Rust: no points in API/functional, concurrency, or tests; total score is capped at 35.
- Any `unsafe` in submitted crate code, an exposed guard/reference into protected state, or shared-state mutation outside synchronization: Concurrency correctness is zero and total score is capped at 49.
- No genuine multithreaded test: Test quality is capped at 8/20 and total score at 69.
- Missing or fabricated run evidence: Evidence is zero. A mismatch between claimed and observed results must be recorded in the validation report.
- External course materials, network availability, generated build products, and learner self-reports are never prerequisites or completion evidence.

## 1. Required API and build hygiene — 10 points

- 4: Public names, generic shape, return types, visibility, and derives conform to the specified contract closely enough for an independent client test to compile.
- 2: Zero capacity is rejected with the typed error and positive capacity is immutable.
- 2: `cargo fmt --check` and `cargo clippy --all-targets -- -D warnings` pass.
- 2: Only standard-library production dependencies are used; the crate is focused and contains no unrelated features or artifacts.

## 2. Sequential functional correctness — 20 points

- 4: Insert and get below capacity return the required snapshots and outcomes.
- 4: Updating returns the prior value without duplicating or promoting the key.
- 4: Full insertion evicts and returns exactly the oldest pair, then inserts the new pair.
- 3: Removal updates mapping and FIFO membership; missing removal is a no-op.
- 3: Removed-then-reinserted keys become newest; subsequent eviction reflects that order.
- 2: Length is accurate and never exceeds the positive fixed capacity across all transitions.

Use independent black-box cases, including capacity one, an update while full, removal of oldest/middle/newest where applicable, reinsertion, and several consecutive evictions. Do not infer correctness only from learner tests.

## 3. Concurrency correctness — 20 points

- 7: All mutable abstract state is under one auditable mutex, and every invariant-relevant read or mutation occurs while holding it.
- 5: Operation bodies maintain map/order agreement atomically and return values correspond to the same protected transition.
- 4: The written linearization points agree with the actual implementation for lookup, both insert paths, and removal.
- 2: Lock-taking paths convert poison to `CacheError::Poisoned` without production-path `unwrap`, `expect`, or silent recovery.
- 2: Owned/cloned return values prevent a guard or borrow from escaping, and worker sharing uses Rust's safe `Arc`/trait behavior.

Stress with distinct and same-key insertions under an independent bounded harness. A deadlock, panic, capacity breach, impossible outcome count, or map/order symptom loses the relevant points even if learner tests happened to pass.

## 4. Test quality and determinism — 20 points

- 7: Sequential tests cover every required transition and outcome, including stable FIFO position on update and reinsertion order.
- 3: Tests assert the capacity/map/order behavior through public observations after intermediate transitions, not merely that calls return `Ok`.
- 5: The distinct-key concurrent case uses at least four workers, coordinated start, joins, capacity below attempt count, and schedule-independent assertions including outcome counts and final length.
- 3: The same-key concurrent case establishes one insertion, remaining updates, no eviction, length one, and final value membership without predicting a winner.
- 2: There are no sleeps, timing thresholds, unseeded/random behavior, ignored worker results, network calls, or order assumptions; repeated local runs remain stable.

Expected distinct-key count for an initially empty cache with `n` unique insertions and capacity `c < n`: `c` calls report `Inserted`, `n - c` report `Evicted`, and zero report `Updated`, independent of serialization order.

## 5. Design and engineering reasoning — 15 points

- 4: `DESIGN.md` states mapping/order equivalence, uniqueness, positive fixed capacity, and `len <= capacity`, plus any representation-specific invariant.
- 3: Each operation has a precise transition and result; update-without-promotion and removal/reinsertion are unambiguous.
- 3: The argument connects one mutex and critical-section transitions to linearizability without claiming that mutual exclusion alone proves functional correctness.
- 2: Complexity is honest. A `VecDeque` search/removal by key is linear unless the representation supplies additional validated indexing.
- 2: Poisoning and two plausible failure modes are tied to specific tests or inspection steps.
- 1: Scope stays bounded; limitations and non-goals are explicit.

## 6. Reproducible evidence — 5 points

- 2: Exact tool versions, commands, and exit statuses are present.
- 2: Recorded summaries match the examiner's formatting, lint, and test observations, or discrepancies are honestly identified.
- 1: Test inventory and known limitations are concrete. Build output directories and assertions such as "should pass" receive no evidence credit.

## 7. Comprehension — 10 points

Award up to the indicated total for technically precise, implementation-connected answers:

- Q1–Q2 (3 points): identifies the abstract mapping/FIFO/capacity state, core invariants and threatening operations, and places linearization points within actual lock-held reads or transitions.
- Q3 (1.5 points): permits either serialization. If A is first, A reports `Inserted`, B reports eviction of `(a, 1)`, and final state is `b -> 2`; the symmetric B-first history is also permitted. `Updated`, two `Inserted` results, a final length other than one, or eviction by the first linearized call is impossible.
- Q4 (1 point): `a` is evicted because updating it does not promote its FIFO position; choosing `b` reveals accidental LRU/update promotion.
- Q5 (1 point): explains scheduler freedom and spurious timing, then connects barriers to simultaneous eligibility and assertions to invariants/outcome multisets rather than winner identity.
- Q6 (1 point): explains panic-while-guarded poison signaling and typed propagation; a defensible alternative such as explicit recovery is accompanied by the risk/availability tradeoff.
- Q7 (1.5 points): identifies at least three substantive changes among invariant partitioning, cross-shard atomicity, linearization points, weak-memory reasoning, reclamation, progress, schedule exploration, and test oracles.
- Q8 (1 point): distinguishes sampled execution evidence from a reasoned contract argument and explicitly excludes full correctness proof, performance/progress, official assignments, advanced CS431 topics, and whole-course completion as appropriate.

Answers that merely restate prompts without connecting to the submitted implementation receive at most half credit. Contradictions between prose and executable behavior are scored against the observed behavior and noted for remediation.

## Examiner record

Record command results, independent test identifiers, section scores, critical caps, and the final unit-only decision in validator-controlled evidence. Preserve a failed attempt and its logs. Never copy this rubric, independent tests, or answer anchors into a learner-safe directory.
