# Alternative designs

Several independent extensions preserve the lesson while changing tradeoffs:

- Keep a separate last-run cursor so blocking does not reset scheduler
  fairness; add priorities only after defining starvation behavior.
- Replace the mapping array with a two-level software page table, or use a
  bitmap-backed frame allocator and explicit shared-frame reference counts.
- Hide structures behind opaque handles so representation changes do not alter
  the ABI; tests would then need invariant-query functions.
- Give RAMFS inode numbers and directory entries, separating object lifetime
  from names. An append-only block log could add crash recovery.
- Drive process actions as user-mode coroutines in hosted tests before adding
  AArch64 exception frames and real context switching.

None is implemented in the reference because each introduces a second major
mechanism that would obscure the three bounded state machines being assessed.
