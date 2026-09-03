# Sealed trade-off analysis

## Direct bytecode emission

Emitting during recursive descent makes the reference small and exposes jump
patching clearly.  It also entangles parsing with storage allocation, prevents
whole-program type checks, and makes source-to-bytecode debugging harder.  An
AST or typed intermediate representation would be preferable once the language
gains functions or optimization.

## Fixed arrays

Fixed code, local, operand-stack, and heap arrays provide deterministic failure
points and avoid allocator behavior in the VM loop.  Their limits are blunt:
valid large programs are rejected, and the million-byte source ceiling is much
larger than the code ceiling.  Production code should use checked dynamic
growth with explicit configured maxima.

## Absolute word offsets

Absolute offsets make guest interpretation and disassembly simple.  Editing or
linking bytecode requires rewriting targets.  Relative offsets or labeled basic
blocks scale better for relocation.

## Reusing local slots across blocks

Restoring the next-slot counter at block exit satisfies the simultaneous-local
limit and keeps frames compact.  It would complicate closures or debugging
metadata because an old lexical variable and a later one share a slot.

## Host arithmetic checks

GCC overflow builtins give concise, reliable checks for the configured pinned
compiler.  A portability-focused implementation would isolate these behind an
arithmetic module with standards-only fallbacks and exhaustive boundary tests.

## Tower boundary

The bytecode tower is executable and finite, but it deliberately sidesteps a
self-hosted lexer and parser.  It is a useful bootstrap milestone, not a basis
for claiming that the interpreter accepts its own C implementation as source.
