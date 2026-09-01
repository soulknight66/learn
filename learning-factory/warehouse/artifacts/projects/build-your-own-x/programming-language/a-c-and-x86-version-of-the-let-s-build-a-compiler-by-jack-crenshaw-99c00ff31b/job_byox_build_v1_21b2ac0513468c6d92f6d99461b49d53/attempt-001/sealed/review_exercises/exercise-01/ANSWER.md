# Exercise 01 review answer

After the function prologue and aligned frame allocation, `%rsp` is 16-byte
aligned at each call site as required by the x86-64 System V caller. One pending
8-byte expression push changes it to the wrong congruence. A library routine may
assume alignment and fail even though ordinary integer instructions do not.

Valid repairs include:

1. Ensure expression evaluation cannot call: branch to a shared statement-level
   error epilogue only after restoring all temporary pushes. This is the Mica
   reference strategy.
2. Track temporary stack depth and add/remove an 8-byte padding slot around a
   call when needed.
3. Store virtual expression operands in fixed frame slots or registers rather
   than changing `%rsp`.

The invariant should be written mechanically: every control-flow edge into a
call has zero pending expression pushes (or otherwise has the ABI-required stack
congruence), and all outgoing edges restore the same depth. Arithmetic-only
tests never transfer control to code that relies on the ABI, so they cannot
demonstrate call-site alignment.
