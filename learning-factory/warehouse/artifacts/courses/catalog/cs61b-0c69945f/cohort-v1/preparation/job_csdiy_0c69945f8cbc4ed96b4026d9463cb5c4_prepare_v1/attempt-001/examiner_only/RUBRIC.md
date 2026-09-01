# Examiner-Only Rubric: Generic Ring Deque Kickoff

Do not distribute this file in the learner view. Score only durable evidence in the submitted files and the results of examiner-controlled compilation and execution. A learner's claim that a requirement works is not evidence by itself.

## Validation procedure

1. Confirm the five required learner deliverables are present and no compiled artifacts or downloaded course materials are included.
2. From a clean disposable output directory, compile the two Java sources using the submission's documented JDK command. Capture compiler output and exit status.
3. Run `kickoff.RingDequeTest` at least twice. Capture output, exit status, and whether the results are identical.
4. Inspect production imports, fields, and resize paths to confirm that behavior is implemented with one circular `Object[]`, not delegated to a collection.
5. Exercise the published API with examiner-controlled deterministic cases for wraparound, repeated grow/shrink cycles, exceptions, slot clearing, and iterator invalidation. Do not place these cases or their answers in the learner view.
6. Review `DESIGN.md`, `README.md`, and `COMPREHENSION_RESPONSES.md` against the submitted implementation rather than as free-standing prose.

Record tool version, commands, exit states, and the submission identity with the result. Only the worker-harness validator may promote the unit state.

## Critical gates and score caps

- A submission that does not compile receives at most **20/100**.
- A production implementation that delegates storage or deque operations to `Deque`, `ArrayDeque`, `LinkedList`, or another collection receives at most **25/100** and zero for Section B.
- Missing production source, missing test source, fabricated test output, nondeterministic external dependencies, or a test runner that performs no effective checks prevents a passing result.
- Any uncaught failure in the learner's test runner or an examiner-controlled required-contract test prevents a passing result, regardless of the numeric subtotal.
- A valid pass requires **80/100 or higher**, all critical gates satisfied, and complete required deliverables.
- Passing records completion only for `unit_kickoff_ring_deque_v1`; it must not mark the course complete.

## A. Public contract and observable behavior — 30 points

- **8 points:** Mixed `addFirst`/`addLast` histories preserve exact front-to-back order through wraparound and growth.
- **6 points:** `removeFirst`, `removeLast`, `get`, `size`, and `isEmpty` return correct results and maintain state through reuse after emptying.
- **6 points:** Null insertion, empty removal, and invalid indexing throw the exact specified exception types without mutation; the object remains usable.
- **5 points:** Iteration is front-to-back, complete, non-mutating, and independent for two iterators; exhausted `next()` and iterator `remove()` throw the required exceptions.
- **5 points:** Every successful structural change invalidates existing iterators, both `hasNext()` and `next()` detect it, and observation or a failed mutation does not invalidate an iterator.

Award a bullet only to the extent supported by execution evidence. Do not substitute the learner's randomized test for targeted examiner cases.

## B. Representation correctness and resource hygiene — 18 points

- **6 points:** Uses one circular `Object[]` with a coherent front/size (or equivalent) invariant; no ordinary end operation shifts all live elements.
- **5 points:** Starts at capacity 8, doubles only when needed, preserves logical order while growing, and applies the stated half-size shrink rule after removal.
- **3 points:** Never shrinks below 8 and remains correct over multiple boundary-crossing grow/shrink cycles.
- **2 points:** Every vacated live-element slot is nulled, including both removal directions and resize transitions; reflection or equivalent examiner inspection finds no stale reference outside the active region.
- **2 points:** Failed operations preserve all representation state, and structural-modification tracking changes exactly when specified.

The implementation need not use a particular field naming scheme. Judge the invariant and behavior, not resemblance to a reference layout.

## C. Complexity and algorithmic reasoning — 12 points

- **5 points:** `size`, `isEmpty`, and `get` are worst-case `O(1)`, and non-resizing end operations do constant work.
- **3 points:** Iterator creation is `O(1)`; a full traversal is `O(n)` time with `O(1)` auxiliary state.
- **4 points:** The design note gives a sound aggregate, accounting, or potential-style justification for amortized `O(1)` end operations. It must address why doubling provides enough cheap operations before another growth and why shrinking at one-quarter full avoids immediate grow/shrink oscillation.

## D. Deterministic testing evidence — 20 points

- **3 points:** The standalone runner executes effective checks without `-ea` or third-party libraries, reports failures clearly, and prints success only at the end.
- **5 points:** Targeted tests cover empty and index boundaries, mixed end operations, wraparound, growth, shrink-triggering histories, repeated empty/reuse, and state after exceptions.
- **4 points:** Targeted iterator tests cover order, exhaustion, unsupported removal, successful-mutation invalidation through both queried methods, and non-invalidating operations.
- **6 points:** A fixed seed is visible in code; at least 10,000 generated operations use a standard-library oracle only in tests; size, emptiness, and full sequence are compared after every step; seed and operation position appear in divergence diagnostics.
- **2 points:** Tests are repeatable, reasonably factored, and complete promptly with no time, network, environment-order, or sleep dependency.

Give no credit for a named test that cannot fail when production behavior is intentionally perturbed in the behavior it claims to check.

## E. Engineering communication and submission quality — 10 points

- **3 points:** Exact public API, sensible encapsulation, useful names, and focused comments; any unchecked operation is narrow and justified.
- **3 points:** `DESIGN.md` accurately records the invariant, all end/resize transitions, error and iterator policy, stale-reference handling, and two genuine alternatives with tradeoffs.
- **2 points:** `README.md` states a reasonable JDK version, layout, and machine-independent clean compile/run commands that the examiner reproduces.
- **2 points:** Submission is focused and clean: no binaries, absolute machine paths, copied solution material, unrelated framework, or generated dependency tree.

## F. Comprehension — 10 points

Evaluate accuracy, connection to the submitted implementation, and independent reasoning. Allocate **1.25 points per response**:

1. Identifies the active logical region, physical mapping, bounds on size/capacity, and unambiguous empty/full representation.
2. Correctly traces nonzero-front growth and front insertion and names the invariant facts that preserve order; an alternative valid normalization strategy is acceptable.
3. Explains Java's generic-array restriction and why the chosen `Object[]` boundary is safe given controlled writes and typed reads; any cast must be localized and justified.
4. Accounts for copies across operation sequences and explains the hysteresis created by shrinking at one-quarter full rather than merely repeating the target complexity.
5. Identifies unintended object retention as the nonfunctional defect and proposes evidence capable of observing backing-slot clearing rather than only abstract deque output.
6. Distinguishes targeted transition coverage from broad model comparison and identifies a real oracle limitation, such as representation, complexity, or shared semantic assumptions.
7. Matches actual modification tracking, distinguishes successful structural changes from observations/failures, and separates best-effort misuse detection from synchronization.
8. Identifies the ambiguity between stored `null` and absence/error under some API choices, proposes a coherent compatibility strategy, and names affected behavioral tests.

If a response describes an implementation different from the submitted code, award at most half credit for that response even if the abstract explanation is sound.

## Result record

The examiner should preserve:

- section scores and applied cap, if any;
- concrete failing contract cases;
- compile and test commands with exit status;
- validation label and validator identity; and
- the explicit result scope `unit_kickoff_ring_deque_v1 only`.

Do not infer course completion from this score.

---

Provenance: independently authored examiner guidance for the manager-authored kickoff, based only on the supplied CSDIY catalog snapshot and the public task contract; no official rubric, hidden grader, or external course content was retrieved.

Validation label: `EXAMINER_GUIDANCE_AWAITING_HARNESS_VALIDATION`
