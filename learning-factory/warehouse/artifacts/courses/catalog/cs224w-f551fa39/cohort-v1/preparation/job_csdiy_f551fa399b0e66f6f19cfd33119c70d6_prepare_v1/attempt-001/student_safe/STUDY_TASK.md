# Study Task: A Reliable Graph Core and Message-Passing Step

## Goal and timebox

Build a small, production-minded Python package that turns a precise graph contract into tested behavior. Timebox the work to about 8 hours. Prefer a narrow, well-explained implementation over extra features.

Use only the Python standard library. Do not use NetworkX, NumPy, PyTorch, graph-learning libraries, network access, or external datasets.

## Required layout

Submit at least:

```text
src/graph_baseline/__init__.py
src/graph_baseline/model.py
src/graph_baseline/algorithms.py
src/graph_baseline/message_passing.py
tests/
DESIGN.md
EVIDENCE.md
COMPREHENSION_RESPONSES.md
```

Expose the specified public objects from `graph_baseline`. Keep test fixtures small and authored in the test files.

## Part 1: Define and enforce the graph contract

Implement an immutable-by-interface `Graph` representing a finite, simple, undirected graph.

The constructor or a documented factory must accept an iterable of node identifiers and an iterable of endpoint pairs. Enforce this contract:

- a node identifier is a nonempty `str`;
- identifiers are unique;
- every edge endpoint names a declared node;
- self-loops are invalid;
- repeated edges, including reversed repeats such as `(a, b)` and `(b, a)`, describe one edge rather than multiple edges;
- public node, edge, and neighbor iteration is lexicographically deterministic;
- callers cannot mutate the graph through returned collections;
- invalid input raises `ValueError` with a useful message.

Provide these operations, using the names and return shapes below:

```python
Graph.nodes() -> tuple[str, ...]
Graph.edges() -> tuple[tuple[str, str], ...]
Graph.neighbors(node: str) -> tuple[str, ...]
Graph.degree(node: str) -> int
```

Store every returned undirected edge with its smaller endpoint first, and return edges in lexicographic order. A lookup for an undeclared node must raise `ValueError`.

## Part 2: Implement deterministic graph algorithms

Implement:

```python
bfs_distances(graph: Graph, start: str) -> dict[str, int]
connected_components(graph: Graph) -> tuple[tuple[str, ...], ...]
```

`bfs_distances` returns distances only for nodes reachable from `start`; its dictionary insertion order must follow deterministic BFS discovery order. An invalid start node raises `ValueError`.

Each connected component must list its members lexicographically. Return components ordered by their smallest member. Empty graphs therefore have no components.

## Part 3: Implement one message-passing layer

Implement this pure-Python operation:

```python
mean_message_step(
    graph: Graph,
    features: dict[str, tuple[float, ...]],
    w_self: tuple[tuple[float, ...], ...],
    w_neighbor: tuple[tuple[float, ...], ...],
    bias: tuple[float, ...],
) -> dict[str, tuple[float, ...]]
```

For node `v`, let `h_v` be its input feature vector. Let `m_v` be the coordinate-wise mean of its neighbors' vectors. For an isolated node, `m_v` is the all-zero vector of the input dimension. Compute

```text
output_v = bias + w_self @ h_v + w_neighbor @ m_v
```

There is no activation function. Both weight matrices have `d_out` rows and `d_in` columns; `bias` has length `d_out`. Requirements:

- `features` has exactly one vector for every declared node and no other keys;
- all feature vectors have one common, nonzero input dimension when the graph is nonempty;
- both matrices and the bias have consistent, nonzero output dimensions;
- ragged or incompatible shapes raise `ValueError`;
- the result iterates in `Graph.nodes()` order;
- the function does not mutate the graph or any caller-owned feature or parameter collection.

Document and test your chosen behavior for an empty graph. Keep that behavior internally consistent rather than adding unrelated tensor abstractions.

## Part 4: Build evidence, not just examples

Use `unittest`. Your suite must exercise:

- canonical edge storage and deterministic iteration;
- a path or branching graph with known BFS distances;
- disconnected components and an isolated node;
- duplicate and reversed edge input;
- each invalid graph condition in the contract;
- missing, extra, ragged, and dimension-mismatched feature/parameter inputs;
- a hand-calculated nontrivial message-passing case;
- isolated-node message passing;
- absence of caller-input mutation;
- permutation equivariance under at least one nontrivial bijective renaming of node identifiers.

The permutation test should rename graph nodes and feature keys together, apply the same shared parameters, undo the output renaming, and compare with the original result using an explicit floating-point tolerance.

Run the complete suite offline with:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

In `EVIDENCE.md`, record the command, environment assumptions, resulting summary, and a compact table connecting each contract area to one or more tests. Do not claim a passing run that you did not observe.

## Part 5: Explain the engineering

In `DESIGN.md`, record:

- the public contract and internal representation;
- where validation occurs and why;
- deterministic-ordering choices;
- construction, storage, query, BFS, components, and message-step complexity;
- at least one alternative representation and its tradeoffs;
- numerical assumptions and known limitations;
- one sensible next extension that is explicitly outside this unit.

Then answer the prompts in `COMPREHENSION.md` in `COMPREHENSION_RESPONSES.md`. Cite relevant functions or tests where useful. Keep the implementation and explanations your own; external course material is neither required nor assumed available.

## Stop boundary

Stop after the required package, tests, design note, evidence record, and comprehension responses work together. Do not add training loops, datasets, automatic differentiation, GPU support, or a graph framework. Those belong to later units.
