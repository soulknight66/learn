# Examiner Rubric: Stable Matching as an Executable Contract

**Audience:** examiner only—do not release this file or derived answer guidance to the learner  
**Artifact status:** `PREPARED_NOT_VALIDATED`  
**Unit:** `kickoff_01_stable_matching_engineering`  
**Scale:** 100 points; provisional unit pass requires at least 80 points and every critical condition below

## Evaluation protocol

Evaluate the submitted artifact, not the learner's claim about it.

1. Preserve the original submission and evaluate a working copy in an isolated environment with network access disabled.
2. Follow only the setup and test commands documented in the learner's README. Record command, exit status, runtime, and captured output.
3. Inspect source and tests. Learner tests passing is evidence, but never the sole evidence of semantic correctness.
4. Exercise independent valid and invalid cases. Adapt cases only at the learner's documented public interface; do not repair their implementation.
5. Use the definition of a blocking pair to check returned mappings independently of the learner's checker.
6. Score each section, apply caps and critical conditions, and preserve concrete evidence for every deduction.

Do not infer success from file presence. Do not modify job or course state directly; report evidence to the harness-controlled validator.

## Critical conditions and caps

All three manifest critical conditions must hold:

- the implementation runs through the documented command;
- every examined valid-input output is a bijection with no blocking pair; and
- the work contains no leaked examiner material or represented-as-original copied evidence.

Apply these caps after ordinary scoring:

- Cannot execute because required instructions, source, or declared dependencies are missing: maximum **39** and critical failure.
- Any valid instance produces a crash, non-bijection, or unstable result: maximum **59** and critical failure.
- The implementation does not perform deferred acceptance (for example, it searches all matchings) despite returning stable examples: maximum **69**.
- No substantive termination or stability argument tied to the submitted implementation: maximum **74**.
- No independent definition-based stability oracle in tests: maximum **79**.
- Confirmed use of examiner-only content or materially unattributed copied work: **no pass**, with evidence recorded for review rather than an allegation based on style alone.

A score of 80 or more is not a pass when a critical condition fails. Conversely, satisfying critical conditions does not waive the 80-point threshold.

## Scoring

### A. Reproducibility and contract — 20 points

- **5:** A clean-copy test run follows one exact, noninteractive README command, needs no network, and returns meaningful process status.
- **4:** The public input/output representation and empty-instance behavior are unambiguous and demonstrated with an original example.
- **6:** Boundary validation reliably rejects unequal sizes, overlapping group IDs, missing/unknown participants, duplicate ranking entries, and other violations of strict complete rankings. It never returns a purported matching after invalid input.
- **3:** Calls do not mutate either input maps or nested ranking sequences.
- **2:** Failure type/result is consistent, and messages or structured details distinguish the four required fault classes.

Full credit requires behavior and documentation to agree. Deduct at least 2 for relying on unspecified hash iteration behavior without analysis, even if one runtime happens to be repeatable.

### B. Deferred-acceptance implementation — 25 points

- **6:** Proposal state ensures each left participant considers right participants in declared preference order without repeating or skipping a candidate.
- **6:** Engagement/rejection transitions maintain at most one current partner per participant and make the right participant retain the more-preferred proposal.
- **5:** Free-participant handling and termination are correct, including empty and one-pair instances.
- **4:** The result is deterministic and independent of map insertion order under the stated strict-preference model.
- **4:** Rank lookup is preindexed (or equivalently efficient), so the matching phase is worst-case (O(n^2)), not (O(n^3)) from repeated linear preference searches.

Inspect the actual transition logic. A familiar function name or pasted pseudocode is not evidence.

### C. Verification quality — 20 points

- **5:** A direct oracle checks membership, cardinality, bijection, and every possible blocking pair from returned output and preferences; it does not call or reconstruct the proposal algorithm.
- **4:** Tests include empty, singleton, and at least two nontrivial examples, one with a rejection.
- **4:** Tests exercise all valid strict complete preference profiles for the (2 \times 2) case and check properties rather than only snapshots.
- **3:** Larger generated tests use an explicit seed and print/reveal enough failing input to reproduce a failure.
- **2:** Malformed-input tests cover every documented class and verify non-mutation at nested-container depth.
- **2:** Repeatability and consistent-ID-renaming or insertion-order behavior are tested where the language permits.

Independently spot-check at least all (2 \times 2) profiles plus multiple examiner-chosen instances of sizes 0, 1, 3, and 6. The examiner checker should invert the left-to-right mapping, build rank indexes directly from input, and scan all unmatched pairs against the blocking-pair definition. Do not import the learner's oracle.

### D. Proof and complexity reasoning — 25 points

- **6:** At least three useful invariants are stated precisely, initialized, preserved by actual code transitions, and used later. Expected substance includes monotone proposal indices/no repeated proposals, matching consistency, and each right participant retaining their favorite proposal received so far.
- **5:** Termination uses a finite monotone measure and bounds proposals by (n^2), including the (n=0) case.
- **7:** Stability proof covers both required cases. If left participant (l) never proposed to right participant (r), (l) must finish with someone ranked above (r). If (l) did propose and was not retained, (r)'s held partner can only improve thereafter, so (r) does not prefer (l) to the final partner. The answer must connect these facts to submitted state transitions.
- **3:** Proposer optimality is correctly stated across all stable matchings, not confused with global welfare, uniqueness of every stable matching, or merely stability. The explanation supports processing-order independence for the final partner mapping under strict complete preferences.
- **4:** Time and auxiliary space are reported separately for validation, rank indexing, matching, and oracle. For ordinary map/list representations, expected worst-case bounds are (O(n^2)) time for each stage and (O(n^2)) stored preference/rank information overall; justified representation-specific alternatives are acceptable.

Do not award proof credit for theorem names alone. Minor notation mistakes can lose 1–2 points; an argument that assumes its conclusion earns no credit for that subpart.

### E. Engineering judgment and comprehension — 10 points

- **2:** Code separates validation from matching transitions, uses model-revealing names, avoids global mutable state, and contains no required generated clutter or machine-specific path.
- **2:** Design, code, tests, and README describe the same behavior; limitations and citations are honest.
- **2:** Oracle-independence and metamorphic-renaming responses identify plausible shared-failure and identifier/order bugs.
- **2:** The multiple-stable-matchings response supplies and checks a valid smallest example, and correctly selects the left-proposing outcome.
- **2:** The chosen model extension identifies at least two genuinely affected contracts/invariants, while the evidence-limits response distinguishes testing from proof and explicitly denies whole-course completion.

## Comprehension answer guidance

Use this section to assess substance, allowing equivalent notation and examples.

1. A sound contract includes equal disjoint groups, strict complete permutations, an empty case, a left-to-right bijection, stability, deterministic behavior, non-mutation, and explicit rejection. The trace must point to real validation code.
2. Useful invariants include: each proposal index only increases; a left participant proposes to a right participant at most once and in preference order; an engagement map is one-to-one; and each right participant holds the most-preferred proposer seen so far. The learner needs three tied to transitions, not this exact set.
3. The total number of not-yet-made possible proposals decreases on each proposal step, or total proposal indices increase, giving at most (n^2) proposals. Empty input performs none.
4. The two-case argument described in section D is required. A claim that termination alone implies stability is wrong.
5. Left-proposer optimality means every left participant weakly prefers this partner to their partner in every other stable matching. It does not say the stable matching is unique or optimize total rank. With strict complete preferences, different choices of which free proposer moves next do not change the left-optimal partner mapping.
6. With explicit permutation checks and rank maps, validation, preprocessing, matching, and a full blocking-pair scan are each (O(n^2)) time. Preferences/rank indexes occupy (O(n^2)); live engagement, queue, and proposal-index state occupy (O(n)). Credit accurate bounds for the actual representation.
7. Examples include stale inverse mappings, skipped proposals, or incorrect replacement comparisons. A checker derived from internal engagement state might repeat or overlook the same defect; reconstructing the inverse and scanning preferences from the returned mapping reduces that coupling.
8. Consistent bijective renaming should commute with the algorithm: renaming the original output should equal the output on renamed input. This can expose accidental lexical-ID ordering, mixed namespaces, or inconsistent lookups.
9. A valid smallest example has (n=2). One canonical profile is:

   ```text
   L1: R1 > R2       R1: L2 > L1
   L2: R2 > R1       R2: L1 > L2
   ```

   Both `{L1-R1, L2-R2}` and `{L1-R2, L2-R1}` are stable. Left-proposing deferred acceptance returns the first, where both left participants receive their first choice. An isomorphic example is fully acceptable. Require explicit blocking-pair checks for both matchings.
10. Judge the chosen extension on internal consistency. For example, ties require a definition of stability and a tie-breaking/policy contract; incomplete lists require possible unmatched outputs and an acceptability rule; capacities require non-bijection cardinality and per-receiver quotas.
11. Passing finite tests does not alone prove stability for all valid finite inputs, termination, asymptotic complexity, or proposer optimality. A code-connected proof/analysis supports those universal claims. The kickoff omits most catalog topics and is explicitly not whole-course completion.

## Final examiner record

Record:

- raw section scores and capped final score;
- whether each critical condition passed;
- exact commands and exit statuses;
- independent cases exercised and any minimal counterexample;
- artifact paths supporting proof/documentation credit;
- a unit recommendation of `PASS`, `REVISE`, or `INVALID_EVIDENCE`; and
- the mandatory scope statement: **“This recommendation concerns only `kickoff_01_stable_matching_engineering` and makes no course-completion claim.”**

Only the worker-harness validator may promote unit state.

---

**Provenance:** Independently authored examiner guidance for the manager-authored kickoff, based only on the supplied CSDIY catalog snapshot at source commit `adce8e13789dc16aa6d1fbe163e9541736defae4`. No external course material, official assignment, hidden grader, or learner submission was used to prepare it.
