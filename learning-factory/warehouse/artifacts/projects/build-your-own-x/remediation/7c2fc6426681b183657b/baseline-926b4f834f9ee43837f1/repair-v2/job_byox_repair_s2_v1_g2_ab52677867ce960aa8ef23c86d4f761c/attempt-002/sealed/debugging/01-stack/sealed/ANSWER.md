# Answer: comparison flags

The draft performed the operand `cmp`, then compared an opcode selector to choose `sete`, `setl`, or
`setg`. The selector `cmp` replaced the operand flags. Branch on the selector first; in each selected
case, perform the operand comparison immediately before its `setcc`. Regression inputs must include
unequal signed pairs in both orders and a negative-versus-positive pair.
