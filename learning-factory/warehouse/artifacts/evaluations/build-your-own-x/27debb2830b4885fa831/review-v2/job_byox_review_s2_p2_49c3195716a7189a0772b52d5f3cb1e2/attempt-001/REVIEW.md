# Independent review

## Verdict

**REVISE.** The pack is coherent, useful, and unusually candid about its partial status. Its recorded
checks reproduce independently. One high-priority defect remains in the sealed reference at the
public `run(chunk)` trust boundary, so the reference is not yet a correct oracle for the stated
bytecode contract.

## Prioritized finding

### P1 (high): malformed bytecode can escape deterministic VM rejection

`REQUIREMENTS.md` says that every instruction has `{ op, arg, span }`, diagnostics carry a valid span
or `null`, and the VM deterministically rejects malformed chunks. In
`sealed/reference/src/vm.mjs`, `validateChunk` destructures `span` without validating it (line 42)
and interpolates an unknown, untrusted `op` into an error message (line 58).

Independent probes observed all of the following:

- `op: Symbol("bad")` throws host `TypeError` with no stable code;
- an object-valued opcode has its `toString` hook executed, and that hook's host `Error` escapes;
- `span: "not-a-span"` is accepted and later exposed as the `span` of an
  `E_UNDEFINED_NAME` `MicaRuntimeError`.

These outcomes contradict the advertised untrusted-chunk boundary and are not covered by the
submitted malformed-bytecode cases. Revise the validator to type-check `op` before constructing any
message from it, avoid coercing hostile values, and accept only `null` or a structurally valid source
span. Add sealed regressions that require `MicaRuntimeError` / `E_INVALID_BYTECODE` for invalid opcode
types and span shapes. If arbitrary JavaScript objects are intentionally out of scope, narrow the
public contract explicitly to an inert data representation and validate that representation.

## Other review results

- **Reproducibility and claim honesty:** the pinned Node version, syntax check, baseline failure,
  sealed passes, CLI smoke output, 57-file audit, and manifest labels all reproduce. The artifact does
  not claim `BUILDS`, `TESTED`, `FUZZED`, `BENCHMARKED`, `REVIEWED`, `TRANSFER_VERIFIED`, or
  `PRODUCTIONIZED`; `GENERATED` + `PARTIAL` and `independent_validation: REQUIRED` are appropriate.
- **Learner usefulness:** the requirements define observable APIs, grammar, spans, semantics,
  diagnostics, and bytecode clearly. The starter, concepts, design questions, debugging prompts, and
  review exercises form a sensible progression. The deliberately failing starter suite is explained
  accurately and fails for the documented TODO stages.
- **Progressive disclosure:** learner-facing files contain stubs, examples, and guidance, while
  reference code, tests, design answers, and exercise answers are consistently under `sealed/`
  paths. The actual student-view export policy cannot be proven from this full reviewer bundle;
  prose telling learners not to inspect sealed content is not itself access control.
- **License and provenance:** the documents distinguish the CC0 catalog metadata from the linked
  resource's `NOASSERTION` license and do not turn the link into a reuse grant. Internal identifiers,
  commits, and the recorded snapshot link agree. The upstream material needed to verify the hashes
  and independent-generation/no-copy assertion is not available here, so those claims remain
  provenance assertions rather than independently established facts.
- **Dependency and safety surface:** submitted modules use only relative imports and declared Node
  built-ins. Static inspection found no `eval`, `Function` construction, network module, or subprocess
  module use. The disclosed recursion, memory, fuzzing, benchmarking, compatibility, and
  productionization limits are accurate.

This verdict is advisory only. It does not award or publish a `REVIEWED` label.
