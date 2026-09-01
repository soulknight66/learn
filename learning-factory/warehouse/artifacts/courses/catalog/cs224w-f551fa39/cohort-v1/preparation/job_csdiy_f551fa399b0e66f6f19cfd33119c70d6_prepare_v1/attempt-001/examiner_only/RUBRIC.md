# Independent Examiner Rubric — Graph Software Baseline

Keep this document examiner-only. Evaluate produced artifacts and observed behavior; do not accept a learner or agent's assertion of completion as evidence.

## Scope and decision

This rubric evaluates only `managed_unit_01_graph_software_baseline`. It does not evaluate or complete CS224w and must not be used to imply that the manager-authored task is an official Stanford assignment.

Score out of 100. A provisional unit pass requires all of the following:

- at least 75 points overall;
- at least 27/35 across Graph Model plus Graph Algorithms;
- at least 14/20 for Message Passing;
- the full suite passes in an examiner-controlled run;
- no hard-fail condition applies.

Only the worker-harness validator may record `SUCCEEDED`; the examiner's score is evidence supplied to that validator.

## Reproducible examination

From the submission root, run with network disabled:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Retain stdout, stderr, exit status, and the submitted files. Inspect rather than trust `EVIDENCE.md`. Supplement learner tests with examiner-owned cases that import only the public API and cover renamed nodes, generator inputs, reversed duplicates, invalid endpoints, isolated nodes, empty graphs, and mismatched matrix shapes. Do not place examiner tests or this rubric in a student-safe location.

## A. Graph model and contract — 20 points

- **5:** accepts finite iterable inputs (including one-shot generators), validates unique nonempty string nodes, and rejects undeclared endpoints and self-loops with useful `ValueError`s;
- **5:** collapses duplicate/reversed undirected edges and stores canonical endpoint order;
- **5:** `nodes`, `edges`, and `neighbors` have the exact tuple shapes and deterministic lexical ordering; unknown-node queries fail as specified;
- **5:** returned values do not expose mutable internals, and degree/neighborhood results remain consistent across boundary cases.

Expected independent checks include an empty graph, a declared isolated node, reversed duplicate pairs, a generator consumed exactly once, and attempted mutation of returned objects.

## B. Graph algorithms — 15 points

- **8:** BFS returns exact shortest unweighted distances for reachable nodes only, uses deterministic discovery order, handles isolated starts, and rejects an invalid start;
- **7:** connected components include every node exactly once, sort members and components as specified, and handle empty/disconnected graphs.

A scan or traversal that repeatedly sorts whole edge lists or otherwise misses the claimed `O(V + E)` traversal target loses complexity credit even if tiny fixtures pass.

## C. Mean message passing — 20 points

- **8:** correctly computes coordinate-wise neighbor means and the two affine contributions for nontrivial `d_in` and `d_out`;
- **4:** isolated nodes use a zero neighbor vector, so their result is `bias + w_self @ h_v`;
- **5:** validates exact feature-key coverage, common nonzero feature width, rectangular matrices, equal matrix shapes, and compatible bias/output width using `ValueError`;
- **3:** returns nodes in graph order without mutating graph, features, matrices, or bias, and documents a consistent empty-graph convention.

Use nonsymmetric matrices and unequal node features in examiner cases. Symmetric or all-one fixtures can conceal transposition, self/neighbor, and averaging errors.

## D. Tests and evidence — 20 points

- **8:** tests cover the required normal, disconnected, isolated, duplicate, and invalid cases with meaningful assertions;
- **5:** a hand-computed multidimensional oracle detects arithmetic or orientation errors;
- **4:** a genuine bijective-renaming test compares inverse-renamed outputs with an explicit floating-point tolerance;
- **3:** `EVIDENCE.md` truthfully records the command/result and maps contract areas to tests; the examiner can reproduce it.

Tests that merely duplicate implementation logic to calculate their expected values receive no oracle credit. Tests must be deterministic and require no network, clock, random seed, or external package.

## E. Software engineering and design note — 15 points

- **4:** small coherent modules, deliberate public exports, readable names and types, and no unnecessary framework or generated clutter;
- **4:** validation responsibilities, data invariants, deterministic-order decisions, and failure semantics are documented and match behavior;
- **4:** time/space analysis is correct for construction, storage, queries, traversals, and message passing;
- **3:** limitations, numerical assumptions, one alternative representation, its tradeoff, and a bounded next extension are candidly described.

## F. Comprehension — 10 points

Award one point per prompt when the response is correct, specific, and consistent with the code. Expected anchors:

1. Construction enforces node/edge invariants once; algorithms can then assume valid endpoints, simplicity, and stable adjacency.
2. Sets offer average constant-time membership/insertion but nondeterministic iteration unless sorted; sorted tuples give stable iteration and compact immutable exposure but cost sorting and slower membership.
3. An undirected duplicate must not inflate degree or weight that neighbor twice in the mean.
4. With zero neighbor mean, the neighbor matrix contributes zero and the output is `bias + w_self @ h_v`; an explicit test protects this convention.
5. With adjacency access, BFS is `O(V_r + E_r)` time on the reachable subgraph and `O(V_r)` auxiliary space, apart from stored graph adjacency.
6. Shared weights plus a commutative mean are independent of names/order. Node-index-specific weights, order-sensitive aggregation, incomplete key renaming, or using sorted position as meaning can break equivariance.
7. The graph owns topology invariants; the message function owns feature coverage and shape compatibility. The separation prevents every traversal from revalidating topology while keeping tensor errors local.
8. Credit depends on a concrete defect-to-test link; labels alone are insufficient.
9. Examples include scalar multisets `{0, 2}` and `{1, 1}`, both with mean 1, or `{1}` and `{1, 1}`. Mean can lose distribution and degree/multiplicity; sum plus degree or a richer injective aggregator is a bounded improvement.
10. Reasonable answers revisit adjacency storage, streaming/chunked APIs, sparse feature operations, or materialization boundaries and state a real cost such as slower access, complexity, or lost immutability.

## Hard fails and caps

Hard fail (no unit pass regardless of points): source is materially absent; the prescribed test command cannot import/run due to the submission; the implementation depends on network access or prohibited external packages; or evidence is fabricated/tampered.

Cap at 69: tests pass only after an examiner changes the public contract or implementation; core invalid inputs are silently accepted; or message passing works only for scalar/all-one cases.

Cap at 59: BFS or connected components is substantially missing, or message passing is a stub.

Minor formatting differences that do not alter the specified public types or behavior should not dominate the score. Record every deduction against observed files, command output, or an examiner-owned test result.
