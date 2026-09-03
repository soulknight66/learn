# Code-review exercise answer

The snippet trusts `pc` for both opcode and operand reads, trusts the opcode
domain, decrements `sp` before proving it is nonzero, trusts the target's sign
and range, and converts a possibly negative value to `size_t`.  These can cause
out-of-bounds reads, stack underflow, or a later out-of-bounds fetch.

Validate in this order: prove `pc < count`, fetch opcode, prove it is recognized,
prove the operand word exists, read the signed target, prove
`0 <= target < count`, prove `sp > 0`, then pop and conditionally assign the
already-validated target.  Validating the target even when the branch is not
taken keeps bytecode validity independent of runtime data and matches the
challenge contract.
