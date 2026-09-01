# Sealed implementation review

## Outcome

The implementation is internally consistent with the current public header and behavioral requirements for the bounded lab. A strict local build and the sealed deterministic tests pass. This review does not classify the artifact as independently validated, fuzzed, benchmarked, portable across toolchains, or production-ready.

## Findings resolved during review

1. The initial scheduler cursor must represent the slot immediately before slot 0. It is now initialized to `MICA_MAX_PROCESSES - 1`, making the first spawned process the first deterministic selection.
2. Block originally risked being interpreted as RUNNING-only. The final state machine accepts both READY and RUNNING, while wake remains BLOCKED-only.
3. Exit is defined for READY, RUNNING, and BLOCKED live processes. The implementation rejects only EXITED (plus unknown/invalid identities).
4. Duplicate VM mapping now reports `MICA_ERR_EXISTS`, distinguishing it from allocator/accounting corruption (`MICA_ERR_STATE`).
5. RAMFS interval checks avoid `offset + length` overflow and happen before mutation. A staged source copy handles overlap, and tests snapshot the full filesystem around rejected writes.
6. Filename handling is bounded and includes the requirement-specific `.` and `..` rejection.
7. The sealed and starter headers are byte-for-byte checked by the reference Makefile to prevent API drift.

## Invariants checked in code

- Scheduler validation rejects an out-of-range cursor, invalid state value, zero or duplicate live PID, and more than one RUNNING record.
- A failed spawn does not advance `next_pid`; a failed schedule does not change the cursor or output.
- VM resolution checks both the page entry's frame range and the allocator used bit.
- Map publishes a page entry only after a frame is available and cleared. Unmap checks accounting before releasing anything.
- RAMFS validates logical size before I/O and clears every byte when a record is initialized or unlinked.
- Output values are assigned only on success.

## Remaining limitations and risks

The public object layouts are mutable. Deliberately corrupted scheduler metadata receives useful state errors, but not every possible VM alias or RAMFS forged name can be diagnosed. In particular, copying a live address-space struct creates two page tables that name the same frame, while the allocator has no owner field or reference count. Reinitializing only a mapped address space leaks its allocator frames; the documented lifecycle requires unmap first.

There is no synchronization, interrupt safety, atomic instruction use, memory ordering contract, reentrancy analysis, or concurrent test. Raw C pointers can be invalid despite being non-null; the API assumes callers supply accessible storage. PID history is finite, stack-depth constraints have not been measured, and `int` exit-code representation follows the C implementation ABI.

The core was compiled locally with the requested warnings and freestanding flag, but the test run used one host compiler. No sanitizer, static analyzer, formal model checker, cross compiler, coverage tool, fuzzer, or performance benchmark was run. Failure injection beyond explicit invalid states was not performed. These are validation gaps, not implicit passes.

## Local evidence

From `sealed/reference`, the command `make clean && make test` compiled `scheduler.c`, `vm.c`, and `ramfs.c` with `-std=c11 -Wall -Wextra -Werror -pedantic -ffreestanding`, linked the hosted test, and printed `reference tests: PASS` on 2026-08-31. The learner-visible public test was also linked against these reference sources by the collaborating builder and reported 7 passed, 0 failed. Worker-controlled validation remains mandatory.
