# Sealed reference tests

This evaluator-only suite checks middleware continuation safety, pattern validation, scoped
middleware boundaries, nested parameter restoration, bodyless responses, error exposure, JSON
stream limits, abort handling, and server lifecycle. Added regressions cover supported-method
fallthrough, pre-fired abort/error state, invalid UTF-8, a real-socket delayed-parser abort, and the
learner-view allowlist. The public suite is also part of the intended reference check.

Socket-free JavaScript and Python regressions passed on the repair host. Network cases were blocked
by the sandbox's `listen EPERM` policy. Exact commands and observed outcomes are recorded in
`VALIDATION.md`; no independent acceptance label is claimed.
