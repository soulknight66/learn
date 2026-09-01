# Sealed reference implementation

This module is an independently generated reference implementation of the contract in `REQUIREMENTS.md`. It is intentionally isolated from the learner module and uses a different module path so validation cannot accidentally pass by importing starter code.

Implementation files separate scanning, parsing, analysis, compilation, validation, and execution. The reference has no external dependencies. Its tests are split between internal white-box cases in this module and black-box/adversarial oracle cases in `sealed/reference_tests/`. Candidate acceptance is a separate role: `sealed/learner_tests/` imports `example.com/pebble` through a replacement generated only by the harness.

When Go 1.21+ is available, intended commands are:

```bash
GOTOOLCHAIN=local go test ./...
printf '(print (+ 20 22))\n' | GOTOOLCHAIN=local go run ./cmd/pebble
```

Generation-host execution was blocked by the absent Go executable. This directory is reference evidence, not a claim of independent validation or production readiness.
