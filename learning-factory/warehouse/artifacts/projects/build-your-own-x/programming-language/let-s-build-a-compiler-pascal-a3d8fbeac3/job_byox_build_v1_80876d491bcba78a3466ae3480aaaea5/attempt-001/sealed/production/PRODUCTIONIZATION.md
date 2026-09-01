# Productionization assessment

Status: **not productionized**. The manifest correctly records `false`, and the
only validation labels are `GENERATED` and `PARTIAL`.

Before accepting untrusted Mica programs in a service:

1. Compile and test on pinned Free Pascal versions and supported operating
   systems. Record compiler version, flags, binary digest, and complete logs.
2. Add explicit source-byte, token, instruction, variable, nesting, output-byte,
   and wall-clock limits. Reject before allocation where possible.
3. Replace per-element dynamic-array resizing and linear symbol resolution with
   bounded geometric buffers and a deterministic scoped symbol table.
4. Run compilation/execution in a harness-controlled process with an argv array,
   sanitized environment, closed inherited descriptors, process group, timeout,
   captured/quota-limited logs, read-only source, and disposable working area.
5. Normalize unexpected exceptions without exposing host paths or memory details.
   Preserve a private correlation identifier for diagnostics.
6. Add a bytecode verifier even while bytecode remains internal. Validate opcode,
   operands, control-flow targets, slot bounds, and consistent abstract stack
   height at every reachable instruction.
7. Define versioning for language semantics and debug-listing/bytecode formats.
8. Add property tests, coverage-guided fuzzing, differential tests against an
   independent model, mutation testing, and platform transfer validation.
9. Decide whether output is transactional. Current semantics intentionally retain
   lines written before runtime failure; a job API may instead buffer within a
   strict quota and attach a completion flag.
10. Threat-model filesystem paths, oversized inputs, terminal control bytes in
    diagnostics, denial of service, and artifact retention. Mica has no imports or
    syscalls, which narrows but does not remove the host boundary.

Operational readiness also needs ownership, alerting, service-level objectives,
rollback procedures, reproducible releases, dependency monitoring, and an
incident-response path. None is established by this standalone challenge pack.
