<!--
provenance: Learner-authored manifest of this workspace's bounded kickoff implementation and actual local runs.
validation_label: SUBMITTED_FOR_INDEPENDENT_VALIDATION
-->

# Bounded kickoff submission

## Scope and status

This submission attempts only **Engineering a Reliable Binary Min-Priority Queue**, the provided kickoff/first unit. It makes no whole-course or official MIT assignment completion claim. Local checks passed, but only the worker-harness-controlled validator can promote the work.

## Deliverables

- `min_priority_queue.py`: binary min-heap implementation with stable sequence keys, opaque payloads, and pre-mutation priority validation.
- `test_min_priority_queue.py`: nine deterministic `unittest` cases, including a 2,500-operation independent-model trace with seed 6006.
- `benchmark_priority_queue.py`: seven trials at geometrically increasing sizes 250, 1,000, 4,000, and 16,000, with separate push/pop measurements.
- `ENGINEERING_NOTE.md`: invariant, design, exception safety, costs, complete benchmark samples, interpretation, and limitations.
- `COMPREHENSION_RESPONSES.md`: numbered answers 1–7, including all requested heap states and implementation/test evidence.
- `notes.md` and `debugging-log.md`: bounded learning notes and reproducible experiment history.

## Actual validation evidence

```text
$ PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v test_min_priority_queue.py
Ran 9 tests in 0.256s
OK
```

The same suite passed under the provided CPython 3.11.5 executable (`Ran 9 tests in 0.177s; OK`).

```text
$ PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 python3 benchmark_priority_queue.py
python=3.6.8 implementation=CPython
seed=6006 trials=7 sizes=250,1000,4000,16000
```

Median milliseconds by size were:

| n | Push | Pop |
|---:|---:|---:|
| 250 | 0.370 | 1.186 |
| 1,000 | 1.586 | 6.252 |
| 4,000 | 6.564 | 30.752 |
| 16,000 | 28.527 | 172.327 |

These observations have no pass/fail threshold and do not prove asymptotic complexity. Full raw samples and machine context are retained in `ENGINEERING_NOTE.md`.

## Known boundary

The intentionally unsupported features are thread safety, persistence, priority updates, arbitrary deletion, iteration, serialization, and merging. Independent validation is pending.
