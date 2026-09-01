# Learner notes

## Material and scope

I studied only `LEARNING_TASK.md`, `UNIT_BRIEF.md`, and `SELF_CHECK.md`. The normalized source-record
facts available in those files are limited: the record is classified as an official MIT 6.858 Lab 1
unit and has a catalog-level relationship to Zoobar and buffer-overflow attacks. The frame layout,
Python package, tests, and analysis are newly authored practice material, not official course
content.

Unavailable prerequisites include the official lab specification, starter code, course tests,
course-site material, native build environment, Zoobar environment, and an independent transfer
assessment. I did not fetch or infer them.

## Model translated into invariants

- A new frame has length 24 for every request.
- Data is `[0,16)`, initially zero; role is index 16, initially `0x00`; canary is `[17,24)`,
  initially `FRAMEOK`.
- The policy is exactly `role == 0x01`; it reads but does not mutate the frame.
- Length 16 is the last application-safe copy. Length 17 first reaches role; length 18 first reaches
  canary.
- The 24-byte boundary prevents the emulator from indexing beyond its model. It does not make bytes
  16 through 23 application data.
- A hardened rejection must happen before `_copy_bytes`, not after copying and repairing metadata.
- Results contain metadata only, and frame state must not outlive a request.

## Engineering choices and tradeoffs

I separated type validation, fresh-frame construction, ordered copying, role policy, integrity
observation, and path orchestration. This makes validation order directly inspectable and lets a test
spy on the copy boundary. A single generic copy helper also avoids implementing a special 17-byte
case that merely imitates the expected exploit result.

The hardened path rejects rather than truncates. Rejection is fail-closed and exposes a caller/spec
mismatch; truncation could make different inputs silently equivalent. The vulnerable path retains a
24-byte outer capacity only so the semantic emulator remains bounded.

An immutable `NamedTuple` represents observations. I initially chose a frozen dataclass, but the
prescribed `python3` is Python 3.6.8 and has no standard-library `dataclasses`. `NamedTuple` preserves
named immutable fields and works on that available runtime. Its tuple-like positional construction
is a small API tradeoff, while immutability and field names satisfy the contract.

## Security lessons

The most important result is that a canary and authorization metadata protect different
boundaries. A 17-byte vulnerable request can write `0x01` to role and grant access while the canary
is still exactly `FRAMEOK`. A canary that detects later bytes is not an authorization control and
cannot undo a decision made from a corrupted role.

Validation order is itself a security property. A returned “clean” result is insufficient evidence
if the handler could copy first and repair afterward. The focused test therefore watches whether the
copy function is called and snapshots all 24 bytes of an injected frame.

Fresh per-request allocation prevents a forged role, a damaged canary, or a rejected request from
influencing the next decision. Payload-free observations reduce diagnostic exposure, but exact
lengths and outcomes remain metadata that can disclose usage patterns. A production design should
prefer restricted, retained-for-a-purpose aggregate counters and coarse length buckets.

## Evidence summary

The first full test command failed during import because of the Python 3.6/dataclass mismatch. After
the compatibility revision, the exact prescribed command passed 13 tests. Focused rejection-order,
isolation, and privacy tests also passed. A symbolic metadata-only probe observed vulnerable access
at length 17 with an intact canary, canary change at length 18, hardened rejection at length 17, and
a clean following request.

These are local observations for this generated model. They do not establish native memory safety,
Zoobar security, official Lab 1 completion, learning transfer, or course completion.
