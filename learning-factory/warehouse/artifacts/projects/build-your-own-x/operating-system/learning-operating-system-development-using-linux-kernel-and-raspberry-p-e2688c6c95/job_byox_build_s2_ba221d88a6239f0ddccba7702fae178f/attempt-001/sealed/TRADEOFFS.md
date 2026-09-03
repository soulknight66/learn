# Reference tradeoffs

The implementation chooses bounded arrays and linear lookup. That makes every
state archivable, removes allocator failure from the lesson, and keeps error
atomicity easy to inspect. Costs are O(n) lookup, tiny capacities, and public
structure layouts that prevent opaque representation changes.

The scheduler models policy but not execution. Entry points are metadata;
there is no saved register context, stack, exception return, or timer-driven
preemption. The software mapping table models translation semantics but is not
installed in TTBR registers and does not allocate frames or invalidate a TLB.
The RAM filesystem models namespace and byte I/O but provides neither
directories nor persistence.

The freestanding AArch64 build is valuable because it catches accidental libc
dependencies and validates UART/boot integration. QEMU `virt` is deliberately
used instead of claiming board compatibility. A Raspberry Pi build would need
board-specific load addresses, peripheral discovery, mailbox/firmware
interfaces, exception setup, and testing on identified hardware revisions.

Failure atomicity is implemented with preflight checks rather than rollback.
That is appropriate for small in-memory operations. A larger kernel would need
transactions, careful lock ordering, reference counts, and durable recovery
protocols.
