# Debugging exercise answer

1. The compiler probably hides the outer name too early or inserts the new
   symbol before compiling its initializer.  Compile the initializer against
   the old active table, then append the new symbol.  Regress with both an outer
   shadow and a same-scope duplicate.
2. Logical `&&` was likely compiled as an eager binary opcode.  Emit `JZ` before
   the right expression and patch a false-result block.  Regress with a right
   side that would fault and with non-Boolean truthy values to verify result
   normalization.
3. The budget comparison is likely performed after dispatch or uses `>` instead
   of `>=`.  Check `steps >= limit` immediately before fetching an opcode, then
   increment once for that opcode.  Test budgets around a two-word instruction
   to ensure operand words are not charged.
