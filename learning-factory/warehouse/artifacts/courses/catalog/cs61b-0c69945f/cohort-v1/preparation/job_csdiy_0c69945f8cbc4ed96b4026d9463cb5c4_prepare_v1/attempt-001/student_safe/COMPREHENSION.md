# Comprehension Questions

Answer all eight questions in your submission's `COMPREHENSION_RESPONSES.md`. Refer to concrete fields, helper methods, or tests in your own work where useful. Explanations should stand on their own; source-code excerpts alone are not answers.

1. State your complete representation invariant. How does it distinguish logical order from physical array layout, including the empty and full cases?

2. Suppose the backing array is full and the logical front is not at physical index zero. Trace what your implementation does for a growth followed by `addFirst`. Which facts ensure that every old element and the new element have the correct logical index afterward?

3. Java does not permit direct construction of `new E[n]`. How did you represent the backing storage, and why are the reads and writes type-safe under this class's API?

4. A single add or remove can trigger `O(n)` copying. Give an amortized argument for the claimed `O(1)` end operations under both the growth and shrink rules. Explain why the quarter-full shrink threshold matters.

5. What problem can occur if a removed slot is not cleared even when functional tests still pass? Identify a deterministic test or inspection that would provide evidence your implementation clears it.

6. Describe one high-value state transition covered by a targeted test and one different defect class covered by your fixed-seed differential test. What important property can the oracle test still fail to prove?

7. Precisely which events invalidate an iterator in your implementation? Explain what fail-fast behavior can detect and why it does not make the deque thread-safe.

8. Imagine a future client requests support for `null` elements without changing the existing removal signatures. What ambiguity or compatibility problem appears? Propose one API evolution and describe the tests that would need to change or be added.

Do not look for a course-site answer key: these questions concern the decisions and evidence in your own submission.

---

Provenance: course-manager-authored for the local kickoff unit from the supplied CSDIY catalog snapshot; no external course content was retrieved.

Validation label: `PREPARED_AWAITING_HARNESS_VALIDATION`
