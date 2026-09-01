# Productionization assessment

Status: not productionized.

Before deployment, replace the educational HTTP subset with a maintained protocol stack and TLS verifier; define redirect, proxy, DNS, IP-range, cookie, cache, origin, and content-sniffing policy; sandbox all document processing; add wall-clock and CPU budgets; stream bounded bodies instead of buffering whole responses; and introduce observability that never logs sensitive URLs or bodies by default.

Engineering gates should include parser fuzzing with persisted regressions, property tests for layout/paint bounds, differential framing tests, dependency and license review, deterministic benchmarks with declared fixtures, cross-platform CI, threat modeling, and an incident rollback plan.

The present reference intentionally contains no production TCP implementation. The standard library alone cannot provide HTTPS certificate validation, and a naive connector would invite DNS rebinding and server-side request forgery. The injected `Transport` is the deliberate seam for a separately reviewed networking component.
