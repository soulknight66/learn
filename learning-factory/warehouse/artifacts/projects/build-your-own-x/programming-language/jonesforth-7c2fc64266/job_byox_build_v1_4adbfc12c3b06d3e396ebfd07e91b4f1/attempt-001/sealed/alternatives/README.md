# Sealed alternatives

Several independent designs can satisfy most of the educational goal:

1. A two-pass direct interpreter first validates every token and then rescans source to execute. It
   avoids a code buffer but demonstrates less compiler representation.
2. A table-driven dictionary stores token length, spelling, and handler address. It scales more
   cleanly than comparison branches but requires careful relocation and executable-address policy.
3. A token-threaded VM stores handler identifiers in cells. Dispatch is simpler at the cost of
   larger bytecode.
4. A C runtime shim can provide I/O while assembly owns parsing and execution. It improves
   portability but violates this challenge's syscall-only build contract.

None is included as a second executable because duplicate solutions would enlarge the sealed answer
surface without improving the learner contract.

