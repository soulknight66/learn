# Independent Examiner Rubric

Course ID: course_0729adcee037deb352528b85cd365b36  
Unit ID: kickoff_01_bounded_byte_stream  
Maximum score: 100

This rubric is examiner-only. It evaluates one manager-authored kickoff unit and cannot establish completion of CS144 or of a complete computer-networking course.

## Evidence protocol

Assess the submitted files and observed executions, not the learner's prose claim that something passed. Work in an isolated copy with network access disabled. Record the compiler, commands, exit codes, and captured test output. Add examiner-owned black-box cases without modifying the submitted implementation.

Use the required public interface exactly. The local STUDY_TASK.md is authoritative; external CS144 pages, notes, or repositories are neither required evidence nor a basis for changing the contract.

The unit passes only when all of these conditions hold:

- every required submission artifact exists;
- the project configures, builds, and registers a CTest test without downloading dependencies;
- examiner-owned tests for capacity, ordering, lifecycle, error state, and counters pass;
- no reproducible undefined behavior, memory-safety failure, or unbounded/nonterminating required test is observed;
- the score is at least 80.

If a gating condition fails, preserve the evidence and label the unit NOT_COMPLETE regardless of the numeric subtotal. A build failure caused solely by an examiner's incompatible optional warning flag is not a learner failure; use the declared C++17 workflow.

## Scoring

### 1. Reproducible project and interface — 10 points

- 4: clean CMake configure and build succeed offline using C++17 with extensions disabled.
- 2: a library, test executable, and CTest registration are present and usable.
- 2: the public interface matches the specification without weakening types or visibility.
- 2: useful warnings are enabled and the required tree contains no generated binaries or fetched dependency trees.

### 2. Byte preservation and capacity behavior — 25 points

- 6: arbitrary bytes, including embedded nulls, are returned in exact FIFO order.
- 5: zero capacity and zero-length operations behave safely and consistently.
- 6: exact fill and overfill accept only the longest fitting prefix and return the accepted count.
- 4: peek is nonmutating; pop and read remove no more than is present.
- 4: interleaving operations and reuse after removals do not corrupt, duplicate, or lose accepted bytes.

Award no more than 10 points in this section if the buffer can exceed capacity or ordinary operations reorder data.

### 3. Lifecycle, diagnostic state, and accounting — 15 points

- 4: close is idempotent, rejects subsequent pushes, and preserves buffered bytes.
- 3: finished is exactly closed and empty, including transitions while draining.
- 3: error is sticky, idempotent, and orthogonal to buffering and closure.
- 5: pushed and popped counters count actual acceptance/removal only and remain consistent across partial and rejected operations.

### 4. Representation and complexity — 15 points

- 5: constant-time state and accounting queries follow from the representation.
- 5: many small front removals do not shift the whole remaining payload repeatedly; examiner stress evidence is consistent with the stated O(k) removal target.
- 3: storage stays proportional to fixed capacity, returned values, and bounded bookkeeping.
- 2: ownership, iterator/reference invalidation, and integer conversions are safe under the stated count assumption.

Do not require a particular container. A ring buffer, deque, or chunked design may all earn full credit when evidence supports the contract and complexity.

### 5. Learner-owned test quality — 20 points

- 8: focused tests cover every category required in STUDY_TASK.md with meaningful assertions.
- 5: the reference-model run performs at least 10,000 mixed operations using a committed fixed seed and checks state after operations.
- 3: model failures identify the seed and operation index; the suite is deterministic and bounded.
- 2: tests are black-box through the public interface rather than coupled to private storage.
- 2: tests distinguish accepted from offered input and inspected from removed input.

Tests that merely print values without assertions receive no credit for the affected checks. Do not award model-test points based only on a claim in TESTING.md.

### 6. Design and reproduction record — 5 points

- 2: DESIGN.md states useful invariants and connects them to implementation decisions.
- 1: it gives a credible operation-by-operation complexity argument.
- 1: it evaluates a rejected alternative with a concrete tradeoff.
- 1: TESTING.md records sufficient exact local commands and results to repeat the workflow.

### 7. Comprehension — 10 points

Score the response for correct reasoning, not wording:

- 2: invariants and monotonic properties;
- 2: trace accuracy;
- 1: closed versus finished;
- 1: diagnostic error independence;
- 1: representation/complexity analysis;
- 1: focused versus model-based test roles and reproducibility;
- 1: runtime-capacity requirement questions;
- 1: backpressure and caller responsibility.

## Examiner-owned checks

At minimum, supplement the learner's suite with:

- capacities 0, 1, and a small non-power-of-two value;
- offers at, below, and above remaining capacity, verifying only a prefix is accepted;
- byte strings containing null, high-bit, and repeated values;
- peek and oversized pop/read on empty and nonempty streams;
- close while nonempty, drain to finished, repeated close, and rejected post-close input;
- error before and after close, verifying no implicit lifecycle or counter changes;
- enough alternating small writes and reads to force storage reuse;
- counter conservation after every action;
- a deterministic comparison against a simple examiner-owned FIFO model.

For every reachable state, the expected conservation relationships are:

- buffered bytes never exceed capacity;
- remaining capacity equals capacity minus buffered bytes;
- bytes pushed minus bytes popped equals buffered bytes;
- both counters are monotonic;
- finished equals closed and buffered bytes equal to zero.

These relationships are examiner guidance, subject to the stated assumption that cumulative counts fit in std::uint64_t.

## Comprehension answer guide

Question 1 should identify all conservation relationships above. Capacity is fixed; close and error are sticky; counters are monotonic. Finished need not be monotonic before close, but once true no new input can be accepted and it remains true under the specified API.

For Question 2, the expected trace is:

| Step | Return | Buffer | Remaining | Pushed | Popped | Closed | Finished |
|---|---:|---|---:|---:|---:|---|---|
| initial | — | empty | 5 | 0 | 0 | no | no |
| push abc | 3 | abc | 2 | 3 | 0 | no | no |
| peek 2 | ab | abc | 2 | 3 | 0 | no | no |
| push WXYZ | 2 | abcWX | 0 | 5 | 0 | no | no |
| pop 4 | — | X | 4 | 5 | 4 | no | no |
| close | — | X | 4 | 5 | 4 | yes | no |
| push ! | 0 | X | 4 | 5 | 4 | yes | no |
| read 10 | X | empty | 5 | 5 | 5 | yes | yes |

For Question 3, closed means no more input can be accepted; finished additionally requires all accepted input to have been drained. A closed nonempty stream remains readable, peekable, and removable.

For Question 4, implicit discard or close would conflate independent state, lose data, alter future acceptance, and make fault origin difficult to observe. A focused test should set error in an open stream with known buffered data, then verify unchanged bytes, counters, capacity, and closed state, followed by normal operations.

For Question 5, front erasure from a contiguous string can move the remaining suffix on each operation and make repeated small removals quadratic. Accept any representation whose explanation and evidence meet the target without requiring one prescribed design.

For Question 6, focused examples localize named boundaries; the model sequence explores compositions and long state histories. Reproduction evidence includes fixed seed, exact generator/range, failing operation index and operation details, prior state or a bounded trace window, compiler/build command, and assertion mismatch.

For Question 7, credible questions include the outcome of shrinking below occupancy; whether shrinking can reject, block, discard, or defer; whether order changes; minimum/maximum capacity; exception and return behavior; effects on remaining capacity and counters; concurrent-operation rules; and reference/iterator invalidation. Four materially distinct questions earn full credit.

For Question 8, limited acceptance is a backpressure signal. The caller must retain and later retry or otherwise explicitly handle the suffix. Counting offered bytes would break conservation, misstate delivery, and hide loss.

## Final record

Record numeric category scores, gating results, examiner commands and logs, and one final label:

- UNIT_COMPLETE_VALIDATED, or
- UNIT_NOT_COMPLETE.

Never emit a course-complete label from this rubric.

Provenance: independent manager-authored rubric for catalog source commit adce8e13789dc16aa6d1fbe163e9541736defae4. No external material was retrieved.

Rubric preparation label: EXAMINER_RUBRIC_READY_NOT_EXECUTED.
