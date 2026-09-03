# Reference implementation review

## Scope reviewed

The review covered sealed reference source, direct and adversarial tests, public API correspondence,
and learner/solution separation. It did not establish production readiness, security isolation,
performance thresholds, or compatibility beyond the pinned validation runtime.

## Findings addressed in the reference

- Every token and AST diagnostic path retains an exclusive source span.
- Initializers execute before definition, and scope lookup uses `Map.has`, preserving `nil` values.
- Block evaluation exits its scope in `finally`; compiled blocks preserve the operand result while
  removing their environment.
- Conditional compilation gives both branches the same stack effect and patches all sentinels.
- The VM validates opcode operands before execution and bounds hostile control flow.
- Interpreter and VM name, type, division, and duplicate-definition errors agree by code and span.
- APIs return output rather than performing host I/O; only the CLI writes streams.

## Residual limitations

- Recursive parsing and tree evaluation can exhaust the host stack on deeply nested adversarial
  input. There is no configured source-size or nesting limit.
- String concatenation and output arrays have no memory quota.
- Bytecode validation is structural and dynamically checks stack effects; it does not perform a
  whole-control-flow abstract interpretation before execution.
- Diagnostics stop at the first syntax failure and contain no source excerpt.
- The CLI has no explicit file-size limit and should not be treated as an untrusted-code sandbox.
- There is no fuzzing evidence, stored benchmark evidence, package release process, or long-term
  compatibility policy.

Status therefore remains generated and partial. Independent harness validation is still required.
