# Answer: else patch point

The false target of JZ is the first cell of the else body. At `else`, first emit `JMP` and its empty
operand; only then does `code_here` point at that body. Patch the old JZ operand to this post-placeholder
address, and keep the JMP operand address on the patch stack for `then`. A nested false/false case
detects an off-by-one-cell target reliably.
