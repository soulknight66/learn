# Productionization assessment

Status: **not productionized**.

The reference is a bounded, single-threaded teaching model. Moving toward a real Raspberry Pi kernel would require, at minimum:

1. A documented supported-board matrix, reproducible cross-toolchain, pinned firmware assumptions, signed build provenance, and boot-image packaging.
2. EL transitions, per-core stacks, full exception vectors, register context save/restore, timer programming, interrupt-controller support, and serial diagnostics.
3. Architecturally correct translation tables, ASIDs, TLB maintenance, memory attributes, barriers, page allocators, kernel/user separation, and fault containment.
4. Concurrency design with ownership rules, atomics, interrupt/preemption rules, lock ordering, and race-focused tests.
5. Persistent filesystem design with a block-device abstraction, power-loss model, recovery procedure, quotas, authorization, and hostile-media validation.
6. Fuzzing, static analysis, hardware-in-the-loop boot tests, long-duration stress, fault injection, security review, and release criteria.

The host suite is useful evidence about pure state transitions only. There are no real-hardware boot logs, performance measurements, fuzzing results, transfer verification, or operational review in this artifact. Independent validators must retain `productionized: false`.
