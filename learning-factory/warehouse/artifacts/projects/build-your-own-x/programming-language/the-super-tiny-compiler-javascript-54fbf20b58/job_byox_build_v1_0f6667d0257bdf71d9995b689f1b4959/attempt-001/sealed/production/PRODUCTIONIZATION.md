# Productionization assessment

## Verdict

Pebble is **not production-ready**. It is an educational compiler and VM with a
small language surface. This assessment contains recommendations only; it does
not claim that the controls below are implemented or validated.

No benchmark results are claimed. The authoring environment did not provide a
usable Node.js runtime, so the sealed benchmark harness and JavaScript artifacts
could not be executed here. Independent build, test, fuzz, performance, and
security validation remain required.

## Current gaps

- The parser and both execution engines have not been validated on a supported
  runtime in this workspace.
- The educational API is documented for Node.js 20+, but no compatibility matrix,
  packaging validation, release process, or semantic-versioning policy has been established.
- Source locations, diagnostic codes, and malformed-bytecode behavior have an initial contract,
  but compatibility guarantees, multi-error recovery, and exhaustive validator evidence are absent.
- A language-level step budget is not a substitute for memory limits, wall-clock
  deadlines, process isolation, or cancellation.
- There is no demonstrated fuzzing, differential-testing history, coverage
  target, mutation score, or independent security review.
- There are no observed throughput, latency, allocation, or scaling data, and
  therefore no defensible capacity claim.
- Compatibility, concurrency/reentrancy, serialization, logging, and operational
  support policies are not defined.

## Recommended gates before any production use

1. **Specify the boundary.** Decide whether source and bytecode are trusted,
   define input-size and nesting limits, document integer/truthiness behavior,
   and version both the language and bytecode formats.
2. **Harden validation.** Carry source spans, reject malformed AST and bytecode
   shapes, validate stack effects and jump targets, use stable typed errors, and
   ensure host exceptions do not leak as language behavior.
3. **Contain execution.** Run untrusted programs in disposable workers or
   processes with wall-clock, CPU, memory, output, and recursion limits. Support
   cancellation and cap diagnostic/output volume.
4. **Build evidence.** Run unit, integration, tree/VM differential, property,
   fuzz, mutation, and adversarial suites on every supported runtime. Add a
   regression corpus for every discovered defect.
5. **Measure honestly.** Establish representative workloads and service-level
   targets first; then gather reproducible distributions on named hardware and
   runtime versions. Keep raw results and do not generalize beyond the tested
   configuration.
6. **Operationalize.** Add deterministic releases, dependency and license
   review, provenance/SBOM generation, vulnerability response, observability,
   rollback, and data-retention guidance.

Production consideration should begin only after these gates have owners,
acceptance criteria, and independently recorded evidence. Until then, use
Pebble for learning and controlled experiments, not as a security boundary or
service dependency.
