# Sealed reference tests

This evaluator-only suite checks middleware continuation safety, pattern validation, scoped
middleware boundaries, nested parameter restoration, bodyless responses, error exposure, JSON
stream limits, abort handling, and server lifecycle. The public suite is also part of the intended
reference check.

No execution result is claimed on the generation host because Node.js was unavailable. The exact
prescribed commands and observed blocker are recorded in `VALIDATION.md`.
