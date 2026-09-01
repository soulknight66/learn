# Study Task: From a Correct Algorithm to a Trustworthy ADT

## Scenario

An interval-merging routine is easy to get mostly right. Your job is to turn that routine into a small abstraction that a teammate could safely use and later change.

Implement `IntRangeSet`, a mutable set of Java `int` values represented externally as maximal closed intervals. For example, adding `[3, 5]` and then `[6, 8]` results in the single interval `[3, 8]`. Choose a package name that fits your learner workspace and use it consistently.

Use Java 17 or newer and an automated Java test framework available in your workspace. You may use only the standard library in production code.

## Required public API

Provide an immutable value type:

```java
public record IntRange(int lowerInclusive, int upperInclusive) {}
```

Provide a final ADT class with these operations:

```java
public final class IntRangeSet {
    public IntRangeSet();
    public void add(int lowerInclusive, int upperInclusive);
    public boolean contains(int value);
    public List<IntRange> intervals();
}
```

Write useful public specifications for the types and every public operation. The required behavior is:

- A new set is empty.
- `add(lower, upper)` adds every integer from `lower` through `upper`, inclusive.
- If `lower > upper`, `add` throws `IllegalArgumentException` and leaves the set unchanged.
- `contains(value)` reports membership without changing the set.
- `intervals()` returns all maximal intervals in increasing order. Returned intervals must be valid, disjoint, and non-adjacent.
- A caller must not be able to mutate the ADT through the list returned by `intervals()`, and a previously returned list must remain a snapshot even after later calls to `add` or `remove`.
- All operations must behave correctly at `Integer.MIN_VALUE` and `Integer.MAX_VALUE`; do not depend on overflowing arithmetic.

The public `IntRange` value type must reject construction with `lowerInclusive > upperInclusive` by throwing `IllegalArgumentException`.

## Phase 1: design before implementation

In `DESIGN.md`, state:

- the abstract value represented by `IntRangeSet`;
- your abstraction function from the chosen representation to that value;
- a representation invariant strong enough to explain the required output of `intervals()`;
- where and when you will check the invariant; and
- why clients cannot obtain a mutable alias to the representation.

Also document the complexity of each public operation in terms of the number of stored intervals. If a result depends on a specific representation or search strategy, say so.

## Phase 2: baseline implementation and evidence

Implement the constructor, `add`, `contains`, and `intervals`. Keep representation fields private. Add an internal invariant-checking mechanism that can be exercised during development or tests without widening the public API.

Write automated tests before considering the baseline finished. Your test suite must cover:

- empty, singleton, disjoint, overlapping, nested, and transitively merging additions;
- adjacency on either side and bridging two existing intervals;
- invalid ranges and the requirement that exceptional calls make no state change;
- both `int` extremes without overflow-dependent behavior;
- ordering, maximality, immutability, and snapshot behavior of `intervals()`; and
- sequences compared against a simple mathematical or standard-library model over a bounded integer domain.

The model-based check must use a fixed seed or an exhaustively enumerated bounded input space so a failure can be reproduced.

## Phase 3: bounded change request

After the baseline tests pass, extend the same class with:

```java
public void remove(int lowerInclusive, int upperInclusive);
```

`remove(lower, upper)` removes every value from `lower` through `upper`, inclusive. It may shorten an interval, delete one or more intervals, or split one interval into two. Removing values that are absent has no other effect. If `lower > upper`, it throws `IllegalArgumentException` and leaves the set unchanged. All earlier requirements, including correct handling of both `int` extremes, still apply.

Update specifications, design documentation, invariant checks, model-based evidence, and focused tests. Do not discard or weaken baseline tests.

In `CHANGELOG.md`, record:

- which files or abstractions changed;
- which existing design decisions made the change easier or harder; and
- one concrete further change your design could absorb, plus one that would likely require redesign.

## Phase 4: comprehension

Answer every prompt in `COMPREHENSION.md` in a separate file named `COMPREHENSION_RESPONSES.md`. Refer to your own specifications, representation, and tests where requested. Do not edit the prompt file.

## Deliverables

Submit only learner-authored work and generated build/test logs:

- production source for `IntRange` and `IntRangeSet`;
- automated tests, including the deterministic model-based test;
- `DESIGN.md`;
- `CHANGELOG.md`;
- `COMPREHENSION_RESPONSES.md`; and
- the reproducible command and captured result for a clean build and test run.

Do not submit copied course solutions, hidden tests, credentials, or another learner’s files. If your environment lacks a usable Java toolchain or test runner, record the exact blocker rather than inventing test results.

## Timebox

Aim for roughly 45 minutes on the initial contract and design, 2 hours on the baseline, 1.5 hours on tests and boundary hardening, 1.5 hours on the change request, and 45 minutes on review and comprehension. Stop at 8 hours and record any unfinished item plainly; do not broaden the API or build a user interface.
