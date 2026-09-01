# Design questions

Answer these before implementing the corresponding milestone. State an invariant or a counterexample, not just a preference.

## Process model

1. Why is a monotonically increasing PID separate from a recyclable process-table slot?
2. What should happen to the running marker when the running process blocks or exits?
3. At what point in process creation can PID exhaustion be reported without leaving a partial record?
4. Should an idle scheduling decision advance time in this deterministic model? What contract makes tests unambiguous?

## Virtual memory

1. Which arithmetic expression can overflow when validating an address range, and how can you avoid evaluating it unsafely?
2. Which fields must change together when the final mapping of a frame is removed?
3. A write spans two shared pages but only one free frame remains. What observable states are acceptable after the call?
4. Why must copy-on-write be represented separately from ordinary read-only protection?
5. When a copy-on-write mapping has one reference, is copying still necessary? Which flags must be restored?

## Filesystem

1. In what order should open validate the process, name, flags, descriptor capacity, and file capacity?
2. How can premature truncation violate the general failure-atomicity rule?
3. Which object owns the cursor: the file, descriptor, or process? What behavior does fork require here?
4. Why is an independently derived open count useful even though descriptors already identify files?
5. Should a capacity-crossing write be partial or atomic? How does the answer affect callers?

## Invariants and portability

1. Which facts can `pebble_check()` recompute from primary state, and which must it trust?
2. What corrupt indices must be validated before the checker follows them?
3. Which components remain portable C, and which belong in a Raspberry Pi board-support layer?
4. Where would interrupt masking or locks be required if calls could overlap?
5. What evidence would be needed to claim real-hardware boot, MMU correctness, or production readiness?
