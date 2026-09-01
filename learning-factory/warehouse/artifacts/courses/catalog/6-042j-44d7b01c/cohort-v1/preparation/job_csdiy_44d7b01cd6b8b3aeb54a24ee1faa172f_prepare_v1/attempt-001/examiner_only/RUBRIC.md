# Independent examiner rubric — kickoff unit 01

## Scope and authority

This rubric evaluates only **Executable Graph Invariants: A Deterministic Topological Sort**. It cannot establish completion of MIT 6.042J or any broader course. Learner prose claiming success is not evidence. Award a successful unit result only after inspecting the submitted artifacts and running harness-controlled checks in an isolated Python 3.11 environment.

Expected files:

- `submission/toposort.py`
- `submission/test_toposort.py`
- `submission/ENGINEERING_NOTE.md`
- `submission/COMPREHENSION_RESPONSES.md`

Run the learner suite from the attempt root:

```bash
python3 -m unittest discover -s submission -p 'test*.py' -v
```

Run independent tests separately. Do not edit the learner's submission to make it pass. Capture command, exit status, stdout/stderr, and relevant artifact digests as validation evidence.

## Gates

The submission is not passing, regardless of point total, if any of these is true:

1. `toposort.py` cannot be imported, the required public function is absent, or independent tests cannot call it.
2. The learner test suite is absent, discovers zero tests, or does not pass.
3. The implementation cannot return a valid deterministic order for ordinary acyclic graphs or cannot report an ordinary directed cycle via `CycleError`.
4. The engineering note omits a reviewable invariant argument or describes an algorithm materially different from the submitted code.
5. Any required response file is absent.

Use 70/100 as the numeric passing threshold after all gates pass.

## Scoring (100 points)

### A. Implementation and public contract — 40 points

- **10 points — graph normalization:** Forms the vertex union correctly, consumes finite one-shot adjacency iterables safely, and gives duplicate edges set semantics.
- **10 points — acyclic correctness:** Returns each vertex exactly once and respects every distinct edge, including target-only, isolated, disconnected, and empty cases.
- **7 points — deterministic scheduling:** Always selects the Python-lexicographically smallest currently eligible vertex; result does not depend on mapping insertion order, set iteration order, or adjacency order.
- **7 points — failure behavior:** Raises the required `CycleError` for self-loops and multi-vertex cycles; `nodes` is a sorted tuple of exactly the vertices unresolved at the stuck state; message is intelligible.
- **4 points — malformed input and ownership:** Raises `TypeError` for all specified malformed categories without mislabeling them as cycles and does not mutate caller-owned containers.
- **2 points — implementation hygiene:** No prohibited external dependency or unrelated side effect; public names and non-obvious representation choices are documented.

Independent checks should include, at minimum: an empty mapping; neighbor-only vertices; duplicate edges; two disconnected components; several initially eligible vertices; Unicode/string-order cases; reordered dictionaries and adjacencies; generator adjacencies that fail if traversed a second time; self-loop; a cycle with acyclic upstream and downstream vertices; malformed key, neighbor, string adjacency, bytes adjacency, and non-iterable adjacency; and before/after equality checks for mutable inputs.

For a cycle with acyclic vertices feeding into it and vertices reachable from it, the expected unresolved set is all vertices not emitted when the eligible frontier empties, not merely one discovered cycle. Independent order checks must derive validity from the input relation rather than compare only with a single canned ordering.

### B. Learner-owned tests — 20 points

- **6 points — boundary and contract coverage:** Meaningfully exercises all categories enumerated in the study task, with assertions on behavior rather than execution alone.
- **5 points — independent properties:** Includes an order-validity helper that checks vertex coverage, uniqueness, and every edge relation without reusing the production scheduling logic.
- **4 points — generated evidence:** Tests a nontrivial deterministic family of DAGs with an explicit seed or enumeration and produces reproducible failures.
- **3 points — metamorphic evidence:** Clearly identifies and tests a valid transformation such as reordering input presentation or duplicating an existing edge, and asserts the appropriate preserved property.
- **2 points — test quality:** Tests are readable, isolated, reasonably sized, and sensitive to plausible defects. Excessive dependence on one expected list earns no credit here.

### C. Engineering note and proof — 20 points

- **4 points — contract/representation alignment:** Accurately describes actual code, normalization, one-shot iterables, duplicate edges, and public failures.
- **7 points — invariant:** Gives a precise relationship among emitted vertices, remaining vertices, the eligible frontier, and maintained predecessor counts; establishes initialization and preservation without circularly assuming correctness.
- **4 points — progress and exit reasoning:** Identifies a strictly decreasing/increasing finite measure, justifies termination, and distinguishes successful exhaustion from a cycle-stuck state.
- **3 points — complexity:** Derives the target `O((V + E) log V)` upper bound and `O(V + E)` space in terms of distinct edges, accounting for normalization and frontier operations. A tighter supported bound is acceptable.
- **2 points — evidence limits:** Explains what each test style contributes and candidly identifies at least one risk beyond the contract.

Do not award invariant points for merely saying “the graph remains valid” or restating the postcondition. A satisfactory argument makes the maintained counters/frontier correspond to the un-emitted subproblem and uses that correspondence in the cycle conclusion.

### D. Comprehension responses — 15 points

Score the eight numbered responses for accurate causal reasoning, not keyword presence.

- **2 points each for prompts 1–7, capped at 14:** Expected concepts are, respectively: union of keys and neighbors; deduplication before predecessor accounting; canonical tie-breaking and reproducible artifacts; an initialized and preserved state relation; successful exhaustion versus unresolved cyclic dependency; distinct evidence supplied by example/property/metamorphic tests; and one-shot consumption versus propagation of caller-iterator behavior plus an API-boundary tradeoff.
- **1 point for prompt 8:** Distinguishes unchanged semantic correctness from redundant/optional presentation ordering, and assesses the possible added sorting work against actual requirements and maintainability.

Responses that conflict with the submitted implementation lose the associated point even if they describe a valid different design.

### E. Software-engineering quality — 5 points

- **2 points — reviewability:** Clear names, focused functions, and comments/docstrings that explain decisions rather than syntax.
- **2 points — bounded design:** No speculative framework, network access, filesystem behavior, global mutable cache, or unrelated feature expansion.
- **1 point — submission discipline:** Required files only in the relevant area, no cache/build debris, and no assertion of whole-course completion.

## Score record

Record category subtotals, gate results, test evidence location, and a concise defect note for every deduction. The final label must explicitly read either `KICKOFF_UNIT_SUCCEEDED` or `KICKOFF_UNIT_NOT_SUCCEEDED`; never shorten it to a course-level completion claim.
