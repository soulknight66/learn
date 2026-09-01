# Kickoff Submission Manifest

The bounded first-unit submission is in `submission/`:

- `signals.py` — immutable finite-signal value and two convolution algorithms
- `test_signals.py` — deterministic examples, validation checks, generated
  comparisons, and property tests
- `benchmark.py` — reproducible dense and zero-heavy measurements
- `evidence/benchmark.json` — raw learner-produced timing evidence
- `REPORT.md` — engineering analysis, limitations, and provenance
- `COMPREHENSION_RESPONSES.md` — numbered responses to all ten questions

Reproduction commands from this directory:

```bash
python3 -m unittest discover -s submission -p 'test_*.py' -v
PYTHONPATH=submission python3 submission/benchmark.py
```

Local result snapshot: 20 test methods passed. The recorded benchmark contains
seven repetitions per implementation for each of two cases, and output checks
agreed before timings were accepted. Its validation label is
`LEARNER_PRODUCED_UNVALIDATED`.

Completion claim: bounded kickoff artifacts prepared; independent validation
is pending. The EE120 course remains in progress.
