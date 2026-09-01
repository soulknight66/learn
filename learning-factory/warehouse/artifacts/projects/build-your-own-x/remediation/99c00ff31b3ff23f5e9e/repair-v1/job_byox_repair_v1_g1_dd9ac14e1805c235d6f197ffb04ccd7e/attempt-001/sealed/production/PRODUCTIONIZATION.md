# Productionization assessment

`productionized` is `false`. The artifact is an educational implementation with
local functional evidence only.

Before a real deployment, at minimum:

1. Split phases into reviewed interfaces and replace the eager arena with a
   checked chunked allocator.
2. Write assembly output to a same-directory temporary regular file, `fsync` as
   required by the application, and atomically rename only after successful
   close.
3. Add sanitizers, static analysis, allocation-failure injection, compiler
   matrix testing, and coverage-guided fuzzing of lexer/parser/validator inputs.
4. Test generated code across each explicitly supported assembler, linker,
   libc, and x86-64 operating system combination.
5. Define output-volume and wall-clock controls in addition to statement visits.
6. Add structured diagnostics and stable diagnostic identifiers before external
   tools depend on error text.
7. Threat-model untrusted source, generated-file destinations, resource
   exhaustion, and runtime linkage in the actual embedding context.
8. Establish versioned language and assembly interfaces with compatibility
   tests and a release process.

None of those activities is claimed complete here. No production review label
should be inferred from this planning document.
