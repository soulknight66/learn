# Review answer: conditional backpatching

The fragment patches the false jump before testing/emitting the `else`. In an
`if/else`, that sends a false condition to the unconditional end jump rather than
the first else instruction, so the else body is skipped. A true condition falls
through into the else body because the unconditional jump was emitted after the
then body but is placed at the location already selected for false flow.

Correct ordering is:

1. emit `JUMP_IF_FALSE placeholder`;
2. emit the then body;
3. if there is an else, emit `JUMP placeholder`, patch the false jump to the
   first else instruction, emit the else body, then patch the end jump;
4. without an else, patch the false jump to the first instruction after the then
   body.

Tests need observable, distinct bodies: `if true { print 1; } else { print 2; }`
must print only 1, while the false form must print only 2. Add a statement after
the conditional to ensure both paths rejoin. Compilation should reject or
internally assert if any placeholder remains. A richer compiler should retain
labels until final encoding instead of exposing sentinel numeric targets.
