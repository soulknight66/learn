# Independent Examiner Rubric — Trustworthy Range Set Kickoff

## Scope and evidence

This rubric evaluates only the manager-authored kickoff unit `kickoff_01_trustworthy_range_set`. It is not an evaluation of MIT 6.031 completion and does not rely on unavailable official readings or assignments.

Grade from learner artifacts and reproducible validator evidence. Do not accept a learner’s prose claim that code builds or tests pass. Run the clean build and tests in an isolated learner workspace with a bounded timeout, retain captured logs, and record the tested revision. Do not expose this rubric, examiner checks, or expected answers in learner-safe output.

## Result rule

Award 100 points total. `UNIT_READY` requires at least 80 points and all four gates:

1. production code and learner tests compile and execute;
2. essential add/remove membership semantics pass examiner checks, including both `int` extremes;
3. clients cannot mutate or observe later mutation through a value returned by `intervals()`; and
4. all named learner deliverables are present and attributable to the learner.

Otherwise record `REVISION_REQUIRED` with concrete evidence. This result applies to the kickoff unit only.

## Scored criteria

### 1. Public contract and design model — 15 points

- **6:** Specifications define inclusive endpoints, normal effects, invalid-range exceptions, no-state-change guarantees, ordering/maximality, and snapshot behavior without depending on implementation details.
- **5:** `DESIGN.md` gives a coherent abstract value, abstraction function, and representation invariant. The invariant requires valid ranges ordered by lower endpoint, with no overlap or adjacency; their union is the abstract integer set.
- **2:** Invariant-checking placement and use are explained and implemented without adding an inappropriate public mutator or representation accessor.
- **2:** Complexity statements are correct for the submitted representation and clearly separated from contractual guarantees.

### 2. Functional correctness — 25 points

- **10:** `add` correctly handles empty, contained, overlapping, adjacent, bridging, and transitive merges.
- **10:** `remove` correctly handles no-op, whole deletion, prefix/suffix shortening, splitting, and effects spanning multiple intervals.
- **3:** `contains` and `intervals` agree with the represented set; output is ordered, maximal, and stable.
- **2:** Both mutators reject `lower > upper` with `IllegalArgumentException` and preserve prior state.

Examiner checks should include endpoints at `Integer.MIN_VALUE` and `Integer.MAX_VALUE`, adjacency near those endpoints, adding the full domain, removing each extreme, splitting the full domain with an interior removal, and deterministic operation sequences compared with an independent bounded-domain set model.

### 3. Abstraction safety and defensive behavior — 15 points

- **5:** Representation state is private, the public `IntRange` is immutable, and invalid `IntRange` construction is rejected.
- **5:** `intervals()` cannot be structurally modified by a client and does not expose another mutable object reachable from the representation.
- **3:** A previously returned interval list remains unchanged after later ADT mutations; merely wrapping a live list is insufficient.
- **2:** Endpoint logic does not overflow. Full credit requires reasoning or code that avoids unsafe `upper + 1` and `lower - 1` operations at the respective extremes, or proves equivalent guards/widening.

### 4. Learner-authored test evidence — 20 points

- **7:** Focused tests cover all baseline categories named in the task, with assertions strong enough to detect wrong ordering or non-maximal output.
- **5:** Focused removal tests cover every structural case: no-op, deletion, left trim, right trim, split, and a removal spanning several intervals.
- **4:** Exception, state-preservation, immutability, snapshot, and extreme-endpoint behaviors are tested explicitly.
- **4:** A fixed-seed or exhaustive bounded-domain model test checks sequences containing both add and remove against an independent model and produces reproducible failures.

Tests receive credit for defect-detection value, not line count. A model that reuses the production interval-merging logic is not independent.

### 5. Understandability and change readiness — 10 points

- **4:** Names, decomposition, comments, and formatting make the implementation’s cases and invariant visible without narrating obvious syntax.
- **3:** `CHANGELOG.md` accurately connects the `remove` change to design decisions and to actual modified artifacts.
- **3:** The proposed easy future change is compatible with the current abstraction, while the redesign example identifies a genuine pressure on representation or contract.

### 6. Comprehension — 15 points

Award up to the points shown using the answer expectations below. Answers must connect general principles to the submitted work.

- **Q1 (2):** Gives three distinct, concrete links: bug safety to contracts/validation/boundaries/tests; understandability to specification, invariant, naming, or decomposition; and change readiness to abstraction and regression evidence.
- **Q2 (1):** Separates the valid-range precondition/accepted input domain, union postcondition, and invalid-range exception. Explains that unchanged state provides an atomic, predictable failure rather than partial mutation.
- **Q3 (2):** The invariant includes valid, sorted, pairwise disjoint, non-adjacent intervals. The abstraction function is the union of all inclusive integer ranges. Maximality follows from the no-overlap/no-adjacency clauses together with complete representation of that union.
- **Q4 (2):** Identifies overflow from adjacency comparisons such as `upper + 1` at `MAX_VALUE` and from split boundaries such as `lower - 1` at `MIN_VALUE` (or their symmetric forms). Acceptable avoidance uses explicit endpoint guards, safe comparison rearrangement, or widened arithmetic before calculation.
- **Q5 (2):** Explains both direct structural mutation and observation of later internal mutation. An unmodifiable live view blocks the former but not the latter; a snapshot must remain unchanged after subsequent ADT operations.
- **Q6 (1):** A focused test isolates a named boundary/case and localizes failure; an independent model checks broader sequences. Reproducibility comes from exhaustive enumeration, a fixed seed plus logged operations, or equivalent deterministic evidence.
- **Q7 (2):** Covers no effect, full interval deletion, left trim, right trim, split, and a range affecting multiple stored intervals; maps these honestly to tests.
- **Q8 (1):** Gives costs consistent with the implementation using `n` stored intervals and notes output is at least O(n). Does not falsely turn implementation performance into a public guarantee.
- **Q9 (2):** Uses actual change evidence. A strong answer names a stable abstraction/specification or centralized invariant as leverage and a concrete initial coupling/case structure/test weakness as friction, followed by a plausible revision.

## Caps and integrity handling

- Code that does not compile or whose tests cannot start is capped at 35.
- Missing `remove` implementation caps the score at 60.
- No automated learner tests caps the score at 65.
- Demonstrable representation exposure or snapshot failure caps the score at 70 and fails gate 3.
- Fabricated logs, copied solutions, hidden evaluation material, secrets, or another learner’s work must be recorded as an integrity/isolation failure and must not be promoted.

Preserve failing artifacts and logs. Examiner feedback may name violated public requirements and learner-visible counterexamples, but must not disclose hidden test source or this answer guide.
