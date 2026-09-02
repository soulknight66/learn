# Design review questions

Answer these before comparing behavior with any sealed evaluation.

1. State the scheduler invariant before and after every public operation. Which
   operation owns the transition from a running task to ready?
2. Why must selection begin after the previous slot, and what should happen when
   the old task is the only runnable one?
3. How does a newly created ARM context reach a C function without a pre-existing
   call frame? Where does it go if that function returns?
4. Is PID identity tied to a table index? Explain what a stale PID can and cannot
   modify after its old slot is reaped.
5. List all checks needed before computing `base + index * page_size` and before
   computing `offset + length`.
6. Why is permission checking on translation not interchangeable with checking
   only when a mapping is created?
7. Which memory ranges must remain reachable at the exact instruction that sets
   the MMU enable bit?
8. What state could another observer see if RAMFS create publishes `used` before
   the name copy is complete?
9. Should a zero-length read with a null buffer succeed? Defend one contract and
   make it consistent across every API.
10. Which observations come from host execution, which from ARM emulation, and
    which still require independent validation?
