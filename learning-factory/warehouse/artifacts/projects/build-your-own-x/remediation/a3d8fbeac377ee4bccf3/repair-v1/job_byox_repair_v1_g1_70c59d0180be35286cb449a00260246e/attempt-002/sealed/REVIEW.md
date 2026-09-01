# Sealed implementation review

## Summary

The reference candidate is coherent with the written grammar and keeps phases
separate. It is suitable as an independently compilable teaching reference, but
it has not been compiled on the generation host and must not be labeled tested or
production-ready.

## Strengths found by static review

- Lexer cursor updates are centralized in `Advance`; EOF receives the next-byte
  location.
- Decimal accumulation checks Mica's bound before multiplication/addition.
- Parser functions encode precedence and left/right associativity directly.
- Undefined names and redeclarations are compiler failures, including code after
  `halt`.
- Conditional jumps consume conditions; loops therefore have stable stack use.
- VM binary operations preserve operand order.
- The Mica arithmetic domain prevents host `Int64` overflow before explicit range
  checks.
- Step exhaustion is checked before dispatch of instruction 100001.
- CLI modes do not run later phases unnecessarily (`--tokens` never compiles and
  `--bytecode` never executes).

## Findings and residual risks

1. **Native verification missing (high evidence risk).** No Free Pascal compiler
   was present. Syntax, ABI assumptions, and exact `Format` behavior need an
   independent Free Pascal 3.2.x run.
2. **No source-size policy (medium).** The driver rejects only files above
   `High(LongInt)`. A much smaller explicit limit is needed for hostile inputs.
3. **Quadratic growth potential (medium).** Repeated `SetLength` for every token,
   instruction, and name can copy arrays repeatedly. Geometric capacity or
   vectors would be safer for large sources.
4. **Linear symbol lookup (low for teaching, medium at scale).** Many distinct
   names create quadratic compile time.
5. **Exception boundary incomplete (medium).** Only defined language errors are
   normalized. Allocation failure and internal exceptions use Pascal's default
   reporting and exit behavior.
6. **Output has no quota (medium).** The instruction limit bounds lines but a
   production service should also cap bytes and stream through a harness-owned
   sink.
7. **Bytecode trusted internally (low today).** VM checks stack, slots, and taken
   jump targets, but there is no pre-execution verifier. This matters if bytecode
   is ever deserialized or exposed as an input format.
8. **ASCII-only token semantics (documented).** Non-ASCII UTF-8 bytes fail one at
   a time. This is conforming but unfriendly for international identifiers.

## Review disposition

`PARTIAL`. Proceed to isolated compilation with warnings enabled, run public and
sealed suites, add static/fuzz tooling if available, and address any compiler
findings. Do not promote validation or production labels based on this review.
