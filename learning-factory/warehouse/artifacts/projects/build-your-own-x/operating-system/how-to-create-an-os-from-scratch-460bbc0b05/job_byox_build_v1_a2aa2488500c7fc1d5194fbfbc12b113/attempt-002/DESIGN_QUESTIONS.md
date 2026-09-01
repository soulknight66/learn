# Design Questions

Use these questions as review gates. They are prompts, not required written submissions, and they intentionally do not prescribe a representation or algorithm.

## Milestone 1: Empty state and API boundaries

1. After initialization, what can a caller observe in each module?
2. Which arguments can be invalid before module state is consulted?
3. Which output arguments must remain untouched on failure?
4. Can initialization safely replace arbitrary prior bytes, or does it assume the caller zeroed storage?
5. Are public constants used consistently at every boundary?

## Milestone 2: Scheduler lifecycle

1. For every scheduler operation, which source states are legal and what is the destination state?
2. What is the observable result when no process is runnable?
3. How does the scheduling sequence change when a process blocks, wakes, exits, or is reaped?
4. Does an exited but unreaped process still count toward capacity?
5. Can a failed spawn or failed transition accidentally advance scheduling order?
6. If a record is reused, can an identity that should be stale affect its new resident?

## Milestone 3: VM lifecycle

1. What are the first invalid page number and first invalid linear address?
2. What happens on the ninth simultaneous map, and what state must remain unchanged?
3. Can two mappings accidentally expose the same writable storage?
4. How will you verify all 64 bytes are zero after a frame is reused?
5. Which observable values must survive a rejected write to a read-only mapping?
6. Do map and unmap failures preserve both mapping state and frame accounting?

## Milestone 4: Filesystem lifecycle

1. Which exact byte sequences are valid names, and where is the maximum length boundary?
2. Are names compared exactly, including case?
3. Is an empty file distinct from a missing file in every operation?
4. What must happen to the old contents when a write interval crosses byte 128?
5. What should a read do when its destination holds only part of the bytes remaining after its offset?
6. After unlink and create, could stale content become observable?
7. Which bytes must be observed when a write begins beyond the old logical end?
8. Does one file reaching 128 bytes change the independent capacity of another file?

## Milestone 5: Final contract review

1. For each limit, have you tested zero, one, the exact limit, and one beyond it?
2. For each state-changing call, have you tested repetition and the wrong source state?
3. Can any error path change a cursor, counter, output, contents, or protection bit?
4. Does behavior depend on stack garbage, pointer values, time, or call history that the contract does not expose?
5. Does the implementation remain within C11 and the supplied build environment?
6. Are you testing the documented behavior rather than only reproducing public test examples?
