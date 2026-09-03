# Sealed trade-offs

## AST slots instead of hash lookups

The resolver uses a 256-entry linear symbol table and writes slot numbers into
the AST. Resolution is quadratic in the worst case, but the explicit variable
limit bounds that cost and keeps the reference easy to audit. A hash table
would matter for a larger language.

## Stack-frame variables instead of register allocation

Every source variable owns one eight-byte frame slot. This produces readable
assembly and stable semantics but unnecessary loads and stores. Optimization is
outside the learning objective.

## Direct assembly instead of an intermediate representation

The backend walks the AST directly. That makes the interpreter/backend
correspondence visible, but control-flow analysis and machine-independent
optimization would be cleaner with an IR.

## libc output instead of syscalls

Calling `printf` and `fputs` demonstrates the ABI and avoids integer-formatting
code. It also ties generated programs to a C runtime. Pebble flushes after each
printed value so failures have deterministic status, trading buffered-output
performance for a small and exact I/O contract; a dedicated runtime layer
could make error reporting and output quotas more flexible.

## Fixed semantic limits

One-megabyte input, 128-level trees/blocks, 256 variables, and default fuel are
simple and deterministic. They are policy choices rather than universal
language truths; changing them changes observable acceptance and should be
versioned.

## GNU assembly as the sole target

AT&T syntax works with the available `cc` driver and needs no dependency. It is
not portable to Windows x64, AArch64, or assemblers expecting Intel/NASM syntax.
