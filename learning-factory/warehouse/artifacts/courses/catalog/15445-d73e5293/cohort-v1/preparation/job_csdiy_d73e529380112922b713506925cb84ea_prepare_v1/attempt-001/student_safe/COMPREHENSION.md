# Comprehension Prompts

Answer all prompts in `submission/COMPREHENSION_RESPONSES.md`. Use your own implementation, terminology, and evidence. A compact state table or diagram is welcome. Do not merely restate the task specification; explain why the behavior follows and point to relevant tests or code locations.

## 1. Trace replacement and dirtiness

Assume capacity two and a store initially containing pages `10: "A"`, `20: "B"`, and `30: "C"`. Trace this sequence:

1. fetch 10; unpin 10;
2. fetch 20; unpin 20;
3. fetch 10; write `"A2"` to 10; unpin 10;
4. fetch 30.

After each numbered step, show the resident pages, pin counts, dirty flags, and LRU-to-MRU order. State which store calls occur and what the store contains at the end. Relate the trace to one automated test.

## 2. Account for repeated pins

A client fetches the same page three times and then unpins it twice. Explain the state that must remain, why the page is or is not eligible for eviction, and how your API prevents pin-count underflow. Identify the invariant and test evidence involved.

## 3. Analyze a two-stage failure

With capacity one, make page 1 resident, dirty, and unpinned, then fetch nonresident page 2. Analyze both cases:

- the store write of page 1 fails;
- that write succeeds but the store read of page 2 fails.

For each case, describe the permitted store side effects, required in-memory state, returned error, and how a retry behaves. Explain how your implementation orders or stages work to produce that result.

## 4. Separate an invariant from a test

Choose one nontrivial pool invariant. Explain why checking it after one example is weaker than preserving it at every state transition. Describe a mixed-sequence test that could expose two distinct violations of that invariant.

## 5. Defend the ownership boundary

Explain how callers access page bytes in your API. Who owns the bytes, how long is access valid, and what happens when a frame is evicted or the pool is destroyed? Discuss one alternative (for example a copied value, RAII guard, callback, or raw reference) and the bug class it would make more or less likely.

## 6. Connect complexity to representation

Give the expected time complexity of lookup, resident fetch, recency update, victim choice, write, and unpin in your implementation. Connect each result to concrete state structures. Then identify one apparently convenient implementation choice that would violate the requested performance target.

## 7. Reason about a future concurrency extension

Concurrency is outside this unit. Nevertheless, choose one operation and describe a specific two-thread interleaving that could break pinning, uniqueness, dirtiness, or recency if the current code were used concurrently. Name the shared state involved and outline one possible synchronization boundary without implementing it.

## 8. State the evidence boundary

Explain why this microcomponent is relevant to a database course but is not evidence that you completed BusTub Project #1 or CMU 15-445. Name at least three additional provenance or validation facts that would be needed before a later job could honestly present an official assignment unit.
