# Study task: engineer a reliable connectivity component

## Assignment

Implement a fixed-universe union-find component in Java and use it in a small client that finds when an append-only connection stream first becomes fully connected. Treat the API and error behavior below as a contract. Your work must be self-contained and must use only the Java standard library.

Target Java 11 or later. Do not use a union-find implementation, graph library, test framework, annotation processor, or other external dependency. Write the test classes as executable programs whose `main` methods throw `AssertionError` on a failed check, so their result does not depend on Java's optional `assert` flag.

## Required layout

Create exactly these learner deliverables:

```text
submission/
├── src/main/java/study/unit1/UnionFind.java
├── src/main/java/study/unit1/ConnectivityMilestone.java
├── src/test/java/study/unit1/UnionFindTest.java
├── src/test/java/study/unit1/ConnectivityMilestoneTest.java
├── DESIGN.md
├── EVIDENCE.md
└── COMPREHENSION_RESPONSES.md
```

Generated class files and scratch build directories are not deliverables.

## Part 1: `UnionFind`

Create `public final class UnionFind` in package `study.unit1` with this public API:

```java
public UnionFind(int siteCount)
public int siteCount()
public int componentCount()
public int find(int site)
public boolean connected(int first, int second)
public boolean union(int first, int second)
public int componentSize(int site)
```

The contract is:

- Sites are the integers from `0` through `siteCount - 1`.
- A negative constructor argument throws `IllegalArgumentException`. Zero sites is valid.
- Any site argument outside the valid range throws `IndexOutOfBoundsException`, consistently across every applicable method.
- Initially each site is its own component, so `componentCount()` equals `siteCount` and each valid component has size one.
- `find(site)` returns a stable representative for the site's current component: two sites have equal returned representatives exactly when they are connected at that moment. A later successful union may change a representative.
- `connected(first, second)` reports whether both sites are currently in the same component.
- `union(first, second)` merges two distinct components and returns `true`; it changes nothing and returns `false` if they were already connected, including a self-union.
- `componentSize(site)` returns the number of sites currently connected to that site.
- `siteCount()` never changes. `componentCount()` decreases by exactly one for each successful union and never for an unsuccessful union.
- The class exposes no mutable internal array or collection and performs no input/output.
- The class is mutable and is not required to be thread-safe. State that limitation in its class documentation.

Use a parent forest, weighted union by component size, and path compression during `find`. Component-size metadata belongs to roots; do not scan all sites to implement a query. Aim for `O(n)` construction and space, constant-time count queries, and the standard inverse-Ackermann amortized bound for a sequence of union/find operations. Do not describe the amortized operations as strictly worst-case constant time.

## Part 2: `ConnectivityMilestone`

Create `public final class ConnectivityMilestone` in package `study.unit1`. It must provide this public operation:

```java
public static int eventsUntilFullyConnected(int siteCount, int[][] events)
```

Each row of `events`, in array order, represents one undirected connection event and must contain exactly two site indices. The result is the smallest prefix length `k`, from `0` through `events.length`, for which all sites are in at most one component after the first `k` events. Return `-1` if no such prefix exists. Thus an empty or one-site universe needs zero events, provided the complete input is valid. Duplicate connections and self-connections still occupy a position in the stream even though they do not merge components.

The client contract is:

- A negative `siteCount` throws `IllegalArgumentException`.
- A null `events` array, a null row, or a row whose length is not two throws `IllegalArgumentException`.
- An endpoint outside `0` through `siteCount - 1` throws `IndexOutOfBoundsException`.
- Validate the complete event matrix before returning a result. A malformed later row must not be hidden merely because an earlier prefix became connected.
- Do not mutate the outer array or any event row.
- Reuse `UnionFind`; do not implement a second connectivity engine.
- Preserve input order, and stop algorithmic processing once the first valid milestone is known.

The intended running time is `O(n + m α(n))` and auxiliary space is `O(n)` for `n` sites and `m` events, apart from the supplied matrix.

## Part 3: design note

Write `DESIGN.md` before or alongside the code. Keep it between 600 and 1,000 words and cover:

1. the public contract and why the exception choices protect state;
2. forest, root, size, and component-count invariants;
3. why `find` terminates and returns a component representative;
4. why both the already-connected and merging branches of `union` preserve the invariants;
5. how weighting and path compression affect performance, with careful amortized wording;
6. why the milestone client validates all input before processing it; and
7. encapsulation, mutability, thread-safety, and deletion limitations.

Use your own diagrams or pseudocode if helpful, but do not paste an implementation from an external source.

## Part 4: executable tests

Both required test classes must have a `public static void main(String[] args)` entry point and must fail with a nonzero process result when a check fails. Keep all test data deterministic. If you generate cases, use fixed seeds and report them.

Your tests must cover at least:

- zero-, one-, and multi-site construction;
- successful, duplicate, transitive, and self unions;
- component counts, component sizes, and representative equivalence;
- every invalid-input category for every relevant public operation;
- a sequence large enough to exercise weighting and repeated compression without reading private fields;
- milestone results at prefix zero, in the middle, at the end, and never;
- duplicate and self-connection events and a malformed event after an otherwise sufficient prefix;
- preservation of the event matrix;
- repeated calls on separate instances to catch accidental shared state; and
- seeded model-based comparisons against a simple independent oracle, such as label relabeling or graph reachability. The oracle must not duplicate the parent-forest implementation.

Tests should target observable behavior, not a particular root number or private parent-array shape when more than one valid shape is possible.

## Part 5: reproducible evidence

In `EVIDENCE.md`, record:

- the Java runtime and compiler versions;
- the exact compile and run commands used;
- the exit result of each test program;
- a short inventory mapping each contract category to one or more learner tests;
- every deterministic random seed and the number and size range of generated cases; and
- known limitations or an explicit statement that none beyond the assigned scope are known.

A minimal manual run can compile all four source files into a scratch output directory and invoke these two class names:

```text
study.unit1.UnionFindTest
study.unit1.ConnectivityMilestoneTest
```

Do not treat copied terminal text as sufficient proof: the validator will rerun the commands independently.

## Part 6: comprehension responses

Answer every prompt in `COMPREHENSION.md` in `submission/COMPREHENSION_RESPONSES.md`. Refer to your own implementation and tests where requested. Keep the responses concise but show reasoning; unexplained complexity labels or yes/no answers are insufficient.

## Suggested timebox

- Contract and invariants: 60–90 minutes
- Implementation: 90–150 minutes
- Focused and model-based tests: 120–180 minutes
- Design, evidence, and comprehension writing: 90–150 minutes
- Final clean-room compile and run: 30 minutes

Stop at ten hours and document any incomplete portion rather than quietly expanding the scope.
