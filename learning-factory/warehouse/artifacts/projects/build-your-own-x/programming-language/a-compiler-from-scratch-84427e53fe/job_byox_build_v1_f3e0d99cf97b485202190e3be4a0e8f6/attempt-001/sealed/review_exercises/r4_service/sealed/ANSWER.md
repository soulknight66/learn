# R4 answer

The instruction budget does not bound request bytes, tokens, recursive parse depth, AST/bytecode/local allocation, VM stack size, output bytes, wall-clock time spent compiling or writing, or process memory. Enforce input/output quotas at the transport, structural limits inside each compiler stage, cancellation deadlines in the embedding layer, and OS-level isolation/resource limits for hostile tenants. Avoid logging source bodies.
