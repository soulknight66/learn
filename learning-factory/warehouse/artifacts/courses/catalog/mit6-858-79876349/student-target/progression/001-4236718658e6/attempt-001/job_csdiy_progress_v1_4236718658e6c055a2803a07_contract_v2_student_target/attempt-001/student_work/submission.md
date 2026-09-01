# Bounded-task submission

## Delivered artifacts

The completed practice artifact is under `submission/`:

```text
submission/
├── src/frameguard/__init__.py
├── src/frameguard/model.py
├── tests/test_model.py
├── THREAT_MODEL.md
├── DESIGN.md
├── DEBUG_LOG.md
└── REPORT.md
```

`frameguard.model` exposes the required constants, immutable `Observation`,
`vulnerable_request`, and `hardened_request`. The implementation uses only the Python standard
library, has no mutable request state, emits no diagnostics, and never places payload/frame content
in results.

## Locally observed behavior

For a symbolic input `[data × 16] || [0x01]`, the vulnerable path returned accepted/granted with
overflow 1 and an intact canary. The hardened path returned rejected/not granted with
`PAYLOAD_TOO_LONG`, overflow 1, and an intact canary. A separate 18-byte vulnerable input changed a
canary byte. A following empty request began with the initial role and canary.

Final command from `submission/`:

```text
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Observed result: exit status 0, 13 tests, `OK`. `submission/REPORT.md` contains the SHA-256 manifest,
redacted trace, exact outcome comparison, provenance, and limitations.

Validation label: `LEARNER_CAPTURED_LOCAL_EVIDENCE_FOR_GENERATED_PRACTICE_TASK_ONLY`.

## Completion boundary

The bounded generated practice task is implemented and locally self-checked. Independent
worker-harness validation was not available while preparing this record. No official specification,
starter code, hidden test, native target, or transfer assessment was available. This submission does
not claim official Lab 1 credit, security of MIT/Zoobar or any native/web program, demonstrated
transfer, or course completion.
