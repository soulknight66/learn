# Design questions

Answer these in your own notes before reading any review feedback.

1. Which invariants relate `current_slot`, task state, and `quantum_left` before and after a tick?
2. Why are PIDs distinct from reusable task slots, and what stale-handle bug appears if they are not?
3. Should an idle interval advance simulated time? How would sleeping tasks ever wake if it did not?
4. Which registers must a cooperative ARM AAPCS context switch preserve? Which additional state is
   required for interrupt-driven preemption or floating-point code?
5. How can a cross-page write be checked without modifying its first page before discovering that its
   second page is read-only or unmapped?
6. At what exact lifecycle transition should physical frames be reclaimed, and what evidence remains
   after that transition?
7. How can full-file replacement reuse old blocks while remaining unchanged on `ENOSPC`?
8. What aliasing problem occurs if the source of a filesystem write points into a block being
   replaced?
9. Which parts of this RAM model correspond to a real ARM short-descriptor page table, and which are
   only pedagogical analogies?
10. What new atomicity and locking requirements appear with interrupts, SMP, or a persistent device?
11. Which test or trace would convince you round-robin selection is deterministic across wraparound?
12. What evidence would be required before describing this artifact as secure or production-ready?
