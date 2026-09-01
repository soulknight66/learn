# Sealed implementation review

Review scope: static inspection of the generated reference source and test
design. The Java compiler and JVM were unavailable on the generation host, so
this is not a `REVIEWED` validation claim.

## Findings addressed in the artifact

- Constant-pool indexes are assigned through ordered interning and class bytes
  contain no host metadata.
- Forward and backward branch offsets are patched from the opcode address and
  checked before narrowing.
- A join label is not emitted past the end of a method whose two branches both
  return.
- The analyzer’s continuing-path merge prevents verifier-visible uninitialized
  loads after conditional or zero-iteration control flow.
- Operand stack requirements are derived structurally, including the extra
  `PrintStream` receiver during `print`.
- Public results defensively copy mutable byte arrays and expose immutable
  diagnostic lists.
- Scanner newline handling treats CRLF as a unit and never relies on platform
  line parsing.

## Residual risks requiring independent validation

- The reference Java source has not been compiled on this host.
- Version-49 verification behavior must be exercised by loading every generated
  control-flow shape on Java 17+.
- Boundary cases around 32,767-byte branch spans, 65,535-byte method bodies,
  65,534 constant-pool entries, 255 locals, and 100,000 tokens need generated
  tests on a toolchain-equipped host.
- Recursion budgets are logical limits; an unusually constrained JVM thread
  stack could still warrant iterative passes.
- The compiler is a learning implementation, not hardened for hostile multi-
  tenant execution. Loading output executes compiled arithmetic and printing.

## Suggested production-review gates

Require independent compilation with `-Xlint:all -Werror`, mutation testing of
diagnostics, verifier loading across supported JVM vendors, fuzzing of scanner
and parser boundaries, deterministic-build comparison in clean containers, and
resource measurements before changing any validation label.

