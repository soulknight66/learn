# Productionization assessment

Production status is false. This teaching interpreter should not execute adversarial source in a
security boundary.

Before any production claim, isolate execution in a separately constrained process; impose wall,
CPU, address-space, output, and file limits outside the guest VM; replace or justify seek-based
loading; test allocation and write failures; add structured diagnostics; split compiler and VM
modules; fuzz the lexer/parser/VM; run undefined/address sanitizers where supported; test multiple
compilers and architectures; and establish a supported-version/security-response policy.

The instruction budget bounds bytecode dispatch, not compile time, resident memory beyond stated
tables, stdout size across all programs, or host library behavior. The guest has no file/network
operations today, but the host process still inherits its ambient environment. Those distinctions
must be addressed by a harness, not by a prose promise.

No production benchmark, profiler trace, fuzz campaign, portability matrix, or external review was
performed during generation. Independent validation remains mandatory.
