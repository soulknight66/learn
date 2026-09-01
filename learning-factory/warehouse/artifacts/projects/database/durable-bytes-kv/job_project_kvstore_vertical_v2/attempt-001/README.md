# Durable Bytes: a persistent key-value store challenge

Build a bytes-to-bytes store that begins as an in-memory map and evolves into a recoverable,
append-only persistent system. The future learner sees requirements, starter code, and public
tests first. References, deeper tests, design commentary, and expected reviews live under
`sealed/` and should be revealed intentionally.

## Learner workflow

```sh
PYTHONPATH=starter python3 -m unittest discover -s public_tests -v
# After implementing, reveal and compare intentionally:
PYTHONPATH=sealed/reference python3 -m unittest discover -s public_tests -v
PYTHONPATH=production/implementation python3 -m unittest discover -s sealed/reference_tests -v
```

`production/implementation` is a stable archive path for an instrumented teaching variant;
it is not a claim of production readiness. See `production/PRODUCTIONIZATION.md` for the
unresolved deployment work.

## Exact validation commands

Run every bounded check and write fresh benchmark evidence:

```sh
python3 scripts/run_all.py
```

Or run the stages individually from this archive root:

```sh
python3 environment/check_python.py
PYTHONPATH=sealed/reference python3 -m unittest discover -s public_tests -v
PYTHONPATH=sealed/reference python3 -m unittest discover -s sealed/reference_tests -v
PYTHONPATH=production/implementation python3 -m unittest discover -s public_tests -v
PYTHONPATH=production/implementation python3 -m unittest discover -s sealed/reference_tests -v
KVSTORE_IMPL=reference python3 adversarial/fuzz/model_fuzz.py --operations 600
KVSTORE_IMPL=production python3 adversarial/fuzz/model_fuzz.py --operations 600
KVSTORE_IMPL=production python3 adversarial/stress/thread_stress.py --threads 6 --operations 80
KVSTORE_IMPL=production python3 adversarial/fault-injection/torn_tail.py
! KVSTORE_IMPL=buggy python3 debugging/lost-delete/test_bug.py
KVSTORE_IMPL=reference python3 debugging/lost-delete/test_bug.py
python3 benchmarks/benchmark.py --operations 500 --output benchmarks/results/smoke.json
```

The leading `!` marks the intentionally failing buggy regression as a successful
reproduction. `KVSTORE_IMPL` accepts `reference` or `production` in adversarial scripts and
also accepts `buggy` in the debugging regression.

The archive also includes deterministic fuzzing, concurrency stress, crash-tail fault
injection, an actual benchmark harness, a single-root-cause debugging challenge, and a
realistic code-review exercise. All implementation prose and code were newly authored; the
upstream catalog and tutorial are linked only as provenance.
