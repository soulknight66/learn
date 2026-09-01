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

The archive also includes deterministic fuzzing, concurrency stress, crash-tail fault
injection, an actual benchmark harness, a single-root-cause debugging challenge, and a
realistic code-review exercise. All implementation prose and code were newly authored; the
upstream catalog and tutorial are linked only as provenance.
