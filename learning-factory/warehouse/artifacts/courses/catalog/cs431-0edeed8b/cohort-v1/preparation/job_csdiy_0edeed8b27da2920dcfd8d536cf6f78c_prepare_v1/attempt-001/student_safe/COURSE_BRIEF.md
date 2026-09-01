# CS431: Concurrent Programming — Kickoff Brief

## What this packet is

This is a manager-authored first study unit inspired by the supplied CSDIY catalog description of KAIST CS431. It is not represented as an official KAIST lesson or assignment. The source snapshot describes a roughly 50-hour Rust concurrency course spanning programming models, locks, lock-free structures, and hazard pointers, but it supplies only metadata and external links. None of the linked website, recordings, slides, assignments, or paper was retrieved for this packet.

This kickoff is intentionally much smaller: about six hours on one mutex-protected component. Completing it can demonstrate the objectives of this unit only. It cannot demonstrate completion of CS431.

## Unit 1: Concurrency contracts and a FIFO cache

You will specify, implement, and test a bounded concurrent FIFO cache in safe Rust. The data structure is modest on purpose. The work is in making behavior precise, maintaining related state atomically, testing without depending on lucky thread schedules, and leaving evidence another engineer can reproduce.

By the end of the unit, you should be able to:

- state representation invariants separately from examples;
- relate a sequential API contract to concurrent histories;
- identify a linearization point for each mutex-protected operation;
- design assertions that remain valid under every permitted schedule;
- distinguish mutual exclusion, functional correctness, and progress properties;
- produce build and test evidence that can be independently checked.

## Working model

A sequential specification says what each operation does to an abstract state. A concurrent implementation must additionally explain how overlapping calls can be understood. For this unit, use linearizability as the target: every completed call should appear to take effect at one instant between its invocation and return, and the resulting total order must obey the sequential cache contract.

One mutex can make the linearization argument relatively direct when every field participating in the invariant is read or changed while the same guard is held. The lock itself does not establish that the FIFO queue and key/value map agree, that capacity is enforced, or that return values satisfy the contract. Those are representation and functional-correctness obligations.

Treat tests as executable evidence, not a proof. Sequential tests should pin down boundary behavior and state transitions. Concurrent tests should coordinate threads with barriers or channels and make schedule-independent assertions. A wall-clock sleep does not establish that a desired interleaving occurred and often creates flaky tests.

Rust mutex poisoning is also part of the public behavior. A panic while a guard is held can poison `std::sync::Mutex`. This unit's contract requires operations that need the lock to report a typed `Poisoned` error instead of silently recovering or panicking through `unwrap`.

## Prerequisite check

Before starting, you should be able to create a Rust library crate and explain ownership, borrowing, `Result`, generic trait bounds, `Arc`, `Mutex`, and scoped or joined threads. You should also recognize hash-map and queue complexity. If two or more of those are unfamiliar, pause for a Rust/concurrency refresher; that refresher is not counted as completing this unit.

## Scope boundary

This unit does not cover atomics, memory orderings, lock-free progress, reclamation, hazard pointers, or performance benchmarking. It does not ask you to access any external course link. Those subjects and any official assignment sequence require later material retrieval and course expansion.

Read `STUDY_TASK.md` for the exact contract and deliverables, then answer the questions in `COMPREHENSION.md` after your implementation and tests are complete.
