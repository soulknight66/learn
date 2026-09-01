# Independent Examiner Rubric: Weighted Interval Scheduling Kickoff

## Scope and authority

This rubric evaluates only `manager_unit_001_weighted_interval_engineering`. It does not certify coverage or completion of MIT 6.046. A learner statement, a self-reported test result, or the existence of files is not completion evidence; the worker-harness-controlled validator must record the result after independent checks.

Keep this file and all expected-response guidance outside the learner-safe view.

## Required artifacts

Evaluate these four learner-created files:

```text
submission/interval_scheduler.py
submission/test_interval_scheduler.py
submission/DESIGN.md
submission/COMPREHENSION_RESPONSES.md
```

Use a fresh process and a bounded timeout. First run:

```bash
PYTHONPATH=submission python3 -m unittest -v submission/test_interval_scheduler.py
```

Then run examiner-owned cases that do not import helpers from the learner's tests. Include exhaustive small instances, every validation class, permutations, zero-value ties, negative times, touching endpoints, and a moderately large performance case. Capture command, exit status, timeout status, and logs as durable evidence.

## Non-negotiable gates

The unit cannot pass if any of these conditions holds, regardless of points:

- one or more required artifacts is missing or unreadable;
- the public API or `Job` fields differ from the specification;
- learner tests fail, hang, or are nondeterministic on repeat execution;
- examiner checks find a non-optimal schedule, incompatible output, incorrect canonical tie result, or unprescribed input-order dependence;
- production code enumerates subsets or otherwise misses the required asymptotic boundary;
- the submission relies on third-party packages, network access, external services, precomputed case tables, or modifications to the examiner environment;
- the implementation mutates a valid caller-provided sequence or its records;
- the design note presents a materially false correctness or complexity claim.

## Scored criteria (100 points)

### A. Contract conformance and behavior — 25 points

- **3 points:** Exact public API, immutable `Job`, list-of-ID return type, and empty-input behavior.
- **6 points:** Complete validation: container category; `Job` elements; nonempty unique string IDs; exact integer-but-not-boolean numeric fields; increasing endpoints; and nonnegative values. Correct exception categories are used.
- **3 points:** Half-open compatibility is enforced, including equality at touching endpoints and arbitrary negative coordinates.
- **6 points:** Returned subset is feasible and has maximum total value over all compatible subsets.
- **5 points:** Canonical sort, reverse-bit tie preference, forward output order, zero-value behavior, and permutation invariance are exact.
- **2 points:** Inputs remain unchanged and the function has no observable I/O side effects.

### B. Algorithm, proof, and cost — 20 points

- **5 points:** Canonical sorting and predecessor lookup are implemented coherently, with binary search or an equivalently bounded method.
- **6 points:** Optimization state and recurrence are correct; the invariant covers both maximum value and the preferred subset within every prefix.
- **5 points:** Equal-value decisions implement the reverse-bit rule, decisions are recorded consistently, and reconstruction follows them without quadratic schedule copying.
- **4 points:** End-to-end analysis accounts for validation, ordering, predecessor computation, optimization, and reconstruction; it states `O(n log n)` key comparisons and `O(n)` auxiliary records and qualifies the unit-cost model for strings and Python integers.

### C. Test engineering — 25 points

- **6 points:** Direct tests cover empty, singleton, compatible, overlapping, greedy-trap, endpoint, negative-time, zero-value, and multi-optimum behavior.
- **4 points:** Invalid inputs cover all specified categories, including booleans and duplicate IDs, and check the prescribed exception class.
- **7 points:** The exhaustive oracle independently enumerates subsets, checks compatibility and total value, and applies the exact reverse-bit tie rule; it neither calls nor structurally reimplements the production dynamic program.
- **5 points:** At least 200 fixed-seed valid instances of at most 10 jobs are compared exactly with the oracle. The seed is explicit and runs are bounded and reproducible.
- **3 points:** Tests check input preservation and multiple permutations and contain useful failure context without order or timing flakiness.

### D. Implementation quality — 10 points

- **4 points:** Code is clear, cohesive, and maintainable; names expose the model and helpers have focused responsibilities.
- **2 points:** Types and docstrings describe the public contract without contradicting it.
- **2 points:** Behavior is deterministic, imports have no surprising side effects, and errors are raised deliberately rather than incidentally.
- **2 points:** No unnecessary framework, I/O layer, global mutable state, or out-of-scope feature obscures the component.

### E. Design note — 10 points

- **2 points:** Contract interpretation addresses validation, half-open intervals, canonicalization, and ties.
- **3 points:** Algorithm, state invariant, predecessor relation, decisions, and reconstruction are precise enough to audit against code.
- **2 points:** Correctness argument covers feasibility, optimal value, and unique tie selection rather than citing the algorithm by name.
- **2 points:** Complexity and testing claims are accurate and supported by the submitted implementation and suite.
- **1 point:** At least two realistic extensions identify concrete assumptions or change risks.

### F. Comprehension — 10 points

- **2 points:** Questions 1–3 correctly distinguish interval semantics, primary optimization, determinism, and the worked tie case.
- **3 points:** Questions 4–6 correctly connect predecessor search, the prefix invariant, induction, stored decisions, and reconstruction.
- **3 points:** Questions 7–9 accurately discuss whole-path complexity, validation/side effects, and oracle independence.
- **2 points:** Questions 10–12 give valid conditional metamorphic relations, calibrate fixed-seed evidence, and trace an extension to at least two changed assumptions.

## Expected reasoning for comprehension responses

Use these notes to assess substance; equivalent correct reasoning earns credit.

1. Half-open intervals make `finish == start` non-overlapping and model immediate reuse. Under closed intervals, two jobs such as `[0, 2]` and `[2, 3]` share time 2 and conflict.
2. The primary goal is maximum total value. The secondary rule chooses the lexicographically smallest reversed canonical membership vector. Without it, different input orders or implementation details can return different optimal schedules.
3. Canonical order is `P, R, Q`. Both `{R}` and `{P, Q}` have value 12. Their reverse vectors are `(0, 1, 0)` and `(1, 0, 1)`, respectively, so `{R}` wins and the output is `["R"]`.
4. For each canonical job, the predecessor is the greatest earlier canonical index whose finish is at most the current start, or a sentinel if none exists. The comparison is `<=` because endpoints may touch under `[start, finish)`.
5. A sound state describes the best value and contract-preferred subset for a canonical prefix. The induction splits feasible optima into those excluding the newest job and those including it plus an optimum over its predecessor prefix; equal values select exclusion at the greatest differing index.
6. Reconstruction must use the same stored include/exclude choices and predecessor jumps. Re-deciding an equality differently can preserve total value while violating the required membership vector.
7. Expected structural costs are sorting and all predecessor searches in `O(n log n)` comparisons, linear validation/optimization/reconstruction, and `O(n)` auxiliary records. String comparisons depend on common-prefix length, and arithmetic/comparison costs grow with integer bit length.
8. Full validation yields one predictable failure category before semantic work and prevents accidental partial processing or mutation. The implementation should work from its own ordered records and leave the caller's sequence untouched.
9. The oracle should enumerate all small subsets directly rather than invoke the production recurrence or helpers. Value-only comparison misses incompatibility, output order, and the prescribed choice among equal-value subsets.
10. Valid examples include input permutation invariance; translating every endpoint by the same integer; or multiplying all values by one positive integer. Preconditions and expected output equality must be stated, especially so ties and validity are preserved.
11. A fixed seed makes failures reproducible and the sampled corpus repeatable; it does not prove correctness or coverage. Purpose-built endpoint, tie, zero-value, validation, or adversarial overlap cases remain necessary.
12. Accept any chosen extension if the response identifies two genuine changes. Examples include loss of single-machine compatibility for multiple machines, invalidated precomputation under updates, snapshot/non-mutation changes for mutable jobs, or loss of global sorting and future knowledge in a stream.

## Passing rule

Record a unit pass only when all gates pass, the total is at least **80/100**, and these section floors are met:

- Contract conformance and behavior: at least 20/25
- Algorithm, proof, and cost: at least 14/20
- Test engineering: at least 17/25
- Comprehension: at least 6/10

Record section scores, gate results, test command evidence, and a concise defect list. A passing unit record must remain labeled as this manager-authored kickoff only; it must not update the course to completed.

