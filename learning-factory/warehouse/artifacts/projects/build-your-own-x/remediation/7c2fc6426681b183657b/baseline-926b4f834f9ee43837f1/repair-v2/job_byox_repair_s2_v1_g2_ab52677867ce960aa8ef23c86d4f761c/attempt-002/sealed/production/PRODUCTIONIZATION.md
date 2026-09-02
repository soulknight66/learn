# Productionization gap analysis

This artifact is explicitly not productionized. Converting it into a deployable language runtime
would require, at minimum:

- a supported ABI and platform matrix, reproducible release builds, signed artifacts, and SBOM;
- PIE/ASLR compatibility and validated relative branch targets;
- streaming input, source spans, recoverable diagnostics, and well-defined invalid-byte handling;
- guard pages or memory-safe isolation for VM regions and systematic integer/pointer proofs;
- process-level sandboxing, quotas, cancellation, and a documented signal policy;
- differential and coverage-guided fuzzing with retained corpora and sanitizer-assisted companion
  models;
- deterministic conformance suites on every target plus load, soak, and fault-injection testing;
- profiling before optimization, with independently reproduced benchmark baselines;
- versioned bytecode if code is serialized, including verifier and compatibility rules;
- external security review and operational ownership for vulnerability response.

Local unit-test success does not establish any of these properties. No production-readiness label is
claimed.
