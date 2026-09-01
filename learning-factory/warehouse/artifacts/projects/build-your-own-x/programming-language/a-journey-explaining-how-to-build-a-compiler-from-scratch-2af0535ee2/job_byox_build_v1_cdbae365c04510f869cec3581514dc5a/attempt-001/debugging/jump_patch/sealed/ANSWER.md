# Answer

emit appends at the old code_count and then increments it. The placeholder's index must be the return
value from emit, or code_count minus one immediately afterward. The shown code records the next
instruction, so patching corrupts the first true-branch instruction or writes out of range for an empty
branch.

If the condition instruction consumes its operand, stack depth at both branch entries is the
pre-condition baseline. Each statement branch must return to that baseline, and the merge also has
that depth. An expression-valued conditional would instead require both paths to leave exactly one
value over the same baseline.
