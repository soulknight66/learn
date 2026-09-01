<!--
provenance: Independently manager-authored examiner rubric for kickoff_priority_queue_engineering_v1; no remote course content was retrieved.
validation_label: EXAMINER_GUIDANCE_NOT_YET_APPLIED
confidentiality: EXAMINER_ONLY
-->

# Independent rubric: reliable min-priority queue kickoff

## Scope and decision

This rubric evaluates only `kickoff_priority_queue_engineering_v1`. It is not an MIT rubric and cannot award, imply, or contribute an automatic claim of whole-course completion.

Use a clean copy of the learner submission. Run learner tests and independent checks with bounded process time and captured output. Inspect source as well as behavior; passing self-authored tests alone is insufficient evidence.

The unit may receive `UNIT_VALIDATED` only when all pass gates hold and the score is at least **80/100**. Otherwise record `UNIT_NOT_YET_VALIDATED`, retain the failed evidence, and report concrete defects. Only the worker-harness-controlled validator may apply either label.

## Pass gates

All of these are mandatory:

1. All five required files are present, readable, and relevant; commands/results claimed in the engineering note are not fabricated.
2. The module imports without side effects that mutate external state, access the network, or start unbounded work.
3. Learner tests pass twice in fresh processes, and all independent contract/correctness tests pass.
4. Production queue operations use an actual binary heap. Use of `heapq`, third-party priority queues, global re-sorting, `sort`, or `sorted` in the production path fails this gate.
5. The benchmark is deterministic in workload generation, bounded, and has no timing-based pass assertion.
6. Comprehension responses are substantive and consistent with the submitted code and evidence.

Static inspection should distinguish forbidden production shortcuts from an allowed simple oracle confined to tests.

## Scored criteria (100 points)

### A. Public contract and validation — 15

- 4: exact class/method surface and `(item, priority)` return order.
- 5: numeric boundary is correct: finite `int`/`float` accepted; `bool` and other types raise `TypeError`; non-finite floats raise `ValueError`.
- 3: empty `peek`/`pop` raise `IndexError`, and `peek` is non-mutating.
- 3: rejected operations preserve prior observable state.

### B. Heap implementation and correctness — 25

- 10: insertion, root removal, last-entry replacement, and upward/downward restoration are correct.
- 5: downward repair compares both children and selects the lesser ordering key.
- 5: monotonic tie metadata provides FIFO behavior and payloads are never ordering operands.
- 3: private representation remains coherent over long interleaved traces.
- 2: implementation structure and claimed worst-case bounds agree.

### C. Deterministic test engineering — 20

- 7: focused tests cover empty/singleton, varied insertion order, exhaustion, repeated peek, negative and float priorities, equal priorities, and opaque payloads.
- 5: invalid inputs and no-partial-mutation behavior are tested distinctly.
- 6: an independent model drives at least 1,000 interleaved operations with fixed recorded seeds and compares outputs plus state observations throughout.
- 2: tests are isolated and independent of network, timing, execution order, and ambient randomness.

### D. Engineering note and performance evidence — 15

- 6: representation, invariant, exception safety, operation costs, and limitations are accurate and concise.
- 4: test oracle, seeds, commands, and actual results are reproducible.
- 5: benchmark has at least four geometric sizes, multiple trials, separate push/pop observations, raw summaries, environment context, and appropriately cautious interpretation.

### E. Comprehension — 20

- Q1, 3 points: exact acceptance/exception matrix and unchanged-state guarantee.
- Q2, 3 points: full ordering invariant, root consequence, and path-local restoration argument.
- Q3, 4 points: every insert/pop state and comparison is correct.
- Q4, 2 points: stable metadata and a test with mutually non-orderable payloads.
- Q5, 3 points: minimal counterexample, faulty trace, and violated invariant.
- Q6, 3 points: independent-oracle value, reproducibility, and stepwise observations.
- Q7, 2 points: distinguishes empirical consistency from proof and identifies realistic distortions.

### F. Reproducibility and submission hygiene — 5

- 3: standard-library-only commands run from a clean submission without manual edits; generated artifacts are excluded.
- 2: names, documentation, and failure reporting let another engineer reproduce the evidence.

## Independent check set

At minimum, the harness should independently exercise:

- fresh length/emptiness and empty exceptions;
- ascending, descending, alternating, duplicate, negative, integer, and finite-float priorities;
- multiple equal-priority instances of a class that raises if ordering is attempted;
- `peek` repeated before and after mutations;
- each invalid category on empty and nonempty queues, comparing a full subsequent pop sequence to a control queue;
- long fixed-seed interleavings against a separate list-based model; and
- adversarial down-heap cases where the right child is smaller than the left.

Inspect the production module for prohibited imports/calls and for sorting hidden behind helpers. Execute the learner suite twice in separate bounded processes. Execute the benchmark once with a bounded timeout; score the method and honesty of its report, not machine speed.

## Examiner answer guide

1. `3` and `3.5` are accepted. `True` and `"3"` raise `TypeError`; NaN and either infinity raise `ValueError`. Each rejection occurs before mutation, so length, minimum, stability order, and later pop sequence are unchanged.

2. A correct key is effectively `(priority, insertion_sequence)`. Every parent's key is no greater than either child's. Repeated parent links therefore show that the root is globally least. Insert can violate only its new ancestor path; replacing a popped root can violate only a descendant path, both of heap height `O(log n)`.

3. Insert: append `3` to get `[2, 5, 4, 9, 7, 8, 3]`; compare with parent `4` and swap to `[2, 5, 3, 9, 7, 8, 4]`; compare with `2` and stop. Pop: remove `2`, move final `4` to the root to get `[4, 5, 3, 9, 7, 8]`; compare children `5` and `3`, swap with `3`, producing `[3, 5, 4, 9, 7, 8]`; `4` has child `8`, so stop.

4. A unique, increasing insertion sequence breaks priority ties; comparisons use priority then sequence and never reach the payload. A strong test pushes two instances whose comparison methods raise, gives them priority `7`, and asserts FIFO pops without error.

5. One minimal example is `[1, 4, 2, 5]`. After popping `1`, replacement gives `[5, 4, 2]`. A left-only repair swaps to `[4, 5, 2]`, leaving the root greater than its right child. Equivalent four-entry valid heaps and traces earn full credit.

6. The model supplies an implementation-independent behavioral oracle over many state transitions. Fixed seeds make failures repeatable; retaining or reporting the trace makes them localizable. Compare return values/exceptions, `peek`, length, emptiness, and eventually the entire pop order after each applicable step, not merely the final size.

7. Timing trends can be consistent with the expected implementation and reveal gross regressions; they cannot prove a worst-case asymptotic bound. Interpreter warm-up, scheduling, CPU scaling, caches, allocation/garbage collection, timer resolution, and workload mix are valid distortions. Multiple sizes/trials and robust summaries help; source/invariant reasoning establishes the complexity claim.

If a response merely repeats a conclusion without the requested reasoning or conflicts with observed code, award no more than half credit for that question.

---

Rubric provenance: independently manager-authored for this bounded kickoff from catalog-level context only; official MIT rubric status: **not claimed**; remote content retrieved: no.  
Validation label: **EXAMINER_GUIDANCE_NOT_YET_APPLIED**.
