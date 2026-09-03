# Sealed implementation review

## Review outcome

The reference is suitable as an educational oracle after independent
validation, with explicit partial scope.  It is not productionized.

## Positive properties

- Source is read with a fixed maximum and retained for token lifetimes.
- The lexer uses byte-counted input and ASCII classification.
- Parser errors retain the first stable source location.
- Recursive syntax paths acquire a checked 256-level budget before descent.
- Symbol lookup, shadowing, same-scope duplicates, and slot reuse are separate.
- Short-circuit operators use control flow rather than eager arithmetic.
- VM instructions validate operands, stack state, memory, jumps, arithmetic,
  and instruction budget at the execution boundary.
- Runtime failures retain the source path and opcode location, including zero
  budget before the first dispatch.
- The subprocess test harness uses argument arrays and timeouts.

## Findings and accepted limitations

1. The compiler emits unreachable fallthrough code after explicit returns.
   This is safe but increases bytecode size.
2. Diagnostics stop at the first error.  There is no recovery or multi-error
   reporting.
3. Output already written is not rolled back if a later runtime error occurs.
4. `--emit` is a human-readable stream without a magic value, version, word
   count, checksum, or loader.  It must not be treated as a durable format.
5. Source-to-bytecode locations exist only in memory and are not emitted.
6. The guest tower reserves parts of its heap for simulated state and therefore
   cannot offer the full nested heap capacity.
7. Arithmetic checks rely on compiler builtins supported by the pinned GCC.
8. There is no sandbox beyond the deliberately tiny guest capability set;
   resource controls are in-process fixed limits and a step budget.
9. The complete builder tree contains sealed material by design.  Publication
   remains conditional on an orchestrator-validated learner projection.

## Required before broader use

Address the production checklist in `sealed/production/PRODUCTIONIZATION.md`,
add independent fuzzing/sanitizer evidence, define a bytecode verifier and file
format if loading is introduced, and repeat validation on each supported host.
