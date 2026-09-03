# Reference implementation review

## Scope reviewed

The review covered sealed reference source, direct and adversarial tests, public API correspondence,
and the deterministic learner-projection policy. It did not establish production readiness,
security isolation, performance thresholds, or compatibility beyond the pinned validation runtime.

## Findings addressed in the reference

- Every token and AST diagnostic path retains an exclusive source span.
- Initializers execute before definition, and scope lookup uses `Map.has`, preserving `nil` values.
- Block evaluation exits its scope in `finally`; compiled blocks preserve the operand result while
  removing their environment.
- Conditional compilation gives both branches the same stack effect and patches all sentinels.
- The VM copies required own data properties into validated records, checks opcode types and source
  span structure before execution, avoids invoking accessors, and bounds hostile control flow.
- Interpreter and VM name, type, division, and duplicate-definition errors agree by code and span.
- APIs return output rather than performing host I/O; only the CLI writes streams.
- The base learner projection uses an explicit top-level allowlist, rejects every `sealed` path
  component, emits content hashes for selected files, and has an external materialized-view
  comparison mode. Production repair did not create a learner workspace.

## Residual limitations

- Recursive parsing and tree evaluation can exhaust the host stack on deeply nested adversarial
  input. There is no configured source-size or nesting limit.
- String concatenation and output arrays have no memory quota.
- Bytecode validation is structural and dynamically checks stack effects; it does not perform a
  whole-control-flow abstract interpretation before execution.
- JavaScript `Proxy` inputs are outside the bytecode API contract because no in-process validator
  can inspect them without permitting user-defined traps to run.
- Diagnostics stop at the first syntax failure and contain no source excerpt.
- The CLI has no explicit file-size limit and should not be treated as an untrusted-code sandbox.
- A controlling harness must still materialize the learner projection outside the production pack
  and run the verifier's `--projected-root` mode before publication.
- There is no fuzzing evidence, stored benchmark evidence, package release process, or long-term
  compatibility policy.

Status therefore remains generated and partial. Independent harness validation is still required.
