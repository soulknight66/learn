<!--
provenance: Manager-authored from catalog-level context for this job; not an official MIT assignment. No remote course content was retrieved.
validation_label: PREPARED_NOT_VALIDATED
-->

# Study task: engineer a reliable min-priority queue

## Goal

Build a small Python component whose behavior, algorithmic costs, tests, and limitations are clear enough for independent review. Use a binary min-heap for the production implementation. The task is self-contained and uses only the Python standard library.

## Required submission

Submit these five files:

- `min_priority_queue.py` — production implementation;
- `test_min_priority_queue.py` — deterministic `unittest` suite;
- `benchmark_priority_queue.py` — bounded, reproducible measurement script;
- `ENGINEERING_NOTE.md` — design and evidence report; and
- `COMPREHENSION_RESPONSES.md` — your numbered answers to `COMPREHENSION.md`.

Do not include generated caches, copied course material, credentials, or external answer text.

## Public contract

Implement a class named `MinPriorityQueue` with no required constructor arguments and these operations:

```python
push(item: object, priority: int | float) -> None
peek() -> tuple[object, int | float]
pop() -> tuple[object, int | float]
__len__() -> int
is_empty() -> bool
```

The returned tuple order is always `(item, priority)`.

The following behavior is part of the contract:

- Smaller numeric priorities are returned first.
- Equal priorities are stable: items with the same priority are returned in insertion order.
- Payload objects do not need to be comparable to one another.
- Priorities may be finite `int` or `float` values, including negative values. Reject `bool` and every other type with `TypeError`. Reject positive or negative infinity and NaN with `ValueError`.
- A rejected `push` must leave all previously observable queue state unchanged.
- `peek` and `pop` on an empty queue raise `IndexError` and leave the queue empty.
- `peek` does not mutate observable state.

Thread safety, persistence, priority updates, item deletion, iteration, serialization, and merging queues are outside this unit's scope. Do not add those features at the expense of the specified contract.

## Algorithm and cost constraints

Maintain a binary min-heap in the production implementation. Ordering must account for priority and stable insertion order without comparing payloads.

- `push` and `pop`: worst-case `O(log n)` time;
- `peek`, `len`, and `is_empty`: `O(1)` time; and
- queue storage: `O(n)` space.

Do not use `heapq`, a third-party priority-queue implementation, a globally sorted backing collection, or `sort`/`sorted` to implement a production queue operation. A deliberately simple independent oracle in tests may sort its own model data.

Keep representation details private. Favor readable index calculations and small helpers over clever compression. Public behavior, not a particular helper layout, is fixed.

## Test work

Use `unittest` and make the suite runnable with:

```text
python3 -m unittest -v test_min_priority_queue.py
```

Cover, at minimum:

- fresh and exhausted queues;
- one item and several insertion orders;
- negative, integer, and finite floating-point priorities;
- repeated equal priorities and non-comparable payload objects;
- repeated `peek` calls;
- each invalid-priority category and the no-partial-mutation guarantee;
- interleaved pushes and pops; and
- a deterministic model-based trace of at least 1,000 operations using recorded fixed seed values.

The model must be simpler than, and independent of, the heap algorithm. Compare public results and length/emptiness observations throughout the trace, not just at the end. Tests must not depend on elapsed-time thresholds, network access, test order, or unrecorded randomness.

## Performance observation

In `benchmark_priority_queue.py`, build a deterministic workload over at least four geometrically increasing input sizes. Measure push and pop phases separately, use multiple trials, and report the size, trial count, and a robust summary such as the median. Keep the largest workload bounded so the script is suitable for routine review.

Record the actual command, Python version, relevant machine context available without privileged inspection, raw summaries, and your interpretation in `ENGINEERING_NOTE.md`. Timing trends may be consistent with an expected cost; they do not prove an asymptotic bound. Do not use a pass/fail timing threshold.

## Engineering note

Keep `ENGINEERING_NOTE.md` concise and include:

1. the representation and invariant in your own words;
2. how stable ties avoid ordering payloads;
3. validation and exception-safety decisions;
4. a per-operation time and space analysis;
5. the deterministic test strategy, oracle, and seed values;
6. benchmark method, raw summaries, and cautious interpretation; and
7. known limitations or unresolved risks.

Commands and results must reflect an actual run. If something cannot run, preserve the failure output and explain the blocker instead of inventing a result.

## Suggested work sequence

1. Restate the contract as test cases before implementing.
2. Implement the smallest correct heap and run focused tests frequently.
3. Add invalid-input and state-preservation tests.
4. Add the deterministic reference-model trace.
5. Review the implementation for representation leaks and accidental payload comparisons.
6. Run the bounded benchmark and write the engineering note.
7. Complete the comprehension responses, then run the full suite once more.

Submission is evidence awaiting independent validation. It is not evidence that the wider course is complete.

---

Preparation provenance: manager-authored for this kickoff from catalog-level context only; official MIT assignment status: **not claimed**; remote content retrieved: no.  
Validation label: **PREPARED_NOT_VALIDATED**.
