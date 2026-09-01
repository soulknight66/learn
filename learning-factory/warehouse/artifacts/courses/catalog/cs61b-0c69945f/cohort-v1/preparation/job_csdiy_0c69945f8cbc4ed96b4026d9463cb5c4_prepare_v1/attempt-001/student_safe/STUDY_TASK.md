# Study Task: Engineer a Generic Ring Deque

Implement a production-quality generic deque backed by a resizable circular array. Your work must be self-contained and use only the Java standard library.

## Deliverables

Create exactly these learner deliverables relative to your submission root:

```text
src/main/java/kickoff/RingDeque.java
src/test/java/kickoff/RingDequeTest.java
DESIGN.md
README.md
COMPREHENSION_RESPONSES.md
```

Do not submit compiled `.class` files, an `out/` directory, downloaded dependencies, copied solutions, or external course material.

## Required public API

`RingDeque.java` must declare `package kickoff;` and this public type:

```java
public final class RingDeque<E> implements Iterable<E>
```

Declare exactly the following public operations. Methods inherited from Java platform types or supplied by their default implementations do not count as additional declarations:

```java
public RingDeque()
public int size()
public boolean isEmpty()
public void addFirst(E item)
public void addLast(E item)
public E get(int index)
public E removeFirst()
public E removeLast()
public java.util.Iterator<E> iterator()
```

You may add private fields and private methods. Do not add another public constructor or public method.

## Behavioral contract

The logical deque is an ordered sequence from front to back.

- A new deque is empty, has size zero, and iterates over no elements.
- `addFirst(item)` inserts at logical index `0`.
- `addLast(item)` inserts after the current last element.
- `get(index)` returns the element at the zero-based logical index without changing the deque.
- `removeFirst()` and `removeLast()` remove and return the corresponding element.
- `size()` and `isEmpty()` must always agree.
- `null` elements are not supported. Either add operation given `null` must throw `NullPointerException` and leave the deque unchanged.
- Removing from an empty deque must throw `NoSuchElementException` and leave it unchanged.
- `get(index)` must throw `IndexOutOfBoundsException` when `index < 0` or `index >= size()`, leaving the deque unchanged.
- After any specified exception, the same deque must remain usable and satisfy its invariant.

An iterator must visit the elements once in front-to-back order without changing the deque. An exhausted iterator's `next()` must throw `NoSuchElementException`, and its `remove()` must throw `UnsupportedOperationException`.

The iterator must also be fail-fast within a single thread. After an iterator is created, any successful add or remove on that deque invalidates it; its subsequent `hasNext()` or `next()` must throw `ConcurrentModificationException`. Operations that merely observe state or fail before changing state do not invalidate it. This behavior detects misuse but is not a thread-safety guarantee.

## Representation and performance constraints

- Store elements in one resizable circular `Object[]` data array. The initial and minimum capacity is `8`.
- Do not use `java.util.Deque`, `ArrayDeque`, `LinkedList`, or any other collection as the production backing store. Those types may be used only in test code.
- When an insertion would exceed the current capacity, double the capacity while preserving logical order.
- After a successful removal, if capacity is at least `16` and size is at most one quarter of capacity, halve the capacity. Never shrink below `8`.
- Clear a removed element's obsolete array slot so the deque does not retain stale references.
- `size()`, `isEmpty()`, and `get(index)` must take worst-case `O(1)` time.
- Adds and removals at either end must take amortized `O(1)` time. Resizing may take `O(n)` time.
- Creating an iterator must take `O(1)` time; traversing all elements must take `O(n)` time and `O(1)` auxiliary space.

The implementation need not be thread-safe. Avoid network access, current-time assumptions, sleeps, and nondeterministic behavior.

## Deterministic test program

`RingDequeTest` must be a standalone test runner with a `public static void main(String[] args)`. It must require no third-party testing framework, print a clear success summary only after all checks pass, and terminate with a nonzero result or an uncaught assertion on failure. Do not rely solely on Java's optional `assert` keyword; checks must still execute when `-ea` is absent.

At minimum, your tests must cover:

- empty-state behavior and every specified exception;
- order under mixed additions and removals at both ends;
- index boundaries and state preservation after failed operations;
- wraparound, growth, shrink-triggering histories, and reuse after becoming empty;
- iterator order, exhaustion, unsupported removal, invalidation, and non-invalidating observations; and
- a fixed-seed differential test of at least 10,000 operations against a trusted standard-library oracle used only in test code.

For the differential test, record the seed in code and include it in failure messages. Compare size, emptiness, and the full front-to-back sequence after every generated operation so that the first divergence is reproducible. Keep targeted tests as well: randomized testing does not replace explicit boundary checks.

## Design and usage notes

In `DESIGN.md`, use your own words to document:

1. the representation invariant, including how logical indices correspond to physical locations;
2. how each end operation and each resize preserves that invariant;
3. a concise amortized analysis of the resize policy;
4. how exception paths, iterator invalidation, and stale-reference clearing are handled; and
5. two alternatives you considered and why you did not choose them for this contract.

In `README.md`, state the required Java version, show clean commands that compile into a disposable `out/` directory and run the test program, and summarize the file layout. Verify that these commands work in a clean checkout. One valid command shape is:

```bash
mkdir -p out
javac -d out src/main/java/kickoff/RingDeque.java src/test/java/kickoff/RingDequeTest.java
java -cp out kickoff.RingDequeTest
```

If you use a different standard JDK command sequence, document it precisely. Do not require an IDE or a machine-specific absolute path.

Finally, answer every prompt in `COMPREHENSION.md` in `COMPREHENSION_RESPONSES.md`. The responses must describe your submitted implementation, not a hypothetical one.

## Final self-check

Before submission, start from no `out/` directory, run the commands in your README twice, and confirm identical successful results. Check that all required source and documentation files are present and that no generated binaries or external materials are included.

---

Provenance: course-manager-authored from the supplied CSDIY CS61B catalog snapshot at source commit `adce8e13789dc16aa6d1fbe163e9541736defae4`; no official assignment body or external solution was used.

Validation label: `PREPARED_AWAITING_HARNESS_VALIDATION`
