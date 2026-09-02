# Productionization assessment

Status: **not productionized**.

The reference is suitable for a bounded local learning exercise. It is not a
safe compiler service. Before any production use, the implementation would
need:

- a subprocess sandbox for generated native code and the host assembler/linker;
- OS-enforced CPU, address-space, file-size, descriptor, syscall, and output
  quotas in addition to language fuel;
- non-fatal allocation propagation and a tested allocation ceiling;
- reliable write-error propagation from interpreted and compiled output;
- directory durability after atomic rename and a policy for output permissions;
- fuzzing of lexer/parser/resolver boundaries under ASan and UBSan;
- reproducible toolchain pinning plus tests on each supported ABI;
- structured diagnostics rather than unescaped path/name interpolation;
- concurrency, cancellation, observability, and artifact-retention policies;
- an independent security and correctness review.

The current code must not be described as hardened merely because its local
tests pass. The manifest deliberately records `productionized: false`.
