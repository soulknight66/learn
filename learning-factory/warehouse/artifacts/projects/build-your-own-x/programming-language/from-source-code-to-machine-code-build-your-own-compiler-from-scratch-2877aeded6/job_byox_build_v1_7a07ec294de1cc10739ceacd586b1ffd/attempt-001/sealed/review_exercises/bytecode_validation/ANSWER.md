# Review findings: validate while running

This design can perform observable output before discovering an invalid suffix. For example, decoded
`CONST 7; PRINT; UNKNOWN; HALT` writes `7\n` and then fails, violating the requirement that validation
finish before execution or output. It also cannot safely handle jumps with a linear `for`, prove target
boundaries, reject unreachable instructions, or check merge depths.

Decode the entire byte stream into addressed instructions, validate operands and targets, run a
control-flow stack analysis to completion, and only then pass the immutable validated result to a
separate executor. A local precondition check in a dispatch loop is defense in depth, not a replacement
for whole-program validation.
