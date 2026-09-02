# Answer: scheduler stall

Distance zero examines `current` before any peer. A yield normally changes the
current task from running to ready, so it immediately selects itself. Startup
tests can miss this when their separate no-current path starts explicitly at
slot zero rather than calling this function with a real current index.

Begin the loop at distance one and include `SLOT_COUNT` as the final distance.
The last iteration deliberately wraps back to current, allowing it only when no
other ready slot exists. A regression sequence is: slots 0 and 1 ready, current
0; expect 1, then with current 1 expect 0. A singleton table should still return
its sole ready slot after the complete wrap.
