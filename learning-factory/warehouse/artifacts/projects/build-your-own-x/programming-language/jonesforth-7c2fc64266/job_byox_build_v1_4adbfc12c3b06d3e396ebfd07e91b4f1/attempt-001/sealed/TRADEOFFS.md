# Sealed tradeoffs

## Chosen: bytecode staging

Staging gives compile-error atomicity and demonstrates both compiler and interpreter boundaries. It
costs a second bounded buffer and one more dispatch loop. Directly executing tokens would be smaller
but could not satisfy the later-unknown-token rule without a separate validation pass.

## Chosen: direct built-in recognition

A few length and byte comparisons are easy to audit for ten words. A linked dictionary or hash
table would scale better and teach word lookup more directly, but it would add address-bearing data
structures that distract from the initial parser and VM.

## Chosen: fixed static storage

Static input, code, data-stack, and formatting regions make bounds visible in the binary and avoid
allocator dependencies. The cost is a hard 4095-byte language limit and a larger BSS reservation.
BSS does not occupy equivalent bytes in the executable file.

## Chosen: syscall-only process

Direct Linux calls keep the assembly boundary honest and create useful lessons about short reads and
writes. The executable is consequently Linux/x86-64 specific. A libc wrapper would be more portable
but would hide startup and I/O semantics.

## Deferred language features

Colon definitions, control flow, strings, return stacks, dictionary mutation, and persistence are
excluded. Each would require new syntax, bytecode validation, resource limits, and tests. Adding them
without those policies would turn a deterministic teaching VM into an underspecified one.

