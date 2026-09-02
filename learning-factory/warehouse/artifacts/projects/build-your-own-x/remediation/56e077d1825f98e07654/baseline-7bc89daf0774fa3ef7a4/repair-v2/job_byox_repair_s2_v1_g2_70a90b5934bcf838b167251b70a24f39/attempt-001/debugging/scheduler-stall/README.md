# Scheduler stall

A candidate emits `tasks: AAA` and then times out even though task B is ready.
Host logs show that each call to `choose_slot` returns the current task.

Inspect `fixture.c` and answer:

1. Which iteration violates the after-current policy?
2. Why can this evade tests that begin with no current task?
3. Give the smallest change and one regression sequence that distinguishes the
   defective and corrected policies.

Do not alter task states or special-case two tasks; the fix should preserve one
bounded wrap for any current slot.
