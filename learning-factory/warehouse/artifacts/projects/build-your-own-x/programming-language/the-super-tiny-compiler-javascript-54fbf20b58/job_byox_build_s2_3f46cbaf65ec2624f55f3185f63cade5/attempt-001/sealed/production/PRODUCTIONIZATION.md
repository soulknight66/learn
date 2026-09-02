# Productionization assessment

Status: **not productionized**. `safe-runner.js` is a partial hardening example and does not justify a production label.

## Implemented hardening

- Rejects source over a configurable UTF-8 byte ceiling before scanning.
- Applies deterministic token, AST-node, and generated-byte ceilings.
- Uses an iterative, cycle-aware AST counter.
- Rejects unknown or invalid limit settings.
- Returns measurements as data rather than logging source text.
- Never executes generated JavaScript.

## Blocking gaps

Size checks do not enforce wall-clock time, CPU, process memory, parser nesting, output count, or execution steps. Token and AST checks happen after their respective phases allocate data. Several compiler phases recurse and can exhaust the JavaScript stack before an AST-node check runs. There is no cancellation path, worker-process boundary, operating-system sandbox, tenant isolation, audit log, package/version policy, release signing, telemetry, incident procedure, or compatibility commitment.

Generated JavaScript must not run in a privileged application process. A real execution service needs a separately launched, low-privilege process or stronger sandbox with bounded time, memory, file descriptors, output, and no network/filesystem authority. JavaScript `vm` alone is not a security boundary.

## Before deployment

1. Make parse and all tree passes depth-aware or iterative, with limits enforced during construction.
2. Run compilation and execution in separate supervised processes with killable deadlines and OS resource limits.
3. Define versioned input, diagnostic, AST, and generated-output contracts.
4. Add property-based, mutation, differential, load, and security testing on a pinned Node release matrix.
5. Add structured metrics that omit source and literals by default, plus redaction and retention rules.
6. Threat-model generated-code execution and obtain independent security review.
7. Establish deterministic builds, dependency scanning, artifact signing, rollback, and incident response.

The manifest therefore correctly retains `productionized: false` and `PARTIAL`.
