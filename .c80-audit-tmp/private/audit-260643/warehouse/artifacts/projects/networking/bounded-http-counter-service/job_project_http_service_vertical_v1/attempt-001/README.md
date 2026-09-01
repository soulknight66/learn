# Bounded HTTP Counter Service

Build a small HTTP/1.1 service without a web framework, then examine why protocol parsing,
overload behavior, concurrency, lifecycle, and operations matter as much as route code. The
service stores named integer counters in memory and exposes compare-and-set and idempotent
increment operations. It is intentionally loopback-only and uses Python 3.11's standard
library so the engineering mechanisms remain visible.

This pack was newly generated from a Build Your Own X catalog relationship. No tutorial code
or prose was copied. `PROVENANCE.json` distinguishes catalog metadata, generated material,
measured evidence, and inferences.

## Progressive learner path

1. Read `REQUIREMENTS.md`, `CONCEPTS.md`, and `DESIGN_QUESTIONS.md`.
2. Implement the contract in `starter/http_service.py`.
3. Run `public_tests/` against only the starter tree.
4. Stress parsing, overload, and shutdown behavior before revealing `sealed/`.
5. Reveal the reference and compare it with two concurrency alternatives that share the
   same import/API contract.
6. Reproduce the isolated debugging challenge and submit a review for the cache PR.
7. Run the benchmark on your own machine and interpret raw measurements before reading the
   production gap review.

`sealed/` is a reveal boundary for human learning, not a claim of hostile multi-user
sandboxing. Copy `starter/`, `public_tests/`, and the top-level learner documents to create a
student view; do not mount `sealed/` into that view.

## Commands

```sh
# Learner-visible contract (expected to fail until starter is implemented)
PYTHONPATH=starter python3 -m unittest discover -s public_tests -v

# Reference and two architecture alternatives
PYTHONPATH=sealed/reference:sealed/shared python3 -m unittest discover -s public_tests -v
PYTHONPATH=sealed/alternatives/thread_per_connection:sealed/shared python3 -m unittest discover -s public_tests -v
PYTHONPATH=sealed/alternatives/event_loop:sealed/shared python3 -m unittest discover -s public_tests -v

# Run every bounded factory check, including fresh measured benchmark output
python3 scripts/run_all.py
```

Validation labels are evidence-scoped. Passing these bounded checks supports `BUILDS`,
`TESTED`, `FUZZED`, `BENCHMARKED`, and `REVIEWED` only alongside `PARTIAL`. It does not support
`PRODUCTIONIZED`: see `production/PRODUCTIONIZATION.md` for unresolved work.

## Navigation

- `starter/`, `public_tests/`: initial exercise surface
- `sealed/reference/`, `sealed/reference_tests/`: tested solution and withheld checks
- `sealed/alternatives/`: bounded worker-pool, thread-per-connection, and selector comparison
- `adversarial/`: deterministic parser, injected-fault, and slow-client probes
- `benchmarks/`: actual local execution and raw JSON measurements
- `debugging/partial-body/`: one-root-cause failure with sealed diagnosis and patch
- `review_exercises/cache-layer/`: plausible performance PR and expected review
- `production/`: operations sketch and honest non-production limitations
