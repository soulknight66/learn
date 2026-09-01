# Comprehension Prompts

Answer these questions in COMPREHENSION_ANSWERS.md after completing the implementation. Explain reasoning in your own words. Do not paste implementation code except for a very small fragment when essential to an explanation.

## 1. State invariants

State the relationships among fixed capacity, buffered bytes, remaining capacity, bytes pushed, and bytes popped. Which relationships should hold after every public operation, and which state properties are monotonic?

## 2. Trace the contract

For a stream of capacity 5, trace this sequence:

1. push the three bytes abc;
2. peek 2;
3. push the four bytes WXYZ;
4. pop 4;
5. close;
6. push the one byte !;
7. read 10.

Make a table with the return value where applicable, buffered byte sequence, remaining capacity, both counters, closed state, and finished state after each step. Explain any partial or rejected operation.

## 3. Lifecycle distinctions

Why are “closed” and “finished” separate observations? Describe a reachable state in which one is true and the other is false, and identify what operations remain meaningful there.

## 4. Orthogonal error state

What bugs could result if set_error implicitly discarded bytes or closed the producer side even though the contract says the error flag is diagnostic? Name a test that would isolate such coupling.

## 5. Representation and complexity

Explain why repeatedly erasing a prefix from one contiguous string can violate the workload target. Describe how your chosen representation avoids that problem and account for the complexity of each data-moving operation.

## 6. Test strategy

Your deterministic model test and your focused example tests can catch overlapping defects. What does each style contribute? If operation 7,432 in the model test fails, what evidence would let another engineer reproduce and minimize it?

## 7. Requirement change

Suppose a later version permits changing capacity at runtime. List at least four contract questions that must be answered before implementation, including what should happen when a requested new capacity is below the current buffered size. Do not implement this change.

## 8. Systems connection

Relate partial acceptance to backpressure between a fast producer and a slow consumer. What must a correct caller do with an unaccepted suffix, and why would silently counting offered bytes undermine observability?

There is no answer key in the learner materials. Submit your own reasoned responses.

Provenance: manager-authored question set for kickoff_01_bounded_byte_stream, derived from the local task contract rather than retrieved course content.

Validation label: QUESTION_SET_PREPARED_WITHOUT_ANSWERS.
