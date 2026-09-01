# Compiler-stack answer

For `print (+ 1 2)`, the required trace is `[] → [1] → [1,2] → [3] → []`. Emitting print before add yields `[] → [1] → [1,2] → [1] → [3]`, leaving one value at halt. The violated invariant is that compiling an expression has net effect +1 and the enclosing statement then consumes exactly that one result.

The smallest structural regression compiles `(print (+ 1 2))` and asserts opcode order `[Push, Push, Add, Print, Halt]`, then calls `ValidateBytecode`. It need not run the VM or assert a numeric result.
