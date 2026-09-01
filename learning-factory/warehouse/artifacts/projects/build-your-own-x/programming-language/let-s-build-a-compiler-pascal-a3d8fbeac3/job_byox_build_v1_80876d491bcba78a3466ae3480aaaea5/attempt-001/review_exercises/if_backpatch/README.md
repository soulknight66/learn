# Exercise: review conditional backpatching

Review `candidate_fragment.pas` without running it. Trace bytecode for an `if`
with no `else`, then for an `if/else`. Identify control-flow errors, state the
correct destinations for each jump, and propose tests that distinguish a
condition that is true from one that is false.

Also comment on whether a placeholder numeric target should survive past the
compiler boundary.
