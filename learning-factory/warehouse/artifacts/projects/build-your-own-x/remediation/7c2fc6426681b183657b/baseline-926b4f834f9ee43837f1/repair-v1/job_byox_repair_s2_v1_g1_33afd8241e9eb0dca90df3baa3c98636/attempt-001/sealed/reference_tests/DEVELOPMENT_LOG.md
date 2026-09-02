# Retained development evidence

The first public-suite execution after the reference assembled completed 10 tests in 0.019 seconds
and failed four: comparison/bitwise output, nested conditionals, recursion, and the stack-word
example. Observed comparison output began `0\n-1\n` where the contract expected `-1\n0\n`;
recursion ended with `error: data stack overflow`; and the stack implementation produced
`2 1 1\n3\n` while the original test incorrectly expected `1 1 2\n3\n`.

Review found two independent causes. The comparison dispatcher performed selector comparisons after
the operand comparison, overwriting status flags before `setcc`; it was changed so each operand
comparison immediately precedes its condition-code capture. That repaired comparison, conditional,
and recursion behavior. The stack output was correct for standard `( a b c -- b c a )` `rot`, so the
public expectation was corrected rather than changing the primitive.

The immediate rerun completed the same 10 tests in 0.019 seconds with `OK`. The first sealed boundary
suite run completed 13 tests in 0.044 seconds with `OK`. Final clean-run evidence is recorded in the
root `VALIDATION.md`.
