# Code-review exercise

## Exercise 01: calls from a stack-style emitter

An x86-64 System V backend establishes a frame aligned to 16 bytes. Its binary
expression emitter pushes the left operand, evaluates the right operand, and—on
one error-reporting path inside the right operand—calls a C library function
before popping the left operand.

Review this design for ABI correctness. State the stack invariant that the
emitter must maintain, give at least two valid repairs, and explain why testing
only arithmetic expressions without calls can miss the defect.

The solution-bearing review is kept in the matching sealed exercise directory.
