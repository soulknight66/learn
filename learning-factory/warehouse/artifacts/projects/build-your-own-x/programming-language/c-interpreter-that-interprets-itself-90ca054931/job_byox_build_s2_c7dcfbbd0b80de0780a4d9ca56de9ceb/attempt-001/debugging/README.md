# Debugging exercise

Assume an otherwise conforming implementation exhibits these three symptoms:

1. `int x=5; { int x=x+1; }` reports an unknown name in the initializer.
2. `0 && (1/0)` raises division by zero.
3. A loop exactly at its configured instruction budget sometimes executes one
   extra instruction.

For each symptom, identify the likely invariant violation, propose the smallest
regression test, and specify which layer should own the fix.  Avoid changing the
language contract to match the bug.
