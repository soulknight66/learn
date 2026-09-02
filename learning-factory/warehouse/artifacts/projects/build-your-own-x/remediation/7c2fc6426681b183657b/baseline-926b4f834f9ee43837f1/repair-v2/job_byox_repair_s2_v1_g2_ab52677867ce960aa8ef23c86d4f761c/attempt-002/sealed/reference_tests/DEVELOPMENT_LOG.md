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

A later independent review found that `parse_number` returned overflow before inspecting a
nondigit suffix. Consequently, valid names such as `9223372036854775808x` and
`-9223372036854775809x` were misclassified as out-of-range integers. Repair generation 2 added a
complete lexical-shape pass before range conversion and a two-case regression. The focused test and
the resulting 14-test sealed suite both completed with `OK`; exact commands are in `VALIDATION.md`.
