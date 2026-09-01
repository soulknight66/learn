# Learning task: implement and harden a byte-frame request model

## Goal

Build a deterministic, local-only Python package named `frameguard`. It must include two request paths over the same semantic byte-frame model:

1. a deliberately vulnerable path that copies across an application-data boundary; and
2. a hardened path that validates the boundary before any copy.

Use the contrast to explain how memory corruption becomes an authorization-integrity failure. This is original practice material derived only from the catalog-level theme; it is not an official MIT Lab 1 specification.

## Required submission

Create this inspectable structure:

```text
submission/
├── src/
│   └── frameguard/
│       ├── __init__.py
│       └── model.py
├── tests/
│   └── test_model.py
├── THREAT_MODEL.md
├── DESIGN.md
├── DEBUG_LOG.md
└── REPORT.md
```

You may split code or tests into additional files, but the listed paths must remain present. The implementation must run with Python 3 and the standard library alone.

## Public model contract

Expose these constants from `frameguard.model`:

```text
DATA_SIZE = 16
ROLE_OFFSET = 16
CANARY_OFFSET = 17
CANARY = b"FRAMEOK"
FRAME_SIZE = 24
```

A fresh frame has exactly 24 bytes:

- indices `[0, 16)` are zero-filled application-data bytes;
- index `16` is the role byte, initially `0x00`;
- indices `[17, 24)` contain `b"FRAMEOK"`.

The authorization policy is pure: access is granted exactly when the role byte equals `0x01`. Each request starts from a fresh frame; no frame or decision state may leak between requests.

Define an immutable result value with these fields and meanings:

```text
accepted: bool
access_granted: bool
reason: str
payload_length: int
overflow_bytes: int
canary_intact: bool
```

Expose these functions:

```text
vulnerable_request(payload: bytes) -> Observation
hardened_request(payload: bytes) -> Observation
```

Both functions must reject a non-`bytes` argument by raising `TypeError` before frame construction or mutation. Do not coerce strings, byte arrays, or other values.

### Vulnerable path

For payload lengths from 0 through 24 inclusive, copy bytes in order beginning at frame index 0, even when the copy crosses `DATA_SIZE`. Then compute the observation from the resulting frame.

- Set `accepted` to `True` and `reason` to `"OK"`.
- Grant access exactly according to the role-byte policy.
- Set `overflow_bytes` to `max(0, payload_length - DATA_SIZE)`.
- Report whether the canary region still exactly equals `CANARY`.

For payloads longer than `FRAME_SIZE`, perform no copy and return a rejected observation with reason `"MODEL_CAPACITY_EXCEEDED"`, no access, the requested payload length, the same overflow-count formula, and an intact canary. This outer capacity is a safety boundary of the semantic emulator, not the application-data boundary being studied.

### Hardened path

Validate the application-data boundary before copying.

- For lengths from 0 through `DATA_SIZE` inclusive, accept and copy only within the data region. Use reason `"OK"`; the role byte and canary must remain at their initial values.
- For every payload longer than `DATA_SIZE`, perform no copy and return a rejected observation with reason `"PAYLOAD_TOO_LONG"`, no access, the requested payload length, the overflow-count formula, and an intact canary.

Silent truncation is not permitted. Neither path may return, print, or persist the raw payload or a full frame dump.

## Architecture and implementation constraints

- Keep fresh-frame construction, byte copying, pure authorization, and request-path orchestration separately inspectable.
- Make validation order evident in code; the hardened path must have no partially mutated rejection state.
- Avoid mutable module-level request state.
- Do not use `ctypes`, native extensions, `eval`, `exec`, subprocesses, sockets, HTTP clients, or shell commands in the package.
- Keep results and diagnostics deterministic. Do not include clocks, randomness, machine-specific paths, or payload content.
- Use names and short comments to explain security boundaries rather than narrating individual Python operations.

## Required deterministic tests

Use `unittest`. Include assertions that independently cover:

- the exact fresh-frame layout and pure role-byte policy;
- payload lengths 0, 15, and 16 on both paths;
- a derived 17-byte payload that grants access through the vulnerable path without changing the initial prefix requirement into a special-case implementation;
- rejection of that same payload by the hardened path;
- a payload that demonstrably changes at least one canary byte on the vulnerable path;
- lengths 24 and 25 at the semantic model's outer boundary;
- invalid input types and exact exception behavior;
- exact reason strings, overflow counts, access decisions, and canary observations;
- request isolation after both an authorization-changing request and a rejected request; and
- absence of raw payload bytes from result representations and any diagnostics you add.

Add at least one table-driven test that exercises a meaningful range of lengths or byte values. A test must fail if the hardened handler copies first and merely repairs the role byte afterward.

Run the suite from `submission/` with:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## Engineering analysis

### `THREAT_MODEL.md`

Identify assets, actors, the untrusted-input boundary, security properties, concrete abuse cases, assumptions, and non-goals. Trace at least one abuse case from input through byte mutation to an authorization decision. Distinguish authorization integrity, canary integrity, availability, and diagnostic privacy. Explain why this model is not evidence that a native program or web application is secure.

### `DESIGN.md`

Document the frame ranges, module responsibilities, validation order, and request-isolation strategy. Defend rejection instead of truncation. Discuss why a canary can detect some corruption but does not prevent the role byte from being used, and describe one production-safe observability design that does not record payload contents. State at least two limitations of the model.

### `DEBUG_LOG.md`

Record real investigation evidence. For each entry include a hypothesis, experiment or focused test, observation, and resulting decision. If implementation succeeds immediately, investigate boundary behavior or deliberately perturb a local working copy and restore it; do not invent a failure. Include at least one entry about a security invariant and one about diagnostic privacy or state isolation.

### `REPORT.md`

Provide:

- an artifact inventory;
- the exact test command, exit status, and observed test count;
- a SHA-256 digest for every submitted source, test, and Markdown file except `REPORT.md` itself;
- a compact trace showing frame regions before and after one vulnerable request, with payload bytes redacted or described symbolically;
- a comparison of vulnerable and hardened outcomes for the same boundary-crossing input;
- known limitations and any unresolved failure; and
- the label `LEARNER_CAPTURED_LOCAL_EVIDENCE_FOR_GENERATED_PRACTICE_TASK_ONLY`.

End the report by stating that the submission does not claim official Lab 1 credit, transfer, or course completion.

## Diagnostic prompts

If a boundary test fails, inspect region slices before inspecting the authorization result: which region changed first? If a hardened test passes unexpectedly, ask whether it passed because validation occurred before mutation or because corrupted state was repaired afterward. If two tests influence one another, identify which object outlived a request. If diagnostics expose payload bytes, decide what minimum lengths, reason codes, and integrity flags would still support operations.
