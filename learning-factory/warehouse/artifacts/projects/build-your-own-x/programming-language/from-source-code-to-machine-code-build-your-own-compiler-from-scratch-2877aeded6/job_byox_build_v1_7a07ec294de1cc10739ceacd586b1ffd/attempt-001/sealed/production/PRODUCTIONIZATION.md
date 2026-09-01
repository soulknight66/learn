# Productionization assessment

Status: **not productionized**. The reference is an educational executable specification.

Before processing hostile inputs in a service, add externally enforced byte/source/output limits,
compile and run deadlines, process isolation, memory and file quotas, and cancellation. Validate in a
separate least-privilege process; do not rely on the bytecode verifier as a security sandbox. Define
whether output is buffered transactionally or may be partial after a runtime fault.

A durable format would need an explicit version/feature policy, compatibility tests, maximum section
sizes, canonical encodings, debug/source maps, and likely integrity or signature metadata. A service
would also need structured diagnostics, metrics for rejection classes and resource use, trace-safe
identifiers, rate limiting, and redaction rules.

Compiler hardening should replace recursion with bounded or iterative traversal where practical, split
semantic resolution from emission, cap AST and scope counts, and add mutation/property tests under an
independent harness. CLI durability would require directory fsync policy, permissions/ownership rules,
and platform-specific atomic-replacement tests.

No production claims, service-level objectives, security audit, compatibility guarantee, or benchmark
threshold is asserted by this artifact.
