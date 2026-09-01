# Study task: executable graph invariants

## Mission

Build a small Python component that returns a reproducible topological order for a directed graph, reports cycles through a documented exception, and is supported by mathematical reasoning and serious automated tests.

Stay within a 4–6 hour timebox. Prefer a narrow, well-supported implementation over optional features.

## Deliverables

Create these files:

```text
submission/
├── toposort.py
├── test_toposort.py
├── ENGINEERING_NOTE.md
└── COMPREHENSION_RESPONSES.md
```

Use Python 3.11 and only the standard library. Tests must run with:

```bash
python3 -m unittest discover -s submission -p 'test*.py' -v
```

## Required public contract

In `submission/toposort.py`, expose:

```python
class CycleError(ValueError):
    nodes: tuple[str, ...]

def topological_sort(graph: Mapping[str, Iterable[str]]) -> list[str]:
    ...
```

The contract is:

- `graph[u]` enumerates directed edges `u -> v`.
- The vertex set is every mapping key plus every vertex mentioned in an adjacency iterable. A vertex therefore need not have its own key.
- All vertex identifiers must be strings. An adjacency value that is itself a `str` or `bytes`, a non-iterable adjacency value, or any non-string key or neighbor is malformed input and must cause `TypeError`.
- Adjacency iterables are finite and may be one-shot iterators. Do not assume that they can be traversed twice.
- Repeated occurrences of the same edge represent one graph edge. They must not change the result or create a false cycle.
- Do not mutate the input mapping or any caller-owned adjacency collection.
- For an acyclic graph, return every vertex exactly once. Each edge's source must precede its target.
- Make the result reproducible: whenever several vertices are currently eligible, choose the lexicographically smallest string according to Python's normal string ordering.
- The empty graph returns an empty list.
- If the graph contains a cycle, raise `CycleError`. Its `nodes` attribute must be a sorted tuple containing all vertices left unresolved when progress becomes impossible. The exception message must be useful to a human but has no prescribed wording.
- Unexpected exceptions raised from a caller's custom mapping or iterator are outside this unit's recovery contract; do not disguise them as cycle errors.

Document the public names and the major representation choices. Do not add filesystem, network, global-cache, or command-line side effects to the module.

## Work sequence

### 1. Specify before coding — about 30 minutes

In rough notes, identify the accepted input domain, postcondition, reproducibility rule, and each failure path. List the mutable state your algorithm will maintain and what each part is intended to mean.

### 2. Implement — about 60–90 minutes

Implement the contract with an asymptotic target of `O((V + E) log V)` time and `O(V + E)` additional space, where `E` counts distinct edges. Keep normalization, scheduling, and failure reporting reviewable.

### 3. Build evidence through tests — about 60–90 minutes

Write deterministic `unittest` coverage. Include examples and broader properties. At minimum, exercise:

- empty, isolated, disconnected, chain, and branching graphs;
- vertices that appear only as neighbors;
- duplicate edges;
- multiple simultaneously eligible vertices and reordered input mappings;
- a self-loop and a longer cycle;
- each malformed-input category in the contract;
- preservation of caller-owned containers;
- a deterministic family of generated acyclic graphs checked by an independent order-validity helper.

Include at least one metamorphic test: transform an input in a way that should preserve a stated property, and check that property. Seed any pseudo-random generator explicitly so failures are reproducible.

### 4. Write the engineering note — about 60 minutes

In no more than 1,200 words, write `submission/ENGINEERING_NOTE.md` with these headings:

1. **Contract and representation** — summarize boundary decisions and how one-shot iterables and duplicate edges are handled.
2. **Invariant and initialization** — state a precise loop invariant and show why it holds before the first scheduling step.
3. **Preservation, progress, and termination** — argue why one iteration preserves the invariant, what strictly progresses, and why the algorithm terminates.
4. **Success and cycle cases** — connect the exit states to the public postcondition and to the contents of `CycleError.nodes`.
5. **Complexity** — justify bounds in terms of vertices and distinct edges; include normalization costs.
6. **Test strategy and limitations** — distinguish example, property-oriented, and metamorphic evidence, then name at least one risk outside the stated contract.

Your note must describe the code you actually submit. A generic textbook proof is not sufficient.

### 5. Respond and review — about 30–45 minutes

Put numbered responses to every prompt from `COMPREHENSION.md` in `submission/COMPREHENSION_RESPONSES.md`. Then run the test command from the repository root, review the diff, and check that no generated caches or unrelated files are included.

## Submission boundary

Do not fetch course websites, recordings, assignments, packages, or solution material for this unit. The supplied task is complete as written. Do not claim completion of the cataloged course in your note; this work covers only the kickoff.
