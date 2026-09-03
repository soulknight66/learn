# Tradeoffs and alternatives

- Fixed tables make exhaustion deterministic and eliminate allocator dependencies, but impose small
  global limits and linear scans.
- Public state makes invariants teachable and corruption testing easy, but a production kernel would
  hide layouts behind module boundaries.
- Exclusive frames simplify reverse ownership. Shared memory and copy-on-write would require owner
  sets or reference counts plus explicit permission-transition rules.
- Rejecting unlink while open avoids generation counters and deferred reclamation, but differs from
  Unix name/object lifetime semantics.
- A single scheduler cursor is sufficient without interrupts. Preemption would require a critical
  section strategy and a separate saved execution context.
- Full-write-or-error semantics simplify rollback. A real filesystem API often permits partial writes
  and must report exactly how far durable progress reached.
- A software translation table is testable on the host but does not establish page-table format, TLB
  behavior, or protection in hardware.
- A Multiboot loader keeps the challenge focused on kernel state rather than firmware/disk boot, at
  the cost of delegating early machine setup.
