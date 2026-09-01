# Independent Examiner Rubric

Access label: EXAMINER_ONLY · CONTAINS_SCORING_AND_REFERENCE_ANSWERS  
Validation label: PREPARED_FOR_INDEPENDENT_EXECUTION · NOT_YET_APPLIED

Do not copy this file, its point allocations, gates, or reference results into learner-visible artifacts.

## Decision rule

Score out of 100 using fresh execution evidence and source inspection. A unit passes only when:

- the total is at least 75;
- every critical gate below passes; and
- the validator has retained command results and relevant output artifacts.

A learner statement, screenshot, checked box, or bundled passing log is not independent evidence. Passing this rubric promotes only kickoff_01_reaching_definitions. It never promotes the full course.

## Critical gates

All gates are mandatory.

1. **Runnable submission:** The documented test command starts in a clean copy of the submission using Python 3.11 and no network.
2. **Semantic core:** At least one examiner-owned branch/loop case reaches the correct least fixed point, including kill-on-redefinition.
3. **Bounded behavior:** Tests and analyzer terminate on a finite cyclic fixture under the validator timeout.
4. **Safe failure:** A malformed or contract-invalid input exits 2 without changing a pre-existing output file.
5. **Required evidence present:** Source, tests, README.md, ANALYSIS.md, and COMPREHENSION_RESPONSES.md are present and inspectable.

If a gate fails, record the evidence, continue scoring for diagnostic value, and cap the decision at NOT_PASSED.

## Independent examination procedure

1. Work in an examiner-created temporary copy. Record the Python version and file inventory.
2. Run:

       python3 -m unittest discover -s tests -v

3. Run the command-line module on examiner-owned valid and invalid fixtures. Do not rely only on learner tests.
4. Run one valid fixture twice to distinct outputs and compare the bytes.
5. Seed the destination with known bytes, run an invalid fixture, and compare the destination afterward.
6. Import and call the analysis core without the command-line layer.
7. Inspect implementation and tests for hard-coded fixture answers, global mutable state, nondeterministic set serialization, shell/network use, and writes outside the requested destination.
8. Evaluate ANALYSIS.md and COMPREHENSION_RESPONSES.md against the reference reasoning below.

Use a bounded validator timeout. Treat timeout, crash, traceback on expected invalid input, or environmental mutation as captured failure evidence.

## Scoring

### A. Semantic correctness — 35 points

- **5 points — Model and validation:** Correctly constructs unique blocks/statements, validates all named edges and entry constraints, computes reachability, and excludes unreachable definitions from the domain.
- **7 points — Sequential transfer:** before is captured before each statement; a definition kills every prior fact for its variable and generates exactly itself; uses and null definitions do not change state.
- **8 points — Joins and branches:** Uses union for forward may-analysis and preserves all legitimate definitions at a join.
- **10 points — Cycles and least fixed point:** Starts from bottom, revisits affected successors, converges on examiner loop cases, and preserves the empty entry boundary.
- **5 points — Output semantics:** Reports exact reachable/unreachable, IN, OUT, and before maps with neither omitted reachable state nor leaked unreachable state.

Award no more than 17/35 if the implementation handles only acyclic graphs. Award no more than 20/35 if kill removes just one same-variable definition rather than all of them.

### B. Software-engineering quality — 25 points

- **5 points — Separation of concerns:** Analysis core is callable without files, JSON, process arguments, or printing; model and boundary responsibilities are clear.
- **6 points — Validation and diagnostics:** All specified malformed cases are rejected before analysis with exit 2, a stable concise stderr message, and no expected-error traceback.
- **5 points — Atomic safe output:** Writes a sibling temporary file and replaces only after complete successful serialization; cleans its temporary artifact on failure; preserves an existing destination on errors.
- **5 points — Determinism:** Stable queue/predecessor policy, explicit sorting, exact canonical JSON, and byte-identical repeated output.
- **4 points — Maintainability:** Clear names and small responsibilities, no hidden global state, no unnecessary dependency, and accurate README/ANALYSIS documentation.

Merely writing the destination directly earns 0 for atomic safe output even if ordinary successful tests pass.

### C. Verification quality — 20 points

- **10 points — Semantic suite:** Assertions with explicit oracles cover straight-line redefinition, diamond join, a revisited loop, empty blocks, and valid unreachable code.
- **5 points — Contract and failure suite:** Covers the listed structural errors and malformed JSON, including sentinel preservation and exit/diagnostic assertions.
- **3 points — Layer coverage:** At least one direct core test and one fresh-directory subprocess test; temporary resources are isolated and cleaned.
- **2 points — Repeatability:** Test order is irrelevant, no network or ambient-path assumption exists, and repeat serialization is compared byte for byte.

Tests that merely invoke code without asserting exact results receive at most 5/20.

### D. Explanation and comprehension — 20 points

- **6 points — Question 1:** Correct D and E fixed-point states and a credible multi-pass trace.
- **5 points — Question 2:** Correct facts by variable, concrete counterexample path, and sound may-versus-must distinction.
- **4 points — Question 3:** Finite-domain monotonic termination argument and a valid insertion bound, distinct from queue-pop complexity.
- **2 points — Question 4:** Correct schedule-independence conditions, performance observation, and determinism risk.
- **3 points — Question 5:** Correct exit/diagnostic/file contract plus an isolated automated-test design.

Responses must explain reasoning. Output copied from a run without an argument earns at most half credit for the corresponding item.

## Reference results for the comprehension graph

Fact lists below are lexicographically sorted.

### Question 1 reference

- IN[D] = {a1:x, a2:y, b1:x, c1:z, d1:y}
- OUT[D] = {a1:x, b1:x, c1:z, d1:y}
- IN[E] = {a1:x, b1:x, c1:z, d1:y}
- OUT[E] = {a1:x, b1:x, c1:z, d1:y}

A satisfactory trace observes that initial propagation through A reaches B and C, their outputs first meet at D, and D's output adds facts along the D-to-B back edge. B must then be processed again; its changed output can require D to be reconsidered. Exact pop order and number of pops may differ under a fair deterministic schedule.

Useful supporting fixed-point states:

- OUT[A] = {a1:x, a2:y}
- OUT[B] = {a2:y, b1:x, c1:z, d1:y}
- OUT[C] = {a1:x, a2:y, c1:z}

Do not require these supporting states if the requested states and revisit reasoning are correct.

### Question 2 reference

Immediately before e1:

- x may be defined by a1 or b1;
- y may be defined by d1; and
- z may be defined by c1.

The nonempty set for z does not prove initialization on every path. The path A to B to D to E reaches e1 without executing c1. Union answers whether a definition can reach; definite initialization normally needs a must property, using an intersection-style meet with a carefully chosen universal/top initialization and explicit boundary treatment. Accept an equivalent sound formulation, including a direct definitely-defined-variable analysis. Do not accept simply replacing union with intersection while retaining empty initialization everywhere; that collapses the analysis incorrectly.

### Question 3 reference

There are finitely many reachable blocks and definition facts. Each IN and OUT is a subset of the finite definition domain. Starting from empty sets, the union/transfer system is monotone, so facts only accumulate in fixed-point states until no state changes. A general valid upper bound on successful fact insertions across all IN sets is R times the number of definition facts; because the entry IN is fixed empty, (R - 1) times that number is a sharper bound under this contract. Either bound earns full credit when assumptions are stated.

This does not bound careless enqueue or pop operations: an implementation can enqueue unchanged successors repeatedly or keep duplicates in the queue. The worklist must enqueue based on state change and use a disciplined pending policy.

### Question 4 reference

FIFO and deterministic reverse-postorder priority compute the same least fixed point when both start at bottom, implement the same monotone equations and entry boundary, fairly process every dependency affected by a change, and run to stability. Reverse postorder commonly reduces revisits on mostly forward control flow but does not alter semantics. Hash-set iteration, unordered predecessor discovery, unstable equal-priority ties, or unsorted serialization are acceptable examples of accidental nondeterminism.

### Question 5 reference

The expected observable behavior is exit status 2, one stable concise diagnostic on stderr with no expected-input traceback, and the sentinel output remaining byte-for-byte unchanged. A good test creates an isolated temporary directory, writes the invalid input and sentinel destination there, invokes the module with explicit absolute paths and a controlled environment, captures status/stdout/stderr with a timeout, and rereads the exact destination bytes. Equivalent isolation that does not depend on the ambient working directory is acceptable.

## Examiner-owned semantic probes

Use at least one fixture not present verbatim in learner files. Useful mutations include:

- two branch arms defining the same variable, followed by a join and then a redefinition;
- a loop with two same-variable definitions that both reach the loop header but are both killed later;
- an unreachable strongly connected component containing otherwise plausible facts;
- a reachable empty self-loop;
- permuting input block order while preserving IDs and semantics; and
- multiple invalidities to check the implementation's documented deterministic error selection.

Expected results should be derived independently before executing the learner program. Store the fixture, expected canonical JSON, command result, and comparison result as validator evidence.

## Provenance and scope

This rubric was independently authored for the learning-factory kickoff specification, not extracted from PKU materials. Catalog basis: CSDIY commit adce8e13789dc16aa6d1fbe163e9541736defae4, source content SHA-256 5c26f67523735d0b6f94bd684d945d637207e18ad98e7ca8268df6c70bc434fd. No remote link was fetched. Applying this rubric can validate only this eight-hour manager-authored unit.
